package com.thesis.crm.engagement.widget;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** Hình dạng dữ liệu của API công khai {@code /api/v1/widget/**} (UC009/UC010). */
public final class WidgetDtos {

    private WidgetDtos() {}

    /** Widget gửi khoá công khai; {@code token} là phiên cũ lưu ở localStorage (11.3), có thể rỗng. */
    public record StartSessionRequest(@NotBlank @Size(max = 64) String widgetKey, String token) {}

    /** Độ dài kiểm ở service để thông báo đúng câu của đặc tả 4.2, không phải câu chung của Bean Validation. */
    public record SendMessageRequest(String content) {}

    /** {@code displayName}: tên doanh nghiệp tự đặt, không đặt thì là tên doanh nghiệp. */
    public record Appearance(String primaryColor, String position, String greetingMessage, String avatarUrl,
                             String displayName) {}

    public record CitationDto(String documentId, String title, String snippet) {}

    /** {@code senderType}: CUSTOMER / BOT / AGENT / SYSTEM. */
    public record MessageDto(UUID id, String senderType, String content, List<CitationDto> citations,
                             Instant sentAt) {}

    /**
     * {@code status}: ACTIVE — hiện khung chat; SUSPENDED — doanh nghiệp bị khoá / hết thuê bao /
     * kênh tắt, widget hiện "dịch vụ tạm ngừng" (UC009 11.2). Khi SUSPENDED thì không có token.
     */
    public record SessionResponse(String status, String token, Appearance appearance,
                                  String conversationStatus, List<MessageDto> messages, boolean infoShared) {}

    /**
     * Khách để lại thông tin (bổ sung UC010). {@code consent} BẮT BUỘC true — Nghị định 13: không đồng ý thì
     * không lưu tên/SĐT. Phải có ít nhất SĐT hoặc email.
     */
    public record ContactInfoRequest(String fullName, String phone, String email, Boolean consent) {}

    /**
     * Không trả gì về hồ sơ khác (kể cả "SĐT này đã có người dùng") — khách là người ngoài, lộ chuyện
     * trùng là lộ việc một số điện thoại đã là khách của cửa hàng.
     */
    public record ContactInfoResponse(boolean infoShared, String conversationStatus, List<MessageDto> messages) {}

    /** Các tin MỚI phát sinh từ thao tác (tin của khách + trả lời) và trạng thái hội thoại sau đó. */
    public record TurnResponse(String conversationStatus, List<MessageDto> messages) {}
}
