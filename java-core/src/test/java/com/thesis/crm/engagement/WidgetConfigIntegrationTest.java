package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import org.junit.jupiter.api.MethodOrderer;
import org.junit.jupiter.api.Order;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestMethodOrder;
import org.springframework.http.MediaType;

/**
 * UC009 — quản trị viên sinh mã nhúng, cấu hình widget, thử chatbot; rồi khách mở được phiên trên
 * đúng tên miền vừa khai. Dùng doanh nghiệp B của lớp nền (A dùng cho UC016/UC017).
 */
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class WidgetConfigIntegrationTest extends EngagementIntegrationTestBase {

    private static final java.util.UUID AGENT_B = java.util.UUID.randomUUID();
    private static boolean seededB;

    private void seedB() throws Exception {
        if (seededB) {
            return;
        }
        seededB = true;
        try (Connection c = owner()) {
            try (PreparedStatement ps = c.prepareStatement("""
                    INSERT INTO platform.tenant_subscriptions (tenant_id, plan_id, status, period_start, period_end)
                    SELECT ?, id, 'ACTIVE', now() - interval '1 day', now() + interval '29 days'
                    FROM platform.subscription_plans WHERE code = 'TRIAL'""")) {
                ps.setObject(1, TENANT_B);
                ps.executeUpdate();
            }
            try (PreparedStatement ps = c.prepareStatement("""
                    INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                    VALUES (?, ?, ?, 'x', 'Nhân viên B', 'ACTIVE')""")) {
                ps.setObject(1, AGENT_B);
                ps.setObject(2, TENANT_B);
                ps.setString(3, AGENT_B.toString().substring(0, 8) + "@nv.vn");
                ps.executeUpdate();
            }
        }
    }

    @Test
    @Order(1)
    void chuaCoWidget_404_nhanVienKhongSinhDuoc_quanTriSinhDuocMotLan() throws Exception {
        seedB();
        mvc.perform(get("/api/v1/widget-config").with(as(TENANT_B))).andExpect(status().isNotFound());
        mvc.perform(post("/api/v1/widget-config").with(asUser(TENANT_B, AGENT_B, "AGENT")))
                .andExpect(status().isForbidden());

        mvc.perform(post("/api/v1/widget-config").with(as(TENANT_B)))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.publicKey").value(org.hamcrest.Matchers.matchesPattern("^wk_[0-9a-f]{32}$")))
                .andExpect(jsonPath("$.data.isActive").value(true))
                .andExpect(jsonPath("$.data.allowedDomains").isEmpty());
        mvc.perform(post("/api/v1/widget-config").with(as(TENANT_B))).andExpect(status().isConflict());
        assertThat(auditCount("WIDGET_CREATED")).isEqualTo(1);
    }

    @Test
    @Order(2)
    void luuCauHinh_chuanHoaTenMien_kiemDuLieu_vaChiQuanTri() throws Exception {
        mvc.perform(put("/api/v1/widget-config").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"primaryColor":"#10b981","greetingMessage":"Chào bạn!",
                                 "allowedDomains":["https://Shop-B.vn/lien-he","shop-b.vn","*.shop-b.vn","localhost"]}"""))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.primaryColor").value("#10B981"))
                .andExpect(jsonPath("$.data.allowedDomains.length()").value(3))
                .andExpect(jsonPath("$.data.allowedDomains[0]").value("shop-b.vn"));

        mvc.perform(put("/api/v1/widget-config").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"primaryColor\":\"red\"}")).andExpect(status().isUnprocessableEntity());
        mvc.perform(put("/api/v1/widget-config").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"allowedDomains\":[\"không hợp lệ\"]}")).andExpect(status().isUnprocessableEntity());
        mvc.perform(put("/api/v1/widget-config").with(asUser(TENANT_B, AGENT_B, "AGENT"))
                .contentType(MediaType.APPLICATION_JSON).content("{\"greetingMessage\":\"x\"}"))
                .andExpect(status().isForbidden());

        // Nhân viên vẫn XEM được
        mvc.perform(get("/api/v1/widget-config").with(asUser(TENANT_B, AGENT_B, "AGENT")))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.greetingMessage").value("Chào bạn!"));
    }

    @Test
    @Order(3)
    void maNhung_chuaKhoa_vaKhachMoPhienDuocTrenTenMienVuaKhai() throws Exception {
        String body = mvc.perform(get("/api/v1/widget-config/snippet").with(as(TENANT_B)))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        String key = data(body).get("publicKey").asText();
        assertThat(data(body).get("snippet").asText()).contains("data-widget-key=\"" + key + "\"").contains("<script");

        widgetSession(key, "https://www.shop-b.vn")
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.status").value("ACTIVE"))
                .andExpect(jsonPath("$.data.appearance.primaryColor").value("#10B981"));
        widgetSession(key, "https://khac.vn").andExpect(status().isForbidden());

        // Tắt widget → khách thấy "tạm ngừng" ngay, không cần sinh lại mã (UC009 4a)
        mvc.perform(put("/api/v1/widget-config").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"isActive\":false}")).andExpect(status().isOk());
        widgetSession(key, "https://shop-b.vn").andExpect(jsonPath("$.data.status").value("SUSPENDED"));
        mvc.perform(put("/api/v1/widget-config").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"isActive\":true}")).andExpect(status().isOk());
    }

    @Test
    @Order(4)
    void thuChatbot_goiAiThat_khongGhiGiVaoCsdl() throws Exception {
        AI.respond(FakeAiServer.answer("Đây là câu trả lời thử."));
        long before = count("SELECT count(*) FROM engagement.conversations WHERE tenant_id = '" + TENANT_B + "'");
        mvc.perform(post("/api/v1/widget-config/test-chat").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"message\":\"gói pro giá bao nhiêu\",\"history\":[{\"role\":\"user\",\"content\":\"chào\"}]}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.answer").value("Đây là câu trả lời thử."))
                .andExpect(jsonPath("$.data.citations[0].title").value("Bảng giá 2026"));
        assertThat(AI.lastTenantHeader.get()).isEqualTo(TENANT_B.toString());
        assertThat(count("SELECT count(*) FROM engagement.conversations WHERE tenant_id = '" + TENANT_B + "'"))
                .isEqualTo(before);

        mvc.perform(post("/api/v1/widget-config/test-chat").with(asUser(TENANT_B, AGENT_B, "AGENT"))
                .contentType(MediaType.APPLICATION_JSON).content("{\"message\":\"hi\"}"))
                .andExpect(status().isForbidden());

        AI.respond(new FakeAiServer.Script(500, "{}", 0));
        mvc.perform(post("/api/v1/widget-config/test-chat").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"message\":\"hi\"}")).andExpect(status().isServiceUnavailable());
    }

    @Test
    @Order(6)
    void kyTuSaoPhuCaDuoiQuocGia_bitTuChoi() throws Exception {
        // Lỗ hổng R2: "*.vn" hay "*.com.vn" cho widget chạy trên MỌI website .vn — gõ nhầm một
        // dòng là mất toàn bộ lớp chặn nhúng trái phép.
        for (String rong : new String[] {"*.vn", "*.com.vn", "*.com", "*.edu.vn"}) {
            mvc.perform(put("/api/v1/widget-config").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                    .content("{\"allowedDomains\":[\"" + rong + "\"]}"))
                    .andExpect(status().isUnprocessableEntity());
        }
    }

    @Test
    @Order(7)
    void tenMienTiengViet_luuDangPunycode_vaKhachMoPhienDuoc() throws Exception {
        // Lỗ hổng R3: trình duyệt gửi Origin dạng punycode (xn--…), người dùng gõ có dấu → hoặc bị
        // từ chối khi lưu, hoặc lưu rồi không bao giờ khớp.
        String ascii = java.net.IDN.toASCII("cửahàng.vn");
        mvc.perform(put("/api/v1/widget-config").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"allowedDomains\":[\"cửahàng.vn\"]}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.allowedDomains[0]").value(ascii));
        String key = data(mvc.perform(get("/api/v1/widget-config").with(as(TENANT_B)))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8)).get("publicKey").asText();
        widgetSession(key, "https://" + ascii).andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("ACTIVE"));
    }

    @Test
    @Order(8)
    void haiWidgetChoMotDoanhNghiep_csdlChan() throws Exception {
        // Lỗ hổng R4: hai quản trị viên bấm "Sinh mã" cùng lúc → kiểm-rồi-chèn đua nhau, ra hai
        // widget; màn chỉ hiện một, khoá kia "mồ côi" vẫn chạy.
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement("""
                INSERT INTO engagement.channels (tenant_id, type, name, widget_key, status, config)
                VALUES (?, 'WEB_WIDGET', 'Widget thứ hai', 'wk_trung_' || substr(md5(random()::text), 1, 8), 'ACTIVE', '{}')""")) {
            ps.setObject(1, TENANT_B);
            org.assertj.core.api.Assertions.assertThatThrownBy(ps::executeUpdate)
                    .hasMessageContaining("uq_channels_one_widget");
        }
    }

    @Test
    @Order(5)
    void cachLy_doanhNghiepAKhongThayWidgetCuaB() throws Exception {
        mvc.perform(get("/api/v1/widget-config").with(as(TENANT_A))).andExpect(status().isNotFound());
    }

    @Test
    @Order(3)
    void tenHienThi_macDinhTenDoanhNghiep_datDuoc_boTrongThiQuayLai() throws Exception {
        String key = data(mvc.perform(get("/api/v1/widget-config/snippet").with(as(TENANT_B)))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8)).get("publicKey").asText();
        String tenDn = "DN " + TENANT_B;
        widgetSession(key, "https://shop-b.vn").andExpect(jsonPath("$.data.appearance.displayName").value(tenDn));

        mvc.perform(put("/api/v1/widget-config").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"displayName\":\"  Cát Tường  \"}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.displayName").value("Cát Tường"));
        widgetSession(key, "https://shop-b.vn").andExpect(jsonPath("$.data.appearance.displayName").value("Cát Tường"));

        mvc.perform(put("/api/v1/widget-config").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"displayName\":\"" + "x".repeat(61) + "\"}")).andExpect(status().isUnprocessableEntity());
        mvc.perform(put("/api/v1/widget-config").with(as(TENANT_B)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"displayName\":\"\"}")).andExpect(status().isOk());
        widgetSession(key, "https://shop-b.vn").andExpect(jsonPath("$.data.appearance.displayName").value(tenDn));
    }

    private org.springframework.test.web.servlet.ResultActions widgetSession(String key, String origin) throws Exception {
        return mvc.perform(post("/api/v1/widget/session").header("Origin", origin)
                .header("X-Forwarded-For", "10.9." + (int) (Math.random() * 250) + ".1")
                .contentType(MediaType.APPLICATION_JSON).content("{\"widgetKey\":\"" + key + "\"}"));
    }

    private static long auditCount(String action) throws Exception {
        return count("SELECT count(*) FROM platform.audit_logs WHERE tenant_id = '" + TENANT_B
                + "' AND action = '" + action + "'");
    }

    private static long count(String sql) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(sql)) {
            ResultSet rs = ps.executeQuery();
            rs.next();
            return rs.getLong(1);
        }
    }
}
