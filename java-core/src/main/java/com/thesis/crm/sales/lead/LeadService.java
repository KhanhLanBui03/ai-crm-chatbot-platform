package com.thesis.crm.sales.lead;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.engagement.util.ContactNormalizer;
import com.thesis.crm.sales.deal.DealDtos.ConvertRequest;
import com.thesis.crm.sales.deal.DealDtos.ConvertResult;
import com.thesis.crm.sales.deal.DealDtos.DealDto;
import com.thesis.crm.sales.deal.DealService;
import com.thesis.crm.sales.lead.LeadDtos.CreateLeadRequest;
import com.thesis.crm.sales.lead.LeadDtos.LeadDetail;
import com.thesis.crm.sales.lead.LeadDtos.LeadDto;
import com.thesis.crm.sales.lead.LeadDtos.OpenLeadConflict;
import com.thesis.crm.sales.lead.LeadDtos.ScoreDto;
import com.thesis.crm.sales.lead.LeadDtos.TransitionError;
import com.thesis.crm.sales.lead.LeadRepository.ContactRef;
import com.thesis.crm.sales.lead.LeadRepository.Filter;
import com.thesis.crm.sales.lead.LeadRepository.LeadRow;
import com.thesis.crm.sales.lead.LeadRepository.ScoreRow;
import com.thesis.crm.security.TenantTransactionScope;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC032 — Quản lý Lead.
 *
 * <p>Quy tắc đã chốt với người dùng:
 * <ul>
 *   <li><b>Quy trình đi tới, được bỏ bước:</b> Mới → Đã liên hệ → Đủ tiềm năng, không lùi. Loại được từ
 *       mọi trạng thái mở (bắt buộc lý do — đây là nhãn học của mô hình chấm điểm UC030). Lead đã loại
 *       chỉ mở lại về Mới. "Đã chuyển Deal" chỉ đặt qua thao tác chuyển đổi của UC033 và khoá luôn.
 *   <li><b>Quyền:</b> mọi người XEM mọi lead. Nhân viên sửa lead của mình hoặc lead chưa ai nhận (sửa lead
 *       chưa ai nhận = tự nhận). Chỉ quản trị viên giao lead cho người khác.
 *   <li><b>Một khách một lead mở</b> — chặn ở CSDL (V132), ở đây chỉ để trả lời dễ hiểu.
 *   <li><b>Không phát sự kiện phễu:</b> UC037 đếm thẳng từ {@code sales.leads}/{@code sales.deals}
 *       (giảm độ sâu bước 9, ghi trong báo cáo).
 * </ul>
 */
@Service
public class LeadService {

    /** Người đang thao tác — lấy từ JWT ở controller. */
    public record Actor(UUID userId, boolean admin) {}

    static final Set<String> OPEN = Set.of("NEW", "CONTACTED", "QUALIFIED");
    static final Set<String> STATUSES = Set.of("NEW", "CONTACTED", "QUALIFIED", "CONVERTED", "DISQUALIFIED");
    static final Set<String> LEVELS = Set.of("LOW", "MEDIUM", "HIGH");
    /** Lý do loại — danh sách cố định để làm được nhãn học máy, không phải chữ tự do. */
    static final List<String> DISQUALIFY_REASONS =
            List.of("NO_BUDGET", "NO_NEED", "BOUGHT_ELSEWHERE", "UNREACHABLE", "SPAM", "OTHER");
    /** Trạng thái được đi tiếp. CONVERTED không có ở đây: chỉ UC033 đặt, qua endpoint riêng. */
    static final Map<String, List<String>> NEXT = Map.of(
            "NEW", List.of("CONTACTED", "QUALIFIED", "DISQUALIFIED"),
            "CONTACTED", List.of("QUALIFIED", "DISQUALIFIED"),
            "QUALIFIED", List.of("DISQUALIFIED"),
            "DISQUALIFIED", List.of("NEW"),
            "CONVERTED", List.of());
    private static final Map<String, String> LABEL = Map.of(
            "NEW", "Mới", "CONTACTED", "Đã liên hệ", "QUALIFIED", "Đủ tiềm năng",
            "CONVERTED", "Đã chuyển Deal", "DISQUALIFIED", "Đã loại");
    static final int MAX_PRODUCT = 200;
    private static final BigDecimal MAX_MONEY = new BigDecimal("9999999999999999.99");   // numeric(18,2)
    private static final int SCORE_HISTORY = 50;

    private final LeadRepository repo;
    private final TenantTransactionScope scope;
    private final AuditLogWriter audit;
    private final ObjectMapper json;
    private final JdbcTemplate jdbc;
    private final DealService deals;

    public LeadService(LeadRepository repo, TenantTransactionScope scope, AuditLogWriter audit, ObjectMapper json,
                       JdbcTemplate jdbc, DealService deals) {
        this.repo = repo;
        this.scope = scope;
        this.audit = audit;
        this.json = json;
        this.jdbc = jdbc;
        this.deals = deals;
    }

    // ── đọc ─────────────────────────────────────────────────────────────────────

    @Transactional(readOnly = true)
    public PageResponse<LeadDto> list(UUID tenantId, String q, String status, String source, UUID ownerUserId,
                                      Integer minScore, UUID contactId, int page, int size) {
        scope.apply(tenantId);
        if (status != null && !STATUSES.contains(status)) {
            throw invalid("INVALID_STATUS", "Trạng thái lead không hợp lệ.");
        }
        if (source != null && !Set.of("AI_AUTO", "MANUAL").contains(source)) {
            throw invalid("INVALID_SOURCE", "Nguồn lead chỉ nhận AI_AUTO hoặc MANUAL.");
        }
        if (minScore != null && (minScore < 0 || minScore > 100)) {
            throw invalid("INVALID_SCORE", "Điểm tối thiểu phải từ 0 đến 100.");
        }
        int p = Math.max(0, page);
        int s = Math.min(Math.max(1, size), 100);
        Filter f = new Filter(ContactNormalizer.searchTokens(q), status, source, ownerUserId, minScore, contactId, p, s);
        return PageResponse.of(repo.search(tenantId, f).stream().map(LeadService::toDto).toList(), p, s,
                repo.count(tenantId, f));
    }

    @Transactional(readOnly = true)
    public LeadDetail detail(UUID tenantId, UUID leadId) {
        scope.apply(tenantId);
        return detailOf(tenantId, require(tenantId, leadId));
    }

    @Transactional(readOnly = true)
    public List<ScoreDto> scores(UUID tenantId, UUID leadId) {
        scope.apply(tenantId);
        require(tenantId, leadId);
        return repo.scores(tenantId, leadId, SCORE_HISTORY).stream().map(this::toScore).toList();
    }

    // ── tạo thủ công (UC032 luồng 1a–2a) ────────────────────────────────────────

    @Transactional
    public LeadDto create(UUID tenantId, Actor actor, CreateLeadRequest r) {
        scope.apply(tenantId);
        if (r == null || r.contactId() == null) {
            throw invalid("CONTACT_REQUIRED", "Chọn khách hàng cho lead.");
        }
        ContactRef contact = repo.findContact(tenantId, r.contactId())
                .orElseThrow(() -> new BusinessException(HttpStatus.NOT_FOUND, "CONTACT_NOT_FOUND",
                        "Không tìm thấy khách hàng."));
        if (contact.deleted() || !"ACTIVE".equals(contact.status())) {
            throw invalid("CONTACT_INACTIVE", "Khách hàng đã bị gộp, ẩn danh hoặc xoá — không tạo lead được.");
        }
        if (r.sourceConversationId() != null) {
            // Gắn hội thoại của khách KHÁC vào lead là ghi sai nguồn — truy ngược doanh thu về sai cuộc trò chuyện
            Optional<UUID> convContact = repo.conversationContact(tenantId, r.sourceConversationId())
                    .orElseThrow(() -> new BusinessException(HttpStatus.NOT_FOUND, "CONVERSATION_NOT_FOUND",
                            "Không tìm thấy hội thoại nguồn."));
            if (convContact.isEmpty() || !convContact.get().equals(r.contactId())) {
                throw invalid("CONVERSATION_CONTACT_MISMATCH", "Hội thoại nguồn không thuộc khách hàng này.");
            }
        }
        String product = product(r.interestedProduct());
        checkBudget(r.budgetMin(), r.budgetMax());
        checkLevel(r.urgency());

        UUID owner = r.ownerUserId() == null ? actor.userId() : r.ownerUserId();
        if (!owner.equals(actor.userId()) && !actor.admin()) {
            throw forbidden("Chỉ quản trị viên được giao lead cho người khác.");
        }
        requireActiveUser(tenantId, owner);

        lockContact(tenantId, r.contactId());
        rejectIfOpenLead(tenantId, r.contactId());
        CreateLeadRequest clean = new CreateLeadRequest(r.contactId(), r.sourceConversationId(), product,
                r.budgetMin(), r.budgetMax(), r.urgency(), owner);
        UUID id = repo.insert(tenantId, clean, owner);

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("source", "MANUAL");
        data.put("via", r.sourceConversationId() != null ? "INBOX" : "LEADS_PAGE");
        data.put("ownerUserId", owner.toString());
        audit.recordUserAction(tenantId, actor.userId(), "LEAD_CREATED", "LEAD", id, data);
        return toDto(require(tenantId, id));
    }

    // ── sửa và đổi trạng thái (UC032 bước 7–9, luồng 7.x, 8.x) ──────────────────

    /**
     * PATCH nhận {@link JsonNode} để phân biệt "không gửi trường" (giữ nguyên) với "gửi null" (xoá giá
     * trị) — record Java gộp hai trường hợp làm một.
     */
    @Transactional
    public LeadDetail update(UUID tenantId, Actor actor, UUID leadId, JsonNode body) {
        scope.apply(tenantId);
        if (body == null || !body.isObject()) {
            throw invalid("INVALID_BODY", "Dữ liệu cập nhật phải là một đối tượng JSON.");
        }
        if (!repo.lock(tenantId, leadId)) {
            throw notFound();
        }
        LeadRow cur = require(tenantId, leadId);
        if ("CONVERTED".equals(cur.status())) {
            throw new BusinessException(HttpStatus.CONFLICT, "LEAD_CONVERTED",
                    "Lead đã chuyển thành Deal — sửa tiếp trên Deal.");
        }
        boolean holder = actor.userId().equals(cur.ownerUserId());
        if (!actor.admin() && !holder && cur.ownerUserId() != null) {
            throw forbidden("Lead đang do " + nameOr(cur.ownerName()) + " phụ trách.");
        }

        // 1. Trạng thái
        String status = cur.status();
        if (body.has("status")) {
            status = text(body, "status");
            if (status == null || !STATUSES.contains(status)) {
                throw invalid("INVALID_STATUS", "Trạng thái lead không hợp lệ.");
            }
        }
        if (!status.equals(cur.status())) {
            if ("CONVERTED".equals(status)) {
                throw invalid("CONVERT_VIA_DEAL", "Dùng thao tác \"Chuyển thành Deal\" để chuyển lead sang Deal.");
            }
            List<String> allowed = NEXT.get(cur.status());
            if (!allowed.contains(status)) {
                throw new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "INVALID_TRANSITION",
                        "Không thể chuyển từ \"" + LABEL.get(cur.status()) + "\" sang \"" + LABEL.get(status)
                                + "\". Được phép: " + labels(allowed) + ".",
                        new TransitionError(cur.status(), status, allowed));
            }
        }

        // 2. Thông tin — lead đã loại phải mở lại rồi mới sửa (tránh sửa âm thầm một lead đã đóng)
        String product = body.has("interestedProduct") ? product(text(body, "interestedProduct"))
                : cur.interestedProduct();
        BigDecimal budgetMin = body.has("budgetMin") ? money(body, "budgetMin") : cur.budgetMin();
        BigDecimal budgetMax = body.has("budgetMax") ? money(body, "budgetMax") : cur.budgetMax();
        String urgency = body.has("urgency") ? text(body, "urgency") : cur.urgency();
        checkBudget(budgetMin, budgetMax);
        checkLevel(urgency);
        List<String> changedFields = new ArrayList<>();
        if (!Objects.equals(product, cur.interestedProduct())) {
            changedFields.add("interestedProduct");
        }
        if (!sameMoney(budgetMin, cur.budgetMin())) {
            changedFields.add("budgetMin");
        }
        if (!sameMoney(budgetMax, cur.budgetMax())) {
            changedFields.add("budgetMax");
        }
        if (!Objects.equals(urgency, cur.urgency())) {
            changedFields.add("urgency");
        }
        if (!changedFields.isEmpty() && "DISQUALIFIED".equals(cur.status()) && "DISQUALIFIED".equals(status)) {
            throw new BusinessException(HttpStatus.CONFLICT, "LEAD_DISQUALIFIED",
                    "Lead đã bị loại — mở lại lead trước khi sửa thông tin.");
        }

        // 3. Lý do loại — bắt buộc khi loại, xoá khi mở lại (UC032 luồng 7.1–7.2)
        String reason;
        if ("DISQUALIFIED".equals(status)) {
            reason = body.has("disqualifyReason") ? text(body, "disqualifyReason")
                    : "DISQUALIFIED".equals(cur.status()) ? cur.disqualifiedReason() : null;
            boolean keepOld = !body.has("disqualifyReason") && "DISQUALIFIED".equals(cur.status());
            if (!keepOld && (reason == null || !DISQUALIFY_REASONS.contains(reason))) {
                throw new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "DISQUALIFY_REASON_REQUIRED",
                        "Chọn lý do loại lead.", Map.of("reasons", DISQUALIFY_REASONS));
            }
        } else {
            if (body.hasNonNull("disqualifyReason")) {
                throw invalid("REASON_ONLY_WHEN_DISQUALIFY", "Lý do loại chỉ dùng khi chuyển lead sang \"Đã loại\".");
            }
            reason = null;
        }

        // 4. Người phụ trách
        UUID owner = cur.ownerUserId();
        String ownerVia = null;
        if (body.has("ownerUserId")) {
            UUID target = uuid(body, "ownerUserId");
            if (!Objects.equals(target, cur.ownerUserId())) {
                if (!actor.admin() && !actor.userId().equals(target)) {
                    throw forbidden("Chỉ quản trị viên được giao hoặc gỡ người phụ trách lead.");
                }
                if (target != null) {
                    requireActiveUser(tenantId, target);
                }
                owner = target;
                ownerVia = actor.admin() ? "ADMIN" : "CLAIM";
            }
        }
        boolean anyChange = !status.equals(cur.status()) || !changedFields.isEmpty()
                || !Objects.equals(reason, cur.disqualifiedReason()) || !Objects.equals(owner, cur.ownerUserId());
        if (!anyChange) {
            return detailOf(tenantId, cur);
        }
        if (!actor.admin() && cur.ownerUserId() == null && owner == null) {
            owner = actor.userId();                       // sửa lead chưa ai nhận = tự nhận
            ownerVia = "CLAIM";
        }

        // 5. Mở lại lead đã loại phải giữ luật một khách một lead mở
        if (OPEN.contains(status) && !OPEN.contains(cur.status())) {
            lockContact(tenantId, cur.contactId());
            rejectIfOpenLead(tenantId, cur.contactId());
        }

        repo.update(tenantId, leadId, status, product, budgetMin, budgetMax, urgency, owner, reason);

        if (!status.equals(cur.status())) {
            Map<String, Object> d = new LinkedHashMap<>();
            d.put("from", cur.status());
            d.put("to", status);
            if (reason != null) {
                d.put("reason", reason);
            }
            audit.recordUserAction(tenantId, actor.userId(), "LEAD_STATUS_CHANGED", "LEAD", leadId, d);
        } else if ("DISQUALIFIED".equals(status) && !Objects.equals(reason, cur.disqualifiedReason())) {
            audit.recordUserAction(tenantId, actor.userId(), "LEAD_STATUS_CHANGED", "LEAD", leadId,
                    Map.of("from", status, "to", status, "reason", reason));
        }
        if (!Objects.equals(owner, cur.ownerUserId())) {
            Map<String, Object> d = new LinkedHashMap<>();
            d.put("fromUserId", cur.ownerUserId() == null ? null : cur.ownerUserId().toString());
            d.put("toUserId", owner == null ? null : owner.toString());
            d.put("via", ownerVia);
            audit.recordUserAction(tenantId, actor.userId(), "LEAD_ASSIGNED", "LEAD", leadId, d);
        }
        if (!changedFields.isEmpty()) {
            // Chỉ ghi TÊN trường đã đổi, không chép giá trị — sản phẩm/ngân sách là thông tin khách hàng
            audit.recordUserAction(tenantId, actor.userId(), "LEAD_UPDATED", "LEAD", leadId,
                    Map.of("fields", changedFields));
        }
        return detailOf(tenantId, require(tenantId, leadId));
    }

    // ── chuyển thành deal (UC033) ───────────────────────────────────────────────

    /**
     * Một transaction: tạo deal + ghi lịch sử giai đoạn đầu + đóng lead. Deal vào giai đoạn mở đầu tiên
     * của phễu mặc định nếu không chỉ định; người phụ trách = người phụ trách lead (chưa ai thì người bấm).
     * Khách đã có deal mở thì VẪN tạo, chỉ cảnh báo — một khách mua nhiều lần là bình thường.
     */
    @Transactional
    public ConvertResult convert(UUID tenantId, Actor actor, UUID leadId, ConvertRequest r) {
        scope.apply(tenantId);
        if (!repo.lock(tenantId, leadId)) {
            throw notFound();
        }
        LeadRow cur = require(tenantId, leadId);
        if ("CONVERTED".equals(cur.status())) {
            throw new BusinessException(HttpStatus.CONFLICT, "LEAD_ALREADY_CONVERTED",
                    "Lead đã được chuyển thành Deal.");
        }
        if ("DISQUALIFIED".equals(cur.status())) {
            throw new BusinessException(HttpStatus.CONFLICT, "LEAD_DISQUALIFIED",
                    "Lead đã bị loại — mở lại lead trước khi chuyển thành Deal.");
        }
        if (!actor.admin() && cur.ownerUserId() != null && !cur.ownerUserId().equals(actor.userId())) {
            throw forbidden("Lead đang do " + nameOr(cur.ownerName()) + " phụ trách.");
        }
        ConvertRequest req = r == null ? new ConvertRequest(null, null, null, null, null) : r;
        String title = req.title() == null || req.title().isBlank()
                ? cur.contactName() + (cur.interestedProduct() == null ? "" : " – " + cur.interestedProduct())
                : req.title();
        if (title.codePointCount(0, title.length()) > 200) {
            title = new String(title.codePoints().limit(200).toArray(), 0, 200);
        }
        UUID owner = cur.ownerUserId() != null ? cur.ownerUserId() : actor.userId();
        String source = "AI_AUTO".equals(cur.source()) ? "AI_LEAD" : "MANUAL";

        int openDeals = deals.openDealsOfContact(tenantId, cur.contactId());
        DealDto deal = deals.createFromLead(tenantId, actor, cur.contactId(), leadId, req.pipelineId(),
                req.stageId(), title, req.amount(), req.expectedCloseDate(), source, owner);
        repo.markConverted(tenantId, leadId, owner);

        audit.recordUserAction(tenantId, actor.userId(), "LEAD_CONVERTED", "LEAD", leadId,
                Map.of("dealId", deal.id().toString()));
        if (cur.ownerUserId() == null) {
            Map<String, Object> d = new LinkedHashMap<>();
            d.put("fromUserId", null);
            d.put("toUserId", owner.toString());
            d.put("via", actor.admin() ? "ADMIN" : "CLAIM");
            audit.recordUserAction(tenantId, actor.userId(), "LEAD_ASSIGNED", "LEAD", leadId, d);
        }
        List<String> warnings = openDeals > 0
                ? List.of("Khách này đang có " + openDeals + " deal khác chưa đóng.")
                : List.of();
        return new ConvertResult(deal, toDto(require(tenantId, leadId)), warnings);
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    private LeadDetail detailOf(UUID tenantId, LeadRow r) {
        ScoreDto latest = repo.scores(tenantId, r.id(), 1).stream().findFirst().map(this::toScore).orElse(null);
        Instant closedAt = switch (r.status()) {
            case "CONVERTED" -> r.convertedAt();
            case "DISQUALIFIED" -> r.updatedAt();       // lead đã loại không sửa được thông tin → mốc ổn định
            default -> null;
        };
        return new LeadDetail(r.id(), r.contactId(), r.contactName(), r.contactPhone(), r.sourceConversationId(),
                r.source(), r.status(), r.interestedProduct(), r.budgetMin(), r.budgetMax(), r.budgetConfidence(),
                r.urgency(), r.currentScore(), r.scoreUpdatedAt(), r.ownerUserId(), r.ownerName(), r.createdAt(),
                latest, r.disqualifiedReason(), repo.convertedDealId(tenantId, r.id()).orElse(null),
                r.convertedAt(), repo.activityCount(tenantId, r.id()), closedAt, NEXT.get(r.status()));
    }

    private ScoreDto toScore(ScoreRow s) {
        JsonNode factors;
        try {
            factors = json.readTree(s.topFactorsJson() == null ? "[]" : s.topFactorsJson());
        } catch (JsonProcessingException e) {
            factors = json.createArrayNode();
        }
        // V113 chưa có cột chế độ chấm — bảng luật dự phòng ghi model_version bắt đầu bằng "rule"
        String mode = s.modelVersion() != null && s.modelVersion().toLowerCase().startsWith("rule") ? "RULE" : "ML";
        return new ScoreDto(s.score(), s.modelVersion(), mode, factors,
                "LOW".equals(s.confidence()) ? "LOW" : "NORMAL", s.scoredAt());
    }

    private static LeadDto toDto(LeadRow r) {
        return new LeadDto(r.id(), r.contactId(), r.contactName(), r.contactPhone(), r.sourceConversationId(),
                r.source(), r.status(), r.interestedProduct(), r.budgetMin(), r.budgetMax(), r.budgetConfidence(),
                r.urgency(), r.currentScore(), r.scoreUpdatedAt(), r.ownerUserId(), r.ownerName(), r.createdAt());
    }

    /**
     * Khoá theo khách trong transaction: hai người tạo/mở lại lead cho cùng khách cùng lúc thì người sau
     * đợi, rồi thấy lead của người trước và nhận 409 dễ hiểu — thay vì lỗi chỉ mục duy nhất trần trụi.
     */
    private void lockContact(UUID tenantId, UUID contactId) {
        jdbc.queryForList("SELECT pg_advisory_xact_lock(hashtextextended(?, 0))",
                "lead-open:" + tenantId + ":" + contactId);
    }

    private void rejectIfOpenLead(UUID tenantId, UUID contactId) {
        repo.findOpenByContact(tenantId, contactId).ifPresent(open -> {
            throw new BusinessException(HttpStatus.CONFLICT, "LEAD_ALREADY_OPEN",
                    "Khách này đang có lead mở" + (open.ownerName() == null ? " chưa ai phụ trách."
                            : " do " + open.ownerName() + " phụ trách."),
                    new OpenLeadConflict(open.id(), open.status(), open.ownerUserId(), open.ownerName()));
        });
    }

    private void requireActiveUser(UUID tenantId, UUID userId) {
        if (repo.activeUserName(tenantId, userId).isEmpty()) {
            throw invalid("OWNER_INVALID", "Người phụ trách không tồn tại hoặc đã ngừng hoạt động.");
        }
    }

    private LeadRow require(UUID tenantId, UUID leadId) {
        return repo.find(tenantId, leadId).orElseThrow(LeadService::notFound);
    }

    private static String product(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        String s = raw.strip();
        if (s.codePointCount(0, s.length()) > MAX_PRODUCT) {
            throw invalid("PRODUCT_TOO_LONG", "Sản phẩm quan tâm tối đa 200 ký tự.");
        }
        return s;
    }

    private static void checkBudget(BigDecimal min, BigDecimal max) {
        for (BigDecimal v : new BigDecimal[] {min, max}) {
            if (v != null && (v.signum() < 0 || v.compareTo(MAX_MONEY) > 0 || v.stripTrailingZeros().scale() > 2)) {
                throw invalid("INVALID_BUDGET", "Ngân sách phải là số không âm, tối đa 2 chữ số thập phân.");
            }
        }
        if (min != null && max != null && max.compareTo(min) < 0) {
            throw invalid("INVALID_BUDGET", "Ngân sách tối đa phải lớn hơn hoặc bằng ngân sách tối thiểu.");
        }
    }

    private static void checkLevel(String level) {
        if (level != null && !LEVELS.contains(level)) {
            throw invalid("INVALID_URGENCY", "Mức độ gấp chỉ nhận LOW, MEDIUM hoặc HIGH.");
        }
    }

    private static boolean sameMoney(BigDecimal a, BigDecimal b) {
        return a == null ? b == null : b != null && a.compareTo(b) == 0;
    }

    private static String text(JsonNode body, String field) {
        JsonNode n = body.get(field);
        if (n == null || n.isNull()) {
            return null;
        }
        if (!n.isTextual()) {
            throw invalid("INVALID_FIELD", "Trường '" + field + "' phải là chuỗi.");
        }
        return n.asText();
    }

    private static BigDecimal money(JsonNode body, String field) {
        JsonNode n = body.get(field);
        if (n == null || n.isNull()) {
            return null;
        }
        if (!n.isNumber()) {
            throw invalid("INVALID_BUDGET", "Trường '" + field + "' phải là số.");
        }
        return n.decimalValue();
    }

    private static UUID uuid(JsonNode body, String field) {
        String s = text(body, field);
        if (s == null) {
            return null;
        }
        try {
            return UUID.fromString(s);
        } catch (IllegalArgumentException e) {
            throw invalid("INVALID_FIELD", "Trường '" + field + "' không đúng định dạng.");
        }
    }

    private static String labels(List<String> statuses) {
        return statuses.isEmpty() ? "không còn trạng thái nào"
                : String.join(", ", statuses.stream().map(LABEL::get).toList());
    }

    private static String nameOr(String name) {
        return name == null || name.isBlank() ? "người khác" : name;
    }

    private static BusinessException notFound() {
        return new BusinessException(HttpStatus.NOT_FOUND, "LEAD_NOT_FOUND", "Không tìm thấy lead.");
    }

    private static BusinessException forbidden(String msg) {
        return new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN", msg);
    }

    private static BusinessException invalid(String code, String msg) {
        return new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, code, msg);
    }
}
