package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.analytics.service.TurnMetricsService;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * UC006 phần 1 — token AI từ sự kiện {@code ai.turn.completed} vào hạn mức {@code AI_TOKEN}, mốc 80% / 100%
 * thật, và {@code GET /api/v1/usage} đọc mốc + chi phí thật (không còn {@code Instant.now()}).
 *
 * <p>Mỗi test một doanh nghiệp riêng (gói TRIAL: 500.000 token, 200 hội thoại).
 */
class UsageIntegrationTest extends EngagementIntegrationTestBase {

    @Autowired TurnMetricsService metrics;
    @Autowired ObjectMapper mapper;

    private UUID tenant;
    private UUID admin;

    @BeforeEach
    void doanhNghiepMoi() throws Exception {
        tenant = UUID.randomUUID();
        admin = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES (?, 'DN hạn mức', ?, ?)",
                    tenant, "hm-" + tenant.toString().substring(0, 8), "hm@" + tenant.toString().substring(0, 8) + ".vn");
            exec(c, """
                    INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                    VALUES (?, ?, ?, 'x', 'Quản trị', 'ACTIVE')""", admin, tenant, admin.toString().substring(0, 8) + "@hm.vn");
            exec(c, """
                    INSERT INTO platform.tenant_subscriptions (tenant_id, plan_id, status, period_start, period_end)
                    SELECT ?, id, 'TRIALING', now() - interval '1 day', now() + interval '13 days'
                    FROM platform.subscription_plans WHERE code = 'TRIAL'""", tenant);
        }
    }

    @Test
    void tokenTuSuKien_congVaoHanMuc_ghiMocTamMuoiRoiMotTram() throws Exception {
        nhan(399_000, 1_000, "0");                         // 400.000 / 500.000 = 80%
        assertThat(cot("used_value")).isEqualTo("400000");
        assertThat(cot("warned_at")).isNotNull();
        assertThat(cot("blocked_at")).isNull();

        nhan(99_000, 1_000, "0");                          // 500.000 — chạm trần
        assertThat(cot("used_value")).isEqualTo("500000");
        assertThat(cot("blocked_at")).isNotNull();
    }

    @Test
    void suKienGiaoLai_khongCongTokenHaiLan() throws Exception {
        JsonNode sk = suKien(1_000, 200, "0");
        assertThat(metrics.ghiNhan(sk)).isTrue();
        assertThat(metrics.ghiNhan(sk)).isFalse();
        assertThat(cot("used_value")).isEqualTo("1200");
    }

    @Test
    void hanMuc_docMocThat_khongDoiGiuaHaiLanXem_vaChiPhiThat() throws Exception {
        nhan(399_000, 1_000, "1.5000");
        nhan(10, 5, "2.2500");
        JsonNode lan1 = hanMuc();
        Thread.sleep(20);
        JsonNode lan2 = hanMuc();
        assertThat(lan1.get("tokens").get("used").asLong()).isEqualTo(400_015);
        assertThat(lan1.get("tokens").get("warnedAt").isNull()).isFalse();
        // Mốc là thời điểm ĐÃ chạm — mở màn lần nữa không được đổi (trước đây trả Instant.now())
        assertThat(lan2.get("warnedAt").asText()).isEqualTo(lan1.get("warnedAt").asText());
        assertThat(lan1.has("blockedAt")).isFalse();
        assertThat(new BigDecimal(lan1.get("costVnd").asText())).isEqualByComparingTo("3.75");
    }

    @Test
    void chuKyQuaHanChuaGiaHan_tokenVanCongNhuHoiThoai() throws Exception {
        // Chưa có công việc gia hạn cuối chu kỳ: widget vẫn đếm hội thoại vào thuê bao này, token phải đi cùng
        try (Connection c = owner()) {
            exec(c, "UPDATE platform.tenant_subscriptions SET period_start = now() - interval '40 days', "
                    + "period_end = now() - interval '26 days' WHERE tenant_id = ?", tenant);
        }
        nhan(700, 300, "0");
        assertThat(cot("used_value")).isEqualTo("1000");
    }

    @Test
    void chuaDungGi_khongCoMoc_chiPhi0() throws Exception {
        JsonNode d = hanMuc();
        assertThat(d.has("warnedAt")).isFalse();
        assertThat(d.has("blockedAt")).isFalse();
        assertThat(new BigDecimal(d.get("costVnd").asText())).isEqualByComparingTo("0");
        assertThat(d.get("tokens").get("quota").asLong()).isEqualTo(500_000);
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private JsonNode hanMuc() throws Exception {
        String body = mvc.perform(get("/api/v1/usage").with(asUser(tenant, admin, "TENANT_ADMIN")))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        return data(body);
    }

    private void nhan(long prompt, long completion, String chiPhi) {
        assertThat(metrics.ghiNhan(suKien(prompt, completion, chiPhi))).isTrue();
    }

    /** Sự kiện ai.turn.completed đúng lược đồ docs/events/ai.turn.completed.v1.json. */
    private JsonNode suKien(long prompt, long completion, String chiPhi) {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("conversation_id", UUID.randomUUID().toString());
        p.put("branch", "RAG");
        p.put("intent", null);
        p.put("status", "SUCCESS");
        p.put("is_answered", true);
        p.put("refusal_reason", null);
        p.put("llm_called", true);
        p.put("is_cached", false);
        p.put("is_degraded", false);
        p.put("is_handoff", false);
        p.put("model_name", "gemini-3.5-flash-lite");
        p.put("model_version", null);
        p.put("prompt_tokens", prompt);
        p.put("completion_tokens", completion);
        p.put("cost_vnd", new BigDecimal(chiPhi));
        p.put("latency_ms", 1200);
        p.put("latency_breakdown", Map.of());
        Map<String, Object> sk = new LinkedHashMap<>();
        sk.put("event_id", UUID.randomUUID().toString());
        sk.put("event_version", 1);
        sk.put("event_type", "TurnCompleted");
        sk.put("tenant_id", tenant.toString());
        sk.put("aggregate_id", p.get("conversation_id"));
        sk.put("occurred_at", Instant.now().toString());
        sk.put("payload", p);
        return mapper.valueToTree(sk);
    }

    private String cot(String ten) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "SELECT " + ten + "::text FROM platform.usage_records WHERE tenant_id = ? AND metric = 'AI_TOKEN'")) {
            ps.setObject(1, tenant);
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString(1) : null;
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
