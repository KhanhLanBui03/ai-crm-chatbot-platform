package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.ResultActions;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;
import org.testcontainers.utility.MountableFile;

/**
 * UC016 — API danh bạ chạy trên Postgres THẬT (pgvector:pg16, cùng image với docker-compose),
 * migration Flyway thật, role runtime {@code crm_app} (KHÔNG phải chủ bảng) — H2 không có RLS nên
 * không dùng được cho bài kiểm cách ly tenant.
 */
@SpringBootTest
@AutoConfigureMockMvc
class ContactApiIntegrationTest {

    static final PostgreSQLContainer<?> PG = new PostgreSQLContainer<>(
            DockerImageName.parse("pgvector/pgvector:pg16").asCompatibleSubstituteFor("postgres"))
            .withDatabaseName("thesis_crm")
            .withUsername("crm_owner")
            .withPassword("changeme")
            // Cùng script khởi tạo với docker-compose: tạo role crm_app + extension
            .withCopyFileToContainer(
                    MountableFile.forHostPath(Path.of("..", "scripts", "init-db.sql").toAbsolutePath()),
                    "/docker-entrypoint-initdb.d/00-init.sql");

    static {
        PG.start();
    }

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", () -> "crm_app");
        r.add("spring.datasource.password", () -> "changeme");
        r.add("spring.flyway.user", () -> "crm_owner");
        r.add("spring.flyway.password", () -> "changeme");
        r.add("eureka.client.enabled", () -> "false");
    }

    static final UUID TENANT_A = UUID.randomUUID();
    static final UUID TENANT_B = UUID.randomUUID();

    @Autowired MockMvc mvc;
    @Autowired ObjectMapper json;

    private static boolean seeded;

    /**
     * Chạy SAU khi Spring đã khởi động (Flyway đã tạo bảng) — {@code @BeforeAll} tĩnh chạy trước
     * context nên chưa có bảng. Cờ tĩnh để chỉ seed một lần cho cả lớp.
     */
    @BeforeEach
    void seedTenants() throws Exception {
        if (seeded) {
            return;
        }
        seeded = true;
        // crm_owner là superuser của container nên ghi được platform.tenants bất chấp RLS
        try (Connection c = owner()) {
            for (UUID t : new UUID[] {TENANT_A, TENANT_B}) {
                try (PreparedStatement ps = c.prepareStatement(
                        "INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES (?, ?, ?, ?)")) {
                    ps.setObject(1, t);
                    ps.setString(2, "DN " + t);
                    ps.setString(3, "dn-" + t.toString().substring(0, 8));
                    ps.setString(4, "admin@" + t.toString().substring(0, 8) + ".vn");
                    ps.executeUpdate();
                }
            }
        }
    }

    // ── Tạo khách (SCR027) ──────────────────────────────────────────────────────

    @Test
    void taoKhachChuanHoaSoDienThoaiVaGhiDongY() throws Exception {
        JsonNode data = create(TENANT_A, """
                {"fullName":"Phạm Minh Tuấn","phone":"0903 111 222","email":"Tuan@Shop.VN",
                 "consentGranted":true}""")
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString()
                .transform(this::data);

        JsonNode c = data.get("contact");
        assertThat(c.get("phone").asText()).isEqualTo("0903111222");
        assertThat(c.get("email").asText()).isEqualTo("tuan@shop.vn");
        assertThat(c.get("primaryChannel").asText()).isEqualTo("PHONE");
        assertThat(c.get("status").asText()).isEqualTo("ACTIVE");
        assertThat(c.get("consentGranted").asBoolean()).isTrue();
        assertThat(c.get("consentAt").isNull()).isFalse();
        assertThat(c.get("conversationCount").asInt()).isZero();
        assertThat(c.get("openLeadCount").asInt()).isZero();
        assertThat(c.get("channelIdentities")).isEmpty();
        assertThat(data.get("duplicateCandidates")).isEmpty();
    }

    @Test
    void trungSoDienThoaiVanTaoVaGoiYHopNhat() throws Exception {
        String first = createdId(TENANT_A, """
                {"fullName":"Khách gốc","phone":"0987 000 111"}""");

        JsonNode data = data(create(TENANT_A, """
                {"fullName":"Khách nhập lại","phone":"+84 987 000 111"}""")
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString());

        assertThat(data.get("duplicateCandidates")).hasSize(1);
        assertThat(data.get("duplicateCandidates").get(0).get("id").asText()).isEqualTo(first);
    }

    @Test
    void thieuCaSoDienThoaiLanThuThiBaoLoi() throws Exception {
        create(TENANT_A, """
                {"fullName":"Không có cách liên hệ"}""")
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.message").value("Phải có ít nhất số điện thoại hoặc địa chỉ thư."));
    }

    @Test
    void soDienThoaiSaiThiBaoLoi() throws Exception {
        create(TENANT_A, """
                {"phone":"12345"}""").andExpect(status().isBadRequest());
    }

    // ── Danh sách, tìm, lọc (SCR026) ────────────────────────────────────────────

    @Test
    void timKhongDauKhongPhanBietHoaThuong() throws Exception {
        String id = createdId(TENANT_A, """
                {"fullName":"Nguyễn Thị Ánh Tuyết","email":"tuyet.nguyen@khach.vn"}""");

        for (String q : new String[] {"tuyet", "ÁNH TUYẾT", "nguyen thi", "khach.vn"}) {
            JsonNode items = list(TENANT_A, "q=" + q).get("items");
            assertThat(items.findValuesAsText("id")).as("q=%s", q).contains(id);
        }
    }

    @Test
    void timTheoSoDienThoaiNhieuKieuGo() throws Exception {
        String id = createdId(TENANT_A, """
                {"fullName":"Khách điện thoại","phone":"0911 222 333"}""");
        for (String q : new String[] {"0911222333", "+84 911 222", "911.222"}) {
            assertThat(list(TENANT_A, "q=" + q).get("items").findValuesAsText("id")).as("q=%s", q).contains(id);
        }
    }

    @Test
    void macDinhAnHoSoDaGopNhung_locTrangThaiThiThay() throws Exception {
        String keep = createdId(TENANT_A, """
                {"fullName":"Bản giữ lại","email":"giu.lai@khach.vn"}""");
        String merged = createdId(TENANT_A, """
                {"fullName":"Bản đã gộp","email":"da.gop@khach.vn"}""");
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "UPDATE engagement.contacts SET status='MERGED', merged_into_contact_id=? WHERE id=?")) {
            ps.setObject(1, UUID.fromString(keep));
            ps.setObject(2, UUID.fromString(merged));
            ps.executeUpdate();
        }

        assertThat(list(TENANT_A, "q=da.gop").get("items").findValuesAsText("id")).doesNotContain(merged);
        assertThat(list(TENANT_A, "q=da.gop&status=MERGED").get("items").findValuesAsText("id")).contains(merged);
    }

    @Test
    void locTheoDongY() throws Exception {
        String yes = createdId(TENANT_A, """
                {"fullName":"Đồng ý lọc","email":"loc.dongy@khach.vn","consentGranted":true}""");
        String no = createdId(TENANT_A, """
                {"fullName":"Chưa đồng ý lọc","email":"loc.chua@khach.vn"}""");

        assertThat(list(TENANT_A, "q=loc.&hasConsent=true").get("items").findValuesAsText("id"))
                .contains(yes).doesNotContain(no);
    }

    @Test
    void sapXepTheoTenVaPhanTrang() throws Exception {
        for (String n : new String[] {"Zed Sapxep", "An Sapxep", "Minh Sapxep"}) {
            createdId(TENANT_A, "{\"fullName\":\"" + n + "\",\"email\":\"" + n.charAt(0) + ".sapxep@khach.vn\"}");
        }
        JsonNode page = list(TENANT_A, "q=sapxep&sort=fullName&size=2&page=0");
        assertThat(page.get("items").findValuesAsText("fullName")).containsExactly("An Sapxep", "Minh Sapxep");
        assertThat(page.get("totalItems").asInt()).isEqualTo(3);
        assertThat(page.get("totalPages").asInt()).isEqualTo(2);
    }

    @Test
    void trangThaiLaThiBaoLoi() throws Exception {
        mvc.perform(get("/api/v1/contacts?status=LUNG_TUNG").with(as(TENANT_A)))
                .andExpect(status().isBadRequest());
    }

    // ── Hồ sơ (SCR024) ──────────────────────────────────────────────────────────

    @Test
    void xemHoSo() throws Exception {
        String id = createdId(TENANT_A, """
                {"fullName":"Xem hồ sơ","email":"ho.so@khach.vn","primaryChannel":"ZALO"}""");
        mvc.perform(get("/api/v1/contacts/" + id).with(as(TENANT_A)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.id").value(id))
                .andExpect(jsonPath("$.data.primaryChannel").value("ZALO"))
                .andExpect(jsonPath("$.data.openDealCount").value(0));
    }

    @Test
    void khongCoThiTra404() throws Exception {
        mvc.perform(get("/api/v1/contacts/" + UUID.randomUUID()).with(as(TENANT_A)))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value("Không tìm thấy khách hàng."));
    }

    // ── CÁCH LY TENANT — chỉ số rò rỉ phải bằng 0 ───────────────────────────────

    @Test
    void doanhNghiepKhacKhongThayKhachCuaMinh_quaApi() throws Exception {
        String idOfA = createdId(TENANT_A, """
                {"fullName":"Bí mật của A","email":"bimat@a.vn"}""");

        assertThat(list(TENANT_B, "q=bimat").get("items")).isEmpty();
        mvc.perform(get("/api/v1/contacts/" + idOfA).with(as(TENANT_B))).andExpect(status().isNotFound());

        // B tạo trùng thư với khách của A: KHÔNG được gợi ý hợp nhất sang dữ liệu của A
        JsonNode data = data(create(TENANT_B, """
                {"fullName":"Khách của B","email":"bimat@a.vn"}""")
                .andReturn().getResponse().getContentAsString());
        assertThat(data.get("duplicateCandidates")).isEmpty();
    }

    @Test
    void rlsTrongCsdlChanTheoTenant_khongPhuThuocCauSql() throws Exception {
        String idOfA = createdId(TENANT_A, """
                {"fullName":"Kiểm RLS","email":"rls@a.vn"}""");

        // Lớp thứ hai, độc lập với câu SQL của ứng dụng: crm_app, đặt tenant B, KHÔNG có WHERE tenant_id
        try (Connection c = DriverManager.getConnection(PG.getJdbcUrl(), "crm_app", "changeme")) {
            c.setAutoCommit(false);
            try (PreparedStatement set = c.prepareStatement("SELECT set_config('app.tenant_id', ?, true)")) {
                set.setString(1, TENANT_B.toString());
                set.execute();
            }
            try (PreparedStatement ps = c.prepareStatement("SELECT count(*) FROM engagement.contacts WHERE id = ?")) {
                ps.setObject(1, UUID.fromString(idOfA));
                try (ResultSet rs = ps.executeQuery()) {
                    rs.next();
                    assertThat(rs.getInt(1)).as("RLS phải giấu khách của A khỏi B").isZero();
                }
            }
            c.rollback();
        }
    }

    // ── Hợp nhất & xác thực ─────────────────────────────────────────────────────

    @Test
    void hopNhatChuaHoTroTra501() throws Exception {
        mvc.perform(post("/api/v1/contacts/" + UUID.randomUUID() + "/merge").with(as(TENANT_A))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"mergedContactId\":\"" + UUID.randomUUID() + "\"}"))
                .andExpect(status().isNotImplemented())
                .andExpect(jsonPath("$.message").value("Chức năng hợp nhất khách hàng chưa được hỗ trợ ở phiên bản này."));
    }

    @Test
    void thieuTenantTrongJwtThiTra401() throws Exception {
        mvc.perform(get("/api/v1/contacts").with(jwt().jwt(j -> j.subject(UUID.randomUUID().toString()))))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void khongDangNhapThiBiChan() throws Exception {
        mvc.perform(get("/api/v1/contacts")).andExpect(status().isUnauthorized());
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private static JwtRequestPostProcessor as(UUID tenantId) {
        return jwt().jwt(j -> j.subject(UUID.randomUUID().toString())
                .claim("tenant_id", tenantId.toString())
                .claim("role", "TENANT_ADMIN"));
    }

    private ResultActions create(UUID tenantId, String body) throws Exception {
        return mvc.perform(post("/api/v1/contacts").with(as(tenantId))
                .contentType(MediaType.APPLICATION_JSON).content(body));
    }

    private String createdId(UUID tenantId, String body) throws Exception {
        String res = create(tenantId, body).andExpect(status().isCreated()).andReturn().getResponse().getContentAsString();
        return data(res).get("contact").get("id").asText();
    }

    private JsonNode list(UUID tenantId, String query) throws Exception {
        String res = mvc.perform(get("/api/v1/contacts?" + query).with(as(tenantId)))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString();
        return data(res);
    }

    private JsonNode data(String body) {
        try {
            return json.readTree(body).get("data");
        } catch (Exception e) {
            throw new IllegalStateException(body, e);
        }
    }

    private static Connection owner() throws Exception {
        return DriverManager.getConnection(PG.getJdbcUrl(), "crm_owner", "changeme");
    }
}
