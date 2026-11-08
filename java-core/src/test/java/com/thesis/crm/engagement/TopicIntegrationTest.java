package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.analytics.service.TurnMetricsService;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * UC038 lớp 1 — sự kiện {@code ai.turn.completed} mang ý định được cộng vào {@code analytics.topic_conversations}
 * và đọc qua {@code GET /api/v1/analytics/topics}. Gọi thẳng logic consumer như test UC039.
 *
 * <p>Mỗi test một doanh nghiệp riêng — số liệu là tổng cộng dồn.
 */
class TopicIntegrationTest extends EngagementIntegrationTestBase {

    @Autowired TurnMetricsService metrics;
    @Autowired ObjectMapper mapper;

    private UUID tenant;
    private UUID admin;
    private UUID agent;
    private UUID channel;
    private UUID contact;
    private UUID identity;

    @BeforeEach
    void doanhNghiepMoi() throws Exception {
        tenant = UUID.randomUUID();
        admin = UUID.randomUUID();
        agent = UUID.randomUUID();
        channel = UUID.randomUUID();
        contact = UUID.randomUUID();
        identity = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES (?, 'DN chủ đề', ?, ?)",
                    tenant, "cd-" + tenant.toString().substring(0, 8), "cd@" + tenant.toString().substring(0, 8) + ".vn");
            for (UUID u : new UUID[] {admin, agent}) {
                exec(c, """
                        INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                        VALUES (?, ?, ?, 'x', 'Người dùng', 'ACTIVE')""", u, tenant, u.toString().substring(0, 8) + "@cd.vn");
            }
            exec(c, "INSERT INTO engagement.channels (id, tenant_id, type, name, status) VALUES (?, ?, 'ZALO', 'Zalo', 'ACTIVE')",
                    channel, tenant);
            exec(c, "INSERT INTO engagement.contacts (id, tenant_id, full_name, primary_channel) VALUES (?, ?, 'Khách', 'ZALO')",
                    contact, tenant);
            exec(c, """
                    INSERT INTO engagement.channel_identities (id, tenant_id, channel_id, contact_id, external_user_id)
                    VALUES (?, ?, ?, ?, ?)""", identity, tenant, channel, contact, "zl-" + identity);
        }
    }

    @Test
    void demTheoHoiThoai_khongTheoLuot_tuChoiVaTuXuLyDung() throws Exception {
        UUID a = hoiThoai();
        UUID b = hoiThoai();
        UUID c = hoiThoai();
        // a hỏi giá 3 lượt, tác tử trả lời cả 3 → 1 hội thoại tự xử lý
        for (int i = 0; i < 3; i++) {
            nhan(a, "PRICING_POLICY", "RAG", true, false, "SUCCESS");
        }
        // b hỏi giá, 1 lượt trả lời + 1 lượt từ chối → bị từ chối, không tính tự xử lý
        nhan(b, "PRICING_POLICY", "RAG", true, false, "SUCCESS");
        nhan(b, "PRICING_POLICY", "RAG", false, false, "SUCCESS");
        // c hỏi giá rồi chuyển giao → không từ chối, không tự xử lý
        nhan(c, "PRICING_POLICY", "HANDOFF", false, true, "SUCCESS");

        JsonNode gia = theoKhoa(baoCao("")).get("PRICING_POLICY");
        assertThat(gia.get("conversationCount").asLong()).isEqualTo(3);
        assertThat(gia.get("botResolvedCount").asLong()).isEqualTo(1);
        assertThat(gia.get("refusalCount").asLong()).isEqualTo(1);
        assertThat(gia.get("topicLabel").asText()).isEqualTo("Giá và chính sách");
        assertThat(gia.get("dimension").asText()).isEqualTo("INTENT");
        assertThat(gia.get("clusterId").isNull()).isTrue();
        assertThat(motCot("SELECT turn_count FROM analytics.topic_conversations WHERE conversation_id = ?", a))
                .isEqualTo("3");
    }

    @Test
    void hoiLaiVaLoiHeThong_khongTinhLaTuChoi() throws Exception {
        UUID a = hoiThoai();
        UUID b = hoiThoai();
        nhan(a, "KB_SEARCH", "CLARIFY", false, false, "SUCCESS");    // chưa hiểu câu, không phải thiếu tài liệu
        nhan(b, "KB_SEARCH", "RAG", false, false, "FAILED");        // lỗi hạ tầng
        JsonNode tra = theoKhoa(baoCao("")).get("KB_SEARCH");
        assertThat(tra.get("conversationCount").asLong()).isEqualTo(2);
        assertThat(tra.get("refusalCount").asLong()).isZero();
        assertThat(tra.get("botResolvedCount").asLong()).isZero();
    }

    @Test
    void khongCoYDinh_hoacHoiThoaiLa_boQuaChuDe_nhungUC039VanCong() throws Exception {
        UUID a = hoiThoai();
        nhan(a, null, "RAG", true, false, "SUCCESS");
        nhan(UUID.randomUUID(), "KB_SEARCH", "RAG", true, false, "SUCCESS");   // hội thoại không có ở CRM
        assertThat(baoCao("")).isEmpty();
        assertThat(motCot("SELECT sum(interaction_count) FROM analytics.metrics_daily WHERE tenant_id = ?", tenant))
                .isEqualTo("2");
    }

    @Test
    void suKienGiaoLai_khongCongHaiLan() throws Exception {
        UUID a = hoiThoai();
        JsonNode sk = suKien(a, "TECH_ERROR", "RAG", false, false, "SUCCESS");
        assertThat(metrics.ghiNhan(sk)).isTrue();
        assertThat(metrics.ghiNhan(sk)).isFalse();
        assertThat(motCot("SELECT turn_count FROM analytics.topic_conversations WHERE conversation_id = ?", a))
                .isEqualTo("1");
    }

    @Test
    void xoaHoiThoai_soLieuChuDeDiTheo() throws Exception {
        UUID a = hoiThoai();
        nhan(a, "GREETING", "SMALL_TALK", true, false, "SUCCESS");
        try (Connection c = owner()) {
            exec(c, "DELETE FROM engagement.conversations WHERE id = ?", a);
        }
        assertThat(baoCao("")).isEmpty();
    }

    @Test
    void cachLyDoanhNghiep_nhanVien403_lopSai400() throws Exception {
        nhan(hoiThoai(), "BUYING_INTENT", "HANDOFF", false, true, "SUCCESS");
        UUID cu = tenant;
        doanhNghiepMoi();
        assertThat(baoCao("")).isEmpty();
        assertThat(cu).isNotEqualTo(tenant);

        mvc.perform(get("/api/v1/analytics/topics").with(asUser(tenant, agent, "AGENT")))
                .andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/analytics/topics?dimension=ABC").with(asUser(tenant, admin, "TENANT_ADMIN")))
                .andExpect(status().isBadRequest());
    }

    @AfterEach
    void traLaiAiGia() {
        AI.topicClusters.set(new FakeAiServer.Script(204, "", 0));
    }

    @Test
    void lopCum_ghepGanCumVoiSoLieuTuChoi_guiDungTenant() throws Exception {
        UUID a = hoiThoai();
        UUID b = hoiThoai();
        UUID c = hoiThoai();
        // a: hai ý định trong cùng ngày, cả hai trả lời được → MỘT hội thoại tự xử lý của cụm
        nhan(a, "PRICING_POLICY", "RAG", true, false, "SUCCESS");
        nhan(a, "KB_SEARCH", "RAG", true, false, "SUCCESS");
        nhan(b, "KB_SEARCH", "RAG", false, false, "SUCCESS");          // bị từ chối
        nhan(c, "KB_SEARCH", "RAG", true, false, "SUCCESS");
        UUID hoaDon = UUID.randomUUID();
        UUID giaoHang = UUID.randomUUID();
        AI.topicClusters.set(new FakeAiServer.Script(200, """
                {"run_id":"%s","started_at":"%s","window_from":"%s","window_to":"%s","conversation_count":3,
                 "min_conversations":3,"status":"DONE","skip_reason":null,"vector_source":"router-tfidf-ngram",
                 "k":2,"silhouette":0.31,"naming_method":"tu-khoa",
                 "clusters":[{"cluster_id":"%s","label":"Hoá đơn · VAT","size":2},
                             {"cluster_id":"%s","label":"Giao hàng","size":1}],
                 "assignments":[{"conversation_id":"%s","cluster_id":"%s"},{"conversation_id":"%s","cluster_id":"%s"},
                                {"conversation_id":"%s","cluster_id":"%s"}]}""".formatted(UUID.randomUUID(), Instant.now(),
                Instant.now().minusSeconds(86400), Instant.now(), hoaDon, giaoHang, a, hoaDon, b, hoaDon, c, giaoHang), 0));

        Map<String, JsonNode> cum = theoKhoa(baoCao("?dimension=CLUSTER"));
        JsonNode hd = cum.get(hoaDon.toString());
        assertThat(hd.get("topicLabel").asText()).isEqualTo("Hoá đơn · VAT");
        assertThat(hd.get("conversationCount").asLong()).isEqualTo(2);       // a tính MỘT lần dù hai ý định
        assertThat(hd.get("botResolvedCount").asLong()).isEqualTo(1);
        assertThat(hd.get("refusalCount").asLong()).isEqualTo(1);
        assertThat(hd.get("clusterId").asText()).isEqualTo(hoaDon.toString());
        assertThat(cum.get(giaoHang.toString()).get("conversationCount").asLong()).isEqualTo(1);
        assertThat(AI.lastTopicTenant.get()).isEqualTo(tenant.toString());   // tenant từ JWT, qua header

        JsonNode ky = kyPhanCum();
        assertThat(ky.get("vectorSource").asText()).isEqualTo("router-tfidf-ngram");
        assertThat(ky.get("k").asInt()).isEqualTo(2);
        assertThat(ky.get("namingMethod").asText()).isEqualTo("tu-khoa");
    }

    @Test
    void lopCum_kyBiBoQua_traRongVaNoiLyDo() throws Exception {
        AI.topicClusters.set(new FakeAiServer.Script(200, """
                {"run_id":"%s","started_at":"%s","window_from":"%s","window_to":"%s","conversation_count":5,
                 "min_conversations":200,"status":"SKIPPED","skip_reason":"TOO_FEW_CONVERSATIONS",
                 "clusters":[],"assignments":[]}""".formatted(UUID.randomUUID(), Instant.now(),
                Instant.now().minusSeconds(86400), Instant.now()), 0));
        assertThat(baoCao("?dimension=CLUSTER")).isEmpty();
        JsonNode ky = kyPhanCum();
        assertThat(ky.get("skipReason").asText()).isEqualTo("TOO_FEW_CONVERSATIONS");
        assertThat(ky.get("minConversations").asInt()).isEqualTo(200);
    }

    @Test
    void lopCum_chuaCoKyNao_traRong_aiHong503() throws Exception {
        assertThat(baoCao("?dimension=CLUSTER")).isEmpty();
        assertThat(kyPhanCum().isNull()).isTrue();
        AI.topicClusters.set(new FakeAiServer.Script(500, "{\"code\":\"INTERNAL\",\"message\":\"x\"}", 0));
        mvc.perform(get("/api/v1/analytics/topics?dimension=CLUSTER").with(asUser(tenant, admin, "TENANT_ADMIN")))
                .andExpect(status().isServiceUnavailable());
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private UUID hoiThoai() throws Exception {
        UUID id = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, """
                    INSERT INTO engagement.conversations (id, tenant_id, channel_id, channel_identity_id, contact_id)
                    VALUES (?, ?, ?, ?, ?)""", id, tenant, channel, identity, contact);
        }
        return id;
    }

    private JsonNode baoCao(String query) throws Exception {
        String body = mvc.perform(get("/api/v1/analytics/topics" + query).with(asUser(tenant, admin, "TENANT_ADMIN")))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        return data(body);
    }

    private JsonNode kyPhanCum() throws Exception {
        String body = mvc.perform(get("/api/v1/analytics/topics/cluster-run").with(asUser(tenant, admin, "TENANT_ADMIN")))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        return json.readTree(body).get("data");
    }

    /** Một ngày duy nhất trong test → mỗi chủ đề đúng một dòng. */
    private static Map<String, JsonNode> theoKhoa(JsonNode ds) {
        Map<String, JsonNode> m = new HashMap<>();
        ds.forEach(d -> m.put(d.get("topicKey").asText(), d));
        return m;
    }

    private void nhan(UUID conv, String yDinh, String branch, boolean traLoi, boolean chuyenGiao, String trangThai) {
        assertThat(metrics.ghiNhan(suKien(conv, yDinh, branch, traLoi, chuyenGiao, trangThai))).isTrue();
    }

    /** Sự kiện ai.turn.completed đúng lược đồ docs/events/ai.turn.completed.v1.json (có trường intent). */
    private JsonNode suKien(UUID conv, String yDinh, String branch, boolean traLoi, boolean chuyenGiao,
            String trangThai) {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("conversation_id", conv.toString());
        p.put("branch", branch);
        p.put("intent", yDinh);
        p.put("status", trangThai);
        p.put("is_answered", traLoi);
        p.put("refusal_reason", traLoi ? null : "NOT_COVERED");
        p.put("llm_called", false);
        p.put("is_cached", false);
        p.put("is_degraded", false);
        p.put("is_handoff", chuyenGiao);
        p.put("model_name", "template");
        p.put("model_version", null);
        p.put("prompt_tokens", 0);
        p.put("completion_tokens", 0);
        p.put("cost_vnd", 0);
        p.put("latency_ms", 10);
        p.put("latency_breakdown", Map.of());
        Map<String, Object> sk = new LinkedHashMap<>();
        sk.put("event_id", UUID.randomUUID().toString());
        sk.put("event_version", 1);
        sk.put("event_type", "TurnCompleted");
        sk.put("tenant_id", tenant.toString());
        sk.put("aggregate_id", conv.toString());
        sk.put("occurred_at", Instant.now().toString());
        sk.put("payload", p);
        return mapper.valueToTree(sk);
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

    private static void exec(Connection c, String query, Object... args) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement(query)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            ps.executeUpdate();
        }
    }
}
