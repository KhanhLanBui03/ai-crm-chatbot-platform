package com.thesis.crm.engagement.repository;

import com.thesis.crm.engagement.entity.ContactNote;
import jakarta.persistence.EntityManager;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/**
 * {@code engagement.contact_notes} — UC017, qua Entity {@link ContactNote} (JPA).
 *
 * <p>Mọi truy vấn lọc {@code tenantId} ngay trong câu (lớp thứ hai cạnh RLS). Gọi trong transaction đã
 * {@code TenantTransactionScope.apply()} — ngoài đó RLS ném lỗi.
 *
 * <p>Giữ nguyên chữ ký các hàm từ bản SQL tay trước đây, nên service không phải đổi.
 */
@Repository
public class NoteRepository {

    /** Một dòng ghi chú kèm tên tác giả — service tự tính {@code canEdit}/{@code flaggedSensitive}. */
    public record NoteRow(
            UUID id, UUID contactId, String content, UUID conversationId, UUID authorUserId,
            String authorName, boolean pinned, Instant editedAt, Instant createdAt) {}

    /** Ghép tên tác giả: tác giả là người cùng doanh nghiệp, đã xoá thì tên rỗng. */
    private static final String SELECT = """
            SELECT new com.thesis.crm.engagement.repository.NoteRepository$NoteRow(
                       n.id, n.contactId, n.content, n.conversationId, n.authorUserId,
                       coalesce(u.fullName, ''), n.pinned, n.editedAt, n.createdAt)
            FROM ContactNote n
            LEFT JOIN User u ON u.id = n.authorUserId AND u.tenantId = n.tenantId
            """;

    private final EntityManager em;

    public NoteRepository(EntityManager em) {
        this.em = em;
    }

    /** Ghi chú chưa xoá của một khách: ghim trước, trong mỗi nhóm mới nhất trước. */
    public List<NoteRow> list(UUID tenantId, UUID contactId) {
        return em.createQuery(SELECT + """
                WHERE n.tenantId = :tenantId AND n.contactId = :contactId AND n.deletedAt IS NULL
                ORDER BY n.pinned DESC, n.createdAt DESC
                """, NoteRow.class)
                .setParameter("tenantId", tenantId)
                .setParameter("contactId", contactId)
                .getResultList();
    }

    public Optional<NoteRow> find(UUID tenantId, UUID contactId, UUID noteId) {
        return em.createQuery(SELECT + """
                WHERE n.tenantId = :tenantId AND n.contactId = :contactId AND n.id = :noteId
                  AND n.deletedAt IS NULL
                """, NoteRow.class)
                .setParameter("tenantId", tenantId)
                .setParameter("contactId", contactId)
                .setParameter("noteId", noteId)
                .getResultStream().findFirst();
    }

    public UUID insert(UUID tenantId, UUID contactId, UUID authorUserId, String content, UUID conversationId) {
        ContactNote note = new ContactNote(tenantId, contactId, authorUserId, content, conversationId);
        em.persist(note);
        em.flush(); // ghi ngay để lỗi ràng buộc nổ ở đây, đúng như INSERT trước đây
        return note.getId();
    }

    /** Đổi NỘI DUNG thì đặt {@code edited_at} — ghim không đi qua đây. */
    public void updateContent(UUID tenantId, UUID noteId, String content) {
        live(tenantId, noteId).ifPresent(n -> n.editContent(content, Instant.now()));
        em.flush();
    }

    public void updatePinned(UUID tenantId, UUID noteId, boolean pinned) {
        live(tenantId, noteId).ifPresent(n -> n.setPinned(pinned));
        em.flush();
    }

    public void softDelete(UUID tenantId, UUID noteId) {
        live(tenantId, noteId).ifPresent(n -> n.softDelete(Instant.now()));
        em.flush();
    }

    /** Hội thoại phải thuộc ĐÚNG khách này, cùng tenant — không gắn ghi chú sang hội thoại của người khác. */
    public boolean conversationBelongsToContact(UUID tenantId, UUID conversationId, UUID contactId) {
        return !em.createQuery("""
                SELECT c.id FROM Conversation c
                WHERE c.tenantId = :tenantId AND c.id = :conversationId AND c.contactId = :contactId
                """, UUID.class)
                .setParameter("tenantId", tenantId)
                .setParameter("conversationId", conversationId)
                .setParameter("contactId", contactId)
                .setMaxResults(1)
                .getResultList().isEmpty();
    }

    /** Ghi chú chưa xoá — sửa/ghim/xoá một ghi chú đã xoá là không làm gì, như câu UPDATE cũ. */
    private Optional<ContactNote> live(UUID tenantId, UUID noteId) {
        return em.createQuery("""
                SELECT n FROM ContactNote n
                WHERE n.tenantId = :tenantId AND n.id = :noteId AND n.deletedAt IS NULL
                """, ContactNote.class)
                .setParameter("tenantId", tenantId)
                .setParameter("noteId", noteId)
                .getResultStream().findFirst();
    }
}
