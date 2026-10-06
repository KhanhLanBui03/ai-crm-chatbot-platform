package com.thesis.crm.common.exception;

import com.thesis.crm.common.enums.UsageMetric;
import org.springframework.http.HttpStatus;

/**
 * Chạm trần một hạn mức của gói — 409, mã {@code <METRIC>_QUOTA_EXCEEDED}.
 *
 * <p>Lớp riêng thay vì {@link BusinessException} trần vì phía ném cần khai
 * {@code @Transactional(noRollbackFor = QuotaExceededException.class)}: lúc từ chối, dịch vụ hạn
 * mức ghi {@code blocked_at} (gói bị hạ giữa chu kỳ), và mốc đó phải được commit dù phản hồi là
 * lỗi. Để rollback thì lần từ chối nào cũng "lần đầu chạm trần".
 *
 * <p>Ở {@code common/} vì không chỉ tài liệu: hạn mức hội thoại (engagement) và người dùng
 * (platform) sẽ ném cùng lớp này.
 */
public class QuotaExceededException extends BusinessException {

    public QuotaExceededException(UsageMetric metric, String message, Object details) {
        super(HttpStatus.CONFLICT, metric.name() + "_QUOTA_EXCEEDED", message, details);
    }
}
