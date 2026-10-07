package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;
import org.springframework.test.web.servlet.ResultActions;

/**
 * UC032 — Quản lý Lead. Đặt trong gói {@code engagement} để dùng chung nền Postgres/Redis thật của
 * {@link EngagementIntegrationTestBase} (lớp nền không public).
 *
 * <p>Mỗi test tự tạo khách hàng riêng — luật "một khách một lead mở" làm các test dùng chung khách
 * giẫm chân nhau.
 */
class LeadIntegrationTest extends EngagementIntegrationTestBase {

    static final UUID TENANT_L = UUID.randomUUID();
    static final UUID TENANT_M = UUID.randomUUID();
    static final UUID ADMIN_L = UUID.randomUUID();
    static final UUID SALE_1 = UUID.randomUUID();
    static final UUID SALE_2 = UUID.randomUUID();
    static final UUID SALE_NGHI = UUID.randomUUID();     // đã ngừng hoạt động
    static final UUID ADMIN_M = UUID.randomUUID();
    static final UUID CHANNEL_L = UUID.randomUUID();

    private static boolean seededLead;

    @BeforeEach
    void seedLead() throws Exception {
        if (seededLead) {
            return;
        }
        seededLead = true;
        try (Connection c = owner()) {
            for (UUID t : new UUID[] {TENANT_L, TENANT_M}) {
                exec(c, "INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES (?, 'DN lead', ?, ?)",
                        t, "l-" + t.toString().substring(0, 8), "a@" + t.toString().substring(0, 8) + ".vn");
            }
            for (Object[] u : new Object[][] {{ADMIN_L, TENANT_L, "Quản trị L", "ACTIVE"},
                    {SALE_1, TENANT_L, "Lan Sale", "ACTIVE"}, {SALE_2, TENANT_L, "Minh Sale", "ACTIVE"},
                    {SALE_NGHI, TENANT_L, "Đã nghỉ", "DISABLED"}, {ADMIN_M, TENANT_M, "Quản trị M", "ACTIVE"}}) {
                exec(c, """
                        INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                        VALUES (?, ?, ?, 'x', ?, ?)""", u[0], u[1], u[0].toString().substring(0, 8) + "@l.vn", u[2], u[3]);
            }
            exec(c, "INSERT INTO engagement.channels (id, tenant_id, type, name, status) VALUES (?, ?, 'ZALO', 'Zalo', 'ACTIVE')",
                    CHANNEL_L, TENANT_L);
        }
    }

    // ── tạo ─────────────────────────────────────────────────────────────────────

    @Test
    void taoTuTrangLead_nguoiTaoPhuTrach_nguonThuCong_vaGhiNhatKy() throws Exception {
        UUID k = khach(TENANT_L, "Nguyễn Văn Tạo", "0901000001");
        JsonNode lead = data(taoLead(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"interestedProduct\":\" Gói Pro \","
                + "\"budgetMin\":1000000,\"budgetMax\":5000000,\"urgency\":\"HIGH\"}")
                .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(lead.get("source").asText()).isEqualTo("MANUAL");
        assertThat(lead.get("status").asText()).isEqualTo("NEW");
        assertThat(lead.get("ownerUserId").asText()).isEqualTo(SALE_1.toString());
        assertThat(lead.get("ownerName").asText()).isEqualTo("Lan Sale");
        assertThat(lead.get("contactName").asText()).isEqualTo("Nguyễn Văn Tạo");
        assertThat(lead.get("interestedProduct").asText()).isEqualTo("Gói Pro");
        assertThat(lead.get("currentScore").isNull()).isTrue();
        assertThat(sql("SELECT action || ':' || (after_data->>'via') FROM platform.audit_logs WHERE entity_id = ?",
                UUID.fromString(lead.get("id").asText()))).containsExactly("LEAD_CREATED:LEADS_PAGE");
    }

    @Test
    void taoLead_kiemDauVao() throws Exception {
        UUID k = khach(TENANT_L, "Kiểm Đầu Vào", "0901000002");
        taoLead(qtv(), "{}").andExpect(status().isUnprocessableEntity());
        taoLead(qtv(), "{\"contactId\":\"" + UUID.randomUUID() + "\"}").andExpect(status().isNotFound());
        taoLead(qtv(), "{\"contactId\":\"" + k + "\",\"budgetMin\":5,\"budgetMax\":1}")
                .andExpect(status().isUnprocessableEntity());
        taoLead(qtv(), "{\"contactId\":\"" + k + "\",\"urgency\":\"RAT_GAP\"}").andExpect(status().isUnprocessableEntity());
        taoLead(qtv(), "{\"contactId\":\"" + k + "\",\"interestedProduct\":\"" + "x".repeat(201) + "\"}")
                .andExpect(status().isUnprocessableEntity());
        // Người phụ trách đã nghỉ việc
        taoLead(qtv(), "{\"contactId\":\"" + k + "\",\"ownerUserId\":\"" + SALE_NGHI + "\"}")
                .andExpect(status().isUnprocessableEntity());
        // Khách của doanh nghiệp khác không tồn tại với doanh nghiệp này
        UUID khachM = khach(TENANT_M, "Khách M", "0901000003");
        taoLead(qtv(), "{\"contactId\":\"" + khachM + "\"}").andExpect(status().isNotFound());
    }

    @Test
    void nhanVienKhongGiaoChoNguoiKhac_quanTriThiDuoc() throws Exception {
        UUID k = khach(TENANT_L, "Giao Người", "0901000004");
        taoLead(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"ownerUserId\":\"" + SALE_2 + "\"}")
                .andExpect(status().isForbidden());
        JsonNode lead = created(taoLead(qtv(), "{\"contactId\":\"" + k + "\",\"ownerUserId\":\"" + SALE_2 + "\"}"));
        assertThat(lead.get("ownerUserId").asText()).isEqualTo(SALE_2.toString());
    }

    @Test
    void motKhachMotLeadMo_409KemLeadCu_loaiRoiThiTaoMoiDuoc() throws Exception {
        UUID k = khach(TENANT_L, "Trùng Lead", "0901000005");
        String id1 = created(taoLead(nv(SALE_1), "{\"contactId\":\"" + k + "\"}")).get("id").asText();
        String body = taoLead(nv(SALE_2), "{\"contactId\":\"" + k + "\"}").andExpect(status().isConflict())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        JsonNode res = json.readTree(body);
        assertThat(res.get("code").asText()).isEqualTo("LEAD_ALREADY_OPEN");
        assertThat(res.get("message").asText()).contains("Lan Sale");
        assertThat(res.get("data").get("leadId").asText()).isEqualTo(id1);

        sua(nv(SALE_1), id1, "{\"status\":\"DISQUALIFIED\",\"disqualifyReason\":\"NO_NEED\"}").andExpect(status().isOk());
        String id2 = created(taoLead(nv(SALE_2), "{\"contactId\":\"" + k + "\"}")).get("id").asText();
        // Mở lại lead cũ khi khách đã có lead mới → vẫn giữ luật một lead mở
        sua(nv(SALE_1), id1, "{\"status\":\"NEW\"}").andExpect(status().isConflict());
        assertThat(id2).isNotEqualTo(id1);
    }

    @Test
    void chiMucCsdlChanHaiLeadMo_keCaKhiBoQuaApi() throws Exception {
        UUID k = khach(TENANT_L, "Chỉ Mục", "0901000006");
        try (Connection c = owner()) {
            String ins = "INSERT INTO sales.leads (tenant_id, contact_id, source, status) VALUES (?, ?, 'AI_AUTO', ?)";
            exec(c, ins, TENANT_L, k, "CONTACTED");
            exec(c, ins, TENANT_L, k, "DISQUALIFIED");               // lead đã đóng không tính
            assertThatThrownBy(() -> exec(c, ins, TENANT_L, k, "QUALIFIED"))
                    .isInstanceOf(SQLException.class).hasMessageContaining("uq_leads_mot_lead_mo_moi_khach");
        }
    }

    @Test
    void taoTuHopThu_ganHoiThoaiNguon_hoiThoaiBiXoaThiMatLienKet() throws Exception {
        UUID k = khach(TENANT_L, "Khách Hộp Thư", "0901000007");
        UUID khac = khach(TENANT_L, "Khách Khác", "0901000008");
        UUID conv = hoiThoai(k);
        taoLead(nv(SALE_1), "{\"contactId\":\"" + khac + "\",\"sourceConversationId\":\"" + conv + "\"}")
                .andExpect(status().isUnprocessableEntity());
        taoLead(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"sourceConversationId\":\"" + UUID.randomUUID() + "\"}")
                .andExpect(status().isNotFound());
        JsonNode lead = created(taoLead(nv(SALE_1),
                "{\"contactId\":\"" + k + "\",\"sourceConversationId\":\"" + conv + "\"}"));
        String id = lead.get("id").asText();
        assertThat(lead.get("sourceConversationId").asText()).isEqualTo(conv.toString());
        assertThat(sql("SELECT after_data->>'via' FROM platform.audit_logs WHERE entity_id = ?", UUID.fromString(id)))
                .containsExactly("INBOX");

        // UC041 xoá hội thoại → lead còn, chỉ mất liên kết (luồng 6.1)
        try (Connection c = owner()) {
            exec(c, "DELETE FROM engagement.conversations WHERE id = ?", conv);
        }
        JsonNode d = chiTiet(qtv(), id);
        assertThat(d.get("sourceConversationId").isNull()).isTrue();
    }

    // ── quy trình trạng thái ────────────────────────────────────────────────────

    @Test
    void diToiDuocBoBuoc_khongLui_khongTuDatChuyenDeal() throws Exception {
        String id = leadMoi(SALE_1, "Quy Trình", "0901000009");
        assertThat(chiTiet(qtv(), id).get("allowedNextStatuses")).extracting(JsonNode::asText)
                .containsExactly("CONTACTED", "QUALIFIED", "DISQUALIFIED");
        JsonNode d = data(sua(nv(SALE_1), id, "{\"status\":\"QUALIFIED\"}").andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(d.get("status").asText()).isEqualTo("QUALIFIED");

        JsonNode loi = json.readTree(sua(nv(SALE_1), id, "{\"status\":\"CONTACTED\"}")
                .andExpect(status().isUnprocessableEntity()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(loi.get("code").asText()).isEqualTo("INVALID_TRANSITION");
        assertThat(loi.get("message").asText()).contains("Đủ tiềm năng").contains("Đã loại");
        assertThat(loi.get("data").get("allowedNextStatuses")).extracting(JsonNode::asText).containsExactly("DISQUALIFIED");

        JsonNode deal = json.readTree(sua(qtv(), id, "{\"status\":\"CONVERTED\"}")
                .andExpect(status().isUnprocessableEntity()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(deal.get("code").asText()).isEqualTo("CONVERT_VIA_DEAL");
        assertThat(sql("SELECT action || ':' || (after_data->>'from') || '>' || (after_data->>'to') "
                + "FROM platform.audit_logs WHERE entity_id = ? AND action = 'LEAD_STATUS_CHANGED'", UUID.fromString(id)))
                .containsExactly("LEAD_STATUS_CHANGED:NEW>QUALIFIED");
    }

    @Test
    void loaiLead_batBuocLyDoTrongDanhSach_khoaSuaThongTin_moLaiVeMoi() throws Exception {
        String id = leadMoi(SALE_1, "Loại Lead", "0901000010");
        JsonNode thieu = json.readTree(sua(nv(SALE_1), id, "{\"status\":\"DISQUALIFIED\"}")
                .andExpect(status().isUnprocessableEntity()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(thieu.get("code").asText()).isEqualTo("DISQUALIFY_REASON_REQUIRED");
        assertThat(thieu.get("data").get("reasons")).hasSize(6);
        sua(nv(SALE_1), id, "{\"status\":\"DISQUALIFIED\",\"disqualifyReason\":\"vì thích\"}")
                .andExpect(status().isUnprocessableEntity());
        sua(nv(SALE_1), id, "{\"status\":\"CONTACTED\",\"disqualifyReason\":\"NO_BUDGET\"}")
                .andExpect(status().isUnprocessableEntity());

        JsonNode d = data(sua(nv(SALE_1), id, "{\"status\":\"DISQUALIFIED\",\"disqualifyReason\":\"NO_BUDGET\"}")
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(d.get("disqualifyReason").asText()).isEqualTo("NO_BUDGET");
        assertThat(d.get("closedAt").isNull()).isFalse();
        assertThat(d.get("allowedNextStatuses")).extracting(JsonNode::asText).containsExactly("NEW");
        // Đổi lý do khi vẫn đang loại: được; sửa thông tin: phải mở lại trước
        sua(nv(SALE_1), id, "{\"disqualifyReason\":\"SPAM\"}").andExpect(status().isOk());
        sua(nv(SALE_1), id, "{\"interestedProduct\":\"Gói mới\"}").andExpect(status().isConflict());

        JsonNode mo = data(sua(nv(SALE_1), id, "{\"status\":\"NEW\",\"interestedProduct\":\"Gói mới\"}")
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(mo.get("status").asText()).isEqualTo("NEW");
        assertThat(mo.get("disqualifyReason").isNull()).isTrue();
        assertThat(mo.get("closedAt").isNull()).isTrue();
        assertThat(mo.get("interestedProduct").asText()).isEqualTo("Gói mới");
    }

    @Test
    void leadDaChuyenDeal_khongSuaDuoc() throws Exception {
        String id = leadMoi(SALE_1, "Đã Chuyển", "0901000011");
        try (Connection c = owner()) {
            exec(c, "UPDATE sales.leads SET status = 'CONVERTED', converted_at = now() WHERE id = ?", UUID.fromString(id));
        }
        sua(qtv(), id, "{\"interestedProduct\":\"x\"}").andExpect(status().isConflict());
        JsonNode d = chiTiet(qtv(), id);
        assertThat(d.get("allowedNextStatuses")).isEmpty();
        assertThat(d.get("closedAt").isNull()).isFalse();
    }

    // ── quyền ───────────────────────────────────────────────────────────────────

    @Test
    void nhanVienChiSuaLeadCuaMinhHoacChuaAiNhan_suaLeadChuaAiNhanLaTuNhan() throws Exception {
        String cuaLan = leadMoi(SALE_1, "Của Lan", "0901000012");
        JsonNode loi = json.readTree(sua(nv(SALE_2), cuaLan, "{\"status\":\"CONTACTED\"}")
                .andExpect(status().isForbidden()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(loi.get("message").asText()).contains("Lan Sale");
        // Tự giao lead của mình cho đồng nghiệp hoặc bỏ trống: chỉ quản trị viên
        sua(nv(SALE_1), cuaLan, "{\"ownerUserId\":\"" + SALE_2 + "\"}").andExpect(status().isForbidden());
        sua(nv(SALE_1), cuaLan, "{\"ownerUserId\":null}").andExpect(status().isForbidden());
        sua(qtv(), cuaLan, "{\"ownerUserId\":\"" + SALE_NGHI + "\"}").andExpect(status().isUnprocessableEntity());
        JsonNode giao = data(sua(qtv(), cuaLan, "{\"ownerUserId\":\"" + SALE_2 + "\"}").andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(giao.get("ownerName").asText()).isEqualTo("Minh Sale");

        // Quản trị bỏ trống người phụ trách → nhân viên sửa = tự nhận
        sua(qtv(), cuaLan, "{\"ownerUserId\":null}").andExpect(status().isOk());
        JsonNode nhan = data(sua(nv(SALE_1), cuaLan, "{\"urgency\":\"LOW\"}").andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(nhan.get("ownerUserId").asText()).isEqualTo(SALE_1.toString());
        assertThat(sql("SELECT after_data->>'via' FROM platform.audit_logs WHERE entity_id = ? AND action = 'LEAD_ASSIGNED' "
                + "ORDER BY created_at", UUID.fromString(cuaLan))).containsExactly("ADMIN", "ADMIN", "CLAIM");
        // Nhật ký sửa thông tin chỉ có TÊN trường, không có giá trị
        assertThat(sql("SELECT after_data::text FROM platform.audit_logs WHERE entity_id = ? AND action = 'LEAD_UPDATED'",
                UUID.fromString(cuaLan))).singleElement().asString().contains("urgency").doesNotContain("LOW");
    }

    @Test
    void khongDoiGiThiKhongGhiGi() throws Exception {
        String id = leadMoi(SALE_1, "Không Đổi", "0901000013");
        sua(nv(SALE_1), id, "{\"status\":\"NEW\",\"budgetMin\":null}").andExpect(status().isOk());
        assertThat(sql("SELECT action FROM platform.audit_logs WHERE entity_id = ?", UUID.fromString(id)))
                .containsExactly("LEAD_CREATED");
    }

    // ── danh sách, chi tiết, cách ly ────────────────────────────────────────────

    @Test
    void danhSach_diemGiamDanChuaChamXepCuoi_locVaTimKhongDau() throws Exception {
        String thap = leadMoi(SALE_1, "Điểm Thấp Danhsach", "0901000014");
        String cao = leadMoi(SALE_2, "Điểm Cao Danhsach", "0901000015");
        String chua = leadMoi(SALE_1, "Chưa Chấm Danhsach", "0901000016");
        diem(thap, 40);
        diem(cao, 92);
        List<String> ids = ids(danhSach(nv(SALE_2), "q=danhsach"));
        assertThat(ids).containsExactly(cao, thap, chua);
        assertThat(ids(danhSach(nv(SALE_2), "q=diem cao"))).containsExactly(cao);
        assertThat(ids(danhSach(nv(SALE_2), "q=0901000016"))).containsExactly(chua);
        assertThat(ids(danhSach(nv(SALE_2), "q=danhsach&minScore=50"))).containsExactly(cao);
        assertThat(ids(danhSach(nv(SALE_2), "q=danhsach&ownerUserId=" + SALE_1))).containsExactly(thap, chua);
        assertThat(ids(danhSach(nv(SALE_2), "q=danhsach&source=AI_AUTO"))).isEmpty();
        assertThat(ids(danhSach(nv(SALE_2), "q=danhsach&status=NEW"))).hasSize(3);
        danhSachRaw(nv(SALE_2), "status=LAMBAY").andExpect(status().isUnprocessableEntity());
        danhSachRaw(nv(SALE_2), "minScore=101").andExpect(status().isUnprocessableEntity());
    }

    @Test
    void lichSuDiem_moiNhatTruoc_phanBietMoHinhVaBangLuat() throws Exception {
        String id = leadMoi(SALE_1, "Lịch Sử Điểm", "0901000017");
        assertThat(data(mvc.perform(get("/api/v1/leads/" + id + "/scores").with(qtv())).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8))).isEmpty();
        assertThat(chiTiet(qtv(), id).get("latestScore").isNull()).isTrue();
        try (Connection c = owner()) {
            String ins = """
                    INSERT INTO sales.lead_scores (tenant_id, lead_id, contact_id, score, model_version, top_factors, scored_at)
                    SELECT tenant_id, id, contact_id, ?, ?, CAST(? AS jsonb), now() - CAST(? AS interval)
                    FROM sales.leads WHERE id = ?""";
            exec(c, ins, 55, "rule-v1", "[]", "2 days", UUID.fromString(id));
            exec(c, ins, 81, "xgb-2026-10", "[{\"name\":\"hỏi giá\",\"contribution\":0.31}]", "1 hour", UUID.fromString(id));
        }
        JsonNode s = data(mvc.perform(get("/api/v1/leads/" + id + "/scores").with(qtv())).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(s).hasSize(2);
        assertThat(s.get(0).get("score").asInt()).isEqualTo(81);
        assertThat(s.get(0).get("scoringMode").asText()).isEqualTo("ML");
        assertThat(s.get(0).get("topFactors").get(0).get("name").asText()).isEqualTo("hỏi giá");
        assertThat(s.get(1).get("scoringMode").asText()).isEqualTo("RULE");
        assertThat(chiTiet(qtv(), id).get("latestScore").get("score").asInt()).isEqualTo(81);
    }

    @Test
    void cachLy_doanhNghiepKhacKhongThayKhongSuaDuoc() throws Exception {
        String id = leadMoi(SALE_1, "Cách Ly Lead", "0901000018");
        JwtRequestPostProcessor m = asUser(TENANT_M, ADMIN_M, "TENANT_ADMIN");
        mvc.perform(get("/api/v1/leads/" + id).with(m)).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/leads/" + id + "/scores").with(m)).andExpect(status().isNotFound());
        sua(m, id, "{\"status\":\"CONTACTED\"}").andExpect(status().isNotFound());
        assertThat(ids(danhSach(m, "q=cach ly"))).isEmpty();
        // Doanh nghiệp M không giao được lead cho người của L
        UUID khachM = khach(TENANT_M, "Khách Riêng M", "0901000019");
        taoLead(m, "{\"contactId\":\"" + khachM + "\",\"ownerUserId\":\"" + SALE_1 + "\"}")
                .andExpect(status().isUnprocessableEntity());
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private static JwtRequestPostProcessor qtv() {
        return asUser(TENANT_L, ADMIN_L, "TENANT_ADMIN");
    }

    private static JwtRequestPostProcessor nv(UUID userId) {
        return asUser(TENANT_L, userId, "AGENT");
    }

    private ResultActions taoLead(JwtRequestPostProcessor who, String body) throws Exception {
        return mvc.perform(post("/api/v1/leads").with(who).contentType(MediaType.APPLICATION_JSON).content(body));
    }

    private ResultActions sua(JwtRequestPostProcessor who, String id, String body) throws Exception {
        return mvc.perform(patch("/api/v1/leads/" + id).with(who).contentType(MediaType.APPLICATION_JSON).content(body));
    }

    private JsonNode created(ResultActions r) throws Exception {
        return data(r.andExpect(status().isCreated()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
    }

    private JsonNode chiTiet(JwtRequestPostProcessor who, String id) throws Exception {
        return data(mvc.perform(get("/api/v1/leads/" + id).with(who)).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
    }

    private ResultActions danhSachRaw(JwtRequestPostProcessor who, String query) throws Exception {
        return mvc.perform(get("/api/v1/leads?" + query).with(who));
    }

    private JsonNode danhSach(JwtRequestPostProcessor who, String query) throws Exception {
        return data(danhSachRaw(who, query).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
    }

    private static List<String> ids(JsonNode page) {
        List<String> out = new ArrayList<>();
        page.get("items").forEach(i -> out.add(i.get("id").asText()));
        return out;
    }

    /** Lead mới của khách mới, do {@code owner} tạo (và phụ trách). */
    private String leadMoi(UUID owner, String ten, String phone) throws Exception {
        UUID k = khach(TENANT_L, ten, phone);
        return created(taoLead(nv(owner), "{\"contactId\":\"" + k + "\"}")).get("id").asText();
    }

    /** Giả lập UC030 ghi điểm qua API nội bộ — ở đây ghi thẳng bằng chủ bảng. */
    private static void diem(String leadId, int score) throws Exception {
        try (Connection c = owner()) {
            exec(c, "UPDATE sales.leads SET current_score = ?, score_updated_at = now() WHERE id = ?",
                    (short) score, UUID.fromString(leadId));
        }
    }

    private static UUID khach(UUID tenantId, String ten, String phone) throws Exception {
        UUID id = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO engagement.contacts (id, tenant_id, full_name, phone, primary_channel) VALUES (?, ?, ?, ?, 'PHONE')",
                    id, tenantId, ten, phone);
        }
        return id;
    }

    private static UUID hoiThoai(UUID contactId) throws Exception {
        UUID identity = UUID.randomUUID();
        UUID conv = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, """
                    INSERT INTO engagement.channel_identities (id, tenant_id, channel_id, contact_id, external_user_id)
                    VALUES (?, ?, ?, ?, ?)""", identity, TENANT_L, CHANNEL_L, contactId, "zalo-" + identity);
            exec(c, """
                    INSERT INTO engagement.conversations (id, tenant_id, channel_id, channel_identity_id, contact_id)
                    VALUES (?, ?, ?, ?, ?)""", conv, TENANT_L, CHANNEL_L, identity, contactId);
        }
        return conv;
    }

    private static List<String> sql(String query, Object... args) throws Exception {
        List<String> out = new ArrayList<>();
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(query)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            try (ResultSet rs = ps.executeQuery()) {
                while (rs.next()) {
                    out.add(rs.getString(1));
                }
            }
        }
        return out;
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
