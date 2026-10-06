package com.thesis.crm.engagement.dto.response;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * DTO danh bạ — khớp TỪNG TÊN TRƯỜNG với docs/openapi/dashboard-api.yaml
 * ({@code KhachHang}, {@code KhachHangChiTiet}, {@code The}, {@code DanhTinhKenh},
 * {@code TaoKhachHangResult}). Đổi tên ở đây là gãy web-dashboard.
 */
public final class ContactDtos {

    private ContactDtos() {}

    /** {@code The} — thẻ phân loại. */
    public record TagDto(UUID id, String name, String color, int usageCount) {}

    /** {@code DanhTinhKenh} — danh tính của khách trên một kênh. */
    public record ChannelIdentityDto(
            UUID id,
            String channelType,
            String externalUserId,
            String displayName,
            String avatarUrl,
            String originDomain,
            Instant lastSeenAt) {}

    /** {@code KhachHang} — một dòng trong danh bạ (SCR026). */
    public record ContactDto(
            UUID id,
            String fullName,
            String phone,
            String email,
            String primaryChannel,
            String status,
            boolean consentGranted,
            Instant consentAt,
            List<TagDto> tags,
            Instant lastInteractionAt,
            Instant createdAt) {}

    /**
     * {@code KhachHangChiTiet} — hồ sơ (SCR024). Hợp đồng dùng {@code allOf} nên JSON phẳng:
     * lặp lại các trường của {@link ContactDto} rồi thêm phần chi tiết.
     */
    public record ContactDetailDto(
            UUID id,
            String fullName,
            String phone,
            String email,
            String primaryChannel,
            String status,
            boolean consentGranted,
            Instant consentAt,
            List<TagDto> tags,
            Instant lastInteractionAt,
            Instant createdAt,
            UUID mergedIntoContactId,
            List<ChannelIdentityDto> channelIdentities,
            int conversationCount,
            int openLeadCount,
            int openDealCount,
            BigDecimal totalDealValue,
            Instant anonymizedAt) {}

    /** {@code TaoKhachHangResult} — trùng thì vẫn tạo, kèm danh sách nghi trùng để gợi ý hợp nhất. */
    public record CreateContactResult(ContactDetailDto contact, List<ContactDto> duplicateCandidates) {}
}
