package com.thesis.crm.common.enums;

/**
 * Ai gửi tin — nguyên văn {@code CHECK} của {@code engagement.messages.sender_type} (V107).
 *
 * <p>Ràng buộc {@code ck_msg_sender}: chỉ {@code AGENT} mới có {@code sender_user_id}; ba loại còn
 * lại phải để trống. Tin {@code CUSTOMER} làm tăng {@code unread_count} của hội thoại (trigger V130).
 */
public enum SenderType {
    CUSTOMER,
    BOT,
    AGENT,
    SYSTEM
}
