package com.thesis.crm.engagement.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.Immutable;

/**
 * {@code engagement.handoff_events} — mỗi lần chuyển hội thoại giữa AI và nhân viên (UC014, V131).
 *
 * <p>Chỉ đọc qua Entity (báo cáo UC039 đếm lý do chuyển giao); bên ghi là {@code AssignmentRepository}.
 * {@code counts_against_ai_quality = false} với chuyển giao vì hết hạn mức hay lỗi LLM — tính vào chất
 * lượng thì một tháng chạm trần làm tác tử trông như đột nhiên kém đi.
 */
@Entity
@Immutable
@Table(name = "handoff_events", schema = "engagement")
public class HandoffEvent {

    @Id
    private UUID id;

    @Column(name = "tenant_id", nullable = false)
    private UUID tenantId;

    @Column(name = "conversation_id", nullable = false)
    private UUID conversationId;

    /** {@code BOT_TO_AGENT | AGENT_TO_BOT}. */
    @Column(nullable = false, length = 20)
    private String direction;

    /** Khớp {@code LyDoChuyenGiao} của hợp đồng. */
    @Column(nullable = false, length = 30)
    private String reason;

    /** {@code AI_AGENT | AGENT | SYSTEM}. */
    @Column(name = "triggered_by", nullable = false, length = 20)
    private String triggeredBy;

    @Column(name = "counts_against_ai_quality", nullable = false)
    private boolean countsAgainstAiQuality;

    @Column(name = "occurred_at", nullable = false)
    private Instant occurredAt;

    protected HandoffEvent() {
        // JPA yêu cầu constructor không tham số
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public UUID getConversationId() { return conversationId; }
    public String getDirection() { return direction; }
    public String getReason() { return reason; }
    public String getTriggeredBy() { return triggeredBy; }
    public boolean isCountsAgainstAiQuality() { return countsAgainstAiQuality; }
    public Instant getOccurredAt() { return occurredAt; }
}
