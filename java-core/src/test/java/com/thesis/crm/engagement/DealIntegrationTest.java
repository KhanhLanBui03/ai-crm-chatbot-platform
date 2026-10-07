package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
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
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;
import org.springframework.test.web.servlet.ResultActions;

/**
 * UC033 (chuyển lead thành deal) + UC034 (deal theo phễu). Phễu mặc định do trigger V133 tạo ngay khi
 * thêm doanh nghiệp — test không tự dựng phễu, nên kiểm luôn cả trigger đó.
 */
class DealIntegrationTest extends EngagementIntegrationTestBase {

    static final UUID TENANT_D = UUID.randomUUID();
    static final UUID TENANT_E = UUID.randomUUID();
    static final UUID ADMIN_D = UUID.randomUUID();
    static final UUID SALE_1 = UUID.randomUUID();
    static final UUID SALE_2 = UUID.randomUUID();
    static final UUID ADMIN_E = UUID.randomUUID();

    private static boolean seededDeal;
    /** Tên giai đoạn → id, của phễu mặc định doanh nghiệp D. */
    private static final Map<String, String> GD = new HashMap<>();

    @BeforeEach
    void seedDeal() throws Exception {
        if (seededDeal) {
            return;
        }
        seededDeal = true;
        try (Connection c = owner()) {
            for (UUID t : new UUID[] {TENANT_D, TENANT_E}) {
                exec(c, "INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES (?, 'DN deal', ?, ?)",
                        t, "d-" + t.toString().substring(0, 8), "a@" + t.toString().substring(0, 8) + ".vn");
            }
            for (Object[] u : new Object[][] {{ADMIN_D, TENANT_D, "Quản trị D"}, {SALE_1, TENANT_D, "Lan Sale"},
                    {SALE_2, TENANT_D, "Minh Sale"}, {ADMIN_E, TENANT_E, "Quản trị E"}}) {
                exec(c, """
                        INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                        VALUES (?, ?, ?, 'x', ?, 'ACTIVE')""", u[0], u[1], u[0].toString().substring(0, 8) + "@d.vn", u[2]);
            }
        }
        JsonNode pheu = data(body(mvc.perform(get("/api/v1/pipelines").with(qtv())).andExpect(status().isOk())));
        pheu.get(0).get("stages").forEach(s -> GD.put(s.get("name").asText(), s.get("id").asText()));
    }

    // ── phễu mặc định ───────────────────────────────────────────────────────────

    @Test
    void doanhNghiepMoiCoSanPheu5GiaiDoan() throws Exception {
        JsonNode pheu = data(body(mvc.perform(get("/api/v1/pipelines").with(nv(SALE_1))).andExpect(status().isOk())));
        assertThat(pheu).hasSize(1);
        assertThat(pheu.get(0).get("isDefault").asBoolean()).isTrue();
        JsonNode st = pheu.get(0).get("stages");
        List<String> ten = new ArrayList<>();
        st.forEach(s -> ten.add(s.get("name").asText()));
        assertThat(ten).containsExactly("Mới tiếp nhận", "Đã báo giá", "Thương lượng", "Thắng", "Thua");
        assertThat(st.get(1).get("requiredFields").get(0).asText()).isEqualTo("amount");
        assertThat(st.get(3).get("isWon").asBoolean()).isTrue();
        assertThat(st.get(4).get("isLost").asBoolean()).isTrue();
        // Doanh nghiệp khác có phễu RIÊNG
        JsonNode e = data(body(mvc.perform(get("/api/v1/pipelines").with(asUser(TENANT_E, ADMIN_E, "TENANT_ADMIN")))));
        assertThat(e.get(0).get("id").asText()).isNotEqualTo(pheu.get(0).get("id").asText());
    }

    // ── UC033 ───────────────────────────────────────────────────────────────────

    @Test
    void chuyenLead_taoDealDauPheu_dongLead_motGiaoDich() throws Exception {
        UUID k = khach(TENANT_D, "Chuyển Đổi", "0902000001");
        String lead = leadMoi(nv(SALE_1), k, "Gói Pro");
        JsonNode kq = data(body(chuyen(nv(SALE_1), lead, "{\"amount\":5000000,\"expectedCloseDate\":\"2026-12-31\"}")
                .andExpect(status().isCreated())));
        JsonNode deal = kq.get("deal");
        assertThat(deal.get("title").asText()).isEqualTo("Chuyển Đổi – Gói Pro");
        assertThat(deal.get("stageName").asText()).isEqualTo("Mới tiếp nhận");
        assertThat(deal.get("source").asText()).isEqualTo("MANUAL");
        assertThat(deal.get("status").asText()).isEqualTo("OPEN");
        assertThat(deal.get("ownerUserId").asText()).isEqualTo(SALE_1.toString());
        assertThat(deal.get("leadId").asText()).isEqualTo(lead);
        assertThat(deal.get("amount").decimalValue()).isEqualByComparingTo("5000000");
        assertThat(kq.get("lead").get("status").asText()).isEqualTo("CONVERTED");
        assertThat(kq.get("warnings")).isEmpty();

        JsonNode l = data(body(mvc.perform(get("/api/v1/leads/" + lead).with(nv(SALE_1)))));
        assertThat(l.get("convertedDealId").asText()).isEqualTo(deal.get("id").asText());
        assertThat(l.get("allowedNextStatuses")).isEmpty();
        JsonNode d = chiTiet(deal.get("id").asText());
        assertThat(d.get("stageHistory")).hasSize(1);
        assertThat(d.get("stageHistory").get(0).get("fromStageId").isNull()).isTrue();

        chuyen(nv(SALE_1), lead, "{}").andExpect(status().isConflict());
        assertThat(sql("SELECT action FROM platform.audit_logs WHERE entity_id = ? ORDER BY created_at",
                UUID.fromString(lead))).contains("LEAD_CONVERTED");
    }

    @Test
    void chuyenLeadAi_nguonAiLead_leadChuaAiNhanThiNguoiBamPhuTrach_khachCoDealMoThiCanhBao() throws Exception {
        UUID k = khach(TENANT_D, "Khách AI", "0902000002");
        taoDeal(nv(SALE_2), "{\"contactId\":\"" + k + "\",\"title\":\"Đơn cũ\"}").andExpect(status().isCreated());
        UUID lead = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO sales.leads (id, tenant_id, contact_id, source, status) VALUES (?, ?, ?, 'AI_AUTO', 'NEW')",
                    lead, TENANT_D, k);
        }
        JsonNode kq = data(body(chuyen(nv(SALE_1), lead.toString(), "{\"title\":\"Đơn AI\"}")
                .andExpect(status().isCreated())));
        assertThat(kq.get("deal").get("source").asText()).isEqualTo("AI_LEAD");
        assertThat(kq.get("deal").get("ownerUserId").asText()).isEqualTo(SALE_1.toString());
        assertThat(kq.get("lead").get("ownerUserId").asText()).isEqualTo(SALE_1.toString());
        assertThat(kq.get("warnings").get(0).asText()).contains("1 deal");
    }

    @Test
    void chuyenLead_chanLeadDaLoai_vaLeadCuaNguoiKhac() throws Exception {
        String cuaLan = leadMoi(nv(SALE_1), khach(TENANT_D, "Của Lan", "0902000003"), null);
        chuyen(nv(SALE_2), cuaLan, "{}").andExpect(status().isForbidden());
        mvc.perform(patch("/api/v1/leads/" + cuaLan).with(nv(SALE_1)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"status\":\"DISQUALIFIED\",\"disqualifyReason\":\"SPAM\"}")).andExpect(status().isOk());
        chuyen(nv(SALE_1), cuaLan, "{}").andExpect(status().isConflict());
        // Không lọt deal nào khi bị từ chối
        assertThat(sql("SELECT count(*) FROM sales.deals WHERE lead_id = ?", UUID.fromString(cuaLan))).containsExactly("0");
    }

    // ── UC034: kéo thả ──────────────────────────────────────────────────────────

    @Test
    void keoTuDo_thieuGiaTriThi422_thuaBatBuocLyDo_moLaiXoaLyDo_lichSuCoThoiGian() throws Exception {
        String id = dealMoi(SALE_1, "Kéo Thả", "0902000004");
        JsonNode thieu = json.readTree(body(keo(nv(SALE_1), id, GD.get("Đã báo giá"), null)
                .andExpect(status().isUnprocessableEntity())));
        assertThat(thieu.get("code").asText()).isEqualTo("MISSING_REQUIRED_FIELDS");
        assertThat(thieu.get("data").get("missingFields").get(0).asText()).isEqualTo("amount");

        sua(nv(SALE_1), id, "{\"amount\":12000000}").andExpect(status().isOk());
        keo(nv(SALE_1), id, GD.get("Đã báo giá"), null).andExpect(status().isOk());
        keo(nv(SALE_1), id, GD.get("Mới tiếp nhận"), null).andExpect(status().isOk());       // lùi được

        JsonNode khongLyDo = json.readTree(body(keo(nv(SALE_1), id, GD.get("Thua"), null)
                .andExpect(status().isUnprocessableEntity())));
        assertThat(khongLyDo.get("code").asText()).isEqualTo("LOST_REASON_REQUIRED");
        keo(nv(SALE_1), id, GD.get("Thua"), "VI_THICH").andExpect(status().isUnprocessableEntity());
        keo(nv(SALE_1), id, GD.get("Thương lượng"), "PRICE").andExpect(status().isUnprocessableEntity());

        JsonNode thua = data(body(keo(nv(SALE_1), id, GD.get("Thua"), "COMPETITOR").andExpect(status().isOk())));
        assertThat(thua.get("status").asText()).isEqualTo("LOST");
        assertThat(thua.get("closeReason").asText()).isEqualTo("COMPETITOR");
        assertThat(thua.get("closedAt").isNull()).isFalse();
        // Deal đã đóng: không sửa thông tin
        sua(nv(SALE_1), id, "{\"title\":\"Đổi tên\"}").andExpect(status().isConflict());

        JsonNode moLai = data(body(keo(nv(SALE_1), id, GD.get("Thương lượng"), null).andExpect(status().isOk())));
        assertThat(moLai.get("status").asText()).isEqualTo("OPEN");
        assertThat(moLai.get("closeReason").isNull()).isTrue();
        assertThat(moLai.get("closedAt").isNull()).isTrue();

        JsonNode thang = data(body(keo(nv(SALE_1), id, GD.get("Thắng"), null).andExpect(status().isOk())));
        assertThat(thang.get("status").asText()).isEqualTo("WON");
        JsonNode ls = thang.get("stageHistory");
        assertThat(ls).hasSize(6);                      // tạo + 5 lần kéo thành công
        for (int i = 1; i < ls.size(); i++) {
            assertThat(ls.get(i).get("durationSeconds").asLong()).isGreaterThanOrEqualTo(0);
            assertThat(ls.get(i).get("fromStageId").asText()).isEqualTo(ls.get(i - 1).get("toStageId").asText());
        }
        assertThat(ls.get(5).get("changedByName").asText()).isEqualTo("Lan Sale");
        assertThat(sql("SELECT after_data->>'reopened' FROM platform.audit_logs WHERE entity_id = ? "
                + "AND action = 'DEAL_STAGE_CHANGED' AND after_data->>'reopened' IS NOT NULL", UUID.fromString(id))).containsExactly("true");
    }

    @Test
    void doiLyDoThuaKhongSinhLichSu() throws Exception {
        String id = dealMoi(SALE_1, "Đổi Lý Do", "0902000005");
        keo(nv(SALE_1), id, GD.get("Thua"), "PRICE").andExpect(status().isOk());
        JsonNode d = data(body(keo(nv(SALE_1), id, GD.get("Thua"), "NO_DECISION").andExpect(status().isOk())));
        assertThat(d.get("closeReason").asText()).isEqualTo("NO_DECISION");
        assertThat(d.get("stageHistory")).hasSize(2);
    }

    @Test
    void quyen_nhanVienKhacKhongKeoDuoc_dealChuaAiNhanKeoLaTuNhan() throws Exception {
        String cuaLan = dealMoi(SALE_1, "Deal Lan", "0902000006");
        JsonNode loi = json.readTree(body(keo(nv(SALE_2), cuaLan, GD.get("Thương lượng"), null)
                .andExpect(status().isForbidden())));
        assertThat(loi.get("message").asText()).contains("Lan Sale");
        sua(nv(SALE_2), cuaLan, "{\"title\":\"x\"}").andExpect(status().isForbidden());
        sua(nv(SALE_1), cuaLan, "{\"ownerUserId\":\"" + SALE_2 + "\"}").andExpect(status().isForbidden());
        sua(qtv(), cuaLan, "{\"ownerUserId\":null}").andExpect(status().isOk());

        JsonNode nhan = data(body(keo(nv(SALE_2), cuaLan, GD.get("Thương lượng"), null).andExpect(status().isOk())));
        assertThat(nhan.get("ownerUserId").asText()).isEqualTo(SALE_2.toString());
    }

    // ── tạo thủ công, sửa, danh sách ────────────────────────────────────────────

    @Test
    void taoDealThuCong_kiemDauVao() throws Exception {
        UUID k = khach(TENANT_D, "Thủ Công", "0902000007");
        taoDeal(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"title\":\" \"}").andExpect(status().isUnprocessableEntity());
        taoDeal(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"title\":\"x\",\"stageId\":\"" + GD.get("Thắng") + "\"}")
                .andExpect(status().isUnprocessableEntity());
        taoDeal(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"title\":\"x\",\"stageId\":\"" + GD.get("Đã báo giá") + "\"}")
                .andExpect(status().isUnprocessableEntity());
        taoDeal(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"title\":\"x\",\"leadId\":\"" + UUID.randomUUID() + "\"}")
                .andExpect(status().isUnprocessableEntity());
        taoDeal(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"title\":\"x\",\"ownerUserId\":\"" + SALE_2 + "\"}")
                .andExpect(status().isForbidden());
        taoDeal(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"title\":\"x\",\"amount\":-1}")
                .andExpect(status().isUnprocessableEntity());
        JsonNode d = data(body(taoDeal(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"title\":\"Mua thêm\","
                + "\"stageId\":\"" + GD.get("Đã báo giá") + "\",\"amount\":3000000}").andExpect(status().isCreated())));
        assertThat(d.get("source").asText()).isEqualTo("MANUAL");
        assertThat(d.get("stageName").asText()).isEqualTo("Đã báo giá");
        assertThat(d.get("ownerUserId").asText()).isEqualTo(SALE_1.toString());
        // Đang ở "Đã báo giá" thì không được xoá giá trị
        sua(nv(SALE_1), d.get("id").asText(), "{\"amount\":null}").andExpect(status().isUnprocessableEntity());
    }

    @Test
    void danhSachTheoPheu_quaHan_vaTongMoiCot() throws Exception {
        String id = dealMoi(SALE_2, "Quá Hạn", "0902000008");
        String homQua = LocalDate.now().minusDays(2).toString();
        JsonNode d = data(body(sua(nv(SALE_2), id, "{\"expectedCloseDate\":\"" + homQua + "\",\"amount\":7000000}")
                .andExpect(status().isOk())));
        assertThat(d.get("isOverdue").asBoolean()).isTrue();

        String pheu = data(body(mvc.perform(get("/api/v1/pipelines").with(qtv())))).get(0).get("id").asText();
        JsonNode trang = data(body(mvc.perform(get("/api/v1/deals").param("pipelineId", pheu)
                .param("ownerUserId", SALE_2.toString()).with(qtv())).andExpect(status().isOk())));
        List<String> ids = new ArrayList<>();
        trang.get("items").forEach(i -> ids.add(i.get("id").asText()));
        assertThat(ids).contains(id);

        JsonNode cot = data(body(mvc.perform(get("/api/v1/pipelines").with(qtv())))).get(0).get("stages").get(0);
        assertThat(cot.get("dealCount").asInt()).isGreaterThanOrEqualTo(1);
        assertThat(cot.get("dealValueTotal").decimalValue()).isGreaterThanOrEqualTo(new java.math.BigDecimal("7000000"));
        mvc.perform(get("/api/v1/deals").param("status", "MO").with(qtv())).andExpect(status().isUnprocessableEntity());
    }

    @Test
    void cachLy_doanhNghiepKhacKhongThayKhongKeo_khongDungGiaiDoanCuaNguoiKhac() throws Exception {
        String id = dealMoi(SALE_1, "Cách Ly Deal", "0902000009");
        JwtRequestPostProcessor e = asUser(TENANT_E, ADMIN_E, "TENANT_ADMIN");
        mvc.perform(get("/api/v1/deals/" + id).with(e)).andExpect(status().isNotFound());
        keo(e, id, GD.get("Thương lượng"), null).andExpect(status().isNotFound());
        JsonNode dsE = data(body(mvc.perform(get("/api/v1/deals").with(e))));
        assertThat(dsE.get("totalItems").asLong()).isZero();
        // Deal của E kéo vào giai đoạn của D → giai đoạn "không tồn tại" với E
        UUID kE = khach(TENANT_E, "Khách E", "0902000010");
        String dealE = data(body(taoDeal(e, "{\"contactId\":\"" + kE + "\",\"title\":\"E\"}")
                .andExpect(status().isCreated()))).get("id").asText();
        keo(e, dealE, GD.get("Thương lượng"), null).andExpect(status().isUnprocessableEntity());
        // Không chuyển được lead của D
        String leadD = leadMoi(nv(SALE_1), khach(TENANT_D, "Lead D", "0902000011"), null);
        chuyen(e, leadD, "{}").andExpect(status().isNotFound());
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private static JwtRequestPostProcessor qtv() {
        return asUser(TENANT_D, ADMIN_D, "TENANT_ADMIN");
    }

    private static JwtRequestPostProcessor nv(UUID userId) {
        return asUser(TENANT_D, userId, "AGENT");
    }

    private static String body(ResultActions r) throws Exception {
        return r.andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
    }

    private ResultActions chuyen(JwtRequestPostProcessor who, String leadId, String json) throws Exception {
        return mvc.perform(post("/api/v1/leads/" + leadId + "/convert").with(who)
                .contentType(MediaType.APPLICATION_JSON).content(json));
    }

    private ResultActions taoDeal(JwtRequestPostProcessor who, String json) throws Exception {
        return mvc.perform(post("/api/v1/deals").with(who).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    private ResultActions sua(JwtRequestPostProcessor who, String id, String json) throws Exception {
        return mvc.perform(patch("/api/v1/deals/" + id).with(who).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    private ResultActions keo(JwtRequestPostProcessor who, String id, String stageId, String reason) throws Exception {
        String json = "{\"stageId\":\"" + stageId + "\"" + (reason == null ? "" : ",\"closeReason\":\"" + reason + "\"") + "}";
        return mvc.perform(post("/api/v1/deals/" + id + "/stage").with(who)
                .contentType(MediaType.APPLICATION_JSON).content(json));
    }

    private JsonNode chiTiet(String id) throws Exception {
        return data(body(mvc.perform(get("/api/v1/deals/" + id).with(qtv())).andExpect(status().isOk())));
    }

    private String leadMoi(JwtRequestPostProcessor who, UUID contactId, String product) throws Exception {
        String json = "{\"contactId\":\"" + contactId + "\"" + (product == null ? "" : ",\"interestedProduct\":\"" + product + "\"") + "}";
        return data(body(mvc.perform(post("/api/v1/leads").with(who).contentType(MediaType.APPLICATION_JSON).content(json))
                .andExpect(status().isCreated()))).get("id").asText();
    }

    /** Deal thủ công ở cột đầu, do {@code owner} tạo và phụ trách. */
    private String dealMoi(UUID owner, String ten, String phone) throws Exception {
        UUID k = khach(TENANT_D, ten, phone);
        return data(body(taoDeal(nv(owner), "{\"contactId\":\"" + k + "\",\"title\":\"" + ten + "\"}")
                .andExpect(status().isCreated()))).get("id").asText();
    }

    private static UUID khach(UUID tenantId, String ten, String phone) throws Exception {
        UUID id = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO engagement.contacts (id, tenant_id, full_name, phone, primary_channel) VALUES (?, ?, ?, ?, 'PHONE')",
                    id, tenantId, ten, phone);
        }
        return id;
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
