package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.thesis.crm.engagement.assignment.HandoffWatchdog;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;

/**
 * UC014 (chuyển giao) + UC015 (gán hội thoại): tự giao theo chế độ của doanh nghiệp, trạng thái trực
 * tuyến, sự kiện chuyển giao, trả về hàng chờ, job quá hạn. Hội thoại tạo QUA API WIDGET thật; AI giả
 * trả "chuyển giao" để kích hoạt đúng đường đi của UC014.
 */
class AssignmentIntegrationTest extends EngagementIntegrationTestBase {

    static final UUID TENANT_G = UUID.randomUUID();
    static final UUID TENANT_H = UUID.randomUUID();
    static final UUID ADMIN_G = UUID.randomUUID();
    static final UUID AG1 = UUID.randomUUID();
    static final UUID AG2 = UUID.randomUUID();
    static final UUID USER_H = UUID.randomUUID();
    static final String KEY_G = "wk_g_" + UUID.randomUUID().toString().substring(0, 8);
    static final String ORIGIN_G = "https://shop-g.vn";

    @Autowired HandoffWatchdog watchdog;

    private static boolean seededG;

    @BeforeEach
    void seed() throws Exception {
        AI.respond(FakeAiServer.handoff());
        try (Connection c = owner()) {
            if (!seededG) {
                seededG = true;
                for (UUID t : new UUID[] {TENANT_G, TENANT_H}) {
                    exec(c, "INSERT INTO platform.tenants (id, name, slug, contact_email, status) VALUES (?, 'DN phân công', ?, ?, 'ACTIVE')",
                            t, "g-" + t.toString().substring(0, 8), "a@" + t.toString().substring(0, 8) + ".vn");
                    UUID sub = UUID.randomUUID();
                    exec(c, """
                            INSERT INTO platform.tenant_subscriptions (id, tenant_id, plan_id, status, period_start, period_end)
                            SELECT ?, ?, id, 'ACTIVE', now() - interval '1 day', now() + interval '29 days'
                            FROM platform.subscription_plans WHERE code = 'TRIAL'""", sub, t);
                    exec(c, "INSERT INTO platform.usage_records (tenant_id, subscription_id, metric, used_value, quota_value) "
                            + "VALUES (?, ?, 'CONVERSATION', 0, 1000)", t, sub);
                }
                user(c, TENANT_G, ADMIN_G, "Quản trị G", "TENANT_ADMIN");
                user(c, TENANT_G, AG1, "Nhân viên Một", "AGENT");
                user(c, TENANT_G, AG2, "Nhân viên Hai", "AGENT");
                user(c, TENANT_H, USER_H, "Nhân viên H", "AGENT");
                exec(c, """
                        INSERT INTO engagement.channels (tenant_id, type, name, widget_key, status, config)
                        VALUES (?, 'WEB_WIDGET', 'Web Widget', ?, 'ACTIVE', '{"allowedDomains":["shop-g.vn"]}')""",
                        TENANT_G, KEY_G);
            }
            // Mỗi test bắt đầu sạch: không ai trực, không ai đang giữ việc, chế độ mặc định
            exec(c, "DELETE FROM platform.user_presence WHERE tenant_id = ?", TENANT_G);
            exec(c, "UPDATE engagement.conversations SET status = 'CLOSED' WHERE tenant_id = ?", TENANT_G);
            exec(c, "UPDATE platform.tenants SET assignment_mode = 'LEAST_BUSY' WHERE id = ?", TENANT_G);
            exec(c, "UPDATE platform.usage_records SET used_value = 0 WHERE tenant_id = ?", TENANT_G);
        }
    }

    // ── UC014 b6 / UC015 2b: tự giao ────────────────────────────────────────────

    @Test
    void itViecNhat_giaoChoNguoiDangTrucItViecHon_vaBaoKhachDaCoNguoiNhan() throws Exception {
        online(AG1, true);
        online(AG2, true);
        Cuoc c1 = khachXinGapNguoi();
        Cuoc c2 = khachXinGapNguoi();
        UUID a1 = assignee(c1.conversationId());
        UUID a2 = assignee(c2.conversationId());
        assertThat(a1).isIn(AG1, AG2);
        assertThat(a2).isIn(AG1, AG2).isNotEqualTo(a1);           // người kia đang rảnh hơn
        assertThat(c1.lastSystemText()).isEqualTo("Đã có nhân viên tiếp nhận, bạn chờ trong giây lát nhé.");
        assertThat(trangThai(c1.conversationId())).isEqualTo("AGENT_HANDLING");

        // Sự kiện chuyển giao: AI gây ra, tính vào chất lượng AI, có người nhận
        Map<String, Object> ev = lastEvent(c1.conversationId());
        assertThat(ev).containsEntry("direction", "BOT_TO_AGENT").containsEntry("triggered_by", "AI_AGENT")
                .containsEntry("reason", "CUSTOMER_REQUEST").containsEntry("counts_against_ai_quality", true)
                .containsEntry("to_user_id", a1);
        assertThat(ev.get("accepted_at")).isNotNull();
    }

    @Test
    void nhanVienNgoaiTuyen_boQua_giaoChoQuanTriDangTruc() throws Exception {
        online(AG1, false);
        online(ADMIN_G, true);
        Cuoc c = khachXinGapNguoi();
        assertThat(assignee(c.conversationId())).isEqualTo(ADMIN_G);
    }

    @Test
    void khongAiTruc_vaoHangCho_khachNhanCauChoNhanVien() throws Exception {
        Cuoc c = khachXinGapNguoi();
        assertThat(assignee(c.conversationId())).isNull();
        assertThat(trangThai(c.conversationId())).isEqualTo("PENDING_AGENT");
        assertThat(c.lastSystemText()).startsWith("Cảm ơn bạn! Nhân viên sẽ liên hệ");
        assertThat(lastEvent(c.conversationId()).get("accepted_at")).isNull();
    }

    @Test
    void luanPhien_chiaDeu() throws Exception {
        setMode("ROUND_ROBIN");
        online(AG1, true);
        online(AG2, true);
        UUID a = assignee(khachXinGapNguoi().conversationId());
        UUID b = assignee(khachXinGapNguoi().conversationId());
        UUID c = assignee(khachXinGapNguoi().conversationId());
        assertThat(b).isNotEqualTo(a);
        assertThat(c).isEqualTo(a);
    }

    @Test
    void thuCong_khongTuGiao() throws Exception {
        setMode("MANUAL");
        online(AG1, true);
        assertThat(assignee(khachXinGapNguoi().conversationId())).isNull();
    }

    @Test
    void hetHanMuc_suKienDoHeThong_khongTinhVaoChatLuongAi() throws Exception {
        try (Connection c = owner()) {
            exec(c, "UPDATE platform.usage_records SET used_value = quota_value WHERE tenant_id = ?", TENANT_G);
        }
        Cuoc c = khachNhan("còn hàng không?");
        assertThat(lastEvent(c.conversationId())).containsEntry("reason", "QUOTA_EXCEEDED")
                .containsEntry("triggered_by", "SYSTEM").containsEntry("counts_against_ai_quality", false);
    }

    @Test
    void nhanVienLayKhoiAi_vaTraLaiAi_deuCoSuKien_idThat() throws Exception {
        AI.respond(FakeAiServer.answer("Chào bạn"));
        Cuoc c = khachNhan("chào");
        JsonNode ev = data(mvc.perform(post("/api/v1/conversations/" + c.conversationId() + "/handoff").with(nv(AG1))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"direction\":\"BOT_TO_AGENT\",\"reason\":\"NEGATIVE_SENTIMENT\"}"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(count("SELECT count(*) FROM engagement.handoff_events WHERE id = '" + ev.get("id").asText() + "'")).isEqualTo(1);
        assertThat(ev.get("triggeredBy").asText()).isEqualTo("AGENT");

        mvc.perform(post("/api/v1/conversations/" + c.conversationId() + "/assign").with(nv(AG1))
                .contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isOk());
        assertThat(lastEvent(c.conversationId()).get("accepted_at")).isNotNull();
        mvc.perform(post("/api/v1/conversations/" + c.conversationId() + "/handoff").with(nv(AG1))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"direction\":\"AGENT_TO_BOT\",\"reason\":\"CUSTOMER_REQUEST\"}"))
                .andExpect(status().isOk()).andExpect(jsonPath("$.data.countsAgainstAiQuality").value(false));
        assertThat(lastEvent(c.conversationId())).containsEntry("direction", "AGENT_TO_BOT");
    }

    // ── UC015 1a: trả về hàng chờ ───────────────────────────────────────────────

    @Test
    void traVeHangCho_batLyDo_chiNguoiGiu_giaoLaiNguoiKhacKhongPhaiNguoiVuaTra() throws Exception {
        online(AG1, true);
        Cuoc c = khachXinGapNguoi();
        assertThat(assignee(c.conversationId())).isEqualTo(AG1);
        online(AG2, true);

        release(nv(AG1), c, "bận").andExpect(status().isUnprocessableEntity());
        release(nv(AG2), c, "không phải của tôi").andExpect(status().isForbidden());
        release(nv(AG1), c, "Hết ca làm việc").andExpect(status().isOk())
                .andExpect(jsonPath("$.data.assignedUserId").value(AG2.toString()));
        assertThat(count("SELECT count(*) FROM platform.audit_logs WHERE entity_id = '" + c.conversationId()
                + "' AND action = 'CONVERSATION_RELEASED'")).isEqualTo(1);
    }

    // ── UC014 7.1 / UC015 6.2: job quá hạn ──────────────────────────────────────

    @Test
    void choQuaHan_nangUuTien_quaLauThiKhan() throws Exception {
        Cuoc c = khachXinGapNguoi();                                   // không ai trực → hàng chờ
        setHandover(c.conversationId(), 6);
        watchdog.runOnce(Instant.now());
        assertThat(priority(c.conversationId())).isEqualTo("HIGH");
        assertThat(count("SELECT count(*) FROM platform.audit_logs WHERE entity_id = '" + c.conversationId()
                + "' AND action = 'CONVERSATION_ESCALATED' AND severity = 'WARNING'")).isEqualTo(1);
        setHandover(c.conversationId(), 16);
        watchdog.runOnce(Instant.now());
        assertThat(priority(c.conversationId())).isEqualTo("URGENT");

        // Có người vào trực → lần chạy sau giao luôn
        online(AG2, true);
        watchdog.runOnce(Instant.now());
        assertThat(assignee(c.conversationId())).isEqualTo(AG2);
    }

    @Test
    void daGiaoMaNguoiDoNgoaiTuyenKhongTraLoi_tuTraVeHangCho_giaoNguoiKhac() throws Exception {
        online(AG1, true);
        Cuoc c = khachXinGapNguoi();
        assertThat(assignee(c.conversationId())).isEqualTo(AG1);
        online(AG1, false);
        online(AG2, true);
        try (Connection con = owner()) {
            exec(con, "UPDATE engagement.conversations SET assigned_at = now() - interval '6 minutes' WHERE id = ?",
                    UUID.fromString(c.conversationId()));
        }
        watchdog.runOnce(Instant.now());
        assertThat(assignee(c.conversationId())).isEqualTo(AG2);
        assertThat(count("SELECT count(*) FROM platform.audit_logs WHERE entity_id = '" + c.conversationId()
                + "' AND action = 'CONVERSATION_AUTO_RELEASED'")).isEqualTo(1);
    }

    @Test
    void daGiaoVaNguoiDoDaTraLoi_khongBiTraVe() throws Exception {
        online(AG1, true);
        Cuoc c = khachXinGapNguoi();
        mvc.perform(post("/api/v1/conversations/" + c.conversationId() + "/messages").with(nv(AG1))
                .contentType(MediaType.APPLICATION_JSON).content("{\"content\":\"Một đây\"}")).andExpect(status().isCreated());
        online(AG1, false);
        try (Connection con = owner()) {
            exec(con, "UPDATE engagement.conversations SET assigned_at = now() - interval '6 minutes' WHERE id = ?",
                    UUID.fromString(c.conversationId()));
            exec(con, "UPDATE engagement.messages SET sent_at = now() WHERE conversation_id = ? AND sender_type = 'AGENT'",
                    UUID.fromString(c.conversationId()));
        }
        watchdog.runOnce(Instant.now());
        assertThat(assignee(c.conversationId())).isEqualTo(AG1);
    }

    // ── trực tuyến, ô chọn người, thanh cảnh báo ────────────────────────────────

    @Test
    void moHopThu_laDangTruc_oChonNguoiDungTrangThai_khongLanDoanhNghiepKhac() throws Exception {
        mvc.perform(get("/api/v1/conversations").with(nv(AG1))).andExpect(status().isOk());
        JsonNode list = data(mvc.perform(get("/api/v1/conversations/assignees").with(admin()))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        boolean sawAg1Online = false;
        for (JsonNode a : list) {
            assertThat(a.get("userId").asText()).isNotEqualTo(USER_H.toString());
            if (a.get("userId").asText().equals(AG1.toString())) {
                sawAg1Online = a.get("online").asBoolean();
            }
            if (a.get("userId").asText().equals(AG2.toString())) {
                assertThat(a.get("online").asBoolean()).isFalse();
            }
        }
        assertThat(sawAg1Online).isTrue();
    }

    @Test
    void tinhTrangHangCho_chiQuanTri_demDung() throws Exception {
        Cuoc c = khachXinGapNguoi();
        setHandover(c.conversationId(), 6);
        mvc.perform(get("/api/v1/conversations/queue-status").with(nv(AG1))).andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/conversations/queue-status").with(admin())).andExpect(status().isOk())
                .andExpect(jsonPath("$.data.waitingTotal").value(1))
                .andExpect(jsonPath("$.data.waitingOverdue").value(1));
    }

    // ── Rà soát: lỗ hổng tìm ra sau khi chạy thật ──────────────────────────────

    @Test
    void daCoNguoiNhan_uuTienVeThuong() throws Exception {
        // R1: chip "Khẩn" là để kéo người tới nhận. Đã có người nhận mà vẫn "Khẩn" mãi là báo động giả.
        Cuoc c = khachXinGapNguoi();
        setHandover(c.conversationId(), 16);
        watchdog.runOnce(Instant.now());
        assertThat(priority(c.conversationId())).isEqualTo("URGENT");
        mvc.perform(post("/api/v1/conversations/" + c.conversationId() + "/assign").with(nv(AG1))
                .contentType(MediaType.APPLICATION_JSON).content("{}")).andExpect(status().isOk());
        assertThat(priority(c.conversationId())).isEqualTo("NORMAL");
    }

    @Test
    void traVeHangCho_dongHoChoTinhLaiTuLucTraVe() throws Exception {
        // R2: hội thoại chuyển giao từ 3 giờ trước, vừa bị trả về hàng chờ → không được "quá hạn" ngay.
        online(AG1, true);
        Cuoc c = khachXinGapNguoi();
        setHandover(c.conversationId(), 180);
        online(AG1, false);
        setMode("MANUAL");
        release(nv(AG1), c, "Hết ca làm việc").andExpect(status().isOk());
        watchdog.runOnce(Instant.now());
        assertThat(priority(c.conversationId())).isEqualTo("NORMAL");
        mvc.perform(get("/api/v1/conversations/queue-status").with(admin()))
                .andExpect(jsonPath("$.data.waitingOverdue").value(0));
    }

    @Test
    void nguoiCoHaiVaiTro_chiHienMotLanTrongOChon() throws Exception {
        // R3: user_roles cho phép một người nhiều vai trò → JOIN nhân đôi dòng.
        try (Connection c = owner()) {
            exec(c, """
                    INSERT INTO platform.user_roles (user_id, role_id, tenant_id)
                    SELECT ?, id, ? FROM platform.roles WHERE code = 'TENANT_ADMIN' AND tenant_id IS NULL
                    ON CONFLICT DO NOTHING""", AG2, TENANT_G);
        }
        try {
            JsonNode list = data(mvc.perform(get("/api/v1/conversations/assignees").with(admin()))
                    .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
            int n = 0;
            for (JsonNode a : list) {
                if (a.get("userId").asText().equals(AG2.toString())) {
                    n++;
                    assertThat(a.get("role").asText()).isEqualTo("AGENT");   // vai trò nhân viên được ưu tiên
                }
            }
            assertThat(n).isEqualTo(1);
        } finally {
            try (Connection c = owner()) {
                exec(c, """
                        DELETE FROM platform.user_roles WHERE user_id = ?
                          AND role_id = (SELECT id FROM platform.roles WHERE code = 'TENANT_ADMIN' AND tenant_id IS NULL)""", AG2);
            }
        }
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    record Cuoc(String token, String conversationId, String lastSystemText) {}

    private Cuoc khachXinGapNguoi() throws Exception {
        AI.respond(FakeAiServer.handoff());
        return khachNhan("cho tôi gặp nhân viên");
    }

    private Cuoc khachNhan(String content) throws Exception {
        String token = data(mvc.perform(post("/api/v1/widget/session").header("Origin", ORIGIN_G)
                        .header("X-Forwarded-For", "10.7." + ThreadLocalRandom.current().nextInt(256) + ".3")
                        .contentType(MediaType.APPLICATION_JSON).content("{\"widgetKey\":\"" + KEY_G + "\"}"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8))
                .get("token").asText();
        JsonNode turn = data(mvc.perform(post("/api/v1/widget/messages").header("Origin", ORIGIN_G)
                        .header("X-Widget-Token", token).contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of("content", content))))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        String sys = null;
        for (JsonNode m : turn.get("messages")) {
            if ("SYSTEM".equals(m.get("senderType").asText())) {
                sys = m.get("content").asText();
            }
        }
        String convId;
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "SELECT conversation_id FROM engagement.messages WHERE id = ?::uuid")) {
            ps.setString(1, turn.get("messages").get(0).get("id").asText());
            ResultSet rs = ps.executeQuery();
            rs.next();
            convId = rs.getString(1);
        }
        return new Cuoc(token, convId, sys);
    }

    private org.springframework.test.web.servlet.ResultActions release(JwtRequestPostProcessor who, Cuoc c, String reason)
            throws Exception {
        return mvc.perform(post("/api/v1/conversations/" + c.conversationId() + "/release").with(who)
                .contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsString(Map.of("reason", reason))));
    }

    private static JwtRequestPostProcessor nv(UUID agent) {
        return asUser(TENANT_G, agent, "AGENT");
    }

    private static JwtRequestPostProcessor admin() {
        return asUser(TENANT_G, ADMIN_G, "TENANT_ADMIN");
    }

    private static void online(UUID user, boolean on) throws Exception {
        try (Connection c = owner()) {
            exec(c, """
                    INSERT INTO platform.user_presence (user_id, tenant_id, last_active_at)
                    VALUES (?, ?, CASE WHEN ? THEN now() ELSE now() - interval '10 minutes' END)
                    ON CONFLICT (user_id) DO UPDATE SET last_active_at = EXCLUDED.last_active_at""",
                    user, TENANT_G, on);
        }
    }

    private static void setMode(String mode) throws Exception {
        try (Connection c = owner()) {
            exec(c, "UPDATE platform.tenants SET assignment_mode = ? WHERE id = ?", mode, TENANT_G);
        }
    }

    private static void setHandover(String conversationId, int minutesAgo) throws Exception {
        try (Connection c = owner()) {
            exec(c, "UPDATE engagement.conversations SET handover_at = now() - make_interval(mins => ?), "
                    + "queued_at = CASE WHEN assigned_user_id IS NULL THEN now() - make_interval(mins => ?) END WHERE id = ?",
                    minutesAgo, minutesAgo, UUID.fromString(conversationId));
        }
    }

    private static UUID assignee(String conversationId) throws Exception {
        return one("SELECT assigned_user_id FROM engagement.conversations WHERE id = '" + conversationId + "'", UUID.class);
    }

    private static String trangThai(String conversationId) throws Exception {
        return one("SELECT status FROM engagement.conversations WHERE id = '" + conversationId + "'", String.class);
    }

    private static String priority(String conversationId) throws Exception {
        return one("SELECT priority FROM engagement.conversations WHERE id = '" + conversationId + "'", String.class);
    }

    private static Map<String, Object> lastEvent(String conversationId) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement("""
                SELECT direction, reason, triggered_by, counts_against_ai_quality, to_user_id, accepted_at
                FROM engagement.handoff_events WHERE conversation_id = ?::uuid ORDER BY occurred_at DESC LIMIT 1""")) {
            ps.setString(1, conversationId);
            ResultSet rs = ps.executeQuery();
            assertThat(rs.next()).as("phải có sự kiện chuyển giao").isTrue();
            Map<String, Object> m = new java.util.HashMap<>();
            m.put("direction", rs.getString(1));
            m.put("reason", rs.getString(2));
            m.put("triggered_by", rs.getString(3));
            m.put("counts_against_ai_quality", rs.getBoolean(4));
            m.put("to_user_id", rs.getObject(5, UUID.class));
            m.put("accepted_at", rs.getTimestamp(6));
            return m;
        }
    }

    private static long count(String sql) throws Exception {
        Long n = one(sql, Long.class);
        return n == null ? 0 : n;
    }

    private static <T> T one(String sql, Class<T> type) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(sql)) {
            ResultSet rs = ps.executeQuery();
            rs.next();
            return rs.getObject(1, type);
        }
    }

    private static void user(Connection c, UUID tenant, UUID id, String name, String role) throws Exception {
        exec(c, "INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status) VALUES (?, ?, ?, 'x', ?, 'ACTIVE')",
                id, tenant, id.toString().substring(0, 8) + "@g.vn", name);
        exec(c, """
                INSERT INTO platform.user_roles (user_id, role_id, tenant_id)
                SELECT ?, id, ? FROM platform.roles WHERE code = ? AND tenant_id IS NULL""", id, tenant, role);
    }

    private static void exec(Connection c, String sql, Object... args) throws Exception {
        try (PreparedStatement ps = c.prepareStatement(sql)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            ps.executeUpdate();
        }
    }
}
