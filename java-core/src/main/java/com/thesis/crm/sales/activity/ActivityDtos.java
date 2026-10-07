package com.thesis.crm.sales.activity;

import java.time.Instant;
import java.util.UUID;

/** Hình dạng vào/ra của UC035 — khớp {@code HoatDong}, {@code LuuHoatDongRequest} trong dashboard-api.yaml. */
public final class ActivityDtos {

    private ActivityDtos() {}

    /**
     * Schema {@code HoatDong}, thêm vài trường hiển thị để giao diện không phải gọi thêm vòng nữa:
     * tiêu đề deal / sản phẩm của lead đang gắn, tên người được nhắc, hội thoại gốc (hoạt động AUTO).
     */
    public record ActivityDto(
            UUID id, UUID contactId, String contactName, UUID leadId, String leadLabel, UUID dealId,
            String dealTitle, UUID conversationId, String type, String subject, String content, String outcome,
            String source, UUID performedBy, String performedByName, Instant performedAt, Instant remindAt,
            UUID remindUserId, String remindUserName, String remindStatus, Instant createdAt) {}

    public record CreateActivityRequest(
            UUID contactId, UUID leadId, UUID dealId, String type, String subject, String content, String outcome,
            Instant performedAt, Instant remindAt, UUID remindUserId) {}

    /** Số đỏ trên menu "Hoạt động": việc quá hạn + việc hôm nay (giờ Việt Nam) của người đang đăng nhập. */
    public record TodoCount(int overdue, int today) {}
}
