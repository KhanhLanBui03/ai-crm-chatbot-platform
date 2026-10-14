package com.thesis.crm.engagement.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;
import java.io.Serializable;
import java.time.Instant;
import java.util.UUID;

/**
 * {@code engagement.contact_tags} — khách nào mang thẻ nào (UC017). Khoá chính kép
 * {@code (contact_id, tag_id)}. Gắn/gỡ làm trigger cập nhật {@code tags.usage_count}.
 *
 * <p>Gắn thẻ đi qua {@code INSERT … ON CONFLICT DO NOTHING} ở {@code TagRepository} chứ không qua
 * {@code persist()} — xem lý do ở đó. Entity này dùng để đọc và xoá.
 */
@Entity
@IdClass(ContactTag.Key.class)
@Table(name = "contact_tags", schema = "engagement")
public class ContactTag {

    /** Khoá chính kép — JPA bắt buộc có constructor rỗng, {@code equals} và {@code hashCode}. */
    public static class Key implements Serializable {
        private UUID contactId;
        private UUID tagId;

        protected Key() {
        }

        public Key(UUID contactId, UUID tagId) {
            this.contactId = contactId;
            this.tagId = tagId;
        }

        @Override
        public boolean equals(Object o) {
            return o instanceof Key k && java.util.Objects.equals(contactId, k.contactId)
                    && java.util.Objects.equals(tagId, k.tagId);
        }

        @Override
        public int hashCode() {
            return java.util.Objects.hash(contactId, tagId);
        }
    }

    @Id
    @Column(name = "contact_id", nullable = false, updatable = false)
    private UUID contactId;

    @Id
    @Column(name = "tag_id", nullable = false, updatable = false)
    private UUID tagId;

    @Column(name = "tenant_id", nullable = false, updatable = false)
    private UUID tenantId;

    @Column(name = "tagged_by", updatable = false)
    private UUID taggedBy;

    @Column(name = "tagged_at", nullable = false, updatable = false)
    private Instant taggedAt;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @Column(name = "updated_at", nullable = false, updatable = false)
    private Instant updatedAt;

    protected ContactTag() {
        // JPA yêu cầu constructor không tham số
    }

    public UUID getContactId() { return contactId; }
    public UUID getTagId() { return tagId; }
    public UUID getTenantId() { return tenantId; }
    public UUID getTaggedBy() { return taggedBy; }
    public Instant getTaggedAt() { return taggedAt; }
}
