package com.thesis.crm.platform.service.impl;

import com.thesis.crm.client.AiServiceClient;
import com.thesis.crm.client.AiServiceClient.KbDocumentAccepted;
import com.thesis.crm.client.AiServiceClient.KbDocumentCreate;
import com.thesis.crm.client.AiServiceException;
import com.thesis.crm.client.ObjectStorageClient;
import com.thesis.crm.common.enums.UsageMetric;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.exception.QuotaExceededException;
import com.thesis.crm.common.util.Texts;
import com.thesis.crm.config.KbProperties;
import com.thesis.crm.platform.dto.request.UploadDocumentRequest;
import com.thesis.crm.platform.dto.response.DocumentUploadResponse;
import com.thesis.crm.platform.dto.response.QuotaUsageResponse;
import com.thesis.crm.platform.entity.UsageRecord;
import com.thesis.crm.platform.service.KnowledgeDocumentService;
import com.thesis.crm.platform.service.OutboxService;
import com.thesis.crm.platform.service.UsageQuotaService;
import com.thesis.crm.security.TenantContext;
import com.thesis.crm.security.TraceIdFilter;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

/**
 * UC018 phía java-core. Thứ tự bước là hợp đồng — {@code docs/contracts/uc018-tai-tai-lieu.md}
 * mục 1.3 và mục 4. Đổi thứ tự ở đây là đổi mã lỗi người dùng nhận.
 *
 * <p>Mọi bước kiểm rẻ (dung lượng, tên, đuôi, hạn mức) đứng TRƯỚC mọi bước có tác dụng phụ (ghi
 * S3, gọi ai-service): tệp bị từ chối thì không để lại gì ở đâu cả.
 */
@Service
public class KnowledgeDocumentServiceImpl implements KnowledgeDocumentService {

    private static final Logger log = LoggerFactory.getLogger(KnowledgeDocumentServiceImpl.class);

    /**
     * Gương của {@code DINH_DANG_THEO_DUOI} trong {@code ai-service/src/ai/rag/ingest/mime.py}.
     * java-core chặn sớm để khỏi ghi S3 và gọi ai-service cho một tệp chắc chắn bị từ chối;
     * ai-service vẫn kiểm lại, kèm nội dung thật.
     */
    static final List<String> DUOI_NHAN = List.of(".pdf", ".docx", ".txt", ".md", ".markdown", ".html", ".htm");

    /** Tên theo đặc tả UC018 và Master Plan §2.6 — chốt 27/09/2026 (ADR-0017 quyết định 4). */
    static final String TOPIC = "crm.kb.document.uploaded";
    static final String AGGREGATE_TYPE = "document";
    static final String EVENT_TYPE = "DocumentUploaded";

    private static final int TEN_TEP_TOI_DA = 255;

    private final UsageQuotaService usageQuotaService;
    private final OutboxService outboxService;
    private final ObjectStorageClient objectStorage;
    private final AiServiceClient aiService;
    private final KbProperties kb;

    public KnowledgeDocumentServiceImpl(UsageQuotaService usageQuotaService, OutboxService outboxService,
            ObjectStorageClient objectStorage, AiServiceClient aiService, KbProperties kb) {
        this.usageQuotaService = usageQuotaService;
        this.outboxService = outboxService;
        this.objectStorage = objectStorage;
        this.aiService = aiService;
        this.kb = kb;
    }

    /**
     * Một transaction cho cả lượt. Khoá dòng hạn mức giữ từ lúc kiểm tới lúc cộng — kể cả trong
     * lúc ghi S3 và chờ ai-service — để hai lượt đồng thời không cùng lọt qua ô cuối cùng.
     *
     * <p>{@code noRollbackFor}: lượt bị 409 có thể vừa ghi {@code blocked_at}; mốc đó phải được
     * commit dù phản hồi là lỗi.
     */
    @Override
    @Transactional(noRollbackFor = QuotaExceededException.class)
    public DocumentUploadResponse upload(MultipartFile file, UploadDocumentRequest request) {
        UUID tenantId = TenantContext.requireTenantId();

        // ── Kiểm rẻ, chưa ghi gì ────────────────────────────────────────────────────────
        // 413 lớp hai. Lớp một là giới hạn multipart của servlet, cùng đọc crm.kb.max-file-size.
        if (file.getSize() > kb.maxFileSize().toBytes()) {
            throw new BusinessException(HttpStatus.PAYLOAD_TOO_LARGE, "FILE_TOO_LARGE",
                    "Tệp vượt quá 20 MB. Hãy tách nhỏ rồi tải lên từng phần.");
        }
        String tenTep = KbObjectKey.cleanFileName(file.getOriginalFilename());
        int doDaiTen = Texts.codePointLength(tenTep);
        if (doDaiTen == 0 || doDaiTen > TEN_TEP_TOI_DA) {
            throw new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "INVALID_METADATA",
                    "Tên tệp phải từ 1 đến " + TEN_TEP_TOI_DA + " ký tự");
        }
        String duoi = KbObjectKey.extension(tenTep);
        if (!DUOI_NHAN.contains(duoi)) {
            throw new BusinessException(HttpStatus.UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_FORMAT",
                    "Không nhận đuôi " + (duoi.isEmpty() ? "(trống)" : duoi) + ". Chỉ nhận: "
                            + String.join(", ", DUOI_NHAN));
        }

        // ── Hạn mức tồn kho (ADR-0020): khoá hai dòng tới hết transaction ─────────────
        // Thứ tự DOCUMENT → STORAGE_MB là cố định ở mọi đường gọi; khoá ngược thứ tự là deadlock.
        UsageRecord soTaiLieu = usageQuotaService.lockForConsumption(UsageMetric.DOCUMENT, 1);
        UsageRecord dungLuong = usageQuotaService.lockForConsumption(UsageMetric.STORAGE_MB, file.getSize());

        // ── Tác dụng phụ: từ đây mọi đường lỗi phải dọn object vừa ghi ─────────────────
        String key = KbObjectKey.build(tenantId, UUID.randomUUID(), tenTep);
        String fileUri = objectStorage.put(key, file, file.getSize());

        UUID nguoiTai = TenantContext.currentUserId().orElse(null);
        KbDocumentAccepted daNhan;
        try {
            daNhan = aiService.createKbDocument(tenantId, MDC.get(TraceIdFilter.MDC_KEY), new KbDocumentCreate(
                    fileUri, tenTep, request.title(), request.description(), request.language(), nguoiTai));
        } catch (AiServiceException ex) {
            objectStorage.deleteQuietly(key);
            throw dichLoiAiService(ex);
        } catch (RuntimeException ex) {
            objectStorage.deleteQuietly(key);
            throw ex;
        }

        // ── ai-service đã nhận: cộng hạn mức + sự kiện, CÙNG transaction (ADR-0003) ────
        QuotaUsageResponse soTaiLieuSau = usageQuotaService.consume(soTaiLieu, 1);
        QuotaUsageResponse dungLuongSau = usageQuotaService.consume(dungLuong, file.getSize());
        outboxService.append(tenantId, AGGREGATE_TYPE, daNhan.documentId(), EVENT_TYPE, TOPIC,
                payloadSuKien(daNhan, file.getSize(), request.language(), nguoiTai));

        return new DocumentUploadResponse(
                daNhan.documentId(),
                daNhan.jobId(),
                daNhan.title(),
                request.description(),
                daNhan.sourceType(),
                tenTep,
                daNhan.mimeType(),
                file.getSize(),
                request.language(),
                daNhan.status(),
                0,
                daNhan.version(),
                null,
                null,
                null,
                Instant.now(),
                soTaiLieuSau,
                dungLuongSau);
    }

    /**
     * Payload của {@code DocumentUploaded}. Cố ý KHÔNG có tiêu đề, tên tệp, URI: consumer
     * {@code ingestion-cg} đọc chi tiết từ {@code knowledge_documents} theo {@code document_id}, và
     * sự kiện càng ít dữ liệu người dùng nhập thì càng ít thứ phải xoá khi có yêu cầu UC041.
     */
    private static Map<String, Object> payloadSuKien(KbDocumentAccepted d, long sizeBytes, String language,
            UUID uploadedBy) {
        Map<String, Object> p = new LinkedHashMap<>();
        p.put("document_id", d.documentId().toString());
        p.put("version", d.version());
        p.put("source_type", d.sourceType());
        p.put("mime_type", d.mimeType());
        p.put("size_bytes", sizeBytes);
        p.put("language", language);
        p.put("uploaded_by", uploadedBy == null ? null : uploadedBy.toString());
        return p;
    }

    /**
     * ai-service từ chối → lỗi cho người dùng. Bảng đầy đủ: hợp đồng UC018 mục 2.4.
     *
     * <p>Lỗi do NỘI DUNG tệp (413/415/422 validate) chuyển nguyên mã và thông điệp — thông điệp của
     * ai-service viết cho người dùng đọc. Lỗi do HAI BÊN LỆCH NHAU (401, 403 URI, 422 không thấy
     * tệp) thành 500: người dùng không sửa được gì, còn người vận hành cần thấy nó trong log ERROR.
     */
    private static BusinessException dichLoiAiService(AiServiceException ex) {
        if (ex.isUnreachable()) {
            log.error("Không gọi được ai-service", ex);
            return khongPhanHoi();
        }
        String code = ex.getCode();
        switch (ex.getStatus()) {
            case 413:
                return new BusinessException(HttpStatus.PAYLOAD_TOO_LARGE, "FILE_TOO_LARGE", ex.getMessage());
            case 415:
                return new BusinessException(HttpStatus.UNSUPPORTED_MEDIA_TYPE, "UNSUPPORTED_FORMAT",
                        ex.getMessage());
            case 422:
                if ("INVALID_METADATA".equals(code)) {
                    return new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "INVALID_METADATA",
                            ex.getMessage());
                }
                break;
            case 503:
                if ("STORAGE_UNAVAILABLE".equals(code)) {
                    return new BusinessException(HttpStatus.SERVICE_UNAVAILABLE, "STORAGE_UNAVAILABLE",
                            "Kho lưu trữ tệp tạm thời không phản hồi. Thử lại sau.");
                }
                break;
            default:
                break;
        }
        if (ex.getStatus() >= 500) {
            log.error("ai-service lỗi {} {}", ex.getStatus(), code);
            return khongPhanHoi();
        }
        // 401 TENANT_CONTEXT_MISSING, 403 FORBIDDEN_FILE_URI, 422 FILE_NOT_FOUND, 2xx lạ…
        log.error("ai-service từ chối lượt tải vì lệch hợp đồng: {} {} — {}", ex.getStatus(), code, ex.getMessage());
        return new BusinessException(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Lỗi nội bộ");
    }

    private static BusinessException khongPhanHoi() {
        return new BusinessException(HttpStatus.SERVICE_UNAVAILABLE, "AI_SERVICE_UNAVAILABLE",
                "Dịch vụ AI tạm thời không phản hồi. Thử lại sau.");
    }
}
