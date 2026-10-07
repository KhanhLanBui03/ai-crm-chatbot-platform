package com.thesis.crm.sales.activity;

import com.fasterxml.jackson.databind.JsonNode;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.sales.activity.ActivityDtos.ActivityDto;
import com.thesis.crm.sales.activity.ActivityDtos.CreateActivityRequest;
import com.thesis.crm.sales.activity.ActivityDtos.TodoCount;
import com.thesis.crm.sales.activity.ActivityRepository.Filter;
import com.thesis.crm.sales.activity.ActivityRepository.NewActivity;
import com.thesis.crm.sales.activity.ActivityRepository.Owner;
import com.thesis.crm.sales.lead.LeadRepository;
import com.thesis.crm.sales.lead.LeadRepository.ContactRef;
import com.thesis.crm.sales.lead.LeadService.Actor;
import com.thesis.crm.security.TenantTransactionScope;
import java.time.Duration;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC035 — Hoạt động chăm sóc khách và nhắc việc.
 *
 * <p>Luật đã chốt với người dùng:
 * <ul>
 *   <li>Gắn với khách (bắt buộc) và TỐI ĐA một lead hoặc deal của chính khách đó (V134).
 *   <li>Mọi người ghi được lên mọi khách/lead/deal — ghi hoạt động là góp lịch sử, không phải sửa
 *       lead/deal (giống ghi chú UC017). Lead/deal đã đóng vẫn ghi được (chăm sóc sau bán).
 *   <li><b>Không xoá</b> — hoạt động là lịch sử. Người ghi hoặc quản trị cập nhật kết quả/nội dung/nhắc
 *       việc; người được nhắc chỉ đánh dấu nhắc Xong/Huỷ. Dòng AUTO không ai sửa.
 *   <li>Nhắc việc: giờ nhắc phải ở tương lai; "Hẹn lại" bắt buộc có giờ nhắc; mặc định nhắc chính người
 *       ghi, quản trị chọn được người khác.
 *   <li><b>AUTO</b>: đúng một dòng khi nhân viên NHẬN hội thoại từ AI — luật cố định, không gọi LLM.
 * </ul>
 */
@Service
public class ActivityService {

    static final Set<String> TYPES = Set.of("CALL", "MEETING", "QUOTE", "EMAIL", "NOTE");
    static final Set<String> OUTCOMES = Set.of("DONE", "NO_ANSWER", "REFUSED", "NOT_INTERESTED", "RESCHEDULED");
    static final Set<String> REMIND_STATUSES = Set.of("NONE", "PENDING", "SENT", "DONE", "CANCELED");
    static final Set<String> BUCKETS = Set.of("OVERDUE", "TODAY", "UPCOMING");
    static final int MAX_SUBJECT = 200;
    static final int MAX_CONTENT = 5000;
    /** Đồng hồ máy người dùng lệch vài phút là chuyện thường — không coi là "ghi việc ở tương lai". */
    private static final Duration LECH_GIO = Duration.ofMinutes(5);
    static final Map<String, String> LY_DO_CHUYEN_GIAO = Map.of(
            "CUSTOMER_REQUEST", "khách xin gặp nhân viên",
            "LOW_CONFIDENCE", "AI không chắc câu trả lời",
            "NO_GROUNDING", "không tìm thấy thông tin trong tài liệu",
            "NEGATIVE_SENTIMENT", "khách không hài lòng",
            "REPEATED_FAILURE", "AI trả lời không đạt nhiều lần",
            "WRITE_TOOL_APPROVAL", "cần nhân viên duyệt thao tác",
            "QUOTA_EXCEEDED", "hết hạn mức hội thoại AI",
            "LLM_ERROR", "AI tạm thời gặp lỗi");

    private final ActivityRepository repo;
    private final LeadRepository leads;
    private final TenantTransactionScope scope;

    public ActivityService(ActivityRepository repo, LeadRepository leads, TenantTransactionScope scope) {
        this.repo = repo;
        this.leads = leads;
        this.scope = scope;
    }

    // ── đọc ─────────────────────────────────────────────────────────────────────

    @Transactional(readOnly = true)
    public PageResponse<ActivityDto> list(UUID tenantId, Actor actor, UUID contactId, UUID leadId, UUID dealId,
                                          String type, String remindStatus, boolean mine, String bucket,
                                          int page, int size) {
        scope.apply(tenantId);
        if (type != null && !TYPES.contains(type)) {
            throw invalid("INVALID_TYPE", "Loại hoạt động không hợp lệ.");
        }
        if (remindStatus != null && !REMIND_STATUSES.contains(remindStatus)) {
            throw invalid("INVALID_REMIND_STATUS", "Trạng thái nhắc việc không hợp lệ.");
        }
        if (bucket != null && (!mine || !BUCKETS.contains(bucket))) {
            throw invalid("INVALID_BUCKET", "bucket chỉ dùng với mine=true và nhận OVERDUE, TODAY, UPCOMING.");
        }
        int p = Math.max(0, page);
        int s = Math.min(Math.max(1, size), 100);
        Filter f = new Filter(contactId, leadId, dealId, type, remindStatus, mine ? actor.userId() : null, bucket, p, s);
        return PageResponse.of(repo.search(tenantId, f), p, s, repo.count(tenantId, f));
    }

    @Transactional(readOnly = true)
    public TodoCount todoCount(UUID tenantId, Actor actor) {
        scope.apply(tenantId);
        return repo.todoCount(tenantId, actor.userId());
    }

    /** Hoạt động mới nhất của một deal — cho {@code DealChiTiet.activities}. Gọi trong transaction có sẵn. */
    @Transactional(propagation = Propagation.MANDATORY, readOnly = true)
    public List<ActivityDto> ofDeal(UUID tenantId, UUID dealId, int limit) {
        return repo.search(tenantId, new Filter(null, null, dealId, null, null, null, null, 0, limit));
    }

    // ── ghi thủ công ────────────────────────────────────────────────────────────

    @Transactional
    public ActivityDto create(UUID tenantId, Actor actor, CreateActivityRequest r) {
        scope.apply(tenantId);
        if (r == null || r.contactId() == null) {
            throw invalid("CONTACT_REQUIRED", "Chọn khách hàng.");
        }
        ContactRef c = leads.findContact(tenantId, r.contactId())
                .orElseThrow(() -> new BusinessException(HttpStatus.NOT_FOUND, "CONTACT_NOT_FOUND",
                        "Không tìm thấy khách hàng."));
        if (c.deleted() || !"ACTIVE".equals(c.status())) {
            throw invalid("CONTACT_INACTIVE", "Khách hàng đã bị gộp, ẩn danh hoặc xoá.");
        }
        if (r.leadId() != null && r.dealId() != null) {
            throw invalid("ONE_TARGET", "Hoạt động gắn với một lead HOẶC một deal, không cả hai.");
        }
        if (r.leadId() != null && !Objects.equals(repo.contactOfLead(tenantId, r.leadId()).orElse(null), r.contactId())) {
            throw invalid("LEAD_CONTACT_MISMATCH", "Lead không thuộc khách hàng này.");
        }
        if (r.dealId() != null && !Objects.equals(repo.contactOfDeal(tenantId, r.dealId()).orElse(null), r.contactId())) {
            throw invalid("DEAL_CONTACT_MISMATCH", "Deal không thuộc khách hàng này.");
        }
        if (r.type() == null || !TYPES.contains(r.type())) {
            throw invalid("INVALID_TYPE", "Chọn loại hoạt động: gọi điện, gặp mặt, báo giá, email hoặc ghi chú.");
        }
        String subject = text(r.subject(), MAX_SUBJECT, "Tiêu đề");
        String content = text(r.content(), MAX_CONTENT, "Nội dung");
        if (subject == null && content == null) {
            throw invalid("CONTENT_REQUIRED", "Nhập tiêu đề hoặc nội dung hoạt động.");
        }
        if (r.outcome() != null && !OUTCOMES.contains(r.outcome())) {
            throw invalid("INVALID_OUTCOME", "Kết quả hoạt động không hợp lệ.");
        }
        Instant now = Instant.now();
        if (r.performedAt() != null && r.performedAt().isAfter(now.plus(LECH_GIO))) {
            throw invalid("PERFORMED_IN_FUTURE", "Thời điểm thực hiện không được ở tương lai — dùng nhắc việc để hẹn.");
        }
        UUID remindUser = checkRemind(tenantId, actor, r.remindAt(), r.remindUserId(), now);
        if ("RESCHEDULED".equals(r.outcome()) && r.remindAt() == null) {
            throw invalid("REMIND_REQUIRED", "Kết quả \"Hẹn lại\" cần đặt giờ nhắc.");
        }
        UUID id = repo.insert(tenantId, new NewActivity(r.contactId(), r.leadId(), r.dealId(), null, r.type(), subject,
                content, r.outcome(), "MANUAL", actor.userId(), r.performedAt(), r.remindAt(), remindUser));
        return repo.find(tenantId, id).orElseThrow();
    }

    /**
     * PATCH: {@code outcome}, {@code content}, {@code remindStatus}, {@code remindAt} (hẹn lại giờ nhắc).
     * Nhận JsonNode để phân biệt "không gửi" với "gửi null".
     */
    @Transactional
    public ActivityDto update(UUID tenantId, Actor actor, UUID id, JsonNode body) {
        scope.apply(tenantId);
        if (body == null || !body.isObject()) {
            throw invalid("INVALID_BODY", "Dữ liệu cập nhật phải là một đối tượng JSON.");
        }
        Owner o = repo.lock(tenantId, id).orElseThrow(ActivityService::notFound);
        ActivityDto cur = repo.find(tenantId, id).orElseThrow(ActivityService::notFound);
        if ("AUTO".equals(o.source())) {
            throw forbidden("Hoạt động do hệ thống ghi — không sửa được.");
        }
        boolean author = actor.admin() || actor.userId().equals(o.performedBy());
        boolean reminded = actor.userId().equals(o.remindUserId());
        boolean chiDoiNhac = !body.has("outcome") && !body.has("content") && !body.has("remindAt");
        if (!author && !(reminded && chiDoiNhac)) {
            throw forbidden("Chỉ người ghi hoạt động hoặc quản trị viên được sửa.");
        }

        String outcome = body.has("outcome") ? str(body, "outcome") : cur.outcome();
        if (outcome != null && !OUTCOMES.contains(outcome)) {
            throw invalid("INVALID_OUTCOME", "Kết quả hoạt động không hợp lệ.");
        }
        String content = body.has("content") ? text(str(body, "content"), MAX_CONTENT, "Nội dung") : cur.content();

        Instant remindAt = o.remindAt();
        UUID remindUser = o.remindUserId();
        String status = o.remindStatus();
        if (body.has("remindAt")) {
            Instant moi = instant(body, "remindAt");
            if (moi == null) {
                throw invalid("INVALID_REMIND", "Muốn bỏ nhắc việc thì đánh dấu Huỷ.");
            }
            remindUser = checkRemind(tenantId, actor, moi, remindUser, Instant.now());
            remindAt = moi;
            status = "PENDING";                       // hẹn lại = lời nhắc mới, chưa làm
        }
        if (body.has("remindStatus")) {
            String rs = str(body, "remindStatus");
            if (!"DONE".equals(rs) && !"CANCELED".equals(rs) && !"PENDING".equals(rs)) {
                throw invalid("INVALID_REMIND_STATUS", "Nhắc việc chỉ đánh dấu được Xong, Huỷ hoặc mở lại.");
            }
            if ("NONE".equals(o.remindStatus()) && !body.has("remindAt")) {
                throw invalid("NO_REMIND", "Hoạt động này không có nhắc việc.");
            }
            if ("PENDING".equals(rs) && remindAt != null && remindAt.isBefore(Instant.now()) && !body.has("remindAt")) {
                throw invalid("REMIND_IN_PAST", "Mở lại nhắc việc thì đặt giờ nhắc mới ở tương lai.");
            }
            status = rs;
        }
        if ("RESCHEDULED".equals(outcome) && "NONE".equals(status)) {
            throw invalid("REMIND_REQUIRED", "Kết quả \"Hẹn lại\" cần đặt giờ nhắc.");
        }
        repo.update(tenantId, id, outcome, content, remindAt, remindUser, status);
        return repo.find(tenantId, id).orElseThrow();
    }

    // ── ghi tự động (AUTO) ──────────────────────────────────────────────────────

    /**
     * Nhân viên vừa nhận một hội thoại AI chuyển sang — ghi đúng một dòng "Tiếp nhận hội thoại từ AI".
     * Gắn vào deal mở mới nhất của khách, không có thì lead mở, không có nữa thì chỉ hồ sơ khách.
     * Hội thoại chưa gắn khách (không xảy ra với widget, phòng hờ kênh khác) thì bỏ qua.
     *
     * <p>Gọi trong transaction của thao tác nhận/giao — nhận thất bại thì không có dòng hoạt động nào.
     */
    @Transactional(propagation = Propagation.MANDATORY)
    public Optional<UUID> recordHandoffAccepted(UUID tenantId, UUID conversationId, UUID userId, String reason) {
        Optional<UUID> contact = repo.contactOfConversation(tenantId, conversationId);
        if (contact.isEmpty()) {
            return Optional.empty();
        }
        UUID contactId = contact.get();
        Optional<UUID> deal = repo.latestOpenDeal(tenantId, contactId);
        UUID leadId = deal.isPresent() ? null : repo.openLead(tenantId, contactId).orElse(null);
        String lyDo = LY_DO_CHUYEN_GIAO.getOrDefault(reason, "AI chuyển cho nhân viên");
        return Optional.of(repo.insert(tenantId, new NewActivity(contactId, leadId, deal.orElse(null), conversationId,
                "NOTE", "Tiếp nhận hội thoại từ AI", "Lý do chuyển giao: " + lyDo + ".", null, "AUTO", userId,
                null, null, null)));
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    /** Kiểm giờ nhắc + người được nhắc; trả người được nhắc thực tế (mặc định chính người ghi). */
    private UUID checkRemind(UUID tenantId, Actor actor, Instant remindAt, UUID remindUserId, Instant now) {
        if (remindAt == null) {
            if (remindUserId != null) {
                throw invalid("REMIND_AT_REQUIRED", "Chọn giờ nhắc.");
            }
            return null;
        }
        if (!remindAt.isAfter(now)) {
            throw invalid("REMIND_IN_PAST", "Giờ nhắc phải ở tương lai.");
        }
        UUID target = remindUserId == null ? actor.userId() : remindUserId;
        if (!target.equals(actor.userId()) && !actor.admin()) {
            throw forbidden("Chỉ quản trị viên được giao nhắc việc cho người khác.");
        }
        if (leads.activeUserName(tenantId, target).isEmpty()) {
            throw invalid("REMIND_USER_INVALID", "Người được nhắc không tồn tại hoặc đã ngừng hoạt động.");
        }
        return target;
    }

    private static String text(String raw, int max, String label) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        String s = raw.strip();
        if (s.codePointCount(0, s.length()) > max) {
            throw invalid("TEXT_TOO_LONG", label + " tối đa " + max + " ký tự.");
        }
        return s;
    }

    private static String str(JsonNode body, String field) {
        JsonNode n = body.get(field);
        if (n == null || n.isNull()) {
            return null;
        }
        if (!n.isTextual()) {
            throw invalid("INVALID_FIELD", "Trường '" + field + "' phải là chuỗi.");
        }
        return n.asText();
    }

    private static Instant instant(JsonNode body, String field) {
        String s = str(body, field);
        try {
            return s == null ? null : Instant.parse(s);
        } catch (DateTimeParseException e) {
            throw invalid("INVALID_FIELD", "Trường '" + field + "' phải là thời điểm ISO-8601.");
        }
    }

    private static BusinessException notFound() {
        return new BusinessException(HttpStatus.NOT_FOUND, "ACTIVITY_NOT_FOUND", "Không tìm thấy hoạt động.");
    }

    private static BusinessException forbidden(String msg) {
        return new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN", msg);
    }

    private static BusinessException invalid(String code, String msg) {
        return new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, code, msg);
    }
}
