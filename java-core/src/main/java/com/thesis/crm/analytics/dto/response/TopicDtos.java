package com.thesis.crm.analytics.dto.response;

import java.time.LocalDate;
import java.util.UUID;

/** UC038 — SCR052 "Chủ đề hội thoại". Khớp lược đồ {@code ThongKeChuDe} trong {@code dashboard-api.yaml}. */
public final class TopicDtos {

    private TopicDtos() {
    }

    /**
     * Một chủ đề trong một ngày. Giao diện gộp các ngày lại theo {@code topicKey} trước khi hiển thị.
     *
     * @param dimension {@code INTENT} (7 ý định router) hoặc {@code CLUSTER} (cụm ngữ nghĩa)
     * @param topicKey mã ý định ({@code PRICING_POLICY}…) hoặc mã cụm — khoá gộp ở giao diện
     * @param clusterId chỉ có ở lớp {@code CLUSTER}
     * @param topicLabel nhãn chụp lại lúc ghi; hiển thị như văn bản thuần (nhãn cụm do mô hình đặt)
     * @param botResolvedCount hội thoại tác tử tự xử lý trọn — có trả lời, không từ chối, không chuyển giao
     * @param refusalCount hội thoại có ít nhất một lượt bị từ chối
     */
    public record ThongKeChuDe(
            LocalDate statDate,
            String dimension,
            String topicKey,
            UUID clusterId,
            String topicLabel,
            long conversationCount,
            long botResolvedCount,
            long refusalCount) {
    }
}
