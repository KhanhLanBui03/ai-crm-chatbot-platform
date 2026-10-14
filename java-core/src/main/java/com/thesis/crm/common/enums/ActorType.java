package com.thesis.crm.common.enums;

/**
 * Ai thực hiện hành động được ghi kiểm toán — nguyên văn {@code CHECK} của
 * {@code platform.audit_logs.actor_type} (V104).
 *
 * <p>Ràng buộc {@code ck_audit_actor}: {@code USER} và {@code PLATFORM_ADMIN} bắt buộc có
 * {@code actor_user_id}; {@code AI_AGENT} và {@code SYSTEM} thì không cần.
 */
public enum ActorType {
    USER,
    AI_AGENT,
    SYSTEM,
    PLATFORM_ADMIN
}
