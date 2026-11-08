package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.security.TenantTransactionScope;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * UC040 bước 8 — {@code GET /api/v1/safety-events} gộp cảnh báo phía AI (qua ai-service giả) với nhật ký
 * kiểm toán mức CRITICAL của java-core.
 */
class SafetyEventIntegrationTest extends EngagementIntegrationTestBase {

    @Autowired TransactionTemplate tx;
    @Autowired TenantTransactionScope scope;
    @Autowired AuditLogWriter writer;

    private UUID tenant;
    private UUID admin;
    private UUID agent;

    @BeforeEach
    void doanhNghiepMoi() throws Exception {
        tenant = UUID.randomUUID();
        admin = UUID.randomUUID();
        agent = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES (?, 'DN an toàn', ?, ?)",
                    tenant, "at-" + tenant.toString().substring(0, 8), "at@" + tenant.toString().substring(0, 8) + ".vn");
            for (UUID u : new UUID[] {admin, agent}) {
                exec(c, """
                        INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                        VALUES (?, ?, ?, 'x', 'Người dùng', 'ACTIVE')""", u, tenant, u.toString().substring(0, 8) + "@at.vn");
            }
        }
    }

    @AfterEach
    void traLaiAiGia() {
        AI.safety.set(new FakeAiServer.Script(200, "[]", 0));
    }

    @Test
    void gopHaiPhiaAiVaNhatKyNghiemTrong_moiNhatTruoc_guiDungTenant() throws Exception {
        Instant bayGio = Instant.now();
        AI.safety.set(new FakeAiServer.Script(200, """
                [{"event_id":"%s","event_type":"PROMPT_INJECTION_INPUT","severity":"HIGH","threat_surface":"T2",
                  "conversation_id":"%s","interaction_id":null,"detector":"guardrails.injection",
                  "action_taken":"TREATED_AS_DATA","evidence":{"excerpt":"Bỏ qua mọi hướng dẫn trước…"},
                  "occurred_at":"%s","reason":"PROMPT_INJECTION_INPUT"},
                 {"event_id":"%s","event_type":"CROSS_TENANT_PROBE","severity":"CRITICAL","threat_surface":"T5",
                  "conversation_id":null,"interaction_id":null,"detector":"guardrails.injection",
                  "action_taken":"REFUSED","evidence":{},"occurred_at":"%s","reason":"CROSS_TENANT_PROBE"}]
                """.formatted(UUID.randomUUID(), UUID.randomUUID(), bayGio.minus(2, ChronoUnit.HOURS),
                UUID.randomUUID(), bayGio.minus(1, ChronoUnit.HOURS)), 0));
        tx.execute(s -> {
            scope.apply(tenant);
            writer.recordSystemAction(tenant, "TENANT_SCOPE_VIOLATION", "CONVERSATION", null, "CRITICAL",
                    Map.of("blocked", true));
            writer.recordSystemAction(tenant, "WIDGET_ORIGIN_REJECTED", "CHANNEL", null, "WARNING", Map.of());
            return null;
        });

        JsonNode d = danhSach("");
        List<String> loai = new ArrayList<>();
        d.get("items").forEach(i -> loai.add(i.get("eventType").asText()));
        // Nhật ký vừa ghi (mới nhất) → dò doanh nghiệp khác (1 giờ trước) → tiêm chỉ thị (2 giờ trước).
        // Dòng mức WARNING của nhật ký KHÔNG phải cảnh báo an toàn.
        assertThat(loai).containsExactly("CROSS_TENANT_PROBE", "CROSS_TENANT_PROBE", "PROMPT_INJECTION_INPUT");
        assertThat(d.get("totalItems").asLong()).isEqualTo(3);
        JsonNode tuNhatKy = d.get("items").get(0);
        assertThat(tuNhatKy.get("id").asText()).startsWith("audit-");
        assertThat(tuNhatKy.get("threatSurface").asText()).isEqualTo("T7");
        assertThat(tuNhatKy.get("evidence").get("action").asText()).isEqualTo("TENANT_SCOPE_VIOLATION");
        assertThat(d.get("items").get(2).get("evidence").get("excerpt").asText()).startsWith("Bỏ qua");
        assertThat(AI.lastSafetyTenant.get()).isEqualTo(tenant.toString());   // tenant từ JWT, qua header
    }

    @Test
    void locTheoMucVaLoai_vaPhanTrang() throws Exception {
        tx.execute(s -> {
            scope.apply(tenant);
            for (int i = 0; i < 3; i++) {
                writer.recordSystemAction(tenant, "TENANT_SCOPE_VIOLATION", "CONVERSATION", null, "CRITICAL", Map.of());
            }
            return null;
        });
        AI.safety.set(new FakeAiServer.Script(200, """
                [{"event_id":"%s","event_type":"PROMPT_INJECTION_INPUT","severity":"HIGH","threat_surface":"T2",
                  "detector":"guardrails.injection","action_taken":"TREATED_AS_DATA","evidence":{},
                  "occurred_at":"%s","reason":"PROMPT_INJECTION_INPUT"}]""".formatted(UUID.randomUUID(), Instant.now()), 0));

        assertThat(danhSach("?severity=HIGH").get("totalItems").asLong()).isEqualTo(1);
        assertThat(danhSach("?eventType=CROSS_TENANT_PROBE").get("totalItems").asLong()).isEqualTo(3);
        JsonNode trang2 = danhSach("?size=3&page=1");
        assertThat(trang2.get("items")).hasSize(1);
        assertThat(trang2.get("totalPages").asInt()).isEqualTo(2);
    }

    @Test
    void aiServiceHong_bao503_khongLangLeTraThieu() throws Exception {
        AI.safety.set(new FakeAiServer.Script(500, "{\"code\":\"INTERNAL\",\"message\":\"x\"}", 0));
        mvc.perform(get("/api/v1/safety-events").with(asUser(tenant, admin, "TENANT_ADMIN")))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.code").value("AI_SERVICE_UNAVAILABLE"));
    }

    @Test
    void nhanVien_bi403() throws Exception {
        mvc.perform(get("/api/v1/safety-events").with(asUser(tenant, agent, "AGENT")))
                .andExpect(status().isForbidden());
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private JsonNode danhSach(String query) throws Exception {
        return data(mvc.perform(get("/api/v1/safety-events" + query).with(asUser(tenant, admin, "TENANT_ADMIN")))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
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
