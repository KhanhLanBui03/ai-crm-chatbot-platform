package com.thesis.crm.platform.service;

import com.thesis.crm.platform.entity.TenantSubscription;
import com.thesis.crm.platform.entity.UsageRecord;
import com.thesis.crm.platform.repository.TenantSubscriptionRepository;
import com.thesis.crm.platform.repository.UsageRecordRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC006 — cộng token AI của một lượt vào hạn mức {@code AI_TOKEN} của thuê bao còn hiệu lực.
 *
 * <p>Đặc tả: "Token AI được cộng vào mức dùng thông qua sự kiện chứ không bằng lời gọi đồng bộ trên đường
 * nóng". Gọi từ consumer {@code ai.turn.completed} SAU bước chống trùng, trong cùng transaction — sự kiện
 * giao lại không cộng hai lần.
 *
 * <p>Chọn thuê bao GIỐNG HỆT widget khi đếm hội thoại ({@code WidgetRepository.lockConversationQuota}): thuê
 * bao trạng thái còn hiệu lực mới nhất, KHÔNG xét {@code period_end}. Chưa có công việc gia hạn cuối chu kỳ, nên
 * xét hạn chu kỳ ở đây thì token của doanh nghiệp quá hạn bị bỏ rơi trong khi hội thoại vẫn được đếm — hai ô
 * của cùng một màn lệch nhau.
 *
 * <p>Lượt đã chạy thì token đã tiêu: cộng cả khi vượt trần (không từ chối như lúc tải tài liệu). Chặn nằm ở
 * lượt SAU — widget thấy hạn mức đã cạn thì không gọi AI nữa (UC006 4.2).
 */
@Service
public class AiTokenUsageService {

    static final String CHI_SO = "AI_TOKEN";
    /** Thuê bao còn tính tiêu thụ — khớp {@code WidgetRepository.THUE_BAO_HIEU_LUC}. */
    static final List<String> HIEU_LUC = List.of("TRIALING", "ACTIVE", "PAST_DUE");

    private final TenantSubscriptionRepository thueBao;
    private final UsageRecordRepository mucDung;

    public AiTokenUsageService(TenantSubscriptionRepository thueBao, UsageRecordRepository mucDung) {
        this.thueBao = thueBao;
        this.mucDung = mucDung;
    }

    /**
     * @param luc thời điểm của lượt — ghi vào {@code last_calculated_at} và mốc 80% / 100%
     * @return {@code false} nếu không cộng (0 token, hoặc doanh nghiệp không có thuê bao còn hiệu lực)
     */
    @Transactional(propagation = Propagation.MANDATORY)
    public boolean cong(UUID tenantId, long soToken, Instant luc) {
        if (soToken <= 0) {
            return false;
        }
        Optional<TenantSubscription> tb = thueBao.findFirstByTenantIdAndStatusInOrderByPeriodStartDesc(tenantId,
                HIEU_LUC);
        if (tb.isEmpty()) {
            return false;
        }
        UUID id = tb.get().getId();
        mucDung.insertIfAbsent(id, CHI_SO, false);
        Optional<UsageRecord> dong = mucDung.findForUpdate(id, CHI_SO);
        dong.ifPresent(r -> r.cong(soToken, luc));
        return dong.isPresent();
    }
}
