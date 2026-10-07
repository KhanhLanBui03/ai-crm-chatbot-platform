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
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;
import org.springframework.test.web.servlet.ResultActions;

/**
 * UC035 — hoạt động chăm sóc và nhắc việc, gồm hoạt động AUTO sinh khi nhân viên nhận hội thoại từ AI
 * (đi qua API nhận hội thoại THẬT của UC015, không gọi thẳng service).
 */
class ActivityIntegrationTest extends EngagementIntegrationTestBase {

    static final UUID TENANT_H = UUID.randomUUID();
    static final UUID TENANT_K = UUID.randomUUID();
    static final UUID ADMIN_H = UUID.randomUUID();
    static final UUID SALE_1 = UUID.randomUUID();
    static final UUID SALE_2 = UUID.randomUUID();
    static final UUID ADMIN_K = UUID.randomUUID();
    static final UUID CHANNEL_H = UUID.randomUUID();

    private static boolean seededAct;

    @BeforeEach
    void seedAct() throws Exception {
        if (seededAct) {
            return;
        }
        seededAct = true;
        try (Connection c = owner()) {
            for (UUID t : new UUID[] {TENANT_H, TENANT_K}) {
                exec(c, """
                        INSERT INTO platform.tenants (id, name, slug, contact_email, assignment_mode)
                        VALUES (?, 'DN hoạt động', ?, ?, 'MANUAL')""",
                        t, "h-" + t.toString().substring(0, 8), "a@" + t.toString().substring(0, 8) + ".vn");
            }
            for (Object[] u : new Object[][] {{ADMIN_H, TENANT_H, "Quản trị H"}, {SALE_1, TENANT_H, "Lan Sale"},
                    {SALE_2, TENANT_H, "Minh Sale"}, {ADMIN_K, TENANT_K, "Quản trị K"}}) {
                exec(c, """
                        INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                        VALUES (?, ?, ?, 'x', ?, 'ACTIVE')""", u[0], u[1], u[0].toString().substring(0, 8) + "@h.vn", u[2]);
            }
            exec(c, "INSERT INTO engagement.channels (id, tenant_id, type, name, status) VALUES (?, ?, 'ZALO', 'Zalo', 'ACTIVE')",
                    CHANNEL_H, TENANT_H);
        }
    }

    // ── AUTO ────────────────────────────────────────────────────────────────────

    @Test
    void nhanHoiThoaiTuAi_ghiMotDongAuto_ganLeadMo_coDuongDanHoiThoai() throws Exception {
        UUID k = khach(TENANT_H, "Auto Lead", "0903000001");
        String lead = data(body(mvc.perform(post("/api/v1/leads").with(nv(SALE_2)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"contactId\":\"" + k + "\"}")).andExpect(status().isCreated()))).get("id").asText();
        UUID conv = hoiThoaiChoNhanVien(k, "CUSTOMER_REQUEST");

        mvc.perform(post("/api/v1/conversations/" + conv + "/assign").with(nv(SALE_1))).andExpect(status().isOk());
        JsonNode ds = data(body(mvc.perform(get("/api/v1/activities").param("contactId", k.toString()).with(qtv()))));
        assertThat(ds.get("items")).hasSize(1);
        JsonNode a = ds.get("items").get(0);
        assertThat(a.get("source").asText()).isEqualTo("AUTO");
        assertThat(a.get("subject").asText()).isEqualTo("Tiếp nhận hội thoại từ AI");
        assertThat(a.get("content").asText()).contains("khách xin gặp nhân viên");
        assertThat(a.get("performedBy").asText()).isEqualTo(SALE_1.toString());
        assertThat(a.get("leadId").asText()).isEqualTo(lead);
        assertThat(a.get("dealId").isNull()).isTrue();
        assertThat(a.get("conversationId").asText()).isEqualTo(conv.toString());
        assertThat(a.get("remindStatus").asText()).isEqualTo("NONE");

        // Quản trị giao lại cho người khác: sự kiện đã được nhận rồi → KHÔNG ghi thêm
        mvc.perform(post("/api/v1/conversations/" + conv + "/assign").with(qtv()).contentType(MediaType.APPLICATION_JSON)
                .content("{\"assigneeUserId\":\"" + SALE_2 + "\"}")).andExpect(status().isOk());
        assertThat(sql("SELECT count(*) FROM sales.activities WHERE contact_id = ?", k)).containsExactly("1");
        // Dòng AUTO không ai sửa được, kể cả quản trị
        sua(qtv(), a.get("id").asText(), "{\"content\":\"x\"}").andExpect(status().isForbidden());
        // Lead hiển thị đúng số hoạt động
        assertThat(data(body(mvc.perform(get("/api/v1/leads/" + lead).with(qtv())))).get("activityCount").asInt())
                .isEqualTo(1);
    }

    @Test
    void auto_uuTienDealMo_khongCoGiThiChiHoSoKhach() throws Exception {
        UUID coDeal = khach(TENANT_H, "Auto Deal", "0903000002");
        mvc.perform(post("/api/v1/leads").with(nv(SALE_1)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"contactId\":\"" + coDeal + "\"}")).andExpect(status().isCreated());
        String deal = data(body(mvc.perform(post("/api/v1/deals").with(nv(SALE_1)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"contactId\":\"" + coDeal + "\",\"title\":\"Mua thêm\"}")).andExpect(status().isCreated())))
                .get("id").asText();
        UUID c1 = hoiThoaiChoNhanVien(coDeal, "LOW_CONFIDENCE");
        // Nhân viên trả lời câu đầu tiên = tự nhận (UC013)
        mvc.perform(post("/api/v1/conversations/" + c1 + "/messages").with(nv(SALE_1)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"content\":\"Dạ em chào chị\"}")).andExpect(status().isCreated());
        JsonNode a = data(body(mvc.perform(get("/api/v1/activities").param("dealId", deal).with(qtv())))).get("items").get(0);
        assertThat(a.get("source").asText()).isEqualTo("AUTO");
        assertThat(a.get("leadId").isNull()).isTrue();
        assertThat(a.get("content").asText()).contains("AI không chắc");
        // Lọc theo khách — hộp thoại ghi hoạt động chọn lead/deal của đúng khách đó
        assertThat(data(body(mvc.perform(get("/api/v1/deals").param("contactId", coDeal.toString()).with(qtv()))))
                .get("totalItems").asLong()).isEqualTo(1);
        assertThat(data(body(mvc.perform(get("/api/v1/leads").param("contactId", coDeal.toString()).with(qtv()))))
                .get("totalItems").asLong()).isEqualTo(1);
        // Chi tiết deal trả hoạt động thật
        assertThat(data(body(mvc.perform(get("/api/v1/deals/" + deal).with(qtv())))).get("activities")).hasSize(1);

        UUID vangLai = khach(TENANT_H, "Khách Vãng Lai", "0903000003");
        UUID c2 = hoiThoaiChoNhanVien(vangLai, "CUSTOMER_REQUEST");
        mvc.perform(post("/api/v1/conversations/" + c2 + "/assign").with(nv(SALE_2))).andExpect(status().isOk());
        JsonNode b = data(body(mvc.perform(get("/api/v1/activities").param("contactId", vangLai.toString()).with(qtv()))))
                .get("items").get(0);
        assertThat(b.get("leadId").isNull()).isTrue();
        assertThat(b.get("dealId").isNull()).isTrue();
    }

    @Test
    void nhanHoiThoaiKhongQuaAi_khongGhiGi() throws Exception {
        UUID k = khach(TENANT_H, "Không Qua AI", "0903000004");
        UUID conv = hoiThoai(k, "BOT_HANDLING");
        mvc.perform(post("/api/v1/conversations/" + conv + "/assign").with(nv(SALE_1))).andExpect(status().isOk());
        assertThat(sql("SELECT count(*) FROM sales.activities WHERE contact_id = ?", k)).containsExactly("0");
    }

    // ── ghi thủ công ────────────────────────────────────────────────────────────

    @Test
    void ghiThuCong_kiemDauVao() throws Exception {
        UUID k = khach(TENANT_H, "Kiểm Đầu Vào HĐ", "0903000005");
        UUID khac = khach(TENANT_H, "Khách Khác HĐ", "0903000006");
        String leadKhac = data(body(mvc.perform(post("/api/v1/leads").with(nv(SALE_1)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"contactId\":\"" + khac + "\"}")))).get("id").asText();
        String goc = "{\"contactId\":\"" + k + "\",\"type\":\"CALL\",\"subject\":\"Gọi tư vấn\"";
        ghi(nv(SALE_1), goc + ",\"leadId\":\"" + leadKhac + "\"}").andExpect(status().isUnprocessableEntity());
        ghi(nv(SALE_1), goc + ",\"leadId\":\"" + leadKhac + "\",\"dealId\":\"" + UUID.randomUUID() + "\"}")
                .andExpect(status().isUnprocessableEntity());
        ghi(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"type\":\"FAX\",\"subject\":\"x\"}").andExpect(status().isUnprocessableEntity());
        ghi(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"type\":\"CALL\",\"subject\":\"  \"}").andExpect(status().isUnprocessableEntity());
        ghi(nv(SALE_1), goc + ",\"performedAt\":\"" + Instant.now().plus(Duration.ofHours(2)) + "\"}")
                .andExpect(status().isUnprocessableEntity());
        ghi(nv(SALE_1), goc + ",\"remindAt\":\"" + Instant.now().minus(Duration.ofHours(1)) + "\"}")
                .andExpect(status().isUnprocessableEntity());
        ghi(nv(SALE_1), goc + ",\"outcome\":\"RESCHEDULED\"}").andExpect(status().isUnprocessableEntity());
        ghi(nv(SALE_1), goc + ",\"remindAt\":\"" + Instant.now().plus(Duration.ofDays(1)) + "\",\"remindUserId\":\""
                + SALE_2 + "\"}").andExpect(status().isForbidden());

        JsonNode a = data(body(ghi(nv(SALE_1), goc + ",\"outcome\":\"NO_ANSWER\"}").andExpect(status().isCreated())));
        assertThat(a.get("source").asText()).isEqualTo("MANUAL");
        assertThat(a.get("performedByName").asText()).isEqualTo("Lan Sale");
        assertThat(a.get("performedAt").isNull()).isFalse();
        // Quản trị giao nhắc việc cho nhân viên khác được
        JsonNode giao = data(body(ghi(qtv(), goc + ",\"remindAt\":\"" + Instant.now().plus(Duration.ofDays(2))
                + "\",\"remindUserId\":\"" + SALE_2 + "\"}").andExpect(status().isCreated())));
        assertThat(giao.get("remindUserName").asText()).isEqualTo("Minh Sale");
        assertThat(giao.get("remindStatus").asText()).isEqualTo("PENDING");
    }

    @Test
    void chiMucCsdlChanGanCaLeadLanDeal() throws Exception {
        UUID k = khach(TENANT_H, "Ràng Buộc", "0903000007");
        String lead = data(body(mvc.perform(post("/api/v1/leads").with(nv(SALE_1)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"contactId\":\"" + k + "\"}")))).get("id").asText();
        String deal = data(body(mvc.perform(post("/api/v1/deals").with(nv(SALE_1)).contentType(MediaType.APPLICATION_JSON)
                .content("{\"contactId\":\"" + k + "\",\"title\":\"D\"}")))).get("id").asText();
        try (Connection c = owner()) {
            assertThatThrownBy(() -> exec(c, """
                    INSERT INTO sales.activities (tenant_id, contact_id, lead_id, deal_id, type, performed_by)
                    VALUES (?, ?, ?, ?, 'NOTE', ?)""", TENANT_H, k, UUID.fromString(lead), UUID.fromString(deal), SALE_1))
                    .isInstanceOf(SQLException.class).hasMessageContaining("ck_act_toi_da_mot_dich");
        }
    }

    // ── nhắc việc ───────────────────────────────────────────────────────────────

    @Test
    void viecCuaToi_quaHanHomNaySapToi_vaSoDem() throws Exception {
        UUID k = khach(TENANT_H, "Nhắc Việc", "0903000008");
        String goc = "{\"contactId\":\"" + k + "\",\"type\":\"CALL\",\"subject\":\"";
        String quaHan = data(body(ghi(nv(SALE_2), goc + "quá hạn\",\"remindAt\":\""
                + Instant.now().plus(Duration.ofDays(1)) + "\"}"))).get("id").asText();
        try (Connection c = owner()) {
            exec(c, "UPDATE sales.activities SET remind_at = now() - interval '1 hour' WHERE id = ?", UUID.fromString(quaHan));
        }
        ghi(nv(SALE_2), goc + "hôm nay\",\"remindAt\":\"" + Instant.now().plus(Duration.ofMinutes(1)) + "\"}")
                .andExpect(status().isCreated());
        ghi(nv(SALE_2), goc + "sắp tới\",\"remindAt\":\"" + Instant.now().plus(Duration.ofDays(3)) + "\"}")
                .andExpect(status().isCreated());
        ghi(nv(SALE_1), goc + "của Lan\",\"remindAt\":\"" + Instant.now().plus(Duration.ofDays(3)) + "\"}")
                .andExpect(status().isCreated());

        assertThat(chuDe(viec(nv(SALE_2), "OVERDUE"))).containsExactly("quá hạn");
        assertThat(chuDe(viec(nv(SALE_2), "TODAY"))).containsExactly("hôm nay");
        assertThat(chuDe(viec(nv(SALE_2), "UPCOMING"))).containsExactly("sắp tới");
        assertThat(chuDe(viec(nv(SALE_2), null))).containsExactly("quá hạn", "hôm nay", "sắp tới");
        JsonNode dem = data(body(mvc.perform(get("/api/v1/activities/todo-count").with(nv(SALE_2)))));
        assertThat(dem.get("overdue").asInt()).isEqualTo(1);
        assertThat(dem.get("today").asInt()).isEqualTo(1);

        // Xong thì rời danh sách việc
        sua(nv(SALE_2), quaHan, "{\"remindStatus\":\"DONE\",\"outcome\":\"DONE\"}").andExpect(status().isOk());
        assertThat(chuDe(viec(nv(SALE_2), "OVERDUE"))).isEmpty();
        mvc.perform(get("/api/v1/activities").param("mine", "false").param("bucket", "TODAY").with(nv(SALE_2)))
                .andExpect(status().isUnprocessableEntity());
    }

    @Test
    void quyenSua_nguoiGhiHoacQuanTri_nguoiDuocNhacChiDoiTrangThaiNhac() throws Exception {
        UUID k = khach(TENANT_H, "Quyền Sửa HĐ", "0903000009");
        String id = data(body(ghi(qtv(), "{\"contactId\":\"" + k + "\",\"type\":\"MEETING\",\"subject\":\"Gặp\","
                + "\"remindAt\":\"" + Instant.now().plus(Duration.ofDays(1)) + "\",\"remindUserId\":\"" + SALE_1 + "\"}")))
                .get("id").asText();
        sua(nv(SALE_2), id, "{\"remindStatus\":\"DONE\"}").andExpect(status().isForbidden());
        sua(nv(SALE_1), id, "{\"content\":\"đổi nội dung\"}").andExpect(status().isForbidden());
        sua(nv(SALE_1), id, "{\"remindStatus\":\"CANCELED\"}").andExpect(status().isOk());
        sua(nv(SALE_1), id, "{\"remindStatus\":\"SENT\"}").andExpect(status().isUnprocessableEntity());

        // Người ghi hẹn lại giờ nhắc → lời nhắc mới, PENDING
        JsonNode hen = data(body(sua(qtv(), id, "{\"outcome\":\"RESCHEDULED\",\"remindAt\":\""
                + Instant.now().plus(Duration.ofDays(5)) + "\"}").andExpect(status().isOk())));
        assertThat(hen.get("remindStatus").asText()).isEqualTo("PENDING");
        assertThat(hen.get("outcome").asText()).isEqualTo("RESCHEDULED");
        sua(qtv(), id, "{\"remindAt\":\"" + Instant.now().minus(Duration.ofDays(1)) + "\"}")
                .andExpect(status().isUnprocessableEntity());
        // Không có DELETE
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete("/api/v1/activities/" + id)
                .with(qtv())).andExpect(r -> assertThat(r.getResponse().getStatus()).isGreaterThanOrEqualTo(400));
        assertThat(sql("SELECT count(*) FROM sales.activities WHERE id = ?", UUID.fromString(id))).containsExactly("1");
    }

    @Test
    void cachLy_doanhNghiepKhacKhongThayKhongSuaKhongGhiVaoKhachNguoiKhac() throws Exception {
        UUID k = khach(TENANT_H, "Cách Ly HĐ", "0903000010");
        String id = data(body(ghi(nv(SALE_1), "{\"contactId\":\"" + k + "\",\"type\":\"NOTE\",\"content\":\"bí mật\"}")))
                .get("id").asText();
        JwtRequestPostProcessor kk = asUser(TENANT_K, ADMIN_K, "TENANT_ADMIN");
        assertThat(data(body(mvc.perform(get("/api/v1/activities").param("contactId", k.toString()).with(kk))))
                .get("totalItems").asLong()).isZero();
        sua(kk, id, "{\"content\":\"x\"}").andExpect(status().isNotFound());
        ghi(kk, "{\"contactId\":\"" + k + "\",\"type\":\"NOTE\",\"content\":\"x\"}").andExpect(status().isNotFound());
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private static JwtRequestPostProcessor qtv() {
        return asUser(TENANT_H, ADMIN_H, "TENANT_ADMIN");
    }

    private static JwtRequestPostProcessor nv(UUID userId) {
        return asUser(TENANT_H, userId, "AGENT");
    }

    private static String body(ResultActions r) throws Exception {
        return r.andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
    }

    private ResultActions ghi(JwtRequestPostProcessor who, String json) throws Exception {
        return mvc.perform(post("/api/v1/activities").with(who).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    private ResultActions sua(JwtRequestPostProcessor who, String id, String json) throws Exception {
        return mvc.perform(patch("/api/v1/activities/" + id).with(who).contentType(MediaType.APPLICATION_JSON).content(json));
    }

    private JsonNode viec(JwtRequestPostProcessor who, String bucket) throws Exception {
        var req = get("/api/v1/activities").param("mine", "true").with(who);
        if (bucket != null) {
            req = req.param("bucket", bucket);
        }
        return data(body(mvc.perform(req).andExpect(status().isOk())));
    }

    private static List<String> chuDe(JsonNode page) {
        List<String> out = new ArrayList<>();
        page.get("items").forEach(i -> out.add(i.get("subject").asText()));
        return out;
    }

    private static UUID khach(UUID tenantId, String ten, String phone) throws Exception {
        UUID id = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO engagement.contacts (id, tenant_id, full_name, phone, primary_channel) VALUES (?, ?, ?, ?, 'ZALO')",
                    id, tenantId, ten, phone);
        }
        return id;
    }

    private static UUID hoiThoai(UUID contactId, String trangThai) throws Exception {
        UUID identity = UUID.randomUUID();
        UUID conv = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, """
                    INSERT INTO engagement.channel_identities (id, tenant_id, channel_id, contact_id, external_user_id)
                    VALUES (?, ?, ?, ?, ?)""", identity, TENANT_H, CHANNEL_H, contactId, "zl-" + identity);
            exec(c, """
                    INSERT INTO engagement.conversations (id, tenant_id, channel_id, channel_identity_id, contact_id, status)
                    VALUES (?, ?, ?, ?, ?, ?)""", conv, TENANT_H, CHANNEL_H, identity, contactId, trangThai);
        }
        return conv;
    }

    /** Hội thoại AI vừa chuyển cho nhân viên: chờ nhận + một sự kiện BOT_TO_AGENT chưa ai nhận. */
    private static UUID hoiThoaiChoNhanVien(UUID contactId, String lyDo) throws Exception {
        UUID conv = hoiThoai(contactId, "PENDING_AGENT");
        try (Connection c = owner()) {
            exec(c, """
                    INSERT INTO engagement.handoff_events (tenant_id, conversation_id, direction, reason, triggered_by,
                                                           counts_against_ai_quality, queued_at)
                    VALUES (?, ?, 'BOT_TO_AGENT', ?, 'AI_AGENT', true, now())""", TENANT_H, conv, lyDo);
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
