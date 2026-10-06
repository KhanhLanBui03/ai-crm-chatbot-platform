package com.thesis.crm.platform.service;

import java.util.Map;
import java.util.UUID;

/**
 * Ghi sự kiện chờ phát — ADR-0003. Bề mặt DUY NHẤT để các context phát sự kiện: không gọi
 * {@code KafkaTemplate.send()} trong service.
 *
 * <p>Phải chạy trong transaction nghiệp vụ của phía gọi ({@code Propagation.MANDATORY}): sự kiện
 * và thay đổi nghiệp vụ cùng commit hoặc cùng mất — đó là toàn bộ lý do outbox tồn tại.
 */
public interface OutboxService {

    /**
     * @param payload trường {@code payload} của vỏ sự kiện, khoá {@code snake_case}. Trace ID
     *                KHÔNG đặt ở đây — service tự gắn vào header
     */
    void append(UUID tenantId, String aggregateType, UUID aggregateId, String eventType, String topic,
            Map<String, Object> payload);
}
