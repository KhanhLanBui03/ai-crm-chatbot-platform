package com.thesis.crm.platform.service;

import com.thesis.crm.common.enums.UsageMetric;
import com.thesis.crm.platform.dto.response.QuotaUsageResponse;
import com.thesis.crm.platform.entity.UsageRecord;

/**
 * Hạn mức theo gói — UC006. Ngưỡng cảnh báo 80%, ngưỡng chặn 100%.
 *
 * <p>Hai bước tách rời có chủ đích: KHOÁ + kiểm trước khi làm việc tốn kém (ghi S3, gọi
 * ai-service), CỘNG sau khi việc đó thành công. Cả hai PHẢI chạy trong transaction của phía gọi
 * ({@code Propagation.MANDATORY}) — khoá dòng chỉ có nghĩa khi nó sống tới lúc cộng xong.
 */
public interface UsageQuotaService {

    /**
     * Khoá dòng hạn mức của chu kỳ hiện tại tới hết transaction.
     *
     * @throws com.thesis.crm.common.exception.QuotaExceededException 409 khi đã chạm trần
     * @throws com.thesis.crm.common.exception.BusinessException 409 {@code SUBSCRIPTION_NOT_ACTIVE}
     *         khi không có thuê bao đang hiệu lực
     */
    UsageRecord lockForConsumption(UsageMetric metric);

    /** Cộng {@code amount} vào dòng đã khoá, ghi mốc 80%/100% nếu vừa vượt. */
    QuotaUsageResponse consume(UsageRecord locked, long amount);
}
