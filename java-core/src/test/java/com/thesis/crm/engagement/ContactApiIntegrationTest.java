package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

/**
 * UC016 — API danh bạ chạy trên Postgres THẬT (pgvector:pg16, cùng image với docker-compose),
 * migration Flyway thật, role runtime {@code crm_app} (KHÔNG phải chủ bảng) — H2 không có RLS nên
 * không dùng được cho bài kiểm cách ly tenant.
 */
class ContactApiIntegrationTest extends EngagementIntegrationTestBase {

    // ── Tạo khách (SCR027) ──────────────────────────────────────────────────────

    @Test
    void taoKhachChuanHoaSoDienThoaiVaGhiDongY() throws Exception {
        JsonNode data = createContact(TENANT_A, """
                {"fullName":"Phạm Minh Tuấn","phone":"0903 111 222","email":"Tuan@Shop.VN",
                 "consentGranted":true}""")
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8)
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
        String first = createdContactId(TENANT_A, """
                {"fullName":"Khách gốc","phone":"0987 000 111"}""");

        JsonNode data = data(createContact(TENANT_A, """
                {"fullName":"Khách nhập lại","phone":"+84 987 000 111"}""")
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8));

        assertThat(data.get("duplicateCandidates")).hasSize(1);
        assertThat(data.get("duplicateCandidates").get(0).get("id").asText()).isEqualTo(first);
    }

    @Test
    void thieuCaSoDienThoaiLanThuThiBaoLoi() throws Exception {
        createContact(TENANT_A, """
                {"fullName":"Không có cách liên hệ"}""")
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.message").value("Phải có ít nhất số điện thoại hoặc địa chỉ thư."));
    }

    @Test
    void soDienThoaiSaiThiBaoLoi() throws Exception {
        createContact(TENANT_A, """
                {"phone":"12345"}""").andExpect(status().isUnprocessableEntity());
    }

    // ── Danh sách, tìm, lọc (SCR026) ────────────────────────────────────────────

    @Test
    void timKhongDauKhongPhanBietHoaThuong() throws Exception {
        String id = createdContactId(TENANT_A, """
                {"fullName":"Nguyễn Thị Ánh Tuyết","email":"tuyet.nguyen@khach.vn"}""");

        for (String q : new String[] {"tuyet", "ÁNH TUYẾT", "nguyen thi", "khach.vn"}) {
            JsonNode items = list(TENANT_A, "q=" + q).get("items");
            assertThat(items.findValuesAsText("id")).as("q=%s", q).contains(id);
        }
    }

    @Test
    void timTheoSoDienThoaiNhieuKieuGo() throws Exception {
        String id = createdContactId(TENANT_A, """
                {"fullName":"Khách điện thoại","phone":"0911 222 333"}""");
        for (String q : new String[] {"0911222333", "+84 911 222", "911.222"}) {
            assertThat(list(TENANT_A, "q=" + q).get("items").findValuesAsText("id")).as("q=%s", q).contains(id);
        }
    }

    @Test
    void macDinhAnHoSoDaGopNhung_locTrangThaiThiThay() throws Exception {
        String keep = createdContactId(TENANT_A, """
                {"fullName":"Bản giữ lại","email":"giu.lai@khach.vn"}""");
        String merged = createdContactId(TENANT_A, """
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
        String yes = createdContactId(TENANT_A, """
                {"fullName":"Đồng ý lọc","email":"loc.dongy@khach.vn","consentGranted":true}""");
        String no = createdContactId(TENANT_A, """
                {"fullName":"Chưa đồng ý lọc","email":"loc.chua@khach.vn"}""");

        assertThat(list(TENANT_A, "q=loc.&hasConsent=true").get("items").findValuesAsText("id"))
                .contains(yes).doesNotContain(no);
    }

    @Test
    void sapXepTheoTenVaPhanTrang() throws Exception {
        for (String n : new String[] {"Zed Sapxep", "An Sapxep", "Minh Sapxep"}) {
            createdContactId(TENANT_A, "{\"fullName\":\"" + n + "\",\"email\":\"" + n.charAt(0) + ".sapxep@khach.vn\"}");
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
        String id = createdContactId(TENANT_A, """
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
        String idOfA = createdContactId(TENANT_A, """
                {"fullName":"Bí mật của A","email":"bimat@a.vn"}""");

        assertThat(list(TENANT_B, "q=bimat").get("items")).isEmpty();
        mvc.perform(get("/api/v1/contacts/" + idOfA).with(as(TENANT_B))).andExpect(status().isNotFound());

        // B tạo trùng thư với khách của A: KHÔNG được gợi ý hợp nhất sang dữ liệu của A
        JsonNode data = data(createContact(TENANT_B, """
                {"fullName":"Khách của B","email":"bimat@a.vn"}""")
                .andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8));
        assertThat(data.get("duplicateCandidates")).isEmpty();
    }

    @Test
    void headerTenantGiaKhongDoiDuocTenantCuaJwt() throws Exception {
        String idOfB = createdContactId(TENANT_B, """
                {"fullName":"Khách riêng của B","email":"rieng@b.vn"}""");
        // JWT của A + header giả trỏ sang B: tenant phải lấy từ JWT, không từ header (luật 1)
        String res = mvc.perform(get("/api/v1/contacts?q=rieng").with(as(TENANT_A))
                        .header("X-Tenant-Id", TENANT_B.toString()))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8);
        assertThat(data(res).get("items").findValuesAsText("id")).doesNotContain(idOfB);
    }

    @Test
    void rlsTrongCsdlChanTheoTenant_khongPhuThuocCauSql() throws Exception {
        String idOfA = createdContactId(TENANT_A, """
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

    // ── Hồi quy rà soát 06/10 ───────────────────────────────────────────────────

    @Test
    void khachDoNoiKhacGhiVaoCsdlVanTimDuoc() throws Exception {
        // UC011 (tiếp nhận tin, Dev A) hay script khác ghi thẳng bảng — không qua ContactService.
        // Trước đây search_text để trống nên khách này KHÔNG BAO GIỜ tìm ra được.
        UUID id = UUID.randomUUID();
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement("""
                INSERT INTO engagement.contacts (id, tenant_id, full_name, email, primary_channel)
                VALUES (?, ?, 'Đặng Thuỳ Dương', 'duong.widget@khach.vn', 'WEB_WIDGET')""")) {
            ps.setObject(1, id);
            ps.setObject(2, TENANT_A);
            ps.executeUpdate();
        }
        assertThat(list(TENANT_A, "q=thuy duong").get("items").findValuesAsText("id")).contains(id.toString());
    }

    @Test
    void tenGoDangNfdVanTimKhongDauDuoc() throws Exception {
        String nfd = java.text.Normalizer.normalize("Hoàng Yến Nhi", java.text.Normalizer.Form.NFD);
        String id = createdContactId(TENANT_A, "{\"fullName\":\"" + nfd + "\",\"email\":\"yen.nhi@khach.vn\"}");
        assertThat(list(TENANT_A, "q=yen nhi").get("items").findValuesAsText("id")).contains(id);
    }

    @Test
    void timNhieuTuKhongCanLienNhau() throws Exception {
        String id = createdContactId(TENANT_A, """
                {"fullName":"Vũ Quốc Bảo","email":"bao.vu@khach.vn","phone":"0977 888 999"}""");
        // tên và số điện thoại không đứng liền nhau trong chuỗi tìm kiếm
        assertThat(list(TENANT_A, "q=bao 0977888").get("items").findValuesAsText("id")).contains(id);
        assertThat(list(TENANT_A, "q=bao 0911000").get("items").findValuesAsText("id")).doesNotContain(id);
    }

    @Test
    void soDienThoaiGoCaMaQuocGiaLanSo0VanDungVaPhatHienTrung() throws Exception {
        String first = createdContactId(TENANT_A, """
                {"fullName":"Gốc 0","phone":"0966 123 456"}""");
        JsonNode data = data(createContact(TENANT_A, """
                {"fullName":"Gõ +84 0","phone":"+84 0966 123 456"}""")
                .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8));
        assertThat(data.get("contact").get("phone").asText()).isEqualTo("0966123456");
        assertThat(data.get("duplicateCandidates").findValuesAsText("id")).contains(first);
    }

    @Test
    void dongYDuocGhiNhatKyKiemToan() throws Exception {
        String id = createdContactId(TENANT_A, """
                {"fullName":"Kiểm toán đồng ý","email":"kiem.toan@khach.vn","consentGranted":true}""");
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement("""
                SELECT actor_type, actor_user_id, action, after_data ->> 'consentSource'
                FROM platform.audit_logs WHERE entity_type = 'CONTACT' AND entity_id = ?""")) {
            ps.setObject(1, UUID.fromString(id));
            try (ResultSet rs = ps.executeQuery()) {
                assertThat(rs.next()).as("phải có dòng nhật ký kiểm toán").isTrue();
                assertThat(rs.getString(1)).isEqualTo("USER");
                assertThat(rs.getObject(2, UUID.class)).isEqualTo(USER_A);
                assertThat(rs.getString(3)).isEqualTo("CONTACT_CREATED");
                assertThat(rs.getString(4)).isEqualTo("AGENT_MANUAL");
            }
        }
    }

    @Test
    void thamSoSaiKieuThiTra400KhongPhai500() throws Exception {
        mvc.perform(get("/api/v1/contacts?tagId=khong-phai-uuid").with(as(TENANT_A)))
                .andExpect(status().isBadRequest());
        mvc.perform(get("/api/v1/contacts/khong-phai-uuid").with(as(TENANT_A)))
                .andExpect(status().isBadRequest());
        mvc.perform(post("/api/v1/contacts").with(as(TENANT_A))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"consentGranted\": \"co\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void loiDuLieuNhapCungMotMaTrangThai() throws Exception {
        // Ba loại lỗi "dữ liệu khách nhập sai" phải cùng mã để giao diện xử lý một kiểu
        createContact(TENANT_A, "{\"fullName\":\"x\"}").andExpect(status().isUnprocessableEntity());
        createContact(TENANT_A, "{\"phone\":\"12345\"}").andExpect(status().isUnprocessableEntity());
        createContact(TENANT_A, "{\"email\":\"khong-hop-le\"}").andExpect(status().isUnprocessableEntity());
    }

    @Test
    void locTheoThe() throws Exception {
        String tagged = createdContactId(TENANT_A, """
                {"fullName":"Có thẻ VIP","email":"co.the@khach.vn"}""");
        String plain = createdContactId(TENANT_A, """
                {"fullName":"Không thẻ","email":"khong.the@khach.vn"}""");
        UUID tag = UUID.randomUUID();
        try (Connection c = owner()) {
            try (PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO engagement.tags (id, tenant_id, name) VALUES (?, ?, 'VIP-loc')")) {
                ps.setObject(1, tag);
                ps.setObject(2, TENANT_A);
                ps.executeUpdate();
            }
            try (PreparedStatement ps = c.prepareStatement(
                    "INSERT INTO engagement.contact_tags (contact_id, tag_id, tenant_id) VALUES (?, ?, ?)")) {
                ps.setObject(1, UUID.fromString(tagged));
                ps.setObject(2, tag);
                ps.setObject(3, TENANT_A);
                ps.executeUpdate();
            }
        }
        JsonNode items = list(TENANT_A, "tagId=" + tag).get("items");
        assertThat(items.findValuesAsText("id")).contains(tagged).doesNotContain(plain);
        assertThat(items.get(0).get("tags").get(0).get("name").asText()).isEqualTo("VIP-loc");
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

    private JsonNode list(UUID tenantId, String query) throws Exception {
        String res = mvc.perform(get("/api/v1/contacts?" + query).with(as(tenantId)))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8);
        return data(res);
    }
}
