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
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.ResultActions;

/**
 * UC009 bước 10–11 + UC010 — API công khai của widget, chạy trên Postgres + Redis thật, ai-service
 * giả ({@link FakeAiServer}).
 */
class WidgetIntegrationTest extends EngagementIntegrationTestBase {

    /** Doanh nghiệp W: đang hoạt động, widget nhúng được trên shop-w.vn. */
    static final UUID TENANT_W = UUID.randomUUID();
    /** Doanh nghiệp X: widget riêng trên shop-x.vn — để kiểm cách ly. */
    static final UUID TENANT_X = UUID.randomUUID();
    /** Doanh nghiệp bị khoá. */
    static final UUID TENANT_S = UUID.randomUUID();
    /** Doanh nghiệp đã dùng hết hạn mức hội thoại. */
    static final UUID TENANT_Q = UUID.randomUUID();

    static final String KEY_W = "wk_w_" + UUID.randomUUID().toString().substring(0, 8);
    static final String KEY_X = "wk_x_" + UUID.randomUUID().toString().substring(0, 8);
    static final String KEY_S = "wk_s_" + UUID.randomUUID().toString().substring(0, 8);
    static final String KEY_Q = "wk_q_" + UUID.randomUUID().toString().substring(0, 8);

    static final String ORIGIN_W = "https://shop-w.vn";
    static final String ORIGIN_X = "https://shop-x.vn";

    private static boolean seededWidget;

    @BeforeEach
    void seedWidgets() throws Exception {
        if (seededWidget) {
            AI.respond(FakeAiServer.answer("Gói Pro giá 3.990.000đ mỗi tháng."));
            return;
        }
        seededWidget = true;
        try (Connection c = owner()) {
            tenant(c, TENANT_W, "ACTIVE", 200, 0);
            tenant(c, TENANT_X, "ACTIVE", 200, 0);
            tenant(c, TENANT_S, "SUSPENDED", 200, 0);
            tenant(c, TENANT_Q, "ACTIVE", 5, 5);
            channel(c, TENANT_W, KEY_W, "[\"shop-w.vn\"]");
            channel(c, TENANT_X, KEY_X, "[\"shop-x.vn\"]");
            channel(c, TENANT_S, KEY_S, "[\"shop-s.vn\"]");
            channel(c, TENANT_Q, KEY_Q, "[\"shop-q.vn\"]");
        }
        AI.respond(FakeAiServer.answer("Gói Pro giá 3.990.000đ mỗi tháng."));
    }

    // ── Mở phiên ────────────────────────────────────────────────────────────────

    @Test
    void moPhien_dungTenMien_capTokenVaCauHinh() throws Exception {
        session(KEY_W, ORIGIN_W).andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("ACTIVE"))
                .andExpect(jsonPath("$.data.token").isNotEmpty())
                .andExpect(jsonPath("$.data.appearance.greetingMessage").value("Xin chào!"))
                .andExpect(jsonPath("$.data.messages").isEmpty());
    }

    @Test
    void moPhien_tuNhanWww() throws Exception {
        session(KEY_W, "https://www.shop-w.vn").andExpect(status().isOk());
    }

    @Test
    void moPhien_tenMienLa_tuChoiVaGhiNhatKy() throws Exception {
        session(KEY_W, "https://ke-gian.vn").andExpect(status().isForbidden());
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement("""
                SELECT after_data->>'origin' FROM platform.audit_logs
                WHERE tenant_id = ? AND action = 'WIDGET_ORIGIN_REJECTED' AND severity = 'WARNING'""")) {
            ps.setObject(1, TENANT_W);
            ResultSet rs = ps.executeQuery();
            assertThat(rs.next()).isTrue();
            assertThat(rs.getString(1)).isEqualTo("ke-gian.vn");
        }
    }

    @Test
    void moPhien_khoaKhongTonTai_404() throws Exception {
        session("wk_khong_co", ORIGIN_W).andExpect(status().isNotFound());
    }

    @Test
    void moPhien_doanhNghiepBiKhoa_tamNgungKhongCoToken() throws Exception {
        session(KEY_S, "https://shop-s.vn").andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("SUSPENDED"))
                .andExpect(jsonPath("$.data.token").doesNotExist());
    }

    // ── Gửi tin ─────────────────────────────────────────────────────────────────

    @Test
    void guiTin_goiAiDungTenant_luuTinKhachVaTinBotKemTrichDan() throws Exception {
        String token = newToken(KEY_W, ORIGIN_W);
        int before = AI.calls.get();

        JsonNode turn = data(send(token, ORIGIN_W, "gói pro bao nhiêu tiền?").andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));

        assertThat(AI.calls.get()).isEqualTo(before + 1);
        assertThat(AI.lastTenantHeader.get()).isEqualTo(TENANT_W.toString());
        assertThat(turn.get("conversationStatus").asText()).isEqualTo("BOT_HANDLING");
        assertThat(turn.get("messages")).hasSize(2);
        assertThat(turn.get("messages").get(0).get("senderType").asText()).isEqualTo("CUSTOMER");
        JsonNode bot = turn.get("messages").get(1);
        assertThat(bot.get("senderType").asText()).isEqualTo("BOT");
        assertThat(bot.get("citations").get(0).get("title").asText()).isEqualTo("Bảng giá 2026");

        // Hồ sơ khách tên tạm + danh tính + hội thoại được tạo, đúng tenant
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement("""
                SELECT k.full_name, k.consent_granted, v.status, v.tenant_id
                FROM engagement.conversations v JOIN engagement.contacts k ON k.id = v.contact_id
                WHERE v.id = (SELECT conversation_id FROM engagement.messages WHERE id = ?)""")) {
            ps.setObject(1, UUID.fromString(bot.get("id").asText()));
            ResultSet rs = ps.executeQuery();
            assertThat(rs.next()).isTrue();
            assertThat(rs.getString(1)).startsWith("Khách web #");
            assertThat(rs.getBoolean(2)).isFalse();
            assertThat(rs.getObject(4, UUID.class)).isEqualTo(TENANT_W);
        }
    }

    @Test
    void taiLaiTrang_cungToken_khoiPhucLichSu() throws Exception {
        String token = newToken(KEY_W, ORIGIN_W);
        send(token, ORIGIN_W, "xin chào").andExpect(status().isOk());

        JsonNode again = data(mvc.perform(post("/api/v1/widget/session")
                        .header("Origin", ORIGIN_W).header("X-Forwarded-For", randomIp())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"widgetKey\":\"" + KEY_W + "\",\"token\":\"" + token + "\"}"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(again.get("messages")).hasSize(2);
        assertThat(again.get("conversationStatus").asText()).isEqualTo("BOT_HANDLING");
    }

    @Test
    void tokenGia_hoacBiSua_401() throws Exception {
        String token = newToken(KEY_W, ORIGIN_W);
        String[] p = token.split("\\.");
        // Đổi một ký tự phần payload → chữ ký không còn khớp
        String tampered = p[0] + "." + p[1].substring(0, p[1].length() - 2) + "AA." + p[2];
        send(tampered, ORIGIN_W, "hi").andExpect(status().isUnauthorized());
        send("khong-phai-token", ORIGIN_W, "hi").andExpect(status().isUnauthorized());
        send(null, ORIGIN_W, "hi").andExpect(status().isUnauthorized());
    }

    @Test
    void cachLy_tokenDoanhNghiepW_khongDungDuocOTenMienX_vaKhongThayTinCuaX() throws Exception {
        String tokenW = newToken(KEY_W, ORIGIN_W);
        String tokenX = newToken(KEY_X, ORIGIN_X);
        send(tokenX, ORIGIN_X, "tin bí mật của X").andExpect(status().isOk());

        // Token W mang sang trang của X: tên miền không thuộc widget W
        send(tokenW, ORIGIN_X, "hi").andExpect(status().isForbidden());
        // Khách W hỏi tin mới: không bao giờ thấy tin của X
        String body = mvc.perform(get("/api/v1/widget/messages")
                        .header("X-Widget-Token", tokenW).header("Origin", ORIGIN_W))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        assertThat(body).doesNotContain("tin bí mật của X");
    }

    @Test
    void noiDungRongHoacQuaDai_422() throws Exception {
        String token = newToken(KEY_W, ORIGIN_W);
        send(token, ORIGIN_W, "   ").andExpect(status().isUnprocessableEntity());
        send(token, ORIGIN_W, "a".repeat(1001)).andExpect(status().isUnprocessableEntity());
        send(token, ORIGIN_W, "a".repeat(1000)).andExpect(status().isOk());
    }

    @Test
    void aiLoi_chuyenChoNhanVien_LLM_ERROR() throws Exception {
        AI.respond(new FakeAiServer.Script(500, "{\"detail\":\"boom\"}", 0));
        String token = newToken(KEY_W, ORIGIN_W);
        JsonNode turn = turnOf(send(token, ORIGIN_W, "hello"));
        assertThat(turn.get("conversationStatus").asText()).isEqualTo("PENDING_AGENT");
        assertThat(lastSystemMessage(turn)).startsWith("Cảm ơn bạn!");
        assertThat(handoverReason(turn)).isEqualTo("LLM_ERROR");
    }

    @Test
    void aiQuaGioCho_chuyenChoNhanVien() throws Exception {
        AI.respond(new FakeAiServer.Script(200, "{\"answer\":\"muộn\"}", 3000));
        String token = newToken(KEY_W, ORIGIN_W);
        JsonNode turn = turnOf(send(token, ORIGIN_W, "hello"));
        assertThat(turn.get("conversationStatus").asText()).isEqualTo("PENDING_AGENT");
        assertThat(handoverReason(turn)).isEqualTo("LLM_ERROR");
    }

    @Test
    void aiBaoChuyenGiao_CUSTOMER_REQUEST_vaTinSauKhongGoiAiNua() throws Exception {
        AI.respond(FakeAiServer.handoff());
        String token = newToken(KEY_W, ORIGIN_W);
        JsonNode turn = turnOf(send(token, ORIGIN_W, "cho tôi gặp người thật"));
        assertThat(turn.get("conversationStatus").asText()).isEqualTo("PENDING_AGENT");
        assertThat(handoverReason(turn)).isEqualTo("CUSTOMER_REQUEST");
        assertThat(lastSystemMessage(turn)).startsWith("Cảm ơn bạn!");   // AI không nói gì → máy chủ báo

        // 6.3–6.4: hội thoại đang chờ nhân viên → tin tiếp theo không qua AI
        int before = AI.calls.get();
        JsonNode next = turnOf(send(token, ORIGIN_W, "alo?"));
        assertThat(AI.calls.get()).isEqualTo(before);
        assertThat(next.get("messages")).hasSize(1);
        assertThat(next.get("conversationStatus").asText()).isEqualTo("PENDING_AGENT");
    }

    @Test
    void aiDaTuNoiCauChuyenGiao_khongThemTinHeThongLap() throws Exception {
        AI.respond(new FakeAiServer.Script(200, """
                {"answer": "Dạ em đã chuyển cho nhân viên tư vấn ạ.", "citations": [], "route": "HANDOFF",
                 "refused": false, "handoff": true, "latency_ms": 30}
                """, 0));
        String token = newToken(KEY_W, ORIGIN_W);
        JsonNode turn = turnOf(send(token, ORIGIN_W, "gặp nhân viên"));
        assertThat(turn.get("conversationStatus").asText()).isEqualTo("PENDING_AGENT");
        assertThat(turn.get("messages")).hasSize(2);                     // tin khách + câu của AI
        assertThat(turn.get("messages").get(1).get("senderType").asText()).isEqualTo("BOT");
    }

    @Test
    void nhanVienNhanHoiThoaiTrongLucAiDangNghi_khongChenCauTraLoiAiVao() throws Exception {
        // Lỗ hổng R1: AI trả lời chậm; trong lúc đó nhân viên đã nhận hội thoại (UC015). Câu AI về
        // muộn không được chen vào cuộc trò chuyện nhân viên đang giữ (UC010 6.3).
        AI.respond(new FakeAiServer.Script(200, """
                {"answer": "Câu AI về muộn", "citations": [], "route": "RAG", "refused": false,
                 "handoff": false, "latency_ms": 900}
                """, 900));
        String token = newToken(KEY_W, ORIGIN_W);
        Thread nhanVien = new Thread(() -> {
            try {
                Thread.sleep(400);
                try (Connection c = owner(); PreparedStatement ps = c.prepareStatement("""
                        UPDATE engagement.conversations SET status = 'AGENT_HANDLING'
                        WHERE tenant_id = ? AND status = 'BOT_HANDLING' AND id IN
                          (SELECT conversation_id FROM engagement.messages WHERE content = 'nhân viên sắp nhận')""")) {
                    ps.setObject(1, TENANT_W);
                    ps.executeUpdate();
                }
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
        });
        nhanVien.start();
        JsonNode turn = turnOf(send(token, ORIGIN_W, "nhân viên sắp nhận"));
        nhanVien.join();
        assertThat(turn.get("conversationStatus").asText()).isEqualTo("AGENT_HANDLING");
        assertThat(turn.toString()).doesNotContain("Câu AI về muộn");
        assertThat(countMessages(conversationOf(turn), "BOT")).isZero();
    }

    @Test
    void hetHanMuc_vanLuuTin_khongGoiAi_QUOTA_EXCEEDED() throws Exception {
        String token = newToken(KEY_Q, "https://shop-q.vn");
        int before = AI.calls.get();
        JsonNode turn = turnOf(send(token, "https://shop-q.vn", "còn hàng không?"));
        assertThat(AI.calls.get()).isEqualTo(before);
        assertThat(turn.get("conversationStatus").asText()).isEqualTo("PENDING_AGENT");
        assertThat(handoverReason(turn)).isEqualTo("QUOTA_EXCEEDED");
        assertThat(turn.get("messages")).hasSize(2);   // tin khách vẫn được lưu + câu báo
    }

    @Test
    void hoiThoaiMoi_tinhVaoHanMuc_imLangQua24Gio_moHoiThoaiMoi() throws Exception {
        long usedBefore = usage(TENANT_W);
        String token = newToken(KEY_W, ORIGIN_W);
        JsonNode first = turnOf(send(token, ORIGIN_W, "lần 1"));
        assertThat(usage(TENANT_W)).isEqualTo(usedBefore + 1);
        String conv1 = conversationOf(first);

        turnOf(send(token, ORIGIN_W, "lần 1b"));                  // cùng hội thoại, không tính thêm
        assertThat(usage(TENANT_W)).isEqualTo(usedBefore + 1);

        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "UPDATE engagement.conversations SET last_message_at = now() - interval '25 hours' WHERE id = ?")) {
            ps.setObject(1, UUID.fromString(conv1));
            ps.executeUpdate();
        }
        JsonNode later = turnOf(send(token, ORIGIN_W, "lần 2, hôm sau"));
        assertThat(conversationOf(later)).isNotEqualTo(conv1);
        assertThat(usage(TENANT_W)).isEqualTo(usedBefore + 2);
    }

    @Test
    void nutGapNhanVien_CUSTOMER_REQUEST_vaChuaCoTinThi409() throws Exception {
        String token = newToken(KEY_W, ORIGIN_W);
        handoff(token).andExpect(status().isConflict());

        send(token, ORIGIN_W, "hỏi chút").andExpect(status().isOk());
        JsonNode turn = turnOf(handoff(token));
        assertThat(turn.get("conversationStatus").asText()).isEqualTo("PENDING_AGENT");
        assertThat(handoverReason(turn)).isEqualTo("CUSTOMER_REQUEST");
    }

    @Test
    void ngoaiGioLamViec_cauChuyenGiaoBaoKhungGio() throws Exception {
        // Mọi ngày chỉ mở 00:00–00:01 → gần như chắc chắn đang ngoài giờ khi test chạy
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement("""
                UPDATE platform.tenants SET business_hours = '{"mon":{"open":"00:00","close":"00:01"},
                 "tue":{"open":"00:00","close":"00:01"},"wed":{"open":"00:00","close":"00:01"},
                 "thu":{"open":"00:00","close":"00:01"},"fri":{"open":"00:00","close":"00:01"},
                 "sat":{"open":"00:00","close":"00:01"},"sun":{"open":"00:00","close":"00:01"}}'
                WHERE id = ?""")) {
            ps.setObject(1, TENANT_X);
            ps.executeUpdate();
        }
        try {
            String token = newToken(KEY_X, ORIGIN_X);
            send(token, ORIGIN_X, "có ai không").andExpect(status().isOk());
            JsonNode turn = turnOf(handoff(token));
            assertThat(lastSystemMessage(turn)).contains("ngoài giờ làm việc").contains("Thứ Hai–Chủ nhật 00:00–00:01");
        } finally {
            try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                    "UPDATE platform.tenants SET business_hours = '{}' WHERE id = ?")) {
                ps.setObject(1, TENANT_X);
                ps.executeUpdate();
            }
        }
    }

    @Test
    void chongSpam_tinThu11TrongMotPhut_429() throws Exception {
        String token = newToken(KEY_W, ORIGIN_W);
        AI.respond(FakeAiServer.answer("ok"));
        for (int i = 0; i < 10; i++) {
            send(token, ORIGIN_W, "tin " + i).andExpect(status().isOk());
        }
        send(token, ORIGIN_W, "tin 11").andExpect(status().isTooManyRequests());
    }

    @Test
    void hoiTinMoi_chiTraTinSauMocThoiGian() throws Exception {
        String token = newToken(KEY_W, ORIGIN_W);
        JsonNode turn = turnOf(send(token, ORIGIN_W, "mốc"));
        String lastSentAt = turn.get("messages").get(1).get("sentAt").asText();
        String body = mvc.perform(get("/api/v1/widget/messages").param("after", lastSentAt)
                        .header("X-Widget-Token", token).header("Origin", ORIGIN_W))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        assertThat(data(body).get("messages")).isEmpty();
    }

    // ── Khách để lại thông tin (bổ sung UC010) ──────────────────────────────────

    @Test
    void deLaiThongTin_capNhatHoSo_dongYWidget_tinHeThong_khongHoiLai() throws Exception {
        String token = newToken(KEY_W, ORIGIN_W);
        turnOf(send(token, ORIGIN_W, "cho mình hỏi gói pro"));
        JsonNode kq = data(thongTin(token, ORIGIN_W,
                "{\"fullName\":\" Trần Văn Bình \",\"phone\":\"0912 000 111\",\"email\":\"Binh@Ex.VN\",\"consent\":true}")
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(kq.get("infoShared").asBoolean()).isTrue();
        assertThat(kq.has("duplicateCandidates")).isFalse();
        assertThat(lastSystemMessage(kq)).contains("Trần Văn Bình").contains("0912000111").contains("binh@ex.vn");

        UUID contact = contactOf(token);
        assertThat(sqlRow("SELECT full_name || '|' || phone || '|' || email || '|' || consent_granted || '|' || consent_source "
                + "FROM engagement.contacts WHERE id = ?", contact))
                .isEqualTo("Trần Văn Bình|0912000111|binh@ex.vn|true|WIDGET");
        // Nhật ký chỉ có sự kiện + tên trường, KHÔNG có SĐT/tên (NĐ 13)
        String nhatKy = sqlRow("SELECT after_data::text FROM platform.audit_logs WHERE entity_id = ? "
                + "AND action = 'CONTACT_CONSENT_GRANTED'", contact);
        assertThat(nhatKy).contains("WIDGET").contains("phone").doesNotContain("0912").doesNotContain("Bình");

        // Mở lại widget (cùng token) → biết đã để lại, không hỏi lại
        JsonNode phien = data(mvc.perform(post("/api/v1/widget/session").header("Origin", ORIGIN_W)
                .header("X-Forwarded-For", randomIp()).contentType(MediaType.APPLICATION_JSON)
                .content("{\"widgetKey\":\"" + KEY_W + "\",\"token\":\"" + token + "\"}"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(phien.get("infoShared").asBoolean()).isTrue();
        assertThat(data(session(KEY_W, ORIGIN_W).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8))
                .get("infoShared").asBoolean()).isFalse();
    }

    @Test
    void deLaiThongTin_batBuocDongY_coCachLienHe_dungDinhDang() throws Exception {
        String token = newToken(KEY_W, ORIGIN_W);
        turnOf(send(token, ORIGIN_W, "hỏi chút"));
        thongTin(token, ORIGIN_W, "{\"fullName\":\"A\",\"phone\":\"0912000222\",\"consent\":false}")
                .andExpect(status().isUnprocessableEntity());
        thongTin(token, ORIGIN_W, "{\"fullName\":\"A\",\"phone\":\"0912000222\"}").andExpect(status().isUnprocessableEntity());
        thongTin(token, ORIGIN_W, "{\"fullName\":\"A\",\"consent\":true}").andExpect(status().isUnprocessableEntity());
        thongTin(token, ORIGIN_W, "{\"phone\":\"12ab\",\"consent\":true}").andExpect(status().isUnprocessableEntity());
        thongTin(token, ORIGIN_W, "{\"email\":\"khong-phai-email\",\"consent\":true}").andExpect(status().isUnprocessableEntity());
        thongTin(token, "https://site-la.vn", "{\"phone\":\"0912000222\",\"consent\":true}").andExpect(status().isForbidden());
        thongTin(null, ORIGIN_W, "{\"phone\":\"0912000222\",\"consent\":true}")
                .andExpect(r -> assertThat(r.getResponse().getStatus()).isIn(401, 403));
        // Bị từ chối thì hồ sơ không đổi
        assertThat(sqlRow("SELECT consent_granted || '|' || coalesce(phone, '-') FROM engagement.contacts WHERE id = ?",
                contactOf(token))).isEqualTo("false|-");
    }

    @Test
    void deLaiThongTin_khongGhiDeTenVaSoNhanVienDaNhap_chuaNhanTinVanDuoc() throws Exception {
        String token = newToken(KEY_W, ORIGIN_W);
        turnOf(send(token, ORIGIN_W, "xin chào"));
        UUID contact = contactOf(token);
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "UPDATE engagement.contacts SET full_name = 'Chị Hoa (NV sửa)', phone = '0900000001' WHERE id = ?")) {
            ps.setObject(1, contact);
            ps.executeUpdate();
        }
        thongTin(token, ORIGIN_W, "{\"fullName\":\"Hoa\",\"phone\":\"0900000002\",\"email\":\"hoa@x.vn\",\"consent\":true}")
                .andExpect(status().isOk());
        assertThat(sqlRow("SELECT full_name || '|' || phone || '|' || email || '|' || consent_granted "
                + "FROM engagement.contacts WHERE id = ?", contact)).isEqualTo("Chị Hoa (NV sửa)|0900000001|hoa@x.vn|true");

        // Khách chưa nhắn tin nào vẫn để lại được — hồ sơ tạo luôn, chưa có hội thoại nên không có tin hệ thống
        String moi = newToken(KEY_W, ORIGIN_W);
        JsonNode kq = data(thongTin(moi, ORIGIN_W, "{\"phone\":\"0900000003\",\"consent\":true}")
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(kq.get("messages")).isEmpty();
        assertThat(sqlRow("SELECT phone FROM engagement.contacts WHERE id = ?", contactOf(moi))).isEqualTo("0900000003");
    }

    @Test
    void trungSdt_khongTuGop_hoSoKhachHienNghiTrung() throws Exception {
        UUID cu = UUID.randomUUID();
        UUID quanTri = UUID.randomUUID();
        try (Connection c = owner()) {
            try (PreparedStatement ps = c.prepareStatement("""
                    INSERT INTO engagement.contacts (id, tenant_id, full_name, phone, primary_channel)
                    VALUES (?, ?, 'Khách cũ gọi điện', '0977000222', 'PHONE')""")) {
                ps.setObject(1, cu);
                ps.setObject(2, TENANT_W);
                ps.executeUpdate();
            }
            try (PreparedStatement ps = c.prepareStatement("""
                    INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                    VALUES (?, ?, ?, 'x', 'Quản trị W', 'ACTIVE')""")) {
                ps.setObject(1, quanTri);
                ps.setObject(2, TENANT_W);
                ps.setString(3, quanTri.toString().substring(0, 8) + "@w.vn");
                ps.executeUpdate();
            }
        }
        String token = newToken(KEY_W, ORIGIN_W);
        turnOf(send(token, ORIGIN_W, "mình là khách cũ"));
        thongTin(token, ORIGIN_W, "{\"phone\":\"+84 977 000 222\",\"consent\":true}").andExpect(status().isOk());
        UUID khachWeb = contactOf(token);
        assertThat(khachWeb).isNotEqualTo(cu);
        assertThat(sqlRow("SELECT count(*) FROM engagement.contacts WHERE tenant_id = ? AND phone = '0977000222'", TENANT_W))
                .isEqualTo("2");
        JsonNode chiTiet = data(mvc.perform(get("/api/v1/contacts/" + khachWeb)
                .with(asUser(TENANT_W, quanTri, "TENANT_ADMIN"))).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(chiTiet.get("duplicateCandidates")).hasSize(1);
        assertThat(chiTiet.get("duplicateCandidates").get(0).get("id").asText()).isEqualTo(cu.toString());
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private ResultActions session(String key, String origin) throws Exception {
        return mvc.perform(post("/api/v1/widget/session")
                .header("Origin", origin).header("X-Forwarded-For", randomIp())
                .contentType(MediaType.APPLICATION_JSON).content("{\"widgetKey\":\"" + key + "\"}"));
    }

    private String newToken(String key, String origin) throws Exception {
        return data(session(key, origin).andExpect(status().isOk()).andReturn().getResponse()
                .getContentAsString(StandardCharsets.UTF_8)).get("token").asText();
    }

    private ResultActions send(String token, String origin, String content) throws Exception {
        var req = post("/api/v1/widget/messages").header("Origin", origin)
                .contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsString(java.util.Map.of("content", content)));
        if (token != null) {
            req.header("X-Widget-Token", token);
        }
        return mvc.perform(req);
    }

    private ResultActions thongTin(String token, String origin, String body) throws Exception {
        var req = post("/api/v1/widget/contact-info").header("Origin", origin)
                .contentType(MediaType.APPLICATION_JSON).content(body);
        if (token != null) {
            req.header("X-Widget-Token", token);
        }
        return mvc.perform(req);
    }

    /** Hồ sơ khách của token (qua danh tính kênh — mã khách nằm trong phần {@code sub} của token). */
    private UUID contactOf(String token) throws Exception {
        String payload = new String(java.util.Base64.getUrlDecoder().decode(token.split("\\.")[1]), StandardCharsets.UTF_8);
        String visitor = json.readTree(payload).get("sub").asText();
        return UUID.fromString(sqlRow("SELECT contact_id::text FROM engagement.channel_identities WHERE external_user_id = ?",
                visitor));
    }

    private static String sqlRow(String query, Object arg) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(query)) {
            ps.setObject(1, arg);
            ResultSet rs = ps.executeQuery();
            return rs.next() ? rs.getString(1) : null;
        }
    }

    private ResultActions handoff(String token) throws Exception {
        return mvc.perform(post("/api/v1/widget/handoff").header("Origin", originOf(token))
                .header("X-Widget-Token", token));
    }

    /** Tên miền hợp lệ của widget mà token thuộc về (đọc kênh từ CSDL). */
    private String originOf(String token) throws Exception {
        String payload = new String(java.util.Base64.getUrlDecoder().decode(token.split("\\.")[1]), StandardCharsets.UTF_8);
        String chid = json.readTree(payload).get("chid").asText();
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "SELECT config->'allowedDomains'->>0 FROM engagement.channels WHERE id = ?")) {
            ps.setObject(1, UUID.fromString(chid));
            ResultSet rs = ps.executeQuery();
            rs.next();
            return "https://" + rs.getString(1);
        }
    }

    private JsonNode turnOf(ResultActions r) throws Exception {
        return data(r.andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
    }

    private static String lastSystemMessage(JsonNode turn) {
        String last = null;
        for (JsonNode m : turn.get("messages")) {
            if ("SYSTEM".equals(m.get("senderType").asText())) {
                last = m.get("content").asText();
            }
        }
        assertThat(last).as("phải có tin hệ thống báo chuyển giao").isNotNull();
        return last;
    }

    private String conversationOf(JsonNode turn) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "SELECT conversation_id FROM engagement.messages WHERE id = ?")) {
            ps.setObject(1, UUID.fromString(turn.get("messages").get(0).get("id").asText()));
            ResultSet rs = ps.executeQuery();
            rs.next();
            return rs.getString(1);
        }
    }

    private String handoverReason(JsonNode turn) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "SELECT handover_reason FROM engagement.conversations WHERE id = ?::uuid")) {
            ps.setString(1, conversationOf(turn));
            ResultSet rs = ps.executeQuery();
            rs.next();
            return rs.getString(1);
        }
    }

    private static long countMessages(String conversationId, String senderType) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "SELECT count(*) FROM engagement.messages WHERE conversation_id = ?::uuid AND sender_type = ?")) {
            ps.setString(1, conversationId);
            ps.setString(2, senderType);
            ResultSet rs = ps.executeQuery();
            rs.next();
            return rs.getLong(1);
        }
    }

    private static long usage(UUID tenantId) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(
                "SELECT used_value FROM platform.usage_records WHERE tenant_id = ? AND metric = 'CONVERSATION'")) {
            ps.setObject(1, tenantId);
            ResultSet rs = ps.executeQuery();
            rs.next();
            return rs.getLong(1);
        }
    }

    private static String randomIp() {
        ThreadLocalRandom r = ThreadLocalRandom.current();
        return "10." + r.nextInt(256) + "." + r.nextInt(256) + "." + r.nextInt(1, 255);
    }

    private static void tenant(Connection c, UUID id, String status, long quota, long used) throws Exception {
        try (PreparedStatement ps = c.prepareStatement("""
                INSERT INTO platform.tenants (id, name, slug, contact_email, status, suspended_reason, suspended_at)
                VALUES (?, ?, ?, ?, ?, ?, CASE WHEN ? = 'SUSPENDED' THEN now() END)""")) {
            ps.setObject(1, id);
            ps.setString(2, "DN widget " + id);
            ps.setString(3, "w-" + id.toString().substring(0, 8));
            ps.setString(4, "a@" + id.toString().substring(0, 8) + ".vn");
            ps.setString(5, status);
            ps.setString(6, "SUSPENDED".equals(status) ? "Nợ cước" : null);
            ps.setString(7, status);
            ps.executeUpdate();
        }
        UUID sub = UUID.randomUUID();
        try (PreparedStatement ps = c.prepareStatement("""
                INSERT INTO platform.tenant_subscriptions (id, tenant_id, plan_id, status, period_start, period_end)
                SELECT ?, ?, id, 'ACTIVE', now() - interval '1 day', now() + interval '29 days'
                FROM platform.subscription_plans WHERE code = 'TRIAL'""")) {
            ps.setObject(1, sub);
            ps.setObject(2, id);
            ps.executeUpdate();
        }
        try (PreparedStatement ps = c.prepareStatement("""
                INSERT INTO platform.usage_records (tenant_id, subscription_id, metric, used_value, quota_value)
                VALUES (?, ?, 'CONVERSATION', ?, ?)""")) {
            ps.setObject(1, id);
            ps.setObject(2, sub);
            ps.setLong(3, used);
            ps.setLong(4, quota);
            ps.executeUpdate();
        }
    }

    private static void channel(Connection c, UUID tenantId, String key, String domainsJson) throws Exception {
        try (PreparedStatement ps = c.prepareStatement("""
                INSERT INTO engagement.channels (tenant_id, type, name, widget_key, status, config)
                VALUES (?, 'WEB_WIDGET', 'Web Widget', ?, 'ACTIVE',
                        jsonb_build_object('greetingMessage', 'Xin chào!', 'primaryColor', '#4F46E5',
                                           'position', 'BOTTOM_RIGHT', 'allowedDomains', ?::jsonb))""")) {
            ps.setObject(1, tenantId);
            ps.setString(2, key);
            ps.setString(3, domainsJson);
            ps.executeUpdate();
        }
    }
}
