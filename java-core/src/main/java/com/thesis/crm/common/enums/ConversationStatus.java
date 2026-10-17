package com.thesis.crm.common.enums;

/**
 * Trạng thái hội thoại — nguyên văn {@code CHECK} của {@code engagement.conversations.status} (V107).
 *
 * <p>Vòng đời: {@code BOT_HANDLING} → (chuyển giao, UC014) {@code PENDING_AGENT} → (nhân viên nhận)
 * {@code AGENT_HANDLING} → {@code RESOLVED} / {@code CLOSED}. Đóng hội thoại phát
 * {@code crm.conversation.closed} qua outbox (UC026).
 *
 * <p>Thêm giá trị ở đây mà quên migration thì {@code ddl-auto: validate} không bắt được — CHECK chỉ
 * từ chối lúc ghi.
 */
public enum ConversationStatus {
    BOT_HANDLING,
    PENDING_AGENT,
    AGENT_HANDLING,
    RESOLVED,
    CLOSED
}
