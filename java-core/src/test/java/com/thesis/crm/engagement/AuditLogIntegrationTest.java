package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.audit.AuditPiiCipher;
import com.thesis.crm.platform.repository.AuditLogRepository;
import com.thesis.crm.security.TenantTransactionScope;
import jakarta.persistence.EntityManager;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * UC040 — nhật ký kiểm toán: xem danh sách đã che, "xem đầy đủ" kèm lý do và chính lần xem được ghi lại.
 * Hai doanh nghiệp riêng (X, Y) để số dòng không lẫn với nhật ký các test khác sinh ra.
 */
class AuditLogIntegrationTest extends EngagementIntegrationTestBase {

    private static final UUID TENANT_X = UUID.randomUUID();
    private static final UUID TENANT_Y = UUID.randomUUID();
    private static final UUID ADMIN_X = UUID.randomUUID();
    private static final UUID AGENT_X = UUID.randomUUID();
    private static final UUID ADMIN_Y = UUID.randomUUID();
    private static boolean seededAudit;

    @Autowired TransactionTemplate tx;
    @Autowired TenantTransactionScope scope;
    @Autowired AuditLogWriter writer;
    @Autowired AuditLogRepository repo;
    @Autowired EntityManager em;
    @Autowired ObjectMapper mapper;

    @BeforeEach
    void seedAudit() throws Exception {
        if (seededAudit) {
            return;
        }
        seededAudit = true;
        try (Connection c = owner()) {
            for (UUID t : new UUID[] {TENANT_X, TENANT_Y}) {
                exec(c, "INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES (?, 'DN kiểm toán', ?, ?)",
                        t, "kt-" + t.toString().substring(0, 8), "kt@" + t.toString().substring(0, 8) + ".vn");
            }
            for (Object[] u : new Object[][] {{ADMIN_X, TENANT_X, "admin.x@kt.vn"}, {AGENT_X, TENANT_X, "agent.x@kt.vn"},
                    {ADMIN_Y, TENANT_Y, "admin.y@kt.vn"}}) {
                exec(c, """
                        INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                        VALUES (?, ?, ?, 'x', 'Người kiểm toán', 'ACTIVE')""", u[0], u[1], u[2]);
            }
        }
    }

    // ── xem danh sách ───────────────────────────────────────────────────────────

    @Test
    void quanTri_thayNhatKyDoanhNghiepMinh_moiNhatTruoc_khongLanDoanhNghiepKhac() throws Exception {
        UUID e = UUID.randomUUID();
        ghi(TENANT_X, ADMIN_X, "TEST_LIST_1", e);
        ghi(TENANT_X, ADMIN_X, "TEST_LIST_2", e);
        ghi(TENANT_Y, ADMIN_Y, "TEST_LIST_Y", e);

        JsonNode items = data(body(mvc.perform(get("/api/v1/audit-logs").param("entityType", "LEAD")
                .with(admin(TENANT_X, ADMIN_X))).andExpect(status().isOk()))).get("items");
        java.util.List<String> actions = new java.util.ArrayList<>();
        items.forEach(i -> actions.add(i.get("action").asText()));
        assertThat(actions).doesNotContain("TEST_LIST_Y");
        // Mới nhất trước — so vị trí tương đối: test khác cùng lớp cũng ghi LEAD cho doanh nghiệp X
        assertThat(actions.indexOf("TEST_LIST_2")).isLessThan(actions.indexOf("TEST_LIST_1"));
        JsonNode moi = items.get(actions.indexOf("TEST_LIST_2"));
        assertThat(moi.get("actorEmail").asText()).isEqualTo("admin.x@kt.vn");
        assertThat(moi.get("masked").asBoolean()).isFalse();
    }

    @Test
    void locTheoHanhDong_vaMucNghiemTrong_vaPhanTrang() throws Exception {
        UUID e = UUID.randomUUID();
        for (int i = 0; i < 3; i++) {
            ghi(TENANT_X, ADMIN_X, "TEST_PAGE", e);
        }
        tx.execute(s -> {
            scope.apply(TENANT_X);
            writer.recordSystemAction(TENANT_X, "TEST_CRIT", "WIDGET", null, "CRITICAL", Map.of("k", 1));
            return null;
        });

        JsonNode trang = data(body(mvc.perform(get("/api/v1/audit-logs").param("action", "TEST_PAGE")
                .param("size", "2").with(admin(TENANT_X, ADMIN_X))).andExpect(status().isOk())));
        assertThat(trang.get("items")).hasSize(2);
        assertThat(trang.get("totalItems").asLong()).isEqualTo(3);
        assertThat(trang.get("totalPages").asInt()).isEqualTo(2);

        // Cũ nhất trước — dòng đầu của trang theo chiều tăng là dòng cuối của chiều giảm
        JsonNode tang = data(body(mvc.perform(get("/api/v1/audit-logs").param("action", "TEST_PAGE")
                .param("sort", "occurredAt").param("size", "3").with(admin(TENANT_X, ADMIN_X))))).get("items");
        JsonNode giam = data(body(mvc.perform(get("/api/v1/audit-logs").param("action", "TEST_PAGE")
                .param("size", "3").with(admin(TENANT_X, ADMIN_X))))).get("items");
        assertThat(tang.get(0).get("id").asLong()).isEqualTo(giam.get(2).get("id").asLong());

        JsonNode crit = data(body(mvc.perform(get("/api/v1/audit-logs").param("severity", "CRITICAL")
                .with(admin(TENANT_X, ADMIN_X))).andExpect(status().isOk()))).get("items");
        assertThat(crit).isNotEmpty();
        crit.forEach(i -> assertThat(i.get("severity").asText()).isEqualTo("CRITICAL"));
        assertThat(crit.get(0).get("actorType").asText()).isEqualTo("SYSTEM");
        assertThat(crit.get(0).get("actorEmail").isNull()).isTrue();
    }

    @Test
    void timKiem_theoHanhDong_hoacEmailNguoiLam_khongPhanBietHoaThuong() throws Exception {
        ghi(TENANT_X, ADMIN_X, "TEST_SEARCH_ABC", UUID.randomUUID());

        assertThat(data(body(mvc.perform(get("/api/v1/audit-logs").param("q", "search_abc")
                .with(admin(TENANT_X, ADMIN_X))))).get("totalItems").asLong()).isEqualTo(1);
        // Theo email người làm — mọi dòng của ADMIN_X, không lẫn AGENT_X
        JsonNode theoEmail = data(body(mvc.perform(get("/api/v1/audit-logs").param("q", "ADMIN.X@")
                .param("size", "100").with(admin(TENANT_X, ADMIN_X))))).get("items");
        assertThat(theoEmail).isNotEmpty();
        theoEmail.forEach(i -> assertThat(i.get("actorEmail").asText()).isEqualTo("admin.x@kt.vn"));
        // Ký tự đặc biệt của LIKE được tìm đúng nghĩa đen, không thành ký tự đại diện
        assertThat(data(body(mvc.perform(get("/api/v1/audit-logs").param("q", "%")
                .with(admin(TENANT_X, ADMIN_X))))).get("totalItems").asLong()).isZero();
    }

    @Test
    void locTheoNgay_tinhTheoMuiGioDoanhNghiep() throws Exception {
        ghi(TENANT_X, ADMIN_X, "TEST_DATE", UUID.randomUUID());
        String homNay = java.time.LocalDate.now(java.time.ZoneId.of("Asia/Ho_Chi_Minh")).toString();
        String homQua = java.time.LocalDate.now(java.time.ZoneId.of("Asia/Ho_Chi_Minh")).minusDays(1).toString();

        assertThat(data(body(mvc.perform(get("/api/v1/audit-logs").param("action", "TEST_DATE")
                .param("from", homNay).param("to", homNay).with(admin(TENANT_X, ADMIN_X)))))
                .get("totalItems").asLong()).isEqualTo(1);
        assertThat(data(body(mvc.perform(get("/api/v1/audit-logs").param("action", "TEST_DATE")
                .param("to", homQua).with(admin(TENANT_X, ADMIN_X)))))
                .get("totalItems").asLong()).isZero();
    }

    @Test
    void nhanVien_bi403_caXemLanXemDayDu() throws Exception {
        mvc.perform(get("/api/v1/audit-logs").with(asUser(TENANT_X, AGENT_X, "AGENT")))
                .andExpect(status().isForbidden());
        long id = ghiCoDuLieuCaNhan();
        mvc.perform(post("/api/v1/audit-logs/" + id + "/reveal").with(asUser(TENANT_X, AGENT_X, "AGENT"))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"reason\":\"Kiểm tra khiếu nại của khách\"}"))
                .andExpect(status().isForbidden());
    }

    // ── che khi ghi + xem đầy đủ ────────────────────────────────────────────────

    @Test
    void duLieuCaNhan_ghiBanChe_banGocMaHoa_CSDLKhongCoBanRo() throws Exception {
        long id = ghiCoDuLieuCaNhan();

        assertThat(motCot("SELECT after_data->>'phone' FROM platform.audit_logs WHERE id = ?", id)).isEqualTo("091***678");
        assertThat(motCot("SELECT after_data->>'fullName' FROM platform.audit_logs WHERE id = ?", id)).isEqualTo("T*** V*** A***");
        assertThat(motCot("SELECT after_data->>'status' FROM platform.audit_logs WHERE id = ?", id)).isEqualTo("ACTIVE");
        assertThat(motCot("SELECT pii_key_id FROM platform.audit_logs WHERE id = ?", id)).isEqualTo("test-k1");
        // Toàn bộ dòng (kể cả khối mã hoá) không có số điện thoại thật ở dạng rõ
        assertThat(motCot("SELECT a::text || encode(pii_encrypted, 'escape') FROM platform.audit_logs a WHERE id = ?", id))
                .doesNotContain("0912345678").doesNotContain("Trần Văn An");

        JsonNode dong = timTrongDanhSach(id);
        assertThat(dong.get("containsPersonalData").asBoolean()).isTrue();
        assertThat(dong.get("masked").asBoolean()).isTrue();
        assertThat(dong.get("after").get("phone").asText()).isEqualTo("091***678");
    }

    @Test
    void xemDayDu_thieuLyDo_422() throws Exception {
        long id = ghiCoDuLieuCaNhan();
        mvc.perform(post("/api/v1/audit-logs/" + id + "/reveal").with(admin(TENANT_X, ADMIN_X))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"reason\":\"   xem   \"}"))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.code").value("REASON_REQUIRED"));
        mvc.perform(post("/api/v1/audit-logs/" + id + "/reveal").with(admin(TENANT_X, ADMIN_X))
                        .contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isUnprocessableEntity());
        assertThat(motCot("SELECT count(*) FROM platform.audit_logs WHERE action = 'AUDIT_LOG_REVEALED' "
                + "AND after_data->>'auditLogId' = ?", String.valueOf(id))).isEqualTo("0");
    }

    @Test
    void xemDayDu_traBanGoc_vaGhiThemMotDongKemLyDo() throws Exception {
        long id = ghiCoDuLieuCaNhan();
        String lyDo = "Khách khiếu nại bị đổi số điện thoại";

        JsonNode full = data(body(mvc.perform(post("/api/v1/audit-logs/" + id + "/reveal").with(admin(TENANT_X, ADMIN_X))
                        .header("X-Forwarded-For", "203.0.113.7")
                        .contentType(MediaType.APPLICATION_JSON).content("{\"reason\":\"" + lyDo + "\"}"))
                .andExpect(status().isOk())));
        assertThat(full.get("masked").asBoolean()).isFalse();
        assertThat(full.get("after").get("phone").asText()).isEqualTo("0912345678");
        assertThat(full.get("after").get("fullName").asText()).isEqualTo("Trần Văn An");
        assertThat(full.get("before").get("phone").asText()).isEqualTo("0987000111");

        // Chính lần xem sinh một dòng — ai, dòng nào, lý do gì; KHÔNG chứa dữ liệu cá nhân
        Map<String, String> dong = motDong("""
                SELECT actor_user_id::text, actor_email, reason, severity, host(ip_address) AS ip, contains_personal_data,
                       after_data::text AS after
                FROM platform.audit_logs WHERE action = 'AUDIT_LOG_REVEALED' AND after_data->>'auditLogId' = ?""",
                String.valueOf(id));
        assertThat(dong.get("actor_user_id")).isEqualTo(ADMIN_X.toString());
        assertThat(dong.get("actor_email")).isEqualTo("admin.x@kt.vn");
        assertThat(dong.get("reason")).isEqualTo(lyDo);
        assertThat(dong.get("severity")).isEqualTo("WARNING");
        assertThat(dong.get("ip")).isEqualTo("203.0.113.7");
        assertThat(dong.get("contains_personal_data")).isEqualTo("f");
        assertThat(dong.get("after")).doesNotContain("0912345678");
    }

    @Test
    void xemDayDu_dongCuaDoanhNghiepKhac_404() throws Exception {
        long idCuaY = tx.execute(s -> {
            scope.apply(TENANT_Y);
            writer.recordWithPersonalData(TENANT_Y, ADMIN_Y, "CONTACT_MERGED", "CONTACT", UUID.randomUUID(),
                    null, Map.of("phone", "0900000001"), Set.of("phone"));
            return idMoiNhat(TENANT_Y);
        });
        mvc.perform(post("/api/v1/audit-logs/" + idCuaY + "/reveal").with(admin(TENANT_X, ADMIN_X))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"reason\":\"Thử mở dòng của người khác\"}"))
                .andExpect(status().isNotFound());
    }

    @Test
    void chuaCauHinhKhoa_boPhanTruocSau_vanGhiPhanConLai() throws Exception {
        AuditLogWriter khongKhoa = new AuditLogWriter(repo, mapper, em, new AuditPiiCipher("", "k1"));
        UUID e = UUID.randomUUID();
        tx.execute(s -> {
            scope.apply(TENANT_X);
            khongKhoa.recordWithPersonalData(TENANT_X, ADMIN_X, "TEST_NO_KEY", "CONTACT", e,
                    null, Map.of("phone", "0911111111"), Set.of("phone"));
            return null;
        });
        Map<String, String> dong = motDong("""
                SELECT action, contains_personal_data, (after_data IS NULL) AS khong_after,
                       (pii_encrypted IS NULL) AS khong_ma
                FROM platform.audit_logs WHERE entity_id = ?::uuid""", e.toString());
        assertThat(dong.get("action")).isEqualTo("TEST_NO_KEY");
        assertThat(dong.get("contains_personal_data")).isEqualTo("t");
        assertThat(dong.get("khong_after")).isEqualTo("t");
        assertThat(dong.get("khong_ma")).isEqualTo("t");
    }

    @Test
    void maHoa_saiKhoaHoacDuLieuBiSua_baoLoiKhongGiaiMaSai() {
        AuditPiiCipher c = new AuditPiiCipher("AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=", "k1");
        byte[] ma = c.encrypt("{\"phone\":\"0912345678\"}").orElseThrow();
        assertThat(c.decrypt(ma, "k1")).contains("0912345678");
        assertThatThrownBy(() -> c.decrypt(ma, "k0")).hasMessageContaining("khoá");
        ma[ma.length - 1] ^= 1;   // sửa một bit → thẻ xác thực GCM không khớp
        assertThatThrownBy(() -> c.decrypt(ma, "k1")).hasMessageContaining("bị sửa");
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private static JwtRequestPostProcessor admin(UUID tenantId, UUID userId) {
        return asUser(tenantId, userId, "TENANT_ADMIN");
    }

    private void ghi(UUID tenantId, UUID userId, String action, UUID entityId) {
        tx.execute(s -> {
            scope.apply(tenantId);
            writer.recordUserAction(tenantId, userId, action, "LEAD", entityId, Map.of("status", "NEW"));
            return null;
        });
    }

    /** Một dòng "gộp khách" có số điện thoại + tên trước/sau — dữ liệu cá nhân thật cần che. */
    private long ghiCoDuLieuCaNhan() {
        return tx.execute(s -> {
            scope.apply(TENANT_X);
            Map<String, Object> truoc = new LinkedHashMap<>();
            truoc.put("phone", "0987000111");
            Map<String, Object> sau = new LinkedHashMap<>();
            sau.put("phone", "0912345678");
            sau.put("fullName", "Trần Văn An");
            sau.put("status", "ACTIVE");
            writer.recordWithPersonalData(TENANT_X, ADMIN_X, "CONTACT_MERGED", "CONTACT", UUID.randomUUID(),
                    truoc, sau, Set.of("phone", "fullName"));
            return idMoiNhat(TENANT_X);
        });
    }

    private long idMoiNhat(UUID tenantId) {
        return em.createQuery("SELECT max(a.id) FROM AuditLog a WHERE a.tenantId = :t", Long.class)
                .setParameter("t", tenantId).getSingleResult();
    }

    private JsonNode timTrongDanhSach(long id) throws Exception {
        JsonNode items = data(body(mvc.perform(get("/api/v1/audit-logs").param("action", "CONTACT_MERGED")
                .param("size", "100").with(admin(TENANT_X, ADMIN_X))).andExpect(status().isOk()))).get("items");
        for (JsonNode i : items) {
            if (i.get("id").asLong() == id) {
                return i;
            }
        }
        throw new AssertionError("Không thấy dòng " + id + " trong danh sách");
    }

    private static String body(org.springframework.test.web.servlet.ResultActions r) throws Exception {
        return r.andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
    }

    private static String motCot(String query, Object... args) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(query)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString(1) : null;
            }
        }
    }

    private static Map<String, String> motDong(String query, Object... args) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(query)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            try (ResultSet rs = ps.executeQuery()) {
                assertThat(rs.next()).as("phải có đúng một dòng").isTrue();
                Map<String, String> out = new LinkedHashMap<>();
                for (int i = 1; i <= rs.getMetaData().getColumnCount(); i++) {
                    out.put(rs.getMetaData().getColumnLabel(i), rs.getString(i));
                }
                return out;
            }
        }
    }

    private static void exec(Connection c, String query, Object... args) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement(query)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            ps.executeUpdate();
        }
    }
}
