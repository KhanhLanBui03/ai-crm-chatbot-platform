package com.thesis.crm.platform.erasure;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.client.AiPrivacyClient;
import com.thesis.crm.client.AiPrivacyClient.ErasureResult;
import com.thesis.crm.client.AiServiceErrors;
import com.thesis.crm.client.AiServiceException;
import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.enums.UsageMetric;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.config.S3Properties;
import com.thesis.crm.platform.erasure.ErasureDtos.CreateErasureRequest;
import com.thesis.crm.platform.erasure.ErasureDtos.ErasureItem;
import com.thesis.crm.platform.erasure.ErasureDtos.ErasureRequestDetail;
import com.thesis.crm.platform.erasure.ErasureDtos.ErasureRequestDto;
import com.thesis.crm.platform.erasure.ErasureRepository.ContactRow;
import com.thesis.crm.platform.erasure.ErasureRepository.RequestRow;
import com.thesis.crm.platform.service.UsageQuotaService;
import com.thesis.crm.security.TenantTransactionScope;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * UC041 — xử lý yêu cầu xoá dữ liệu cá nhân (Nghị định 13/2023/NĐ-CP), phần của CRM: tiếp nhận, xác
 * minh danh tính, xem trước phạm vi, thực thi trên schema Track A, biên bản và nhật ký kiểm toán. Phần
 * Track B (đoạn tri thức, lượt xử lý AI, tệp gốc, đặc trưng lead) do ai-service xoá khi được gọi —
 * "bên AI không tự khởi động việc xoá".
 *
 * <p><b>Thực thi ĐỒNG BỘ</b> (giảm độ sâu, kế hoạch GD3): một lượt bấm chạy hết rồi trả chi tiết. Ba
 * chặng, không chặng nào giữ transaction quanh lời gọi mạng:
 * <ol>
 *   <li>khoá yêu cầu → kiểm cổng xác minh → {@code IN_PROGRESS} (commit ngay, để lượt bấm thứ hai thấy
 *       đang chạy và bị chặn);</li>
 *   <li>gọi ai-service NGOÀI transaction — giữa lượt đó ai-service gọi ngược
 *       {@code DELETE /internal/contacts/{id}/lead-scores}, giữ transaction ở đây là tự khoá mình;</li>
 *   <li>một transaction cho mọi bảng phía CRM + trả hạn mức + kết luận + kiểm toán.</li>
 * </ol>
 *
 * <p><b>Chạy lại phần dở dang</b> (luồng phụ 8.1): mục {@code DONE} không bao giờ chạy lại. Phía AI hỏng
 * (9.1) thì chỉ các mục AI ghi {@code FAILED}, phía CRM vẫn làm — yêu cầu kết thúc
 * {@code PARTIALLY_FAILED}, bấm lại thì chỉ gọi lại ai-service (endpoint luỹ đẳng).
 */
@Service
public class ErasureService {

    private static final Logger log = LoggerFactory.getLogger(ErasureService.class);
    private static final TypeReference<List<ErasureItem>> ITEMS = new TypeReference<>() {};

    static final Set<String> REQUESTED_BY = Set.of("CONTACT", "STAFF");
    static final Set<String> EXECUTABLE = Set.of("PENDING", "PARTIALLY_FAILED");
    static final String ENTITY = "ERASURE_REQUEST";
    static final int MAX_LEGAL_BASIS = 2_000;

    /**
     * Giới hạn bắt buộc phải hiện cho người duyệt (bước 6). Ghi ngay lúc tạo để màn xem trước/hộp thoại
     * thực thi có nó TRƯỚC khi chạy; thực thi xong thì thay bằng câu của chính ai-service (nói rõ phạm vi
     * phía AI).
     */
    static final String EXTERNAL_NOTE = "Phạm vi xoá dừng ở hệ thống này: dữ liệu đã gửi sang hệ thống bên "
            + "ngoài qua công cụ MCP và dữ liệu đã gửi tới nhà cung cấp mô hình ngôn ngữ KHÔNG nằm trong phạm vi "
            + "xoá. Phải gửi yêu cầu xoá riêng cho đơn vị đó và lưu văn bản xác nhận vào hồ sơ.";

    private final ErasureRepository repo;
    private final TenantTransactionScope scope;
    private final TransactionTemplate tx;
    private final AiPrivacyClient ai;
    private final AuditLogWriter audit;
    private final UsageQuotaService quota;
    private final ObjectMapper json;
    private final String bucket;

    public ErasureService(ErasureRepository repo, TenantTransactionScope scope, TransactionTemplate tx,
                          AiPrivacyClient ai, AuditLogWriter audit, UsageQuotaService quota, ObjectMapper json,
                          S3Properties s3) {
        this.repo = repo;
        this.scope = scope;
        this.tx = tx;
        this.ai = ai;
        this.audit = audit;
        this.quota = quota;
        this.json = json;
        this.bucket = s3.bucket();
    }

    // ── đọc ─────────────────────────────────────────────────────────────────────

    @Transactional(readOnly = true)
    public PageResponse<ErasureRequestDto> list(UUID tenantId, String status, int page, int size) {
        scope.apply(tenantId);
        if (status != null && !Set.of("PENDING", "IN_PROGRESS", "COMPLETED", "PARTIALLY_FAILED").contains(status)) {
            throw invalid("INVALID_STATUS", "Trạng thái yêu cầu xoá không hợp lệ.");
        }
        int p = Math.max(0, page);
        int s = Math.min(Math.max(1, size), 100);
        return PageResponse.of(repo.list(tenantId, status, p * s, s).stream().map(ErasureService::dong).toList(),
                p, s, repo.count(tenantId, status));
    }

    @Transactional(readOnly = true)
    public ErasureRequestDetail detail(UUID tenantId, UUID id) {
        scope.apply(tenantId);
        return chiTiet(require(tenantId, id));
    }

    /**
     * UC041 bước 5 — từng bảng sẽ bị đụng tới và hành động. Phía CRM đếm thật; phía AI để {@code null}
     * ("biết sau khi thực thi"): java-core không đọc schema {@code ai}/{@code knowledge} (ADR-0002).
     */
    @Transactional(readOnly = true)
    public List<ErasureItem> preview(UUID tenantId, UUID contactId) {
        scope.apply(tenantId);
        if (contactId == null) {
            throw invalid("CONTACT_REQUIRED", "Chọn khách hàng cần xem phạm vi xoá.");
        }
        if (repo.findContact(tenantId, contactId).isEmpty()) {
            throw new BusinessException(HttpStatus.NOT_FOUND, "CONTACT_NOT_FOUND", "Không tìm thấy khách hàng.");
        }
        return phamVi(tenantId, contactId);
    }

    // ── bước 1–4 ────────────────────────────────────────────────────────────────

    /** UC041 bước 1–2. Nhân viên tạo thay mặt khách ({@code STAFF}) hoặc ghi nhận yêu cầu khách tự gửi. */
    @Transactional
    public ErasureRequestDetail create(UUID tenantId, UUID actorUserId, CreateErasureRequest r) {
        scope.apply(tenantId);
        if (r == null || r.contactId() == null) {
            throw invalid("CONTACT_REQUIRED", "Chọn khách hàng cần xoá dữ liệu.");
        }
        String canCu = r.legalBasis() == null ? "" : r.legalBasis().strip();
        if (canCu.isEmpty()) {
            throw invalid("LEGAL_BASIS_REQUIRED", "Căn cứ pháp lý là trường bắt buộc.");
        }
        if (canCu.length() > MAX_LEGAL_BASIS) {
            throw invalid("LEGAL_BASIS_TOO_LONG", "Căn cứ pháp lý tối đa 2.000 ký tự.");
        }
        String nguon = r.requestedBy() == null ? "STAFF" : r.requestedBy();
        if (!REQUESTED_BY.contains(nguon)) {
            throw invalid("INVALID_REQUESTED_BY", "Nguồn yêu cầu chỉ nhận CONTACT hoặc STAFF.");
        }
        ContactRow khach = repo.lockContact(tenantId, r.contactId())
                .orElseThrow(() -> new BusinessException(HttpStatus.NOT_FOUND, "CONTACT_NOT_FOUND",
                        "Không tìm thấy khách hàng."));
        if ("ANONYMIZED".equals(khach.status())) {
            throw conflict("CONTACT_ALREADY_ANONYMIZED", "Hồ sơ khách này đã được ẩn danh hoá trước đó.");
        }
        if ("MERGED".equals(khach.status())) {
            throw conflict("CONTACT_MERGED", "Hồ sơ đã được gộp vào hồ sơ khác — tạo yêu cầu cho hồ sơ còn lại.");
        }
        if (repo.hasOpenRequest(tenantId, r.contactId())) {
            throw conflict("ERASURE_ALREADY_OPEN",
                    "Khách này đã có một yêu cầu xoá đang xử lý — không tạo yêu cầu thứ hai.");
        }
        UUID id = repo.insert(tenantId, r.contactId(), nguon, canCu, viet(phamVi(tenantId, r.contactId())),
                EXTERNAL_NOTE);
        audit.recordUserAction(tenantId, actorUserId, "ERASURE_REQUESTED", ENTITY, id,
                Map.of("contactId", r.contactId().toString(), "requestedBy", nguon));
        return chiTiet(require(tenantId, id));
    }

    /** UC041 bước 3–4. Chỉ yêu cầu đang chờ; người xác minh là người đang đăng nhập (từ JWT). */
    @Transactional
    public ErasureRequestDetail verifyIdentity(UUID tenantId, UUID actorUserId, UUID id) {
        scope.apply(tenantId);
        if (!repo.lock(tenantId, id)) {
            throw notFound();
        }
        RequestRow r = require(tenantId, id);
        if (!"PENDING".equals(r.status())) {
            throw conflict("ERASURE_NOT_PENDING", "Chỉ xác minh được yêu cầu đang chờ.");
        }
        if (r.verifiedAt() != null) {
            throw conflict("IDENTITY_ALREADY_VERIFIED", "Danh tính đã được xác minh trước đó.");
        }
        repo.verify(tenantId, id, actorUserId);
        audit.recordUserAction(tenantId, actorUserId, "ERASURE_IDENTITY_VERIFIED", ENTITY, id,
                Map.of("contactId", r.contactId().toString()));
        return chiTiet(require(tenantId, id));
    }

    // ── bước 7–10 ───────────────────────────────────────────────────────────────

    public ErasureRequestDetail execute(UUID tenantId, UUID actorUserId, UUID id) {
        // ── 1. cổng + IN_PROGRESS ────────────────────────────────────────────────
        RequestRow batDau = tx.execute(st -> {
            scope.apply(tenantId);
            if (!repo.lock(tenantId, id)) {
                throw notFound();
            }
            RequestRow r = require(tenantId, id);
            if (!EXECUTABLE.contains(r.status())) {
                throw conflict("ERASURE_NOT_EXECUTABLE", "IN_PROGRESS".equals(r.status())
                        ? "Yêu cầu đang được thực thi."
                        : "Yêu cầu đã hoàn tất — không còn gì để xoá.");
            }
            if (r.verifiedAt() == null) {
                // Luồng phụ 3.1. Bỏ qua phép kiểm này thì ck_erasure_gate vẫn chặn câu UPDATE dưới.
                throw conflict("IDENTITY_NOT_VERIFIED",
                        "Chưa xác minh danh tính chủ thể dữ liệu — không thực thi được yêu cầu xoá.");
            }
            repo.markInProgress(tenantId, id);
            return r;
        });
        UUID khach = batDau.contactId();
        Map<String, ErasureItem> muc = theoKhoa(doc(batDau.itemsJson()));

        // ── 2. phía AI, ngoài transaction ────────────────────────────────────────
        ErasureResult phiaAi = null;
        if (muc.values().stream().anyMatch(m -> laPhiaAi(m) && !"DONE".equals(m.status()))) {
            List<UUID> hoiThoai = tx.execute(st -> {
                scope.apply(tenantId);
                return repo.conversationIds(tenantId, khach);
            });
            phiaAi = goiAi(tenantId, khach, hoiThoai, muc);
        }

        // ── 3. phía CRM + kết luận, một transaction ──────────────────────────────
        ErasureResult ketQuaAi = phiaAi;
        try {
            return tx.execute(st -> {
                scope.apply(tenantId);
                Instant luc = Instant.now();
                lamPhiaCrm(tenantId, khach, muc, luc);
                if (ketQuaAi != null) {
                    traHanMuc(ketQuaAi);
                }
                return ketLuan(tenantId, actorUserId, id, muc, ketQuaAi == null ? null : ketQuaAi.note());
            });
        } catch (RuntimeException ex) {
            // Phần CRM đã rollback trọn — đánh dấu đúng các mục chưa xong là hỏng, phần AI giữ kết quả.
            log.error("UC041 {}: phía CRM hỏng, rollback — {}", id, ex.toString());
            Instant luc = Instant.now();
            muc.replaceAll((k, m) -> !laPhiaAi(m) && !"DONE".equals(m.status())
                    ? m.failed("Lỗi khi cập nhật dữ liệu phía CRM — chưa bảng nào ở phía này bị đổi.", luc) : m);
            return tx.execute(st -> {
                scope.apply(tenantId);
                if (ketQuaAi != null) {
                    traHanMuc(ketQuaAi);
                }
                return ketLuan(tenantId, actorUserId, id, muc, ketQuaAi == null ? null : ketQuaAi.note());
            });
        }
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    /**
     * Danh sách mục theo đúng thứ tự thực thi. Tên bảng phía AI khớp từng chữ với
     * {@code ErasureItem} mà ai-service trả ({@code service.forget_contact}) — kết quả gộp theo khoá
     * {@code schema.bảng}.
     */
    private List<ErasureItem> phamVi(UUID tenantId, UUID k) {
        List<ErasureItem> ds = new ArrayList<>();
        // phía AI — java-core không đếm được (ADR-0002); sales.lead_scores là bảng của mình nên đếm thật
        ds.add(cho("knowledge", "knowledge_documents", "DELETE", null));
        ds.add(cho("knowledge", "knowledge_chunks", "DELETE", null));
        ds.add(cho("ai", "ai_interactions", "DELETE", null));
        ds.add(cho("ai", "ai_feedback", "DELETE", null));
        ds.add(cho("ai", "ai_tool_calls", "DELETE", null));
        ds.add(cho("s3", bucket, "DELETE", null));
        ds.add(cho("sales", "lead_scores", "DELETE", repo.countLeadScores(tenantId, k)));
        // phía CRM
        ds.add(cho("engagement", "contacts", "ANONYMIZE", 1L));
        ds.add(cho("engagement", "channel_identities", "ANONYMIZE", repo.countIdentities(tenantId, k)));
        ds.add(cho("engagement", "messages", "ANONYMIZE", repo.countMessages(tenantId, k)));
        ds.add(cho("engagement", "conversations", "ANONYMIZE", repo.countConversations(tenantId, k)));
        ds.add(cho("engagement", "contact_notes", "DELETE", repo.countNotes(tenantId, k)));
        ds.add(cho("sales", "leads", "ANONYMIZE", repo.countLinkedLeads(tenantId, k)));
        // luồng phụ 5.1 — số đã tổng hợp theo ngày, không quy về cá nhân: giữ nguyên
        ds.add(cho("analytics", "metrics_daily", "KEEP_AGGREGATE", null));
        return ds;
    }

    /** Mục do ai-service thực thi: mọi thứ ngoài schema của Track A, cộng lịch sử điểm lead (gọi ngược). */
    private static boolean laPhiaAi(ErasureItem m) {
        return Set.of("knowledge", "ai", "s3").contains(m.targetSchema())
                || "sales.lead_scores".equals(m.key());
    }

    /**
     * Gọi ai-service rồi GỘP kết quả vào {@code muc}: mục đã {@code DONE} từ lần trước giữ nguyên số dòng
     * (lần gọi lại trả 0 cho phần đã xoá — ghi đè thì biên bản mất số thật). Không gọi được thì mọi mục AI
     * chưa xong ghi {@code FAILED} — không kết luận cả yêu cầu là hoàn tất (luồng phụ 9.1).
     */
    private ErasureResult goiAi(UUID tenantId, UUID khach, List<UUID> hoiThoai, Map<String, ErasureItem> muc) {
        Instant luc = Instant.now();
        List<UUID> gui = hoiThoai == null ? List.of()
                : hoiThoai.subList(Math.max(0, hoiThoai.size() - AiPrivacyClient.TOI_DA_HOI_THOAI), hoiThoai.size());
        try {
            ErasureResult kq = ai.forgetContact(tenantId, khach, gui);
            for (AiPrivacyClient.ErasureItem m : kq.items()) {
                String khoa = m.targetSchema() + "." + m.targetTable();
                ErasureItem cu = muc.get(khoa);
                if (cu != null && "DONE".equals(cu.status())) {
                    continue;
                }
                ErasureItem goc = cu != null ? cu
                        : new ErasureItem(m.targetSchema(), m.targetTable(), m.action(), "PENDING", null, null, null);
                muc.put(khoa, "DONE".equals(m.status())
                        ? goc.done((long) m.affectedRows(), luc)
                        : goc.failed(cauLoi(m.errorCode()), luc));
            }
            return kq;
        } catch (AiServiceException ex) {
            BusinessException dich = AiServiceErrors.dich(ex);
            log.warn("UC041: ai-service không xoá được dữ liệu của khách {} — {} {}", khach, ex.getStatus(),
                    ex.getCode());
            String cau = dich.getCode() + " — " + dich.getMessage();
            muc.replaceAll((k, m) -> laPhiaAi(m) && !"DONE".equals(m.status()) ? m.failed(cau, luc) : m);
            return null;
        } catch (RuntimeException ex) {
            // Phản hồi sai khuôn (lệch hợp đồng) — không biết phía AI đã xoá tới đâu, nên coi như hỏng cả
            // để lần chạy lại gọi lại (endpoint luỹ đẳng). Không để yêu cầu kẹt ở IN_PROGRESS.
            log.error("UC041: phản hồi xoá của ai-service không đọc được — {}", ex.toString());
            String cau = "AI_SERVICE_UNAVAILABLE — phản hồi của dịch vụ AI không đọc được, chạy lại sau.";
            muc.replaceAll((k, m) -> laPhiaAi(m) && !"DONE".equals(m.status()) ? m.failed(cau, luc) : m);
            return null;
        }
    }

    private void lamPhiaCrm(UUID tenantId, UUID k, Map<String, ErasureItem> muc, Instant luc) {
        chay(muc, "engagement.contacts", luc, () -> repo.anonymizeContact(tenantId, k));
        chay(muc, "engagement.channel_identities", luc, () -> repo.anonymizeIdentities(tenantId, k));
        chay(muc, "engagement.messages", luc, () -> repo.redactMessages(tenantId, k));
        chay(muc, "engagement.conversations", luc, () -> repo.clearConversations(tenantId, k));
        chay(muc, "engagement.contact_notes", luc, () -> repo.deleteNotes(tenantId, k));
        chay(muc, "sales.leads", luc, () -> repo.unlinkLeads(tenantId, k));
        // Giữ tổng hợp: không đụng tới, mục đánh dấu xong để tiến độ đủ 100%
        chay(muc, "analytics.metrics_daily", luc, null);
    }

    private static void chay(Map<String, ErasureItem> muc, String khoa, Instant luc,
                             java.util.function.IntSupplier viec) {
        ErasureItem m = muc.get(khoa);
        if (m == null || "DONE".equals(m.status())) {
            return;
        }
        muc.put(khoa, m.done(viec == null ? null : (long) viec.getAsInt(), luc));
    }

    /**
     * Trả hạn mức tồn kho cho tài liệu đã xoá — cùng luật với đường gỡ UC020 (ADR-0023 (f)): con số do
     * ai-service báo, java-core không tự suy. Thứ tự khoá {@code DOCUMENT} → {@code STORAGE_MB} như lúc tải.
     */
    private void traHanMuc(ErasureResult kq) {
        if (kq.releasedDocuments() > 0) {
            quota.release(UsageMetric.DOCUMENT, kq.releasedDocuments());
        }
        if (kq.releasedStorageBytes() > 0) {
            quota.release(UsageMetric.STORAGE_MB, kq.releasedStorageBytes());
        }
    }

    /**
     * Bước 10 — kết luận + biên bản gọn (chốt Q4): biên bản = tiến độ từng bảng + người/lúc xác minh + lúc
     * hoàn tất, ghi trên yêu cầu và trong dòng kiểm toán {@code ERASURE_EXECUTED}. Dòng kiểm toán chỉ có
     * định danh và số đếm — không có tên, số điện thoại hay nội dung nào của khách.
     */
    private ErasureRequestDetail ketLuan(UUID tenantId, UUID actorUserId, UUID id, Map<String, ErasureItem> muc,
                                         String ghiChuAi) {
        List<ErasureItem> ds = List.copyOf(muc.values());
        String trangThai = ds.stream().allMatch(m -> "DONE".equals(m.status())) ? "COMPLETED" : "PARTIALLY_FAILED";
        repo.finish(tenantId, id, trangThai, viet(ds), ghiChuAi);
        RequestRow sau = require(tenantId, id);
        Map<String, Object> bienBan = new LinkedHashMap<>();
        bienBan.put("contactId", sau.contactId().toString());
        bienBan.put("status", trangThai);
        bienBan.put("identityVerifiedBy", sau.verifiedBy() == null ? null : sau.verifiedBy().toString());
        bienBan.put("identityVerifiedAt", sau.verifiedAt() == null ? null : sau.verifiedAt().toString());
        bienBan.put("completedAt", sau.completedAt() == null ? null : sau.completedAt().toString());
        bienBan.put("items", ds.stream().map(m -> {
            Map<String, Object> x = new LinkedHashMap<>();
            x.put("table", m.key());
            x.put("action", m.action());
            x.put("status", m.status());
            x.put("affectedRows", m.affectedRows());
            return x;
        }).toList());
        audit.recordUserAction(tenantId, actorUserId, "ERASURE_EXECUTED", ENTITY, id, bienBan);
        return chiTiet(sau);
    }

    private ErasureItem cho(String schema, String table, String action, Long rows) {
        return new ErasureItem(schema, table, action, "PENDING", rows, null, null);
    }

    private static String cauLoi(String code) {
        if (code == null) {
            return "Không rõ nguyên nhân.";
        }
        return switch (code) {
            case "JAVA_CORE_UNAVAILABLE" -> code + " — ai-service không gọi được java-core để xoá đặc trưng lead.";
            case "STORAGE_UNAVAILABLE" -> code + " — kho tệp không phản hồi, tệp gốc chưa xoá.";
            default -> code;
        };
    }

    private RequestRow require(UUID tenantId, UUID id) {
        return repo.find(tenantId, id).orElseThrow(ErasureService::notFound);
    }

    private ErasureRequestDetail chiTiet(RequestRow r) {
        return new ErasureRequestDetail(r.id(), r.contactId(), r.contactName(), r.requestedBy(), r.legalBasis(),
                r.status(), r.verifiedByName(), r.verifiedAt(), r.requestedAt(), r.completedAt(),
                doc(r.itemsJson()), r.externalNote(), null, r.startedAt());
    }

    private static ErasureRequestDto dong(RequestRow r) {
        return new ErasureRequestDto(r.id(), r.contactId(), r.contactName(), r.requestedBy(), r.legalBasis(),
                r.status(), r.verifiedByName(), r.verifiedAt(), r.requestedAt(), r.completedAt());
    }

    private static Map<String, ErasureItem> theoKhoa(List<ErasureItem> ds) {
        Map<String, ErasureItem> m = new LinkedHashMap<>();
        ds.forEach(x -> m.put(x.key(), x));
        return m;
    }

    private List<ErasureItem> doc(String raw) {
        try {
            return raw == null ? List.of() : json.readValue(raw, ITEMS);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("items của yêu cầu xoá sai khuôn MucXoa", e);
        }
    }

    private String viet(List<ErasureItem> ds) {
        try {
            return json.writeValueAsString(ds);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Không ghi được items của yêu cầu xoá", e);
        }
    }

    private static BusinessException notFound() {
        return new BusinessException(HttpStatus.NOT_FOUND, "ERASURE_REQUEST_NOT_FOUND", "Không tìm thấy yêu cầu xoá.");
    }

    private static BusinessException conflict(String code, String msg) {
        return new BusinessException(HttpStatus.CONFLICT, code, msg);
    }

    private static BusinessException invalid(String code, String msg) {
        return new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, code, msg);
    }
}
