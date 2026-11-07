package com.thesis.crm.analytics.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.analytics.service.TurnMetricsService;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

/**
 * Nhóm tiêu thụ {@code analytics-cg} của topic {@code ai.turn.completed} (UC039). Xác nhận offset THỦ CÔNG,
 * SAU khi cộng dồn đã commit (docs/events/README.md quy ước 4) — xác nhận trước là mất sự kiện khi tiến
 * trình chết giữa chừng.
 *
 * <p>Sự kiện sai lược đồ (thiếu trường, nhánh lạ) thì ghi log rồi xác nhận luôn: giao lại bao nhiêu lần nó
 * vẫn sai, giữ lại chỉ chặn cả phân vùng của doanh nghiệp đó. Lỗi khác (CSDL tạm chết) thì ném ra để Kafka
 * giao lại.
 *
 * <p>Tắt bằng {@code crm.analytics.turn-consumer.enabled=false} (test không có Kafka).
 */
@Component
public class TurnCompletedListener {

    private static final Logger log = LoggerFactory.getLogger(TurnCompletedListener.class);

    private final TurnMetricsService service;
    private final ObjectMapper json;

    public TurnCompletedListener(TurnMetricsService service, ObjectMapper json) {
        this.service = service;
        this.json = json;
    }

    @KafkaListener(
            topics = "ai.turn.completed",
            groupId = TurnMetricsService.NHOM_TIEU_THU,
            autoStartup = "${crm.analytics.turn-consumer.enabled:true}")
    public void nhan(ConsumerRecord<String, String> banTin, Acknowledgment ack) {
        JsonNode suKien;
        try {
            suKien = json.readTree(banTin.value());
        } catch (Exception e) {
            log.error("Bỏ bản tin ai.turn.completed không phải JSON (phân vùng {}, offset {})",
                    banTin.partition(), banTin.offset());
            ack.acknowledge();
            return;
        }
        try {
            boolean moi = service.ghiNhan(suKien);
            if (!moi) {
                log.debug("Bỏ qua sự kiện trùng {}", suKien.path("event_id").asText());
            }
        } catch (IllegalArgumentException e) {
            log.error("Bỏ sự kiện ai.turn.completed sai lược đồ {}: {}", suKien.path("event_id").asText(), e.getMessage());
        }
        ack.acknowledge();
    }
}
