package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;

/**
 * GD2 — mặt tiền java-core cho lượt xử lý AI (SCR036), đánh giá của nhân viên (UC027) và khoảng trống tri
 * thức (SCR034). ai-service giả ({@link FakeAiServer}): kiểm java-core đổi tên trường đúng, gộp chặng độ
 * trễ đúng, tra tên nhân viên ở {@code platform.users}, gửi đúng loại người đánh giá + người từ JWT, và
 * dịch lỗi theo bảng chung ({@code AiServiceErrors}).
 */
class AiInteractionRelayIntegrationTest extends EngagementIntegrationTestBase {

    static final String LUOT = "55555555-5555-5555-5555-555555555555";
    static final String HOI_THOAI = "66666666-6666-6666-6666-666666666666";

    @BeforeEach
    void datLai() {
        AI.interactions.set(new FakeAiServer.Script(200, """
                {"items": [{
                  "id": "%s", "conversation_id": "%s", "message_id": null, "route": "RAG",
                  "intent": "PRICING_POLICY", "intent_confidence": 0.93,
                  "user_query": "niềng răng bao nhiêu tiền", "answer_text": "Dạ 35 triệu [1].",
                  "refused": false, "refusal_reason": null, "discarded_answer": null,
                  "retrieval_top_score": 0.71, "groundedness_score": 1.0,
                  "model_name": "gemini-3.5-flash-lite", "model_version": null,
                  "prompt_tokens": 900, "completion_tokens": 40, "cost_vnd": 0.1235, "latency_ms": 1950,
                  "latency_breakdown": {"guard_ms": 2, "classify_ms": 5, "embed_ms": 10, "retrieve_ms": 30,
                                        "generate_ms": 1900, "postguard_ms": 3},
                  "status": "SUCCESS", "llm_called": true, "degraded": false, "handoff": false,
                  "cached": false,
                  "citations": [{"chunk_id": "11111111-1111-1111-1111-111111111111",
                                 "document_id": "22222222-2222-2222-2222-222222222222",
                                 "document_title": "Bảng giá nha khoa", "section_path": "Niềng răng",
                                 "snippet": "Niềng mắc cài kim loại 35.000.000đ"}],
                  "feedback": [
                    {"id": "77777777-7777-7777-7777-777777777777", "rater_type": "AGENT",
                     "rater_user_id": "%s", "rating": "NEGATIVE", "reason_code": "INCOMPLETE",
                     "comment": "thiếu trả góp", "corrected_answer": "35 triệu, trả góp 0%%.",
                     "rated_at": "2026-11-10T08:00:00Z"},
                    {"id": "88888888-8888-8888-8888-888888888888", "rater_type": "CUSTOMER",
                     "rater_user_id": null, "rating": "POSITIVE", "reason_code": null, "comment": null,
                     "corrected_answer": null, "rated_at": "2026-11-10T07:00:00Z"}],
                  "created_at": "2026-11-10T06:59:00Z"}],
                 "total": 21, "page": 0, "size": 10}
                """.formatted(LUOT, HOI_THOAI, AGENT_A), 0));
        AI.feedback.set(new FakeAiServer.Script(200, """
                {"success": true, "message": "Đã ghi nhận đánh giá",
                 "feedback_id": "44444444-4444-4444-4444-444444444444", "created": true}""", 0));
    }

    @Test
    void danhSachLuot_doiTenTruong_gopChang_traTenNhanVien_ngayTheoMuiGioDoanhNghiep() throws Exception {
        JsonNode trang = data(mvc.perform(get("/api/v1/ai-interactions")
                        .param("refused", "false").param("rating", "NEGATIVE").param("conversationId", HOI_THOAI)
                        .param("from", "2026-11-01").param("to", "2026-11-10").param("size", "10")
                        .with(as(TENANT_A)))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));

        // Tenant từ JWT; ngày của doanh nghiệp (Asia/Ho_Chi_Minh, +07) quy ra nửa khoảng [tu, den)
        assertThat(java.net.URLDecoder.decode(AI.lastInteractionsQuery.get(), StandardCharsets.UTF_8))
                .contains("refused=false", "rating=NEGATIVE", "conversation_id=" + HOI_THOAI,
                        "tu=2026-10-31T17:00:00Z", "den=2026-11-10T17:00:00Z", "size=10");
        assertThat(trang.get("totalItems").asLong()).isEqualTo(21);
        assertThat(trang.get("totalPages").asInt()).isEqualTo(3);
        JsonNode l = trang.get("items").get(0);
        assertThat(l.get("intentLabel").asText()).isEqualTo("PRICING_POLICY");
        assertThat(l.get("userQuery").asText()).isEqualTo("niềng răng bao nhiêu tiền");
        assertThat(l.get("retrievalTopScore").asDouble()).isEqualTo(0.71);
        assertThat(l.get("errorCode").isNull()).isTrue();
        // Gộp chặng như màn Hiệu quả AI: truy hồi = nhúng + truy hồi, kiểm duyệt = trước + hậu kiểm
        JsonNode chang = l.get("latencyBreakdown");
        assertThat(chang.get("retrieve").asInt()).isEqualTo(40);
        assertThat(chang.get("generate").asInt()).isEqualTo(1900);
        assertThat(chang.get("guard").asInt()).isEqualTo(5);
        assertThat(chang.has("rerank")).isFalse(); // chặng không chạy thì không có khoá
        assertThat(l.get("citations").get(0).get("documentTitle").asText()).isEqualTo("Bảng giá nha khoa");
        assertThat(l.get("citations").get(0).get("sectionPath").asText()).isEqualTo("Niềng răng");
        // Tên nhân viên tra ở platform.users; khách không có tên
        JsonNode dg = l.get("feedbacks");
        assertThat(dg).hasSize(2);
        assertThat(dg.get(0).get("ratedByName").asText()).isEqualTo("Nhân viên A");
        assertThat(dg.get(0).get("correctedAnswer").asText()).isEqualTo("35 triệu, trả góp 0%.");
        assertThat(dg.get(1).get("ratedByType").asText()).isEqualTo("CUSTOMER");
        assertThat(dg.get(1).get("ratedByName").isNull()).isTrue();
        assertThat(l.get("feedback").get("id").asText()).isEqualTo("77777777-7777-7777-7777-777777777777");
    }

    /**
     * GD4 — hội thoại mới chỉ có khách đánh giá: không có nhân viên nào để tra tên nên bảng tên là
     * {@code Map.of()}, và {@code Map.of().get(null)} ném NPE → cột ngữ cảnh hộp thư 500 trước khi sửa.
     */
    @Test
    void danhSachLuot_chiCoKhachDanhGia_200() throws Exception {
        AI.interactions.set(new FakeAiServer.Script(200, """
                {"items": [{
                  "id": "%s", "conversation_id": "%s", "message_id": null, "route": "RAG",
                  "intent": "PRICING_POLICY", "intent_confidence": 0.93,
                  "user_query": "tẩy trắng bao nhiêu", "answer_text": "Dạ 2,5 triệu [1].",
                  "refused": false, "status": "SUCCESS", "citations": [],
                  "feedback": [
                    {"id": "88888888-8888-8888-8888-888888888888", "rater_type": "CUSTOMER",
                     "rater_user_id": null, "rating": "NEGATIVE", "reason_code": "INCOMPLETE", "comment": null,
                     "corrected_answer": null, "rated_at": "2026-11-14T02:03:27Z"}],
                  "created_at": "2026-11-14T02:03:26Z"}],
                 "total": 1, "page": 0, "size": 100}
                """.formatted(LUOT, HOI_THOAI), 0));

        JsonNode trang = data(mvc.perform(get("/api/v1/ai-interactions")
                        .param("conversationId", HOI_THOAI).param("size", "100").with(as(TENANT_A)))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));

        JsonNode dg = trang.get("items").get(0).get("feedbacks");
        assertThat(dg).hasSize(1);
        assertThat(dg.get(0).get("ratedByType").asText()).isEqualTo("CUSTOMER");
        assertThat(dg.get(0).get("ratedByName").isNull()).isTrue();
    }

    @Test
    void danhGia_cheThieuLyDo_422_khongGoiAiService() throws Exception {
        int truoc = AI.feedbackCalls.get();
        mvc.perform(post("/api/v1/ai-interactions/" + LUOT + "/feedback").with(as(TENANT_A))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"rating\":\"NEGATIVE\"}"))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.code").value("REASON_REQUIRED"));
        assertThat(AI.feedbackCalls.get()).isEqualTo(truoc);
    }

    @Test
    void danhGia_nhanVien_guiAgentVaNguoiTuJwt_kemCauSua_201() throws Exception {
        mvc.perform(post("/api/v1/ai-interactions/" + LUOT + "/feedback")
                        .with(asUser(TENANT_A, AGENT_A, "AGENT"))
                        .contentType(MediaType.APPLICATION_JSON).content("""
                                {"rating": "NEGATIVE", "reasonCode": "INCOMPLETE", "comment": "  thiếu trả góp  ",
                                 "correctedAnswer": "35 triệu, trả góp 0%."}"""))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.ratedByType").value("AGENT"))
                .andExpect(jsonPath("$.data.ratedByName").value("Nhân viên A"))
                .andExpect(jsonPath("$.data.comment").value("thiếu trả góp"));
        assertThat(AI.lastFeedbackPath.get()).isEqualTo("/v1/ai-interactions/" + LUOT + "/feedback");
        assertThat(AI.lastFeedbackTenant.get()).isEqualTo(TENANT_A.toString());
        JsonNode than = json.readTree(AI.lastFeedbackBody.get());
        assertThat(than.get("rating").asInt()).isEqualTo(-1);
        assertThat(than.get("rater_type").asText()).isEqualTo("AGENT");
        assertThat(than.get("rater_user_id").asText()).isEqualTo(AGENT_A.toString());
        assertThat(than.get("corrected_answer").asText()).isEqualTo("35 triệu, trả góp 0%.");
        assertThat(than.has("tenant_id")).isFalse();
    }

    @Test
    void danhGia_khen_boLyDo() throws Exception {
        mvc.perform(post("/api/v1/ai-interactions/" + LUOT + "/feedback").with(as(TENANT_A))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"rating\":\"POSITIVE\",\"reasonCode\":\"WRONG_INFO\"}"))
                .andExpect(status().isCreated());
        JsonNode than = json.readTree(AI.lastFeedbackBody.get());
        assertThat(than.get("rating").asInt()).isEqualTo(1);
        assertThat(than.get("reason_code").isNull()).isTrue();
    }

    @Test
    void danhGia_luotKhongThuocDoanhNghiep_404_giuMa() throws Exception {
        AI.feedback.set(new FakeAiServer.Script(404,
                "{\"code\":\"INTERACTION_NOT_FOUND\",\"message\":\"Không có lượt xử lý " + LUOT + "\"}", 0));
        mvc.perform(post("/api/v1/ai-interactions/" + LUOT + "/feedback").with(as(TENANT_B))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"rating\":\"POSITIVE\"}"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("INTERACTION_NOT_FOUND"))
                .andExpect(jsonPath("$.message").value("Không tìm thấy lượt trả lời này."));
    }

    @Test
    void aiServiceSap_502() throws Exception {
        AI.interactions.set(new FakeAiServer.Script(500, "{\"code\":\"INTERNAL_ERROR\",\"message\":\"x\"}", 0));
        mvc.perform(get("/api/v1/ai-interactions").with(as(TENANT_A)))
                .andExpect(status().isBadGateway())
                .andExpect(jsonPath("$.code").value("AI_SERVICE_UNAVAILABLE"));
    }

    @Test
    void khoangTrong_doiTenTruong_bacUuTienTheoSoKhach() throws Exception {
        AI.gaps.set(new FakeAiServer.Script(200, """
                {"items": [
                  {"id": "99999999-9999-9999-9999-999999999999", "query_text": "tẩy trắng răng giá bao nhiêu",
                   "gap_type": "NOT_COVERED", "unanswered_count": 4, "distinct_conversation_count": 2,
                   "first_occurred_at": "2026-11-09T01:00:00Z", "last_occurred_at": "2026-11-10T01:00:00Z"}],
                 "total": 1, "page": 0, "size": 25}""", 0));
        mvc.perform(get("/api/v1/knowledge-gaps").param("gapType", "NOT_COVERED").with(as(TENANT_A)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].questionText").value("tẩy trắng răng giá bao nhiêu"))
                .andExpect(jsonPath("$.data.items[0].occurrenceCount").value(4))
                .andExpect(jsonPath("$.data.items[0].distinctContactCount").value(2))
                .andExpect(jsonPath("$.data.items[0].priority").value(2))
                .andExpect(jsonPath("$.data.items[0].lastSeenAt").value("2026-11-10T01:00:00Z"));
    }
}
