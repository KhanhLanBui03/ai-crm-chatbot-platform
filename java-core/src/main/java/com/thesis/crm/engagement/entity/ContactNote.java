package com.thesis.crm.engagement.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.DynamicUpdate;

/**
 * {@code engagement.contact_notes} — ghi chú nội bộ về khách (UC017; V105, V125, V135).
 *
 * <p>Xoá mềm ({@code deleted_at}); {@code edited_at} chỉ đổi khi NỘI DUNG đổi — ghim/bỏ ghim cũng đổi
 * {@code updated_at} (trigger) nên không dùng {@code updated_at} làm "đã sửa".
 * Xoá hội thoại thì {@code conversation_id} về {@code null} (V135), ghi chú vẫn còn.
 */
@Entity
@DynamicUpdate
@Table(name = "contact_notes", schema = "engagement")
public class ContactNote {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "contact_id", nullable = false, updatable = false)
    private UUID contactId;

    @Column(name = "author_user_id", nullable = false, updatable = false)
    private UUID authorUserId;

    /** Ràng buộc: không được rỗng sau khi bỏ khoảng trắng. */
    @Column(nullable = false)
    private String content;

    @Column(name = "conversation_id")
    private UUID conversationId;

    @Column(name = "is_pinned", nullable = false)
    private boolean pinned;

    @Column(name = "edited_at")
    private Instant editedAt;

    @Column(name = "deleted_at")
    private Instant deletedAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    /** Trigger {@code trg_touch_updated_at} tự đặt mỗi lần UPDATE. */
    @Column(name = "updated_at", nullable = false, updatable = false)
    private Instant updatedAt = Instant.now();

    protected ContactNote() {
        // JPA yêu cầu constructor không tham số
    }

    public ContactNote(UUID tenantId, UUID contactId, UUID authorUserId, String content, UUID conversationId) {
        this.tenantId = tenantId;
        this.contactId = contactId;
        this.authorUserId = authorUserId;
        this.content = content;
        this.conversationId = conversationId;
    }

    public UUID getId() { return id; }
    public UUID getTenantId() { return tenantId; }
    public UUID getContactId() { return contactId; }
    public UUID getAuthorUserId() { return authorUserId; }
    public String getContent() { return content; }
    public UUID getConversationId() { return conversationId; }
    public boolean isPinned() { return pinned; }
    public void setPinned(boolean pinned) { this.pinned = pinned; }
    public Instant getEditedAt() { return editedAt; }
    public Instant getDeletedAt() { return deletedAt; }
    public Instant getCreatedAt() { return createdAt; }

    /** Sửa nội dung — đánh dấu "đã sửa". */
    public void editContent(String content, Instant at) {
        this.content = content;
        this.editedAt = at;
    }

    public void softDelete(Instant at) {
        this.deletedAt = at;
    }
}
