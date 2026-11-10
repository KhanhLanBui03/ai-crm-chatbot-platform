package com.thesis.crm.platform.service.impl;

import com.thesis.crm.client.AiKnowledgeClient;
import com.thesis.crm.client.AiKnowledgeClient.KbChunkPage;
import com.thesis.crm.client.AiKnowledgeClient.KbDocument;
import com.thesis.crm.client.AiKnowledgeClient.KbDocumentDeleted;
import com.thesis.crm.client.AiKnowledgeClient.KbDocumentPage;
import com.thesis.crm.client.AiKnowledgeClient.KbIngestionJobPage;
import com.thesis.crm.client.AiKnowledgeClient.KbMetadataUpdate;
import com.thesis.crm.client.AiKnowledgeClient.KbReindexAccepted;
import com.thesis.crm.client.AiServiceClient;
import com.thesis.crm.client.AiServiceClient.KbDocumentAccepted;
import com.thesis.crm.client.AiServiceClient.KbDocumentCreate;
import com.thesis.crm.client.AiServiceErrors;
import com.thesis.crm.client.AiServiceException;
import com.thesis.crm.client.ObjectStorageClient;
import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.enums.UsageMetric;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.exception.QuotaExceededException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.common.util.Texts;
import com.thesis.crm.config.KbProperties;
import com.thesis.crm.platform.dto.request.UpdateDocumentRequest;
import com.thesis.crm.platform.dto.request.UploadDocumentRequest;
import com.thesis.crm.platform.dto.response.CongViecNapResponse;
import com.thesis.crm.platform.dto.response.DoanTaiLieuResponse;
import com.thesis.crm.platform.dto.response.DocumentUploadResponse;
import com.thesis.crm.platform.dto.response.QuotaUsageResponse;
import com.thesis.crm.platform.dto.response.TaiLieuChiTietResponse;
import com.thesis.crm.platform.dto.response.TaiLieuResponse;
import com.thesis.crm.platform.entity.UsageRecord;
import com.thesis.crm.platform.entity.User;
import com.thesis.crm.platform.repository.UserRepository;
import com.thesis.crm.platform.service.KnowledgeDocumentService;
import com.thesis.crm.platform.service.OutboxService;
import com.thesis.crm.platform.service.UsageQuotaService;
import com.thesis.crm.security.CurrentActor;
import com.thesis.crm.security.SecurityUtils;
import com.thesis.crm.security.TenantTransactionScope;
import com.thesis.crm.security.TraceIdFilter;
import java.time.Instant;
import java.util.Collection;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.stream.Collectors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
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

    /** Tên theo đặc tả UC018 và Master Plan §2.6 — chốt 27/09/2026 (ADR-0020 quyết định 4). */
    static final String TOPIC = "crm.kb.document.uploaded";
    static final String AGGREGATE_TYPE = "document";
    static final String EVENT_TYPE = "DocumentUploaded";

    private static final int TEN_TEP_TOI_DA = 255;

    /** {@code entity_type} của ba dòng kiểm toán UC020 bước 8. */
    static final String ENTITY_DOCUMENT = "DOCUMENT";

    private final UsageQuotaService usageQuotaService;
    private final OutboxService outboxService;
    private final ObjectStorageClient objectStorage;
    private final AiServiceClient aiService;
    private final KbProperties kb;
    private final TenantTransactionScope tenantScope;
    private final AiKnowledgeClient kho;
    private final AuditLogWriter audit;
    private final UserRepository users;
    private final TransactionTemplate tx;

    public KnowledgeDocumentServiceImpl(UsageQuotaService usageQuotaService, OutboxService outboxService,
            ObjectStorageClient objectStorage, AiServiceClient aiService, KbProperties kb,
            TenantTransactionScope tenantScope, AiKnowledgeClient kho, AuditLogWriter audit,
            UserRepository users, TransactionTemplate tx) {
        this.usageQuotaService = usageQuotaService;
        this.outboxService = outboxService;
        this.objectStorage = objectStorage;
        this.aiService = aiService;
        this.kb = kb;
        this.tenantScope = tenantScope;
        this.kho = kho;
        this.audit = audit;
        this.users = users;
        this.tx = tx;
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
        UUID tenantId = CurrentActor.requireTenantId();
        // SET LOCAL app.tenant_id NGAY đầu transaction, trước mọi truy vấn — RLS của các bảng hạn mức
        // và outbox dựa vào nó. Filter không đặt được vì nó chạy ngoài transaction.
        tenantScope.apply(tenantId);

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

        // ── Hạn mức tồn kho (ADR-0023): khoá hai dòng tới hết transaction ─────────────
        // Thứ tự DOCUMENT → STORAGE_MB là cố định ở mọi đường gọi; khoá ngược thứ tự là deadlock.
        UsageRecord soTaiLieu = usageQuotaService.lockForConsumption(UsageMetric.DOCUMENT, 1);
        UsageRecord dungLuong = usageQuotaService.lockForConsumption(UsageMetric.STORAGE_MB, file.getSize());

        // ── Tác dụng phụ: từ đây mọi đường lỗi phải dọn object vừa ghi ─────────────────
        String key = KbObjectKey.build(tenantId, UUID.randomUUID(), tenTep);
        String fileUri = objectStorage.put(key, file, file.getSize());

        UUID nguoiTai = SecurityUtils.getCurrentUserId();
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

    // ── UC019 · UC020 — chuyển tiếp sang ai-service (GD1) ───────────────────────────
    // KHÔNG @Transactional ở mức hàm: lời gọi ai-service không được giữ kết nối CSDL. Chỉ hai việc
    // chạm CSDL của java-core — tra tên người tải và ghi kiểm toán — mở transaction ngắn riêng, sau
    // khi ai-service đã trả lời.

    @Override
    public PageResponse<TaiLieuResponse> list(String q, String status, String sourceType, int page, int size) {
        UUID tenantId = CurrentActor.requireTenantId();
        KbDocumentPage trang = goiAi(() -> kho.listDocuments(tenantId, q, status, sourceType, trang(page), co(size)));
        Map<UUID, String> ten = tenNguoiTai(tenantId, trang.items().stream().map(KbDocument::uploadedBy).toList());
        return PageResponse.of(
                trang.items().stream().map(d -> KnowledgeMapper.taiLieu(d, ten.get(d.uploadedBy()))).toList(),
                trang.page(), trang.size(), trang.total());
    }

    @Override
    public TaiLieuChiTietResponse get(UUID documentId) {
        UUID tenantId = CurrentActor.requireTenantId();
        return chiTiet(tenantId, goiAi(() -> kho.getDocument(tenantId, documentId)));
    }

    @Override
    public PageResponse<DoanTaiLieuResponse> chunks(UUID documentId, int page, int size) {
        UUID tenantId = CurrentActor.requireTenantId();
        KbChunkPage trang = goiAi(() -> kho.listChunks(tenantId, documentId, trang(page), co(size)));
        return PageResponse.of(trang.items().stream().map(KnowledgeMapper::doan).toList(),
                trang.page(), trang.size(), trang.total());
    }

    /**
     * Kiểm toán ghi TÊN trường đã sửa, không ghi giá trị: tiêu đề/mô tả có thể chứa tên khách
     * ("Báo giá riêng anh A"), mà nhật ký kiểm toán sống lâu hơn dữ liệu khách (NĐ 13, UC041).
     */
    @Override
    public TaiLieuChiTietResponse update(UUID documentId, UpdateDocumentRequest request) {
        UUID tenantId = CurrentActor.requireTenantId();
        UUID nguoiSua = CurrentActor.requireUserId();
        KbDocument sau = goiAi(() -> kho.updateMetadata(tenantId, documentId,
                new KbMetadataUpdate(request.title(), request.description())));
        ghiKiemToan(tenantId, nguoiSua, "DOCUMENT_UPDATED", documentId,
                Map.of("fields", List.of("title", "description"), "version", sau.version()));
        return chiTiet(tenantId, sau);
    }

    /**
     * Bản cũ vẫn {@code READY} và vẫn được truy hồi tới khi bản bóng nạp xong (ADR-0031) — đặc tả
     * UC020 bước 6 ghi "chuyển về PROCESSING", ở đây thứ chuyển trạng thái là bản bóng. Giao diện
     * điều hướng theo {@code id} của việc nạp trả về, KHÔNG theo {@code documentId} cũ.
     */
    @Override
    public CongViecNapResponse reindex(UUID documentId) {
        UUID tenantId = CurrentActor.requireTenantId();
        UUID nguoiLam = CurrentActor.requireUserId();
        KbReindexAccepted kq = goiAi(() -> kho.reindex(tenantId, documentId));
        ghiKiemToan(tenantId, nguoiLam, "DOCUMENT_REINDEXED", documentId,
                Map.of("shadowDocumentId", kq.jobId().toString(), "version", kq.version()));
        try {
            return KnowledgeMapper.congViec(kho.ingestionJob(tenantId, kq.jobId()));
        } catch (AiServiceException ex) {
            // Bản bóng ĐÃ được xếp hàng — đọc tiến độ hỏng không được biến thành "nạp lại thất bại".
            log.warn("Đã xếp nạp lại {} nhưng chưa đọc được tiến độ bản bóng: {}", documentId, ex.getMessage());
            return new CongViecNapResponse(kq.jobId(), kq.jobId(), null, "REINDEX", "QUEUED", 0, 0, null, null,
                    null, null, null, null, null, Instant.now());
        }
    }

    /**
     * Gỡ ở ai-service trước, rồi MỘT transaction cho phần của java-core: trả lại hạn mức tồn kho
     * (ADR-0023 (f) — thứ tự khoá {@code DOCUMENT} → {@code STORAGE_MB} như lúc tải) và dòng kiểm
     * toán. Lỗi ai-service (502) thì không có gì được ghi.
     *
     * <p>Trả hạn mức theo {@code quotaReleased} của ai-service, không tự suy: chỉ ai-service biết lượt
     * gỡ này có thật sự chuyển một tài liệu ĐƯỢC ĐẾM sang {@code ARCHIVED} không (gỡ lại tài liệu
     * đã gỡ, gỡ bản bóng nạp lại đã hỏng — cả hai đều không trả).
     *
     * <p>Không phát {@code DocumentDeleted} như ADR-0023 (f) ghi: {@code crm.document.v1} chưa có
     * payload và không có consumer nào — ghi ở {@code docs/contracts/giao-dien-gd.md}.
     */
    @Override
    public void archive(UUID documentId) {
        UUID tenantId = CurrentActor.requireTenantId();
        UUID nguoiGo = CurrentActor.requireUserId();
        KbDocumentDeleted kq = goiAi(() -> kho.delete(tenantId, documentId));
        long soByte = kq.fileSizeBytes() == null ? 0 : kq.fileSizeBytes();
        tx.executeWithoutResult(st -> {
            tenantScope.apply(tenantId);
            if (kq.quotaReleased()) {
                usageQuotaService.release(UsageMetric.DOCUMENT, 1);
                if (soByte > 0) {
                    usageQuotaService.release(UsageMetric.STORAGE_MB, soByte);
                }
            }
            audit.recordUserAction(tenantId, nguoiGo, "DOCUMENT_ARCHIVED", ENTITY_DOCUMENT, documentId,
                    Map.of("chunksDeleted", kq.chunksDeleted(), "quotaReleased", kq.quotaReleased()));
        });
    }

    @Override
    public PageResponse<CongViecNapResponse> ingestionJobs(String state, int page, int size) {
        UUID tenantId = CurrentActor.requireTenantId();
        KbIngestionJobPage trang = goiAi(() -> kho.listIngestionJobs(tenantId, state, trang(page), co(size)));
        return PageResponse.of(trang.items().stream().map(KnowledgeMapper::congViec).toList(),
                trang.page(), trang.size(), trang.total());
    }

    /**
     * {@code latestJob}: việc nạp của bản bóng nếu tài liệu đang được nạp lại, không thì của chính
     * nó. Đọc tiến độ hỏng thì để {@code null} — chi tiết tài liệu vẫn xem được.
     */
    private TaiLieuChiTietResponse chiTiet(UUID tenantId, KbDocument d) {
        UUID jobId = d.reindexDocumentId() != null ? d.reindexDocumentId() : d.id();
        CongViecNapResponse viec;
        try {
            viec = KnowledgeMapper.congViec(kho.ingestionJob(tenantId, jobId));
        } catch (AiServiceException ex) {
            log.warn("Không đọc được tiến độ nạp {}: {} {}", jobId, ex.getStatus(), ex.getCode());
            viec = null;
        }
        Map<UUID, String> ten = tenNguoiTai(tenantId, Collections.singletonList(d.uploadedBy()));
        return KnowledgeMapper.chiTiet(d, ten.get(d.uploadedBy()), viec);
    }

    /**
     * {@code uploadedByName} ← {@code platform.users.full_name} — bảng của java-core, đọc dưới RLS
     * của đúng tenant. Một truy vấn cho cả trang. Không thấy người dùng thì {@code null}.
     */
    private Map<UUID, String> tenNguoiTai(UUID tenantId, Collection<UUID> ids) {
        Set<UUID> can = ids.stream().filter(Objects::nonNull).collect(Collectors.toSet());
        if (can.isEmpty()) {
            return Map.of();
        }
        return tx.execute(st -> {
            tenantScope.apply(tenantId);
            return users.findAllById(can).stream().collect(Collectors.toMap(User::getId, User::getFullName));
        });
    }

    /** Transaction riêng, ngắn: chỉ một dòng {@code platform.audit_logs} dưới RLS của tenant. */
    private void ghiKiemToan(UUID tenantId, UUID nguoiLam, String action, UUID documentId, Map<String, ?> duLieu) {
        tx.executeWithoutResult(st -> {
            tenantScope.apply(tenantId);
            audit.recordUserAction(tenantId, nguoiLam, action, ENTITY_DOCUMENT, documentId, duLieu);
        });
    }

    /** Kẹp như các danh sách khác của java-core — ai-service từ chối (422) ngoài khoảng này. */
    private static int trang(int page) {
        return Math.max(0, page);
    }

    private static int co(int size) {
        return Math.min(Math.max(1, size), 100);
    }

    private static <T> T goiAi(Supplier<T> loiGoi) {
        try {
            return loiGoi.get();
        } catch (AiServiceException ex) {
            throw AiServiceErrors.dich(ex);
        }
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
