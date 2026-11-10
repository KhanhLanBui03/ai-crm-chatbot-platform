package com.thesis.crm.platform.service.impl;

import com.thesis.crm.client.AiInteractionClient;
import com.thesis.crm.client.AiInteractionClient.FeedbackRecorded;
import com.thesis.crm.client.AiInteractionClient.FeedbackRequest;
import com.thesis.crm.client.AiInteractionClient.InteractionFeedback;
import com.thesis.crm.client.AiInteractionClient.InteractionPage;
import com.thesis.crm.client.AiInteractionClient.KnowledgeGapPage;
import com.thesis.crm.client.AiServiceErrors;
import com.thesis.crm.client.AiServiceException;
import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.dto.request.DanhGiaAiRequest;
import com.thesis.crm.platform.dto.response.DanhGiaAiResponse;
import com.thesis.crm.platform.dto.response.KhoangTrongTriThucResponse;
import com.thesis.crm.platform.dto.response.LuotXuLyAiResponse;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.platform.entity.User;
import com.thesis.crm.platform.repository.TenantRepository;
import com.thesis.crm.platform.repository.UserRepository;
import com.thesis.crm.platform.service.AiInteractionService;
import com.thesis.crm.security.CurrentActor;
import com.thesis.crm.security.TenantTransactionScope;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.stream.Collectors;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Chuyển tiếp GD2 qua {@link AiInteractionClient}. KHÔNG mở transaction quanh lời gọi ai-service (vài
 * trăm ms tới vài giây): chỉ hai lượt đọc ngắn ở {@code platform} — múi giờ doanh nghiệp và tên nhân viên
 * — mỗi lượt một transaction riêng dưới RLS của đúng tenant.
 */
@Service
public class AiInteractionServiceImpl implements AiInteractionService {

    private static final ZoneId MUI_GIO_MAC_DINH = ZoneId.of("Asia/Ho_Chi_Minh");

    private final AiInteractionClient ai;
    private final UserRepository users;
    private final TenantRepository tenants;
    private final TenantTransactionScope tenantScope;
    private final TransactionTemplate tx;

    public AiInteractionServiceImpl(AiInteractionClient ai, UserRepository users, TenantRepository tenants,
            TenantTransactionScope tenantScope, TransactionTemplate tx) {
        this.ai = ai;
        this.users = users;
        this.tenants = tenants;
        this.tenantScope = tenantScope;
        this.tx = tx;
    }

    @Override
    public PageResponse<LuotXuLyAiResponse> list(String route, Boolean refused, String rating, UUID conversationId,
            LocalDate from, LocalDate to, int page, int size) {
        UUID tenantId = CurrentActor.requireTenantId();
        Instant tu = null;
        Instant den = null;
        if (from != null || to != null) {
            ZoneId zone = muiGio(tenantId);
            tu = from == null ? null : from.atStartOfDay(zone).toInstant();
            den = to == null ? null : to.plusDays(1).atStartOfDay(zone).toInstant();
        }
        Instant tuF = tu;
        Instant denF = den;
        InteractionPage trang = goiAi(() -> ai.list(tenantId, rong(route), refused, rong(rating), conversationId,
                tuF, denF, Math.max(0, page), Math.min(Math.max(1, size), 100)));
        Map<UUID, String> ten = tenNhanVien(tenantId, trang.items().stream()
                .flatMap(i -> i.feedback() == null ? java.util.stream.Stream.<InteractionFeedback>empty()
                        : i.feedback().stream())
                .map(InteractionFeedback::raterUserId).toList());
        return PageResponse.of(trang.items().stream().map(i -> AiInteractionMapper.luot(i, ten)).toList(),
                trang.page(), trang.size(), trang.total());
    }

    @Override
    public DanhGiaAiResponse rate(UUID interactionId, DanhGiaAiRequest request) {
        UUID tenantId = CurrentActor.requireTenantId();
        UUID nhanVien = CurrentActor.requireUserId();
        FeedbackRequest than = cauGui(request.rating(), request.reasonCode(), "AGENT", nhanVien, request.comment(),
                request.correctedAnswer());
        FeedbackRecorded kq = goiAi(() -> ai.feedback(tenantId, interactionId, than));
        String ten = tenNhanVien(tenantId, List.of(nhanVien)).get(nhanVien);
        return new DanhGiaAiResponse(kq.feedbackId(), request.rating(), than.reasonCode(), than.comment(),
                than.correctedAnswer(), "AGENT", nhanVien, ten, Instant.now());
    }

    @Override
    public PageResponse<KhoangTrongTriThucResponse> knowledgeGaps(String gapType, int page, int size) {
        UUID tenantId = CurrentActor.requireTenantId();
        KnowledgeGapPage trang = goiAi(() -> ai.knowledgeGaps(tenantId, rong(gapType), Math.max(0, page),
                Math.min(Math.max(1, size), 100)));
        return PageResponse.of(trang.items().stream().map(AiInteractionMapper::khoangTrong).toList(),
                trang.page(), trang.size(), trang.total());
    }

    /**
     * Thân gửi ai-service. Chê mà thiếu lý do thì 422 {@code REASON_REQUIRED} NGAY ở đây (đặc tả UC027:
     * cưỡng chế ở tầng ứng dụng lẫn CSDL) — không tốn một chuyến sang ai-service. Khen thì bỏ lý do
     * (luồng phụ 3.1): ai-service từ chối lượt khen kèm lý do chê.
     */
    static FeedbackRequest cauGui(String rating, String reasonCode, String raterType, UUID raterUserId,
            String comment, String correctedAnswer) {
        boolean khen = "POSITIVE".equals(rating);
        if (!khen && (reasonCode == null || reasonCode.isBlank())) {
            throw new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "REASON_REQUIRED",
                    "Đánh giá chưa ổn cần chọn một lý do.");
        }
        return new FeedbackRequest(khen ? 1 : -1, khen ? null : reasonCode, raterType, raterUserId, comment,
                correctedAnswer);
    }

    /** {@code full_name} ở {@code platform.users}, một truy vấn cho cả trang; không thấy thì {@code null}. */
    private Map<UUID, String> tenNhanVien(UUID tenantId, Collection<UUID> ids) {
        Set<UUID> can = ids.stream().filter(Objects::nonNull).collect(Collectors.toSet());
        if (can.isEmpty()) {
            return Map.of();
        }
        return tx.execute(st -> {
            tenantScope.apply(tenantId);
            return users.findAllById(can).stream().collect(Collectors.toMap(User::getId, User::getFullName));
        });
    }

    /** "Hôm nay" của doanh nghiệp, không phải của máy chủ — như {@code AiPerformanceService#muiGio}. */
    private ZoneId muiGio(UUID tenantId) {
        String tz = tx.execute(st -> {
            tenantScope.apply(tenantId);
            return tenants.findById(tenantId).map(Tenant::getTimezone).orElse(null);
        });
        try {
            return tz == null ? MUI_GIO_MAC_DINH : ZoneId.of(tz);
        } catch (RuntimeException e) {
            return MUI_GIO_MAC_DINH;
        }
    }

    private static String rong(String s) {
        return s == null || s.isBlank() ? null : s;
    }

    private static <T> T goiAi(Supplier<T> loiGoi) {
        try {
            return loiGoi.get();
        } catch (AiServiceException ex) {
            throw AiServiceErrors.dich(ex);
        }
    }
}
