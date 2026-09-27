package com.thesis.crm.platform.messaging;

import com.thesis.crm.platform.entity.OutboxEvent;
import com.thesis.crm.platform.repository.OutboxEventRepository;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Đọc {@code platform.outbox_events} và phát lên Kafka — nửa sau của Outbox Pattern (ADR-0003).
 *
 * <p>Giao nhận ÍT NHẤT MỘT LẦN: phát xong mà chưa kịp commit {@code published_at} (tiến trình chết)
 * thì lần sau phát lại. Consumer chống trùng theo {@code event_id} ở
 * {@code analytics.processed_events} — nhận trùng là chắc chắn, không phải rủi ro.
 *
 * <p><b>Thứ tự trong một tenant</b> là thứ khoá phân vùng {@code tenant_id} hứa với consumer. Hai
 * chốt giữ nó ở phía phát: chỉ một job phát chạy tại một thời điểm (khoá advisory, xem
 * {@link OutboxEventRepository#tryLockPublisher()}), và một sự kiện phát hỏng thì CHẶN các sự kiện
 * sau của cùng tenant trong lô — phát sự kiện 3 khi sự kiện 2 còn kẹt là giao sai thứ tự. Tenant
 * khác vẫn chạy bình thường: một sự kiện hỏng không làm tắc cả hệ thống.
 *
 * <p>Sự kiện hỏng được thử lại với khoảng lùi 2, 4, 8… tối đa 60 giây, tính từ {@code updated_at}.
 * Chưa có hàng đợi chết (DLQ): sự kiện hỏng vĩnh viễn nằm lại với {@code attempt_count} tăng dần
 * và {@code last_error} — người vận hành nhìn hai cột đó mà xử lý.
 */
@Component
public class OutboxPublisher {

    private static final Logger log = LoggerFactory.getLogger(OutboxPublisher.class);

    /** Chờ broker xác nhận từng bản tin. Dài hơn thì một broker chết giữ khoá job phát quá lâu. */
    private static final long CHO_XAC_NHAN_GIAY = 10;
    private static final long LUI_TOI_DA_GIAY = 60;
    /** {@code crm.document.v1} → phiên bản 1. Quy ước: đổi lược đồ phá tương thích thì tăng hậu tố. */
    private static final Pattern HAU_TO_PHIEN_BAN = Pattern.compile("\\.v(\\d+)$");

    private final OutboxEventRepository repository;
    private final KafkaTemplate<String, Object> kafka;
    private final int batchSize;

    public OutboxPublisher(OutboxEventRepository repository, KafkaTemplate<String, Object> kafka,
            @Value("${crm.outbox.batch-size}") int batchSize) {
        this.repository = repository;
        this.kafka = kafka;
        this.batchSize = batchSize;
    }

    /**
     * Phát một lô. Trả số sự kiện đã phát thành công.
     *
     * <p>Chạy KHÔNG có ngữ cảnh tenant (job nền) — đúng lý do {@code outbox_events} không bật RLS.
     */
    @Transactional
    public int publishPendingBatch() {
        if (!repository.tryLockPublisher()) {
            return 0;
        }
        List<OutboxEvent> lo = repository.findUnpublished(batchSize);
        Set<UUID> tenantDangChan = new HashSet<>();
        int daPhat = 0;
        for (OutboxEvent e : lo) {
            if (tenantDangChan.contains(e.getTenantId())) {
                continue;
            }
            if (chuaToiLuotThuLai(e, Instant.now())) {
                tenantDangChan.add(e.getTenantId());
                continue;
            }
            try {
                kafka.send(banTin(e)).get(CHO_XAC_NHAN_GIAY, TimeUnit.SECONDS);
                e.markPublished(Instant.now());
                daPhat++;
            } catch (InterruptedException ie) {
                Thread.currentThread().interrupt();
                e.markFailed("Bị ngắt khi chờ Kafka xác nhận", Instant.now());
                break;
            } catch (Exception ex) {
                Throwable goc = ex.getCause() != null ? ex.getCause() : ex;
                e.markFailed(goc.getClass().getSimpleName() + ": " + goc.getMessage(), Instant.now());
                tenantDangChan.add(e.getTenantId());
                log.warn("Phát outbox #{} (topic {}) hỏng lần {}: {}", e.getId(), e.getTopic(),
                        e.getAttemptCount(), goc.toString());
            }
        }
        return daPhat;
    }

    /**
     * Vỏ sự kiện đúng {@code docs/events/*.json}: {@code event_id} là {@code outbox_events.id},
     * khoá bản tin là {@code tenant_id}, Trace ID đi ở HEADER Kafka chứ không ở payload.
     */
    static ProducerRecord<String, Object> banTin(OutboxEvent e) {
        Map<String, Object> vo = new LinkedHashMap<>();
        vo.put("event_id", e.getId());
        vo.put("event_version", phienBan(e.getTopic()));
        vo.put("event_type", e.getEventType());
        vo.put("tenant_id", e.getTenantId().toString());
        vo.put("aggregate_id", e.getAggregateId().toString());
        // Chuỗi ISO-8601 thay vì để serializer tự quyết — lược đồ khai "format": "date-time".
        vo.put("occurred_at", e.getCreatedAt().toString());
        vo.put("payload", e.getPayload());

        ProducerRecord<String, Object> r = new ProducerRecord<>(e.getTopic(), e.getTenantId().toString(), vo);
        e.getHeaders().forEach((k, v) -> r.headers().add(k, String.valueOf(v).getBytes(StandardCharsets.UTF_8)));
        return r;
    }

    static int phienBan(String topic) {
        Matcher m = HAU_TO_PHIEN_BAN.matcher(topic);
        return m.find() ? Integer.parseInt(m.group(1)) : 1;
    }

    private static boolean chuaToiLuotThuLai(OutboxEvent e, Instant now) {
        if (e.getAttemptCount() == 0) {
            return false;
        }
        long lui = Math.min(1L << Math.min(e.getAttemptCount(), 6), LUI_TOI_DA_GIAY);
        return e.getUpdatedAt().plus(Duration.ofSeconds(lui)).isAfter(now);
    }
}
