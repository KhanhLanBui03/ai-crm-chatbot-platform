package com.thesis.crm.common.audit;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.common.enums.ActorType;
import com.thesis.crm.common.enums.AuditSeverity;
import com.thesis.crm.platform.entity.AuditLog;
import com.thesis.crm.platform.entity.User;
import com.thesis.crm.platform.repository.AuditLogRepository;
import com.thesis.crm.security.TraceIdFilter;
import jakarta.persistence.EntityManager;
import jakarta.servlet.http.HttpServletRequest;
import java.net.InetAddress;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.slf4j.MDC;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

/**
 * Ghi {@code platform.audit_logs} (V104, V136) qua {@link AuditLogRepository} — bảng chỉ-ghi-thêm:
 * {@code crm_app} có INSERT nhưng bị REVOKE UPDATE/DELETE (V111), Entity {@link AuditLog} là
 * {@code @Immutable}.
 *
 * <p>Gọi TRONG transaction nghiệp vụ, sau {@code TenantTransactionScope.apply()}: thao tác rollback
 * thì dòng kiểm toán rollback theo — không có nhật ký cho việc không xảy ra, và không có việc xảy ra
 * mà thiếu nhật ký.
 *
 * <p>Mọi dòng tự kèm email người làm (chụp lúc ghi), địa chỉ IP, trình duyệt và mã truy vết của request
 * đang chạy — bên gọi không phải truyền.
 *
 * <p><b>Dữ liệu cá nhân</b> (NĐ 13/2023): hai hàm {@code record*Action} KHÔNG được nhận dữ liệu cá nhân — nhật
 * ký sống lâu hơn dữ liệu khách. Thao tác buộc phải lưu giá trị cá nhân để chứng minh (gộp khách, xoá dữ liệu)
 * đi qua {@link #recordWithPersonalData}: phần trước/sau ghi BẢN ĐÃ CHE, bản gốc mã hoá (UC040).
 */
@Component
public class AuditLogWriter {

    private static final TypeReference<Map<String, Object>> MAP = new TypeReference<>() {};

    private final AuditLogRepository repo;
    private final ObjectMapper json;
    private final EntityManager em;
    private final AuditPiiCipher cipher;

    public AuditLogWriter(AuditLogRepository repo, ObjectMapper json, EntityManager em, AuditPiiCipher cipher) {
        this.repo = repo;
        this.json = json;
        this.em = em;
        this.cipher = cipher;
    }

    /** Hành động do người dùng đã đăng nhập thực hiện. */
    public void recordUserAction(
            UUID tenantId, UUID actorUserId, String action, String entityType, UUID entityId,
            Map<String, ?> afterData) {
        requireTransaction();
        requireActor(actorUserId);
        save(new AuditLog(tenantId, ActorType.USER, actorUserId, action, entityType, entityId, AuditSeverity.INFO)
                .withData(null, plain(afterData)));
    }

    /**
     * Sự kiện hệ thống tự ghi nhận, không có người dùng đăng nhập — vd. widget bị nhúng trên tên miền
     * lạ (UC009 10.2). {@code actor_type = 'SYSTEM'} nên không cần {@code actor_user_id}.
     *
     * @param severity {@code INFO | WARNING | CRITICAL}; {@code null} là {@code INFO}
     */
    public void recordSystemAction(
            UUID tenantId, String action, String entityType, UUID entityId, String severity,
            Map<String, ?> afterData) {
        requireTransaction();
        AuditSeverity muc = severity == null ? AuditSeverity.INFO : AuditSeverity.valueOf(severity);
        save(new AuditLog(tenantId, ActorType.SYSTEM, null, action, entityType, entityId, muc)
                .withData(null, plain(afterData)));
    }

    /**
     * Hành động của người dùng mà phần trước/sau buộc phải chứa dữ liệu cá nhân (UC040).
     *
     * <p>{@code before/after} ghi BẢN ĐÃ CHE các trường trong {@code personalKeys}; bản gốc cả hai mã hoá vào
     * {@code pii_encrypted}. Chưa cấu hình khoá hoặc mã hoá lỗi → bỏ hẳn phần trước/sau, vẫn ghi phần còn lại
     * (luồng 2.1) — không bao giờ rơi về lưu bản rõ.
     */
    public void recordWithPersonalData(
            UUID tenantId, UUID actorUserId, String action, String entityType, UUID entityId,
            Map<String, ?> before, Map<String, ?> after, Set<String> personalKeys) {
        requireTransaction();
        requireActor(actorUserId);
        Map<String, Object> b = plain(before);
        Map<String, Object> a = plain(after);
        AuditLog log = new AuditLog(tenantId, ActorType.USER, actorUserId, action, entityType, entityId,
                AuditSeverity.INFO);
        byte[] banMa = maHoa(b, a);
        if (banMa != null) {
            log.withData(PersonalDataMasker.mask(b, personalKeys), PersonalDataMasker.mask(a, personalKeys))
                    .withPersonalData(banMa, cipher.keyId());
        } else {
            log.withPersonalData(null, null);
        }
        save(log);
    }

    /**
     * Ghi lại chính lần "xem đầy đủ" một dòng nhật ký có dữ liệu cá nhân (UC040 bước 7) — ai mở, mở dòng nào,
     * lý do gì. Dòng mới này không chứa dữ liệu cá nhân nào.
     */
    public void recordReveal(UUID tenantId, UUID actorUserId, long revealedLogId, String reason) {
        requireTransaction();
        requireActor(actorUserId);
        save(new AuditLog(tenantId, ActorType.USER, actorUserId, "AUDIT_LOG_REVEALED", "AUDIT_LOG", null,
                AuditSeverity.WARNING)
                .withData(null, Map.of("auditLogId", revealedLogId))
                .withReason(reason));
    }

    /** Bản gốc phần trước/sau của một dòng — chỉ gọi sau khi đã kiểm quyền và đã có lý do. */
    public Map<String, Object> decryptPersonalData(AuditLog log) {
        try {
            return json.readValue(cipher.decrypt(log.getPiiEncrypted(), log.getPiiKeyId()), MAP);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Bản gốc của nhật ký không phải JSON hợp lệ", e);
        }
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    /** Gắn email người làm và ngữ cảnh request rồi lưu. */
    private void save(AuditLog log) {
        if (log.getActorUserId() != null) {
            User u = em.find(User.class, log.getActorUserId());
            log.withActorEmail(u == null ? null : u.getEmail());
        }
        HttpServletRequest req = currentRequest();
        if (req != null) {
            log.withRequest(ip(req), req.getHeader("User-Agent"), MDC.get(TraceIdFilter.MDC_KEY));
        }
        repo.save(log);
    }

    private byte[] maHoa(Map<String, Object> before, Map<String, Object> after) {
        Map<String, Object> goc = new LinkedHashMap<>();
        goc.put("before", before);
        goc.put("after", after);
        try {
            return cipher.encrypt(json.writeValueAsString(goc)).orElse(null);
        } catch (JsonProcessingException e) {
            return null;
        }
    }

    private static HttpServletRequest currentRequest() {
        return RequestContextHolder.getRequestAttributes() instanceof ServletRequestAttributes a
                ? a.getRequest() : null;
    }

    /** Địa chỉ khách thật: phần tử đầu của {@code X-Forwarded-For} do gateway gắn, không có thì địa chỉ kết nối. */
    private static InetAddress ip(HttpServletRequest req) {
        String xff = req.getHeader("X-Forwarded-For");
        String s = xff != null && !xff.isBlank() ? xff.split(",")[0].trim() : req.getRemoteAddr();
        // Chỉ nhận chuỗi IP thuần — getByName với tên miền sẽ đi phân giải DNS
        if (s == null || !s.matches("[0-9a-fA-F:.]+")) {
            return null;
        }
        try {
            return InetAddress.getByName(s);
        } catch (Exception e) {
            return null;
        }
    }

    private static void requireTransaction() {
        if (!TransactionSynchronizationManager.isActualTransactionActive()) {
            throw new IllegalStateException("AuditLogWriter phải gọi bên trong @Transactional.");
        }
    }

    private static void requireActor(UUID actorUserId) {
        if (actorUserId == null) {
            throw new IllegalStateException("Hành động của người dùng phải biết người dùng là ai (ck_audit_actor).");
        }
    }

    /**
     * Chuyển qua {@link ObjectMapper} của Spring trước khi giao cho Hibernate: giá trị thành chuỗi/số/bool thuần,
     * ngày giờ dạng ISO — dạng JSON giống hệt bản ghi cũ. Giữ nguyên giá trị {@code null}.
     */
    private Map<String, Object> plain(Map<String, ?> data) {
        return data == null ? null : json.convertValue(data, MAP);
    }
}
