package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;
import org.springframework.test.web.servlet.ResultActions;

/**
 * UC012 + UC013 (cùng thao tác UC014/UC015) — hộp thư hợp nhất và nhân viên trả lời. Hội thoại
 * được tạo QUA API WIDGET thật, nên test kiểm luôn cả vòng: khách nhắn → nhân viên thấy → nhân viên
 * trả lời → khách nhận trên widget.
 */
class InboxIntegrationTest extends EngagementIntegrationTestBase {

    static final UUID TENANT_I = UUID.randomUUID();
    static final UUID TENANT_J = UUID.randomUUID();
    static final UUID ADMIN_I = UUID.randomUUID();
    static final UUID AGENT_1 = UUID.randomUUID();
    static final UUID AGENT_2 = UUID.randomUUID();
    static final UUID ADMIN_J = UUID.randomUUID();
    static final String KEY_I = "wk_i_" + UUID.randomUUID().toString().substring(0, 8);
    static final String ORIGIN_I = "https://shop-i.vn";

    private static boolean seededInbox;

    @BeforeEach
    void seedInbox() throws Exception {
        AI.respond(FakeAiServer.answer("Gói Pro giá 3.990.000đ mỗi tháng."));
        if (seededInbox) {
            return;
        }
        seededInbox = true;
        try (Connection c = owner()) {
            for (UUID t : new UUID[] {TENANT_I, TENANT_J}) {
                exec(c, """
                        INSERT INTO platform.tenants (id, name, slug, contact_email, status, assignment_mode)
                        VALUES (?, 'DN hộp thư', ?, ?, 'ACTIVE', 'MANUAL')""", t, "i-" + t.toString().substring(0, 8),
                        "a@" + t.toString().substring(0, 8) + ".vn");
                UUID sub = UUID.randomUUID();
                exec(c, """
                        INSERT INTO platform.tenant_subscriptions (id, tenant_id, plan_id, status, period_start, period_end)
                        SELECT ?, ?, id, 'ACTIVE', now() - interval '1 day', now() + interval '29 days'
                        FROM platform.subscription_plans WHERE code = 'TRIAL'""", sub, t);
                exec(c, """
                        INSERT INTO platform.usage_records (tenant_id, subscription_id, metric, used_value, quota_value)
                        VALUES (?, ?, 'CONVERSATION', 0, 1000)""", t, sub);
            }
            for (Object[] u : new Object[][] {{ADMIN_I, TENANT_I, "Quản trị I"}, {AGENT_1, TENANT_I, "Nhân viên Một"},
                    {AGENT_2, TENANT_I, "Nhân viên Hai"}, {ADMIN_J, TENANT_J, "Quản trị J"}}) {
                exec(c, """
                        INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                        VALUES (?, ?, ?, 'x', ?, 'ACTIVE')""", u[0], u[1], u[0].toString().substring(0, 8) + "@i.vn", u[2]);
            }
            exec(c, """
                    INSERT INTO engagement.channels (tenant_id, type, name, widget_key, status, config)
                    VALUES (?, 'WEB_WIDGET', 'Web Widget', ?, 'ACTIVE', '{"allowedDomains":["shop-i.vn"]}')""",
                    TENANT_I, KEY_I);
        }
    }

    // ── UC012: xem ──────────────────────────────────────────────────────────────

    @Test
    void khachNhanQuaWidget_hienTrongHopThu_kemTrichTinCuoiVaChuaDoc() throws Exception {
        Khach k = khachMoi("gói pro bao nhiêu?");
        JsonNode row = findInList(admin(), k.conversationId(), "all");
        assertThat(row.get("contactName").asText()).startsWith("Khách web #");
        assertThat(row.get("channelType").asText()).isEqualTo("WEB_WIDGET");
        assertThat(row.get("status").asText()).isEqualTo("BOT_HANDLING");
        assertThat(row.get("lastMessagePreview").asText()).isEqualTo("Gói Pro giá 3.990.000đ mỗi tháng.");
        assertThat(row.get("unreadCount").asInt()).isEqualTo(1);
        assertThat(row.get("priority").asInt()).isEqualTo(1);

        // Chờ nhận: có; của tôi: không (chưa ai nhận)
        assertThat(findInList(nv(AGENT_1), k.conversationId(), "unassigned")).isNotNull();
        assertThat(findInList(nv(AGENT_1), k.conversationId(), "mine")).isNull();
        // Tìm không dấu theo tên khách
        String body = list(admin(), "all", "&q=khach web").andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        assertThat(body).contains(k.conversationId());
    }

    @Test
    void chiTiet_tinTheoThuTu_tinAiKemTrichDan_vaDanhDauDaDoc() throws Exception {
        Khach k = khachMoi("gói pro bao nhiêu?");
        JsonNode d = data(mvc.perform(get("/api/v1/conversations/" + k.conversationId()).with(admin()))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(d.get("messages")).hasSize(2);
        assertThat(d.get("messages").get(0).get("senderType").asText()).isEqualTo("CUSTOMER");
        JsonNode bot = d.get("messages").get(1);
        assertThat(bot.get("senderType").asText()).isEqualTo("BOT");
        assertThat(bot.get("citations").get(0).get("documentTitle").asText()).isEqualTo("Bảng giá 2026");
        assertThat(bot.get("citations").get(0).get("chunkId").asText()).isEqualTo("11111111-1111-1111-1111-111111111111");
        assertThat(d.get("autoReplyEnabled").asBoolean()).isTrue();
        assertThat(d.get("firstResponseAt").isNull()).isTrue();      // chưa có NGƯỜI trả lời
        assertThat(d.get("hasMoreMessages").asBoolean()).isFalse();

        mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/read").with(nv(AGENT_2)))
                .andExpect(status().isOk());
        assertThat(findInList(admin(), k.conversationId(), "all").get("unreadCount").asInt()).isZero();

        mvc.perform(get("/api/v1/conversations/" + k.conversationId() + "/context").with(admin()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.contact.fullName").value(org.hamcrest.Matchers.startsWith("Khách web #")))
                .andExpect(jsonPath("$.data.summary").doesNotExist());
    }

    @Test
    void phanTrangTinBangConTro() throws Exception {
        Khach k = khachMoi("tin 1");
        sendAsCustomer(k, "tin 2");                                     // 4 tin: khách, bot, khách, bot
        JsonNode p1 = data(mvc.perform(get("/api/v1/conversations/" + k.conversationId() + "/messages")
                .param("size", "3").with(admin())).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(p1.get("items")).hasSize(3);
        assertThat(p1.get("hasMore").asBoolean()).isTrue();
        assertThat(p1.get("items").get(0).get("content").asText()).isNotEqualTo("tin 1");
        JsonNode p2 = data(mvc.perform(get("/api/v1/conversations/" + k.conversationId() + "/messages")
                .param("size", "3").param("before", p1.get("nextCursor").asText()).with(admin()))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(p2.get("items")).hasSize(1);
        assertThat(p2.get("items").get(0).get("content").asText()).isEqualTo("tin 1");
        assertThat(p2.get("hasMore").asBoolean()).isFalse();
    }

    @Test
    void cachLy_doanhNghiepKhacKhongThayKhongMoDuoc() throws Exception {
        Khach k = khachMoi("bí mật của I");
        assertThat(findInList(asUser(TENANT_J, ADMIN_J, "TENANT_ADMIN"), k.conversationId(), "all")).isNull();
        mvc.perform(get("/api/v1/conversations/" + k.conversationId()).with(asUser(TENANT_J, ADMIN_J, "TENANT_ADMIN")))
                .andExpect(status().isNotFound());
        reply(asUser(TENANT_J, ADMIN_J, "TENANT_ADMIN"), k, "chen ngang").andExpect(status().isNotFound());
    }

    // ── UC013: trả lời ──────────────────────────────────────────────────────────

    @Test
    void nhanVienTraLoi_tuNhan_AiNgung_khachNhanTrenWidget() throws Exception {
        Khach k = khachMoi("cho mình hỏi");
        reply(nv(AGENT_1), k, "Chào bạn, mình là Một, hỗ trợ bạn nhé.").andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.senderType").value("AGENT"))
                .andExpect(jsonPath("$.data.senderName").value("Nhân viên Một"))
                .andExpect(jsonPath("$.data.deliveryStatus").value("DELIVERED"));

        JsonNode row = findInList(nv(AGENT_1), k.conversationId(), "mine");
        assertThat(row).isNotNull();
        assertThat(row.get("status").asText()).isEqualTo("AGENT_HANDLING");
        assertThat(row.get("assignedUserName").asText()).isEqualTo("Nhân viên Một");
        JsonNode d = data(mvc.perform(get("/api/v1/conversations/" + k.conversationId()).with(admin()))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(d.get("firstResponseAt").isNull()).isFalse();       // phản hồi đầu tiên của NGƯỜI
        assertThat(d.get("autoReplyEnabled").asBoolean()).isFalse();

        // Widget nhận tin nhân viên
        String poll = mvc.perform(get("/api/v1/widget/messages").header("X-Widget-Token", k.token()).header("Origin", ORIGIN_I))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        assertThat(poll).contains("Chào bạn, mình là Một").contains("\"AGENT\"");

        // Khách nhắn tiếp → không qua AI nữa
        int before = AI.calls.get();
        sendAsCustomer(k, "cảm ơn");
        assertThat(AI.calls.get()).isEqualTo(before);
        assertThat(auditCount(k.conversationId(), "CONVERSATION_ASSIGNED")).isEqualTo(1);
    }

    @Test
    void nguoiKhacDangGiu_nhanVienKhac403_quanTriVanGuiDuoc() throws Exception {
        Khach k = khachMoi("hỏi");
        reply(nv(AGENT_1), k, "Một đây").andExpect(status().isCreated());
        reply(nv(AGENT_2), k, "Hai chen vào").andExpect(status().isForbidden());
        reply(admin(), k, "Quản trị hỗ trợ thêm").andExpect(status().isCreated());
    }

    @Test
    void noiDungRongQuaDai_hoacKhongPhaiChu_422() throws Exception {
        Khach k = khachMoi("hỏi");
        reply(nv(AGENT_1), k, "   ").andExpect(status().isUnprocessableEntity());
        reply(nv(AGENT_1), k, "a".repeat(4001)).andExpect(status().isUnprocessableEntity());
        mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/messages").with(nv(AGENT_1))
                .contentType(MediaType.APPLICATION_JSON).content("{\"content\":\"x\",\"contentType\":\"IMAGE\"}"))
                .andExpect(status().isUnprocessableEntity());
    }

    // ── UC015 / UC014 ───────────────────────────────────────────────────────────

    @Test
    void phanCong_nhanVienChiTuNhan_quanTriGiaoDuocVaGianhLai() throws Exception {
        Khach k = khachMoi("hỏi");
        assign(nv(AGENT_1), k, null).andExpect(status().isOk())
                .andExpect(jsonPath("$.data.assignedUserId").value(AGENT_1.toString()))
                .andExpect(jsonPath("$.data.status").value("AGENT_HANDLING"));
        assign(nv(AGENT_2), k, null).andExpect(status().isForbidden());           // giành của Một
        assign(nv(AGENT_1), k, AGENT_2).andExpect(status().isForbidden());        // nhân viên giao cho người khác
        assign(admin(), k, AGENT_2).andExpect(status().isOk())
                .andExpect(jsonPath("$.data.assignedUserName").value("Nhân viên Hai"));
        assign(admin(), k, ADMIN_J).andExpect(status().isUnprocessableEntity());   // người của doanh nghiệp khác
    }

    @Test
    void traLaiChoAi_AiTraLoiTiep() throws Exception {
        Khach k = khachMoi("hỏi");
        reply(nv(AGENT_1), k, "Một đây").andExpect(status().isCreated());
        handoff(nv(AGENT_2), k, "AGENT_TO_BOT").andExpect(status().isForbidden());
        handoff(nv(AGENT_1), k, "AGENT_TO_BOT").andExpect(status().isOk())
                .andExpect(jsonPath("$.data.direction").value("AGENT_TO_BOT"))
                .andExpect(jsonPath("$.data.countsAgainstAiQuality").value(false));
        int before = AI.calls.get();
        sendAsCustomer(k, "hỏi tiếp");
        assertThat(AI.calls.get()).isEqualTo(before + 1);
        assertThat(findInList(admin(), k.conversationId(), "all").get("assignedUserId").isNull()).isTrue();
    }

    @Test
    void nhanVienChuDongLayKhoiAi_vaoHangCho() throws Exception {
        Khach k = khachMoi("hỏi");
        handoff(nv(AGENT_2), k, "BOT_TO_AGENT").andExpect(status().isOk())
                .andExpect(jsonPath("$.data.countsAgainstAiQuality").value(true));
        assertThat(findInList(admin(), k.conversationId(), "all").get("status").asText()).isEqualTo("PENDING_AGENT");
        handoff(nv(AGENT_2), k, "BOT_TO_AGENT").andExpect(status().isConflict());
    }

    @Test
    void dongHoiThoai_khachThayCauKetThuc_guiTiep409_khachNhanLaiMoHoiThoaiMoi() throws Exception {
        Khach k = khachMoi("hỏi");
        reply(nv(AGENT_1), k, "Một đây").andExpect(status().isCreated());
        doiTrangThai(nv(AGENT_2), k, "RESOLVED").andExpect(status().isForbidden());
        doiTrangThai(nv(AGENT_1), k, "RESOLVED").andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("RESOLVED"));

        String poll = mvc.perform(get("/api/v1/widget/messages").header("X-Widget-Token", k.token()).header("Origin", ORIGIN_I))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        assertThat(poll).contains("Cuộc trò chuyện đã kết thúc").contains("\"RESOLVED\"");

        reply(nv(AGENT_1), k, "còn đó không").andExpect(status().isConflict());
        doiTrangThai(nv(AGENT_1), k, "CLOSED").andExpect(status().isConflict());

        JsonNode next = sendAsCustomer(k, "mình hỏi thêm");
        String newConv = conversationOfMessage(next.get("messages").get(0).get("id").asText());
        assertThat(newConv).isNotEqualTo(k.conversationId());
        assertThat(auditCount(k.conversationId(), "CONVERSATION_STATUS_CHANGED")).isEqualTo(1);
    }

    // ── Rà soát lần 2: lỗ hổng tìm ra sau khi chạy thật ────────────────────────

    @Test
    void lyDoCuaHeThong_nhanVienKhongTuChonDuoc() throws Exception {
        // Lỗ hổng R1: QUOTA_EXCEEDED và LLM_ERROR là lý do do HỆ THỐNG ghi. Nhân viên tự chọn được thì
        // chọn QUOTA_EXCEEDED là "countsAgainstAiQuality = false" — tự làm đẹp chỉ số chất lượng AI.
        // Giao diện đã giấu hai lý do này nhưng API vẫn nhận.
        Khach k = khachMoi("hỏi");
        for (String lyDo : new String[] {"QUOTA_EXCEEDED", "LLM_ERROR"}) {
            mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/handoff").with(nv(AGENT_1))
                            .contentType(MediaType.APPLICATION_JSON)
                            .content("{\"direction\":\"BOT_TO_AGENT\",\"reason\":\"" + lyDo + "\"}"))
                    .andExpect(status().isUnprocessableEntity());
        }
    }

    @Test
    void hoiThoaiDoHetHanMuc_khongTraLaiAiDuoc_khiHanMucVanHet() throws Exception {
        // Lỗ hổng R2: hội thoại chuyển cho người vì HẾT HẠN MỨC. Nhân viên bấm "Trả lại cho AI" thì
        // mọi tin sau đó gọi AI — hạn mức (chỉ kiểm khi mở hội thoại MỚI) bị lách hoàn toàn.
        setUsage(TENANT_I, true);
        try {
            Khach k = khachMoi("hỏi khi đã hết hạn mức");
            assertThat(findInList(admin(), k.conversationId(), "all").get("status").asText()).isEqualTo("PENDING_AGENT");
            handoff(admin(), k, "AGENT_TO_BOT").andExpect(status().isConflict());
        } finally {
            setUsage(TENANT_I, false);
        }
    }

    // ── số trên menu "Hộp thư" ──────────────────────────────────────────────────

    @Test
    void soHoiThoaiCho_khopCsdl_khongLanDoanhNghiep_khongGhiMocDangTruc() throws Exception {
        Khach k = khachMoi("cho mình gặp nhân viên");
        mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/handoff").with(admin())
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"direction\":\"BOT_TO_AGENT\",\"reason\":\"CUSTOMER_REQUEST\"}"))
                .andExpect(status().isOk());
        long trongCsdl;
        UUID moi = UUID.randomUUID();
        try (Connection c = owner()) {
            try (PreparedStatement ps = c.prepareStatement("""
                    SELECT count(*) FROM engagement.conversations
                    WHERE tenant_id = ? AND status = 'PENDING_AGENT' AND assigned_user_id IS NULL""")) {
                ps.setObject(1, TENANT_I);
                try (ResultSet rs = ps.executeQuery()) {
                    rs.next();
                    trongCsdl = rs.getLong(1);
                }
            }
            exec(c, """
                    INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                    VALUES (?, ?, ?, 'x', 'Mới vào', 'ACTIVE')""", moi, TENANT_I, moi.toString().substring(0, 8) + "@i.vn");
        }
        assertThat(trongCsdl).isPositive();
        JsonNode d = data(mvc.perform(get("/api/v1/conversations/waiting-count").with(nv(moi)))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(d.get("waiting").asLong()).isEqualTo(trongCsdl);
        // Menu hỏi định kỳ trên mọi trang → không được biến người đang xem trang khác thành "đang trực"
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "SELECT count(*) FROM platform.user_presence WHERE user_id = ?")) {
            ps.setObject(1, moi);
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                assertThat(rs.getLong(1)).isZero();
            }
        }
        JsonNode j = data(mvc.perform(get("/api/v1/conversations/waiting-count")
                .with(asUser(TENANT_J, ADMIN_J, "TENANT_ADMIN"))).andReturn().getResponse()
                .getContentAsString(StandardCharsets.UTF_8));
        assertThat(j.get("waiting").asLong()).isZero();
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private static void setUsage(UUID tenant, boolean exhausted) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "UPDATE platform.usage_records SET used_value = CASE WHEN ? THEN quota_value ELSE 0 END "
                        + "WHERE tenant_id = ? AND metric = 'CONVERSATION'")) {
            ps.setBoolean(1, exhausted);
            ps.setObject(2, tenant);
            ps.executeUpdate();
        }
    }

    record Khach(String token, String conversationId) {}

    private Khach khachMoi(String firstMessage) throws Exception {
        String token = data(mvc.perform(post("/api/v1/widget/session").header("Origin", ORIGIN_I)
                        .header("X-Forwarded-For", "10.1." + ThreadLocalRandom.current().nextInt(256) + ".9")
                        .contentType(MediaType.APPLICATION_JSON).content("{\"widgetKey\":\"" + KEY_I + "\"}"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8))
                .get("token").asText();
        Khach k = new Khach(token, null);
        JsonNode turn = sendAsCustomer(k, firstMessage);
        return new Khach(token, conversationOfMessage(turn.get("messages").get(0).get("id").asText()));
    }

    private JsonNode sendAsCustomer(Khach k, String content) throws Exception {
        return data(mvc.perform(post("/api/v1/widget/messages").header("Origin", ORIGIN_I)
                        .header("X-Widget-Token", k.token()).contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of("content", content))))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
    }

    private ResultActions reply(JwtRequestPostProcessor who, Khach k, String content) throws Exception {
        return mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/messages").with(who)
                .contentType(MediaType.APPLICATION_JSON).content(json.writeValueAsString(Map.of("content", content))));
    }

    private ResultActions assign(JwtRequestPostProcessor who, Khach k, UUID target) throws Exception {
        return mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/assign").with(who)
                .contentType(MediaType.APPLICATION_JSON)
                .content(target == null ? "{}" : "{\"assigneeUserId\":\"" + target + "\"}"));
    }

    private ResultActions handoff(JwtRequestPostProcessor who, Khach k, String direction) throws Exception {
        return mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/handoff").with(who)
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"direction\":\"" + direction + "\",\"reason\":\"CUSTOMER_REQUEST\"}"));
    }

    private ResultActions doiTrangThai(JwtRequestPostProcessor who, Khach k, String st) throws Exception {
        return mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/status").with(who)
                .contentType(MediaType.APPLICATION_JSON).content("{\"status\":\"" + st + "\"}"));
    }

    private ResultActions list(JwtRequestPostProcessor who, String scope, String extra) throws Exception {
        return mvc.perform(get("/api/v1/conversations?size=100&scope=" + scope + extra).with(who));
    }

    /** Dòng của hội thoại trong danh sách, hoặc null nếu không có. */
    private JsonNode findInList(JwtRequestPostProcessor who, String conversationId, String scope) throws Exception {
        JsonNode page = data(list(who, scope, "").andExpect(status().isOk()).andReturn().getResponse()
                .getContentAsString(StandardCharsets.UTF_8));
        for (JsonNode r : page.get("items")) {
            if (r.get("id").asText().equals(conversationId)) {
                return r;
            }
        }
        return null;
    }

    private static JwtRequestPostProcessor admin() {
        return asUser(TENANT_I, ADMIN_I, "TENANT_ADMIN");
    }

    /** Nhân viên (AGENT) của doanh nghiệp I. */
    private static JwtRequestPostProcessor nv(UUID agent) {
        return asUser(TENANT_I, agent, "AGENT");
    }

    private static String conversationOfMessage(String messageId) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "SELECT conversation_id FROM engagement.messages WHERE id = ?::uuid")) {
            ps.setString(1, messageId);
            ResultSet rs = ps.executeQuery();
            rs.next();
            return rs.getString(1);
        }
    }

    private static long auditCount(String conversationId, String action) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "SELECT count(*) FROM platform.audit_logs WHERE entity_id = ?::uuid AND action = ?")) {
            ps.setString(1, conversationId);
            ps.setString(2, action);
            ResultSet rs = ps.executeQuery();
            rs.next();
            return rs.getLong(1);
        }
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
