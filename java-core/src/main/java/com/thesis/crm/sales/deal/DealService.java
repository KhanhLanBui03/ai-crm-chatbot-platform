package com.thesis.crm.sales.deal;

import com.fasterxml.jackson.databind.JsonNode;
import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.sales.deal.DealDtos.CreateDealRequest;
import com.thesis.crm.sales.deal.DealDtos.DealDetail;
import com.thesis.crm.sales.deal.DealDtos.DealDto;
import com.thesis.crm.sales.deal.DealDtos.MissingFields;
import com.thesis.crm.sales.deal.DealDtos.PipelineDto;
import com.thesis.crm.sales.deal.DealDtos.StageDto;
import com.thesis.crm.sales.deal.DealRepository.DealRow;
import com.thesis.crm.sales.deal.DealRepository.Filter;
import com.thesis.crm.sales.deal.DealRepository.NewDeal;
import com.thesis.crm.sales.deal.DealRepository.StageRow;
import com.thesis.crm.sales.activity.ActivityService;
import com.thesis.crm.sales.lead.LeadRepository;
import com.thesis.crm.sales.lead.LeadRepository.ContactRef;
import com.thesis.crm.sales.lead.LeadService.Actor;
import com.thesis.crm.security.TenantTransactionScope;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC034 — Deal theo phễu (và phần tạo deal dùng chung với UC033).
 *
 * <p>Luật đã chốt với người dùng:
 * <ul>
 *   <li><b>Kéo tự do</b> giữa các giai đoạn mở (khách hay quay lại thương lượng). Vào "Thắng"/"Thua" là
 *       đóng deal; "Thua" bắt buộc 1 trong 6 lý do cố định (UC037 đếm "thua vì gì nhiều nhất"). Kéo deal
 *       đã đóng ra giai đoạn mở là mở lại, xoá lý do thua.
 *   <li>Giai đoạn đích có {@code required_fields} mà deal còn thiếu → 422 kèm danh sách trường thiếu
 *       (luồng 5.1) để giao diện mở đúng ô cần nhập.
 *   <li><b>Quyền giống Lead:</b> ai cũng xem; nhân viên kéo/sửa deal của mình hoặc chưa ai nhận (= tự
 *       nhận); chỉ quản trị viên giao cho người khác.
 *   <li>Mỗi lần đổi giai đoạn ghi {@code sales.deal_stage_history} kèm số giây ở giai đoạn trước.
 *   <li>Chỉ VND; không phát sự kiện phễu (UC037 đếm từ CSDL — giảm độ sâu, như UC032).
 * </ul>
 */
@Service
public class DealService {

    /** Lý do thua — danh sách cố định để thống kê được. */
    static final List<String> LOST_REASONS =
            List.of("PRICE", "COMPETITOR", "NO_BUDGET", "NO_DECISION", "UNREACHABLE", "OTHER");
    static final Set<String> STATUSES = Set.of("OPEN", "WON", "LOST");
    /** Trường mà {@code deal_stages.required_fields} được phép đòi — tên theo hợp đồng (camelCase). */
    static final Set<String> CHECKABLE_FIELDS = Set.of("amount", "expectedCloseDate", "ownerUserId");
    static final int MAX_TITLE = 200;
    private static final BigDecimal MAX_MONEY = new BigDecimal("9999999999999999.99");   // numeric(18,2)
    private static final int MAX_PAGE = 500;      // bảng Kanban lấy trọn một phễu trong một lần gọi

    private final DealRepository repo;
    private final LeadRepository leads;
    private final TenantTransactionScope scope;
    private final AuditLogWriter audit;
    private final ActivityService activities;

    public DealService(DealRepository repo, LeadRepository leads, TenantTransactionScope scope, AuditLogWriter audit,
                       ActivityService activities) {
        this.repo = repo;
        this.leads = leads;
        this.scope = scope;
        this.audit = audit;
        this.activities = activities;
    }

    // ── đọc ─────────────────────────────────────────────────────────────────────

    @Transactional(readOnly = true)
    public List<PipelineDto> pipelines(UUID tenantId, boolean includeInactive) {
        scope.apply(tenantId);
        List<StageRow> stages = repo.stagesWithTotals(tenantId);
        return repo.pipelines(tenantId, includeInactive).stream()
                .map(p -> new PipelineDto(p.id(), p.name(), p.isDefault(), p.isActive(), stages.stream()
                        .filter(s -> s.pipelineId().equals(p.id()))
                        .map(s -> new StageDto(s.id(), s.name(), s.position(), s.probability(), s.won(), s.lost(),
                                s.requiredFields(), s.dealCount(), s.dealValueTotal()))
                        .toList()))
                .toList();
    }

    @Transactional(readOnly = true)
    public PageResponse<DealDto> list(UUID tenantId, UUID pipelineId, UUID stageId, String status, UUID ownerUserId,
                                      UUID contactId, int page, int size) {
        scope.apply(tenantId);
        if (status != null && !STATUSES.contains(status)) {
            throw invalid("INVALID_STATUS", "Trạng thái deal chỉ nhận OPEN, WON hoặc LOST.");
        }
        int p = Math.max(0, page);
        int s = Math.min(Math.max(1, size), MAX_PAGE);
        Filter f = new Filter(pipelineId, stageId, status, ownerUserId, contactId, p, s);
        return PageResponse.of(repo.search(tenantId, f).stream().map(DealService::toDto).toList(), p, s,
                repo.count(tenantId, f));
    }

    @Transactional(readOnly = true)
    public DealDetail detail(UUID tenantId, UUID dealId) {
        scope.apply(tenantId);
        return detailOf(tenantId, require(tenantId, dealId));
    }

    // ── tạo ─────────────────────────────────────────────────────────────────────

    /** SCR046 — tạo deal thủ công trên bảng phễu, chọn khách có sẵn. */
    @Transactional
    public DealDto create(UUID tenantId, Actor actor, CreateDealRequest r) {
        scope.apply(tenantId);
        if (r == null || r.contactId() == null) {
            throw invalid("CONTACT_REQUIRED", "Chọn khách hàng cho deal.");
        }
        if (r.leadId() != null) {
            throw invalid("CONVERT_VIA_LEAD", "Deal từ lead tạo bằng nút \"Chuyển thành Deal\" trên trang lead.");
        }
        requireActiveContact(tenantId, r.contactId());
        UUID owner = r.ownerUserId() == null ? actor.userId() : r.ownerUserId();
        if (!owner.equals(actor.userId()) && !actor.admin()) {
            throw forbidden("Chỉ quản trị viên được giao deal cho người khác.");
        }
        requireActiveUser(tenantId, owner);
        if (r.currency() != null && !"VND".equals(r.currency())) {
            throw invalid("INVALID_CURRENCY", "Hiện chỉ hỗ trợ VND.");
        }
        UUID id = insertDeal(tenantId, actor, r.contactId(), null, r.pipelineId(), r.stageId(), r.title(),
                r.amount(), r.expectedCloseDate(), "MANUAL", owner);
        audit.recordUserAction(tenantId, actor.userId(), "DEAL_CREATED", "DEAL", id,
                Map.of("source", "MANUAL", "via", "BOARD", "ownerUserId", owner.toString()));
        return toDto(require(tenantId, id));
    }

    /**
     * Phần tạo deal của UC033 — gọi từ {@code LeadService.convert} trong CÙNG transaction (MANDATORY):
     * tạo deal và đóng lead là một việc, lỗi giữa chừng thì không việc nào được ghi.
     */
    @Transactional(propagation = Propagation.MANDATORY)
    public DealDto createFromLead(UUID tenantId, Actor actor, UUID contactId, UUID leadId, UUID pipelineId,
                                  UUID stageId, String title, BigDecimal amount, LocalDate expectedCloseDate,
                                  String source, UUID owner) {
        requireActiveContact(tenantId, contactId);
        UUID id = insertDeal(tenantId, actor, contactId, leadId, pipelineId, stageId, title, amount,
                expectedCloseDate, source, owner);
        audit.recordUserAction(tenantId, actor.userId(), "DEAL_CREATED", "DEAL", id,
                Map.of("source", source, "via", "LEAD_CONVERT", "leadId", leadId.toString()));
        return toDto(require(tenantId, id));
    }

    @Transactional(propagation = Propagation.MANDATORY)
    public int openDealsOfContact(UUID tenantId, UUID contactId) {
        return repo.openDealsOfContact(tenantId, contactId);
    }

    private UUID insertDeal(UUID tenantId, Actor actor, UUID contactId, UUID leadId, UUID pipelineId, UUID stageId,
                            String rawTitle, BigDecimal amount, LocalDate date, String source, UUID owner) {
        String title = title(rawTitle);
        checkMoney(amount);
        StageRow stage = resolveStage(tenantId, pipelineId, stageId);
        if (stage.closing()) {
            throw invalid("STAGE_CLOSED", "Deal mới phải bắt đầu ở một giai đoạn đang mở, không phải Thắng/Thua.");
        }
        List<String> missing = missingFields(stage, amount, date, owner);
        if (!missing.isEmpty()) {
            throw missingFieldsError(stage, missing);
        }
        UUID id = repo.insert(tenantId, new NewDeal(contactId, leadId, stage.pipelineId(), stage.id(), title, amount,
                date, source, owner));
        repo.insertHistory(tenantId, id, null, stage.id(), null, actor.userId());
        return id;
    }

    // ── sửa ─────────────────────────────────────────────────────────────────────

    /** PATCH nhận JsonNode để phân biệt "không gửi" (giữ nguyên) với "gửi null" (xoá giá trị). */
    @Transactional
    public DealDetail update(UUID tenantId, Actor actor, UUID dealId, JsonNode body) {
        scope.apply(tenantId);
        if (body == null || !body.isObject()) {
            throw invalid("INVALID_BODY", "Dữ liệu cập nhật phải là một đối tượng JSON.");
        }
        if (!repo.lock(tenantId, dealId)) {
            throw notFound();
        }
        DealRow cur = require(tenantId, dealId);
        requireCanEdit(actor, cur);

        String title = body.has("title") ? title(text(body, "title")) : cur.title();
        BigDecimal amount = body.has("amount") ? money(body, "amount") : cur.amount();
        LocalDate date = body.has("expectedCloseDate") ? date(body, "expectedCloseDate") : cur.expectedCloseDate();
        checkMoney(amount);
        if (body.hasNonNull("currency") && !"VND".equals(text(body, "currency"))) {
            throw invalid("INVALID_CURRENCY", "Hiện chỉ hỗ trợ VND.");
        }
        List<String> changed = new ArrayList<>();
        if (!title.equals(cur.title())) {
            changed.add("title");
        }
        if (!sameMoney(amount, cur.amount())) {
            changed.add("amount");
        }
        if (!Objects.equals(date, cur.expectedCloseDate())) {
            changed.add("expectedCloseDate");
        }
        if (!changed.isEmpty() && !"OPEN".equals(cur.status())) {
            throw new BusinessException(HttpStatus.CONFLICT, "DEAL_CLOSED",
                    "Deal đã đóng — kéo về một giai đoạn đang mở để mở lại rồi mới sửa.");
        }

        UUID owner = cur.ownerUserId();
        String via = null;
        if (body.has("ownerUserId")) {
            UUID target = uuid(body, "ownerUserId");
            if (!Objects.equals(target, cur.ownerUserId())) {
                if (!actor.admin() && !actor.userId().equals(target)) {
                    throw forbidden("Chỉ quản trị viên được giao hoặc gỡ người phụ trách deal.");
                }
                if (target != null) {
                    requireActiveUser(tenantId, target);
                }
                owner = target;
                via = actor.admin() ? "ADMIN" : "CLAIM";
            }
        }
        if (changed.isEmpty() && Objects.equals(owner, cur.ownerUserId())) {
            return detailOf(tenantId, cur);
        }
        if (!actor.admin() && cur.ownerUserId() == null && owner == null) {
            owner = actor.userId();
            via = "CLAIM";
        }
        // Không được bỏ trường mà giai đoạn hiện tại đòi (vd. xoá giá trị khi deal đang ở "Đã báo giá")
        StageRow stage = repo.stage(tenantId, cur.stageId()).orElse(null);
        if (stage != null) {
            List<String> missing = missingFields(stage, amount, date, owner);
            if (!missing.isEmpty()) {
                throw missingFieldsError(stage, missing);
            }
        }

        repo.updateFields(tenantId, dealId, title, amount, date, owner);
        if (!changed.isEmpty()) {
            audit.recordUserAction(tenantId, actor.userId(), "DEAL_UPDATED", "DEAL", dealId, Map.of("fields", changed));
        }
        if (!Objects.equals(owner, cur.ownerUserId())) {
            audit.recordUserAction(tenantId, actor.userId(), "DEAL_ASSIGNED", "DEAL", dealId,
                    assignData(cur.ownerUserId(), owner, via));
        }
        return detailOf(tenantId, require(tenantId, dealId));
    }

    // ── kéo thả (UC034 bước 5–7, luồng 4.x, 5.1) ───────────────────────────────

    @Transactional
    public DealDetail moveStage(UUID tenantId, Actor actor, UUID dealId, UUID stageId, String closeReason) {
        scope.apply(tenantId);
        if (stageId == null) {
            throw invalid("STAGE_REQUIRED", "Chọn giai đoạn đích.");
        }
        if (!repo.lock(tenantId, dealId)) {
            throw notFound();
        }
        DealRow cur = require(tenantId, dealId);
        requireCanEdit(actor, cur);
        StageRow to = repo.stage(tenantId, stageId)
                .orElseThrow(() -> invalid("STAGE_NOT_FOUND", "Giai đoạn không tồn tại."));
        if (!to.pipelineId().equals(cur.pipelineId())) {
            throw invalid("STAGE_OTHER_PIPELINE", "Giai đoạn này thuộc phễu khác.");
        }
        if (to.id().equals(cur.stageId())) {
            if (closeReason != null && to.lost() && !closeReason.equals(cur.closeReason())) {
                // Đổi lý do thua khi deal vẫn ở cột Thua
                requireLostReason(closeReason);
                repo.updateCloseReason(tenantId, dealId, closeReason);
                audit.recordUserAction(tenantId, actor.userId(), "DEAL_STAGE_CHANGED", "DEAL", dealId,
                        Map.of("from", cur.stageId().toString(), "to", to.id().toString(), "status", "LOST",
                                "reason", closeReason));
                return detailOf(tenantId, require(tenantId, dealId));
            }
            return detailOf(tenantId, cur);
        }

        String status = to.won() ? "WON" : to.lost() ? "LOST" : "OPEN";
        String reason = null;
        if (to.lost()) {
            requireLostReason(closeReason);
            reason = closeReason;
        } else if (closeReason != null && !closeReason.isBlank()) {
            throw invalid("REASON_ONLY_WHEN_LOST", "Lý do chỉ dùng khi kéo deal vào \"Thua\".");
        }
        UUID owner = cur.ownerUserId();
        if (!actor.admin() && owner == null) {
            owner = actor.userId();                     // kéo deal chưa ai nhận = tự nhận
        }
        List<String> missing = missingFields(to, cur.amount(), cur.expectedCloseDate(), owner);
        if (!missing.isEmpty()) {
            throw missingFieldsError(to, missing);
        }

        repo.insertHistory(tenantId, dealId, cur.stageId(), to.id(), cur.stageChangedAt(), actor.userId());
        repo.moveStage(tenantId, dealId, to.id(), status, reason, owner);

        Map<String, Object> d = new LinkedHashMap<>();
        d.put("from", cur.stageId().toString());
        d.put("to", to.id().toString());
        d.put("status", status);
        if (reason != null) {
            d.put("reason", reason);
        }
        if (!"OPEN".equals(cur.status()) && "OPEN".equals(status)) {
            d.put("reopened", true);
        }
        audit.recordUserAction(tenantId, actor.userId(), "DEAL_STAGE_CHANGED", "DEAL", dealId, d);
        if (!Objects.equals(owner, cur.ownerUserId())) {
            audit.recordUserAction(tenantId, actor.userId(), "DEAL_ASSIGNED", "DEAL", dealId,
                    assignData(null, owner, "CLAIM"));
        }
        return detailOf(tenantId, require(tenantId, dealId));
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    private StageRow resolveStage(UUID tenantId, UUID pipelineId, UUID stageId) {
        if (stageId == null) {
            StageRow first = repo.defaultFirstStage(tenantId)
                    .orElseThrow(() -> new BusinessException(HttpStatus.CONFLICT, "NO_PIPELINE",
                            "Doanh nghiệp chưa có phễu bán hàng."));
            if (pipelineId != null && !pipelineId.equals(first.pipelineId())) {
                throw invalid("STAGE_REQUIRED", "Chọn giai đoạn của phễu này.");
            }
            return first;
        }
        StageRow s = repo.stage(tenantId, stageId)
                .orElseThrow(() -> invalid("STAGE_NOT_FOUND", "Giai đoạn không tồn tại."));
        if (pipelineId != null && !pipelineId.equals(s.pipelineId())) {
            throw invalid("STAGE_OTHER_PIPELINE", "Giai đoạn này thuộc phễu khác.");
        }
        return s;
    }

    private static List<String> missingFields(StageRow stage, BigDecimal amount, LocalDate date, UUID owner) {
        List<String> missing = new ArrayList<>();
        for (String f : stage.requiredFields()) {
            boolean thieu = switch (f) {
                case "amount" -> amount == null;
                case "expectedCloseDate" -> date == null;
                case "ownerUserId" -> owner == null;
                default -> false;          // tên trường lạ trong cấu hình: bỏ qua, không chặn người dùng
            };
            if (thieu) {
                missing.add(f);
            }
        }
        return missing;
    }

    private static BusinessException missingFieldsError(StageRow stage, List<String> missing) {
        Map<String, String> label = Map.of("amount", "giá trị deal", "expectedCloseDate", "ngày dự kiến chốt",
                "ownerUserId", "người phụ trách");
        return new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "MISSING_REQUIRED_FIELDS",
                "Giai đoạn \"" + stage.name() + "\" cần có " + String.join(", ",
                        missing.stream().map(label::get).toList()) + ".",
                new MissingFields(missing));
    }

    private static void requireLostReason(String reason) {
        if (reason == null || !LOST_REASONS.contains(reason)) {
            throw new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "LOST_REASON_REQUIRED",
                    "Chọn lý do thua.", Map.of("reasons", LOST_REASONS));
        }
    }

    private void requireCanEdit(Actor actor, DealRow d) {
        if (!actor.admin() && d.ownerUserId() != null && !d.ownerUserId().equals(actor.userId())) {
            throw forbidden("Deal đang do " + (d.ownerName() == null ? "người khác" : d.ownerName()) + " phụ trách.");
        }
    }

    private void requireActiveContact(UUID tenantId, UUID contactId) {
        ContactRef c = leads.findContact(tenantId, contactId)
                .orElseThrow(() -> new BusinessException(HttpStatus.NOT_FOUND, "CONTACT_NOT_FOUND",
                        "Không tìm thấy khách hàng."));
        if (c.deleted() || !"ACTIVE".equals(c.status())) {
            throw invalid("CONTACT_INACTIVE", "Khách hàng đã bị gộp, ẩn danh hoặc xoá — không tạo deal được.");
        }
    }

    private void requireActiveUser(UUID tenantId, UUID userId) {
        if (leads.activeUserName(tenantId, userId).isEmpty()) {
            throw invalid("OWNER_INVALID", "Người phụ trách không tồn tại hoặc đã ngừng hoạt động.");
        }
    }

    private DealRow require(UUID tenantId, UUID dealId) {
        return repo.find(tenantId, dealId).orElseThrow(DealService::notFound);
    }

    private DealDetail detailOf(UUID tenantId, DealRow r) {
        return new DealDetail(r.id(), r.contactId(), r.contactName(), r.leadId(), r.pipelineId(), r.stageId(),
                r.stageName(), r.title(), r.amount(), r.currency(), r.expectedCloseDate(), r.overdue(), r.status(),
                r.source(), r.ownerUserId(), r.ownerName(), r.stageChangedAt(), r.createdAt(), r.closeReason(),
                r.closedAt(), repo.history(tenantId, r.id()), List.copyOf(activities.ofDeal(tenantId, r.id(), 50)));
    }

    static DealDto toDto(DealRow r) {
        return new DealDto(r.id(), r.contactId(), r.contactName(), r.leadId(), r.pipelineId(), r.stageId(),
                r.stageName(), r.title(), r.amount(), r.currency(), r.expectedCloseDate(), r.overdue(), r.status(),
                r.source(), r.ownerUserId(), r.ownerName(), r.stageChangedAt(), r.createdAt());
    }

    private static Map<String, Object> assignData(UUID from, UUID to, String via) {
        Map<String, Object> d = new LinkedHashMap<>();
        d.put("fromUserId", from == null ? null : from.toString());
        d.put("toUserId", to == null ? null : to.toString());
        d.put("via", via);
        return d;
    }

    static String title(String raw) {
        String s = raw == null ? "" : raw.strip();
        if (s.isEmpty()) {
            throw invalid("TITLE_REQUIRED", "Nhập tên deal.");
        }
        if (s.codePointCount(0, s.length()) > MAX_TITLE) {
            throw invalid("TITLE_TOO_LONG", "Tên deal tối đa 200 ký tự.");
        }
        return s;
    }

    static void checkMoney(BigDecimal v) {
        if (v != null && (v.signum() < 0 || v.compareTo(MAX_MONEY) > 0 || v.stripTrailingZeros().scale() > 2)) {
            throw invalid("INVALID_AMOUNT", "Giá trị deal phải là số không âm, tối đa 2 chữ số thập phân.");
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
            throw invalid("INVALID_AMOUNT", "Trường '" + field + "' phải là số.");
        }
        return n.decimalValue();
    }

    private static LocalDate date(JsonNode body, String field) {
        String s = text(body, field);
        try {
            return s == null ? null : LocalDate.parse(s);
        } catch (DateTimeParseException e) {
            throw invalid("INVALID_FIELD", "Trường '" + field + "' phải có dạng YYYY-MM-DD.");
        }
    }

    private static UUID uuid(JsonNode body, String field) {
        String s = text(body, field);
        try {
            return s == null ? null : UUID.fromString(s);
        } catch (IllegalArgumentException e) {
            throw invalid("INVALID_FIELD", "Trường '" + field + "' không đúng định dạng.");
        }
    }

    private static BusinessException notFound() {
        return new BusinessException(HttpStatus.NOT_FOUND, "DEAL_NOT_FOUND", "Không tìm thấy deal.");
    }

    private static BusinessException forbidden(String msg) {
        return new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN", msg);
    }

    static BusinessException invalid(String code, String msg) {
        return new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, code, msg);
    }
}
