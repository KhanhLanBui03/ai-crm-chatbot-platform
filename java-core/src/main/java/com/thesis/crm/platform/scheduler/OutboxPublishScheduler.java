package com.thesis.crm.platform.scheduler;

import com.thesis.crm.platform.messaging.OutboxPublisher;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/**
 * Nhịp của job phát outbox — ADR-0003: mỗi 500 ms, lô 100 ({@code crm.outbox.*}).
 *
 * <p>{@code fixedDelay} chứ không {@code fixedRate}: lượt sau chỉ bắt đầu khi lượt trước xong, nên
 * Kafka chậm thì các lượt giãn ra thay vì chồng lên nhau.
 *
 * <p>Tắt được bằng {@code crm.outbox.publisher.enabled=false} — test không có Kafka dùng cờ này để
 * job khỏi giữ khoá và thử kết nối trong nền.
 */
@Component
@ConditionalOnProperty(prefix = "crm.outbox.publisher", name = "enabled", havingValue = "true", matchIfMissing = true)
public class OutboxPublishScheduler {

    private static final Logger log = LoggerFactory.getLogger(OutboxPublishScheduler.class);

    private final OutboxPublisher publisher;

    public OutboxPublishScheduler(OutboxPublisher publisher) {
        this.publisher = publisher;
    }

    @Scheduled(fixedDelayString = "${crm.outbox.poll-interval-ms}")
    public void phatLo() {
        try {
            publisher.publishPendingBatch();
        } catch (RuntimeException e) {
            // Không để ngoại lệ lọt ra: Spring vẫn lên lịch lượt sau, nhưng cần dòng log để biết
            // CSDL (không phải Kafka — lỗi Kafka đã ghi vào từng dòng outbox) đang có vấn đề.
            log.error("Lượt phát outbox hỏng", e);
        }
    }
}
