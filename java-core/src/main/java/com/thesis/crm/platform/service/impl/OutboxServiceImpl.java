package com.thesis.crm.platform.service.impl;

import com.thesis.crm.platform.entity.OutboxEvent;
import com.thesis.crm.platform.repository.OutboxEventRepository;
import com.thesis.crm.platform.service.OutboxService;
import com.thesis.crm.security.TraceIdFilter;
import java.util.Map;
import java.util.UUID;
import org.slf4j.MDC;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * Ghi {@code platform.outbox_events}. Phát lên Kafka là việc của
 * {@code platform/messaging/OutboxPublisher} (500 ms, lô 100) — không phải của service này.
 */
@Service
public class OutboxServiceImpl implements OutboxService {

    private final OutboxEventRepository repository;

    public OutboxServiceImpl(OutboxEventRepository repository) {
        this.repository = repository;
    }

    @Override
    @Transactional(propagation = Propagation.MANDATORY)
    public void append(UUID tenantId, String aggregateType, UUID aggregateId, String eventType,
            String topic, Map<String, Object> payload) {
        String traceId = MDC.get(TraceIdFilter.MDC_KEY);
        Map<String, Object> headers = traceId == null ? Map.of() : Map.of(TraceIdFilter.HEADER, traceId);
        repository.save(new OutboxEvent(tenantId, aggregateType, aggregateId, eventType, topic, payload, headers));
    }
}
