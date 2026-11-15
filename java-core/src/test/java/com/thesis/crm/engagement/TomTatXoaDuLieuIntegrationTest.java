package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ThreadLocalRandom;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;
import org.springframework.test.web.servlet.ResultActions;

/**
 * GD3 — UC026 (tóm tắt) + UC041 (xoá dữ liệu cá nhân) phía java-core, cùng bề mặt {@code /internal/**}.
 * Postgres thật (RLS, role {@code crm_app}), ai-service giả.
 *
 * <p>Cổng ra GD3 cần ba bằng chứng có test: {@code /internal/**} thiếu token → 401; cổng xác minh → 409
 * (và CSDL tự chặn); xoá {@code lead-scores} luỹ đẳng. Phần còn lại khoá các luồng chính + phụ của đặc tả.
 */
class TomTatXoaDuLieuIntegrationTest extends EngagementIntegrationTestBase {

    static final UUID TENANT_G = UUID.randomUUID();
    static final UUID TENANT_H = UUID.randomUUID();
    static final UUID ADMIN_G = UUID.randomUUID();
    static final UUID AGENT_G = UUID.randomUUID();
    static final String KEY_G = "wk_g_" + UUID.randomUUID().toString().substring(0, 8);
    static final String ORIGIN_G = "https://shop-g.vn";

    private static boolean seededG;

    @BeforeEach
    void seedG() throws Exception {
        AI.respond(FakeAiServer.answer("Dạ cửa hàng mở cửa 8 giờ."));
        if (seededG) {
            return;
        }
        seededG = true;
        try (Connection c = owner()) {
            for (UUID t : new UUID[] {TENANT_G, TENANT_H}) {
                exec(c, """
                        INSERT INTO platform.tenants (id, name, slug, contact_email, status, assignment_mode)
                        VALUES (?, 'DN GD3', ?, ?, 'ACTIVE', 'MANUAL')""", t, "g-" + t.toString().substring(0, 8),
                        "a@" + t.toString().substring(0, 8) + ".vn");
                UUID sub = UUID.randomUUID();
                exec(c, """
                        INSERT INTO platform.tenant_subscriptions (id, tenant_id, plan_id, status, period_start, period_end)
                        SELECT ?, ?, id, 'ACTIVE', now() - interval '1 day', now() + interval '29 days'
                        FROM platform.subscription_plans WHERE code = 'TRIAL'""", sub, t);
                exec(c, """
                        INSERT INTO platform.usage_records (tenant_id, subscription_id, metric, used_value, quota_value)
                        VALUES (?, ?, 'CONVERSATION', 0, 1000), (?, ?, 'DOCUMENT', 5, 100),
                               (?, ?, 'STORAGE_MB', 10000, 1000000)""", t, sub, t, sub, t, sub);
            }
            for (Object[] u : new Object[][] {{ADMIN_G, TENANT_G, "Quản trị G"}, {AGENT_G, TENANT_G, "Nhân viên G"}}) {
                exec(c, """
                        INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                        VALUES (?, ?, ?, 'x', ?, 'ACTIVE')""", u[0], u[1], u[0].toString().substring(0, 8) + "@g.vn", u[2]);
            }
            exec(c, """
                    INSERT INTO engagement.channels (tenant_id, type, name, widget_key, status, config)
                    VALUES (?, 'WEB_WIDGET', 'Web Widget', ?, 'ACTIVE', '{"allowedDomains":["shop-g.vn"]}')""",
                    TENANT_G, KEY_G);
        }
    }

    // ── /internal/** ────────────────────────────────────────────────────────────

    @Test
    void noiBo_thieuSaiToken401_jwtNhanVienKhongMoDuoc_dungToken200() throws Exception {
        String conv = khachMoi("chào shop").conversationId();
        String duong = "/internal/conversations/" + conv + "/messages";

        mvc.perform(get(duong).header("X-Tenant-Id", TENANT_G.toString())).andExpect(status().isUnauthorized());
        mvc.perform(get(duong).header("X-Tenant-Id", TENANT_G.toString()).header("X-Internal-Token", "sai"))
                .andExpect(status().isUnauthorized());
        // Bearer của người dùng KHÔNG mở được /internal: chuỗi này không có resource server → 401
        mvc.perform(get(duong).header("Authorization", "Bearer eyJhbGciOiJSUzI1NiJ9.e30.x")
                .header("X-Tenant-Id", TENANT_G.toString())).andExpect(status().isUnauthorized());
        // Kể cả khi đã có danh tính quản trị viên trong ngữ cảnh: thiếu quyền dịch vụ nội bộ → 403
        mvc.perform(get(duong).with(admin()).header("X-Tenant-Id", TENANT_G.toString()))
                .andExpect(status().isForbidden());

        JsonNode trang = data(noiBo(get(duong), TENANT_G).andExpect(status().isOk()).andReturn().getResponse()
                .getContentAsString(StandardCharsets.UTF_8));
        // Cũ trước: tin khách rồi tới câu của bot
        assertThat(trang.get("items").get(0).get("senderType").asText()).isEqualTo("CUSTOMER");
        assertThat(trang.get("items").get(0).get("content").asText()).isEqualTo("chào shop");
        assertThat(trang.get("items").get(0).get("isRedacted").asBoolean()).isFalse();
        assertThat(trang.get("totalPages").asInt()).isEqualTo(1);
    }

    @Test
    void noiBo_tenantKhac404_thieuTenant400() throws Exception {
        String conv = khachMoi("hỏi giờ mở cửa").conversationId();
        noiBo(get("/internal/conversations/" + conv + "/messages"), TENANT_H).andExpect(status().isNotFound());
        mvc.perform(get("/internal/conversations/" + conv + "/messages").header("X-Internal-Token", INTERNAL_TOKEN))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("TENANT_CONTEXT_MISSING"));
    }

    // ── UC026 ───────────────────────────────────────────────────────────────────

    @Test
    void dongHoiThoai_phatSuKienCungTransaction_aiGhiTomTat_cotPhaiHienBonPhan() throws Exception {
        Khach k = khachMoi("mình muốn đặt lịch cạo vôi răng");
        doiTrangThai(admin(), k, "CLOSED", "Khách đã xong").andExpect(status().isOk());

        // Sự kiện nằm trong outbox, đúng lược đồ crm.conversation.closed.v1 (additionalProperties: false)
        JsonNode payload = json.readTree(motGiaTri("""
                SELECT payload::text FROM platform.outbox_events
                WHERE aggregate_id = ?::uuid AND topic = 'crm.conversation.closed' AND event_type = 'ConversationClosed'""",
                k.conversationId()));
        List<String> khoa = new ArrayList<>();
        payload.fieldNames().forEachRemaining(khoa::add);
        assertThat(khoa).containsExactlyInAnyOrder("conversation_id", "closed_by", "close_reason", "closed_at",
                "message_count");
        assertThat(payload.get("closed_by").asText()).isEqualTo(ADMIN_G.toString());
        assertThat(payload.get("message_count").asInt()).isGreaterThanOrEqualTo(3);

        // Chưa có tóm tắt → null
        nguCanh(k).andExpect(jsonPath("$.data.summary").isEmpty());

        // Worker ai-service ghi qua /internal — gửi lại cùng thân (Kafka giao lại) vẫn 200
        String than = tomTat("CLOSING", "2030-01-01T00:00:00+00:00");
        ghiTomTat(k, than).andExpect(status().isOk());
        ghiTomTat(k, than).andExpect(status().isOk());

        nguCanh(k).andExpect(jsonPath("$.data.summary.trigger").value("CLOSING"))
                .andExpect(jsonPath("$.data.summary.mainNeed").value("Đặt lịch cạo vôi răng"))
                .andExpect(jsonPath("$.data.summary.providedInfo").value("Không có"))
                .andExpect(jsonPath("$.data.summary.unresolvedIssues").value("Chưa chốt giờ"))
                .andExpect(jsonPath("$.data.summary.nextSteps").value("Gọi lại xác nhận"))
                .andExpect(jsonPath("$.data.summary.modelVersion").value("gemini-3.5-flash-lite@tt2"))
                .andExpect(jsonPath("$.data.summary.isStale").value(false));
        assertThat(motGiaTri("SELECT summary FROM engagement.conversations WHERE id = ?::uuid", k.conversationId()))
                .isEqualTo("Nhu cầu chính: Đặt lịch cạo vôi răng");

        // Bản CŨ hơn tới muộn (sự kiện giao lại sau khi đã có bản mới) không đè bản mới
        ghiTomTat(k, tomTat("MANUAL", "2029-01-01T00:00:00+00:00")).andExpect(status().isOk());
        nguCanh(k).andExpect(jsonPath("$.data.summary.trigger").value("CLOSING"));
    }

    @Test
    void ghiTomTat_thieuPhan422_triggerSai422_hoiThoaiKhongCo404() throws Exception {
        Khach k = khachMoi("hỏi");
        ghiTomTat(k, tomTat("CLOSING", "2030-01-01T00:00:00+00:00").replace("\"Chưa chốt giờ\"", "\"\""))
                .andExpect(status().isUnprocessableEntity());
        ghiTomTat(k, tomTat("KHONG_CO", "2030-01-01T00:00:00+00:00")).andExpect(status().isUnprocessableEntity());
        noiBo(patch("/internal/conversations/" + UUID.randomUUID() + "/summary")
                .contentType(MediaType.APPLICATION_JSON).content(tomTat("CLOSING", "2030-01-01T00:00:00+00:00")),
                TENANT_G).andExpect(status().isNotFound());
        // Hậu điều kiện là một mệnh đề — không có gì bị ghi nửa vời
        assertThat(motGiaTri("SELECT summarized_at::text FROM engagement.conversations WHERE id = ?::uuid",
                k.conversationId())).isNull();
    }

    @Test
    void tomTatLai_MANUAL_guiLichSuSangAi_ghiVaTraBanMoi_loiAiGiuMaVaGiuBanCu() throws Exception {
        Khach k = khachMoi("giá tẩy trắng răng bao nhiêu?");
        AI.summarize.set(new FakeAiServer.Script(200, """
                {"trigger": "MANUAL", "mainNeed": "Hỏi giá tẩy trắng", "providedInfo": "Không có",
                 "unresolvedIssues": "Chưa báo giá", "nextSteps": "Gửi bảng giá",
                 "modelVersion": "gemini-3.5-flash-lite@tt2", "summaryText": "Nhu cầu chính: Hỏi giá tẩy trắng",
                 "generatedAt": "2030-02-01T00:00:00+00:00", "interactionId": null}""", 0));

        mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/summary").with(nv()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.trigger").value("MANUAL"))
                .andExpect(jsonPath("$.data.mainNeed").value("Hỏi giá tẩy trắng"))
                .andExpect(jsonPath("$.data.isStale").value(false));
        JsonNode gui = json.readTree(AI.lastSummarizeBody.get());
        assertThat(gui.get("conversation_id").asText()).isEqualTo(k.conversationId());
        assertThat(gui.get("trigger").asText()).isEqualTo("MANUAL");
        assertThat(gui.get("messages").get(0).get("sender").asText()).isEqualTo("CUSTOMER");
        assertThat(gui.get("messages").get(0).get("text").asText()).isEqualTo("giá tẩy trắng răng bao nhiêu?");

        // Mô hình không sinh đủ bốn phần → giữ mã, bản cũ nguyên vẹn (UC026 3.1)
        AI.summarize.set(new FakeAiServer.Script(422,
                "{\"code\": \"SUMMARY_SCHEMA_INVALID\", \"message\": \"thiếu phần\"}", 0));
        mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/summary").with(nv()))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.code").value("SUMMARY_SCHEMA_INVALID"));
        AI.summarize.set(new FakeAiServer.Script(503, "{\"code\": \"LLM_ERROR\"}", 0));
        mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/summary").with(nv()))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.code").value("AI_SERVICE_UNAVAILABLE"));
        nguCanh(k).andExpect(jsonPath("$.data.summary.mainNeed").value("Hỏi giá tẩy trắng"));
    }

    // ── UC041 ───────────────────────────────────────────────────────────────────

    @Test
    void xoaDiemLead_noiBo_luyDang() throws Exception {
        Khach k = khachMoi("tôi muốn mua");
        UUID khach = khachCua(k);
        UUID lead = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO sales.leads (id, tenant_id, contact_id, source) VALUES (?, ?, ?, 'MANUAL')",
                    lead, TENANT_G, khach);
            for (int i = 0; i < 2; i++) {
                exec(c, """
                        INSERT INTO sales.lead_scores (tenant_id, lead_id, contact_id, score, model_version)
                        VALUES (?, ?, ?, 70, 'xgb@1')""", TENANT_G, lead, khach);
            }
        }
        String duong = "/internal/contacts/" + khach + "/lead-scores";
        mvc.perform(delete(duong).header("X-Tenant-Id", TENANT_G.toString())).andExpect(status().isUnauthorized());
        // Tenant khác: RLS + lọc tường minh → không chạm dòng nào
        noiBo(delete(duong), TENANT_H).andExpect(status().isOk()).andExpect(jsonPath("$.data.deleted").value(0));
        noiBo(delete(duong), TENANT_G).andExpect(status().isOk()).andExpect(jsonPath("$.data.deleted").value(2));
        noiBo(delete(duong), TENANT_G).andExpect(status().isOk()).andExpect(jsonPath("$.data.deleted").value(0));
        // Lead vẫn còn (đặc tả: "cơ hội tiềm năng vẫn còn")
        assertThat(motGiaTri("SELECT count(*)::text FROM sales.leads WHERE id = ?::uuid", lead.toString()))
                .isEqualTo("1");
    }

    @Test
    void yeuCauXoa_taoXacMinhThucThi_coCongXacMinh_vaChayLaiPhanDoDang() throws Exception {
        Khach k = khachMoi("số điện thoại mình là 0901234567");
        UUID khach = khachCua(k);
        UUID lead = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO sales.leads (id, tenant_id, contact_id, source, source_conversation_id) "
                    + "VALUES (?, ?, ?, 'AI_AUTO', ?::uuid)", lead, TENANT_G, khach, k.conversationId());
            exec(c, "INSERT INTO engagement.contact_notes (tenant_id, contact_id, author_user_id, content) "
                    + "VALUES (?, ?, ?, 'Khách hẹn gọi lại số 0901234567')", TENANT_G, khach, ADMIN_G);
        }

        // ── bước 1–2: nhân viên tạo thay mặt khách; thiếu căn cứ 422; yêu cầu thứ hai 409 (2.1)
        taoYeuCau(nv(), khach, "  ").andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.code").value("LEGAL_BASIS_REQUIRED"));
        JsonNode moi = data(taoYeuCau(nv(), khach, "Điều 16 NĐ 13/2023, khách gửi thư 12/11")
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.status").value("PENDING"))
                .andExpect(jsonPath("$.data.requestedBy").value("STAFF"))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        String id = moi.get("id").asText();
        assertThat(muc(moi, "engagement.messages").get("affectedRows").asInt()).isGreaterThanOrEqualTo(2);
        assertThat(muc(moi, "ai.ai_interactions").get("affectedRows").isNull()).isTrue();
        taoYeuCau(admin(), khach, "lần hai").andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("ERASURE_ALREADY_OPEN"));

        // Nhân viên thường không xử lý được
        mvc.perform(get("/api/v1/erasure-requests").with(nv())).andExpect(status().isForbidden());
        mvc.perform(post("/api/v1/erasure-requests/" + id + "/execute").with(nv())).andExpect(status().isForbidden());

        // ── 3.1: chưa xác minh → 409 ở ứng dụng, và CSDL tự chặn kể cả khi ứng dụng bị bỏ qua
        thucThi(id).andExpect(status().isConflict()).andExpect(jsonPath("$.code").value("IDENTITY_NOT_VERIFIED"));
        assertThatThrownBy(() -> {
            try (Connection c = owner()) {
                exec(c, "UPDATE platform.data_erasure_requests SET status = 'IN_PROGRESS' WHERE id = ?::uuid", id);
            }
        }).isInstanceOf(SQLException.class).hasMessageContaining("ck_erasure_gate");
        assertThat(AI.privacyCalls.get()).isZero();

        // ── bước 3–4
        mvc.perform(post("/api/v1/erasure-requests/" + id + "/verify-identity").with(admin()))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.identityVerifiedByName").value("Quản trị G"));
        mvc.perform(post("/api/v1/erasure-requests/" + id + "/verify-identity").with(admin()))
                .andExpect(status().isConflict());

        // ── lần 1: ai-service sập → mục AI hỏng, phía CRM vẫn xong, PARTIALLY_FAILED (8.1, 9.1)
        AI.privacy.set(new FakeAiServer.Script(503, "{}", 0));
        JsonNode lan1 = data(thucThi(id).andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("PARTIALLY_FAILED"))
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(muc(lan1, "ai.ai_interactions").get("status").asText()).isEqualTo("FAILED");
        assertThat(muc(lan1, "ai.ai_interactions").get("errorMessage").asText()).startsWith("AI_SERVICE_UNAVAILABLE");
        assertThat(muc(lan1, "engagement.contacts").get("status").asText()).isEqualTo("DONE");
        String lucCrm = muc(lan1, "engagement.messages").get("executedAt").asText();
        assertThat(AI.lastPrivacyToken.get()).isEqualTo(INTERNAL_TOKEN);
        assertThat(AI.lastPrivacyQuery.get()).contains("conversationId=" + k.conversationId());

        // Phía CRM: danh bạ ẩn danh, tin đã che, ghi chú xoá, lead còn nhưng mất liên kết hội thoại nguồn
        assertThat(motGiaTri("SELECT status || '|' || coalesce(phone, '-') || '|' || full_name "
                + "FROM engagement.contacts WHERE id = ?::uuid", khach.toString()))
                .isEqualTo("ANONYMIZED|-|Khách đã ẩn danh");
        assertThat(motGiaTri("SELECT count(*)::text FROM engagement.messages WHERE conversation_id = ?::uuid "
                + "AND sender_type <> 'SYSTEM' AND (NOT is_redacted OR content LIKE '%0901234567%')", k.conversationId()))
                .isEqualTo("0");
        assertThat(motGiaTri("SELECT count(*)::text FROM engagement.contact_notes WHERE contact_id = ?::uuid",
                khach.toString())).isEqualTo("0");
        assertThat(motGiaTri("SELECT coalesce(source_conversation_id::text, 'rong') FROM sales.leads WHERE id = ?::uuid",
                lead.toString())).isEqualTo("rong");

        // ── lần 2: chạy lại — chỉ gọi lại ai-service, mục CRM giữ nguyên mốc; trả hạn mức theo số ai-service báo
        AI.privacy.set(new FakeAiServer.Script(200, """
                {"contactId": "%s", "status": "COMPLETED", "note": "Phạm vi xoá phía AI: ... KHÔNG vươn tới MCP",
                 "releasedDocuments": 1, "releasedStorageBytes": 1234,
                 "items": [
                  {"targetSchema": "knowledge", "targetTable": "knowledge_documents", "action": "DELETE", "status": "DONE", "affectedRows": 1, "errorCode": null},
                  {"targetSchema": "knowledge", "targetTable": "knowledge_chunks", "action": "DELETE", "status": "DONE", "affectedRows": 4, "errorCode": null},
                  {"targetSchema": "ai", "targetTable": "ai_interactions", "action": "DELETE", "status": "DONE", "affectedRows": 2, "errorCode": null},
                  {"targetSchema": "ai", "targetTable": "ai_feedback", "action": "DELETE", "status": "DONE", "affectedRows": 0, "errorCode": null},
                  {"targetSchema": "ai", "targetTable": "ai_tool_calls", "action": "DELETE", "status": "DONE", "affectedRows": 0, "errorCode": null},
                  {"targetSchema": "s3", "targetTable": "kb-tai-lieu", "action": "DELETE", "status": "DONE", "affectedRows": 1, "errorCode": null},
                  {"targetSchema": "sales", "targetTable": "lead_scores", "action": "DELETE", "status": "DONE", "affectedRows": 0, "errorCode": null}
                 ]}""".formatted(khach), 0));
        JsonNode lan2 = data(thucThi(id).andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("COMPLETED"))
                .andExpect(jsonPath("$.data.externalSystemsNote").value("Phạm vi xoá phía AI: ... KHÔNG vươn tới MCP"))
                .andExpect(jsonPath("$.data.certificateUri").isEmpty())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        assertThat(muc(lan2, "engagement.messages").get("executedAt").asText()).isEqualTo(lucCrm);
        assertThat(muc(lan2, "knowledge.knowledge_chunks").get("affectedRows").asInt()).isEqualTo(4);
        assertThat(lan2.get("completedAt").isNull()).isFalse();
        assertThat(motGiaTri("SELECT used_value::text FROM platform.usage_records WHERE tenant_id = ?::uuid "
                + "AND metric = 'DOCUMENT'", TENANT_G.toString())).isEqualTo("4");
        assertThat(motGiaTri("SELECT used_value::text FROM platform.usage_records WHERE tenant_id = ?::uuid "
                + "AND metric = 'STORAGE_MB'", TENANT_G.toString())).isEqualTo("8766");

        // Xong rồi thì không chạy nữa; biên bản gọn nằm ở dòng kiểm toán
        thucThi(id).andExpect(status().isConflict()).andExpect(jsonPath("$.code").value("ERASURE_NOT_EXECUTABLE"));
        assertThat(motGiaTri("SELECT count(*)::text FROM platform.audit_logs WHERE entity_id = ?::uuid "
                + "AND action = 'ERASURE_EXECUTED'", id)).isEqualTo("2");
        assertThat(motGiaTri("SELECT after_data->>'status' FROM platform.audit_logs WHERE entity_id = ?::uuid "
                + "AND action = 'ERASURE_EXECUTED' ORDER BY id DESC LIMIT 1", id)).isEqualTo("COMPLETED");
        // Hồ sơ đã ẩn danh thì không tạo yêu cầu mới được
        taoYeuCau(admin(), khach, "lần ba").andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("CONTACT_ALREADY_ANONYMIZED"));
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    record Khach(String token, String conversationId) {}

    private Khach khachMoi(String loiDau) throws Exception {
        String token = data(mvc.perform(post("/api/v1/widget/session").header("Origin", ORIGIN_G)
                        .header("X-Forwarded-For", "10.7." + ThreadLocalRandom.current().nextInt(256) + ".3")
                        .contentType(MediaType.APPLICATION_JSON).content("{\"widgetKey\":\"" + KEY_G + "\"}"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8))
                .get("token").asText();
        JsonNode luot = data(mvc.perform(post("/api/v1/widget/messages").header("Origin", ORIGIN_G)
                        .header("X-Widget-Token", token).contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of("content", loiDau))))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        String msgId = luot.get("messages").get(0).get("id").asText();
        return new Khach(token, motGiaTri("SELECT conversation_id::text FROM engagement.messages WHERE id = ?::uuid",
                msgId));
    }

    private UUID khachCua(Khach k) throws Exception {
        return UUID.fromString(motGiaTri("SELECT contact_id::text FROM engagement.conversations WHERE id = ?::uuid",
                k.conversationId()));
    }

    private ResultActions noiBo(org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder b,
                                UUID tenant) throws Exception {
        return mvc.perform(b.header("X-Tenant-Id", tenant.toString()).header("X-Internal-Token", INTERNAL_TOKEN));
    }

    private ResultActions ghiTomTat(Khach k, String than) throws Exception {
        return noiBo(patch("/internal/conversations/" + k.conversationId() + "/summary")
                .contentType(MediaType.APPLICATION_JSON).content(than), TENANT_G);
    }

    /** Thân PATCH đúng như {@code BanGhiTomTat.thanh_json()} của ai-service. */
    private static String tomTat(String trigger, String luc) {
        return """
                {"trigger": "%s", "mainNeed": "Đặt lịch cạo vôi răng", "providedInfo": "Không có",
                 "unresolvedIssues": "Chưa chốt giờ", "nextSteps": "Gọi lại xác nhận",
                 "modelVersion": "gemini-3.5-flash-lite@tt2", "summaryText": "Nhu cầu chính: Đặt lịch cạo vôi răng",
                 "generatedAt": "%s"}""".formatted(trigger, luc);
    }

    private ResultActions nguCanh(Khach k) throws Exception {
        return mvc.perform(get("/api/v1/conversations/" + k.conversationId() + "/context").with(nv()))
                .andExpect(status().isOk());
    }

    private ResultActions doiTrangThai(JwtRequestPostProcessor who, Khach k, String st, String lyDo) throws Exception {
        return mvc.perform(post("/api/v1/conversations/" + k.conversationId() + "/status").with(who)
                .contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsString(Map.of("status", st, "closedReason", lyDo))));
    }

    private ResultActions taoYeuCau(JwtRequestPostProcessor who, UUID khach, String canCu) throws Exception {
        return mvc.perform(post("/api/v1/erasure-requests").with(who).contentType(MediaType.APPLICATION_JSON)
                .content(json.writeValueAsString(Map.of("contactId", khach.toString(), "legalBasis", canCu))));
    }

    private ResultActions thucThi(String id) throws Exception {
        return mvc.perform(post("/api/v1/erasure-requests/" + id + "/execute").with(admin()));
    }

    private static JsonNode muc(JsonNode yeuCau, String khoa) {
        for (JsonNode m : yeuCau.get("items")) {
            if ((m.get("targetSchema").asText() + "." + m.get("targetTable").asText()).equals(khoa)) {
                return m;
            }
        }
        throw new AssertionError("Không có mục " + khoa + " trong " + yeuCau);
    }

    private static JwtRequestPostProcessor admin() {
        return asUser(TENANT_G, ADMIN_G, "TENANT_ADMIN");
    }

    private static JwtRequestPostProcessor nv() {
        return asUser(TENANT_G, AGENT_G, "AGENT");
    }

    private static String motGiaTri(String sql, Object... args) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(sql)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            ResultSet rs = ps.executeQuery();
            return rs.next() ? rs.getString(1) : null;
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
