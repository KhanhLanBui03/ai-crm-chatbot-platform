package com.thesis.crm.platform.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.catchThrowableOfType;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withException;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.thesis.crm.client.AiKnowledgeClient;
import com.thesis.crm.client.AiKnowledgeClient.KbDocument;
import com.thesis.crm.client.AiKnowledgeClient.KbDocumentPage;
import com.thesis.crm.client.AiKnowledgeClient.KbMetadataUpdate;
import com.thesis.crm.client.AiServiceClient;
import com.thesis.crm.client.AiServiceErrors;
import com.thesis.crm.client.AiServiceException;
import com.thesis.crm.common.exception.BusinessException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.converter.json.Jackson2ObjectMapperBuilder;
import org.springframework.mock.http.client.MockClientHttpRequest;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

/**
 * Lớp chuyển tiếp java-core → ai-service (kế hoạch tích hợp giao diện mục 3), không cần Spring
 * context: {@code snake_case} của ai-service thành đúng tên trường {@code dashboard-api.yaml}, và
 * bảng dịch lỗi 404 / 409 / 422 / 5xx / mất nối / 401.
 *
 * <p>Mapper dựng bằng {@link Jackson2ObjectMapperBuilder} cộng đúng một cờ Boot bật thêm
 * (ngày ra chuỗi ISO) — cùng cấu hình mapper thật của ứng dụng.
 */
class KnowledgeRelayTest {

    static final UUID TENANT = UUID.fromString("eca6b30b-114c-4695-a26f-0916c215adf5");
    static final UUID DOC = UUID.fromString("6f1c0a52-0000-4000-8000-000000000001");
    static final UUID NGUOI_TAI = UUID.fromString("6f1c0a52-0000-4000-8000-0000000000aa");

    final ObjectMapper json = Jackson2ObjectMapperBuilder.json()
            .featuresToDisable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS) // như JacksonAutoConfiguration
            .build();
    MockRestServiceServer ai;
    AiKnowledgeClient kho;

    @BeforeEach
    void dung() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://ai-service");
        ai = MockRestServiceServer.bindTo(builder).build();
        kho = new AiKnowledgeClient(new AiServiceClient(builder.build(), json));
    }

    @Test
    void danhSachSnakeThanhCamelVaTuKhoaMaHoaChat() throws Exception {
        ai.expect(requestTo(org.hamcrest.Matchers.startsWith("http://ai-service/v1/documents?")))
                .andExpect(method(HttpMethod.GET))
                .andExpect(header("X-Tenant-Id", TENANT.toString()))
                .andExpect(req -> assertThat(req.getURI().getRawQuery())
                        .contains("page=0", "size=10", "status=READY",
                                // "&" của người dùng không được thành dấu tách tham số
                                "keyword=b%C3%A1o%20gi%C3%A1%20%26%20status%3DFAILED"))
                .andRespond(withSuccess("""
                        {"items": [{
                          "id": "%s", "title": "Bảng giá dịch vụ 2026", "status": "READY",
                          "source_type": "PDF", "uploaded_by": "%s", "chunk_count": 11,
                          "created_at": "2026-10-18T03:12:45.123456Z", "description": null,
                          "language": "vi", "file_name": "bang-gia.pdf", "mime_type": "application/pdf",
                          "file_size_bytes": 204800, "version": 2, "error_message": null,
                          "indexed_at": "2026-10-18T03:13:02+00:00", "updated_at": "2026-10-18T03:13:02Z",
                          "replaces_document_id": null, "reindex_document_id": null, "contact_id": null
                        }], "total": 21, "page": 0, "size": 10}
                        """.formatted(DOC, NGUOI_TAI), MediaType.APPLICATION_JSON));

        KbDocumentPage trang = kho.listDocuments(TENANT, "báo giá & status=FAILED", "READY", null, 0, 10);
        ai.verify();

        KbDocument d = trang.items().get(0);
        assertThat(d.fileSizeBytes()).isEqualTo(204_800L);
        assertThat(d.uploadedBy()).isEqualTo(NGUOI_TAI);
        assertThat(trang.total()).isEqualTo(21);

        JsonNode ra = json.valueToTree(KnowledgeMapper.taiLieu(d, "Quản trị B17"));
        assertThat(ra.get("sizeBytes").asLong()).isEqualTo(204_800L);
        assertThat(ra.get("chunkCount").asInt()).isEqualTo(11);
        assertThat(ra.get("sourceType").asText()).isEqualTo("PDF");
        assertThat(ra.get("uploadedByName").asText()).isEqualTo("Quản trị B17");
        // Hai dạng múi giờ của ai-service ("Z" và "+00:00") ra cùng một chuỗi ISO
        assertThat(ra.get("createdAt").asText()).isEqualTo("2026-10-18T03:12:45.123456Z");
        assertThat(ra.get("indexedAt").asText()).isEqualTo("2026-10-18T03:13:02Z");
        assertThat(ra.has("file_size_bytes")).isFalse();

        // Tiền tố mã của ai-service ("{MÃ}: {câu}") không lọt ra giao diện
        assertThat(KnowledgeMapper.cauLoi("PARSE_NO_TEXT_EXTRACTED: PDF không có lớp chữ — cần OCR"))
                .isEqualTo("PDF không có lớp chữ — cần OCR");
        assertThat(KnowledgeMapper.cauLoi("Lỗi: không có mã")).isEqualTo("Lỗi: không có mã");
    }

    @Test
    void suaGuiDescriptionNullDeXoaMoTa() {
        ai.expect(requestTo("http://ai-service/v1/documents/" + DOC))
                .andExpect(method(HttpMethod.PATCH))
                .andExpect(req -> assertThat(((MockClientHttpRequest) req).getBodyAsString(StandardCharsets.UTF_8))
                        .isEqualTo("{\"title\":\"Bảng giá mới\",\"description\":null}"))
                .andRespond(withStatus(HttpStatus.UNPROCESSABLE_ENTITY).contentType(MediaType.APPLICATION_JSON)
                        .body("{\"code\":\"INVALID_METADATA\",\"message\":\"Đã có tài liệu khác tên 'Bảng giá mới' ở version 1\"}"));

        BusinessException loi = dich(() -> kho.updateMetadata(TENANT, DOC, new KbMetadataUpdate("Bảng giá mới", null)));
        assertThat(loi.getStatus()).isEqualTo(HttpStatus.UNPROCESSABLE_ENTITY);
        assertThat(loi.getCode()).isEqualTo("INVALID_METADATA");
        assertThat(loi.getMessage()).contains("Bảng giá mới");
    }

    @Test
    void bangDichLoi() {
        traLoi(HttpStatus.NOT_FOUND, "DOCUMENT_NOT_FOUND");
        BusinessException khongThay = dich(() -> kho.getDocument(TENANT, DOC));
        assertThat(khongThay.getStatus()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(khongThay.getCode()).isEqualTo("DOCUMENT_NOT_FOUND");
        assertThat(khongThay.getMessage()).doesNotContain(DOC.toString());

        traLoi(HttpStatus.CONFLICT, "DOCUMENT_BUSY");
        BusinessException ban = dich(() -> kho.delete(TENANT, DOC));
        assertThat(ban.getStatus()).isEqualTo(HttpStatus.CONFLICT);
        assertThat(ban.getCode()).isEqualTo("DOCUMENT_BUSY");

        traLoi(HttpStatus.SERVICE_UNAVAILABLE, "STORAGE_UNAVAILABLE");
        BusinessException hong = dich(() -> kho.delete(TENANT, DOC));
        assertThat(hong.getStatus()).isEqualTo(HttpStatus.BAD_GATEWAY);
        assertThat(hong.getCode()).isEqualTo("AI_SERVICE_UNAVAILABLE");

        ai.reset();
        ai.expect(requestTo("http://ai-service/v1/ai/kb/documents/" + DOC))
                .andRespond(withException(new IOException("Connection refused")));
        BusinessException matNoi = dich(() -> kho.delete(TENANT, DOC));
        assertThat(matNoi.getStatus()).isEqualTo(HttpStatus.BAD_GATEWAY);

        // 401 = java-core quên X-Tenant-Id: lỗi của mình, không phải của người dùng
        traLoi(HttpStatus.UNAUTHORIZED, "TENANT_CONTEXT_MISSING");
        BusinessException lech = dich(() -> kho.getDocument(TENANT, DOC));
        assertThat(lech.getStatus()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR);
    }

    private void traLoi(HttpStatus status, String code) {
        ai.reset();
        ai.expect(org.springframework.test.web.client.ExpectedCount.manyTimes(),
                        requestTo(org.hamcrest.Matchers.containsString(DOC.toString())))
                .andRespond(withStatus(status).contentType(MediaType.APPLICATION_JSON)
                        .body("{\"code\":\"" + code + "\",\"message\":\"Tài liệu " + DOC + " — câu của ai-service\"}"));
    }

    private static BusinessException dich(Runnable loiGoi) {
        AiServiceException ex = catchThrowableOfType(loiGoi::run, AiServiceException.class);
        assertThat(ex).as("ai-service phải ném AiServiceException").isNotNull();
        return AiServiceErrors.dich(ex);
    }
}
