package com.thesis.crm.engagement.repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * {@code engagement.contact_notes} — UC017. SQL tường minh, mọi câu có {@code tenant_id = :tenantId}
 * (lớp thứ hai cạnh RLS — xem {@link ContactQueryRepository}). Gọi trong transaction đã đặt tenant.
 */
@Repository
public class NoteRepository {

    /** Một dòng ghi chú kèm tên tác giả — service tự tính {@code canEdit}/{@code flaggedSensitive}. */
    public record NoteRow(
            UUID id, UUID contactId, String content, UUID conversationId, UUID authorUserId,
            String authorName, boolean pinned, Instant editedAt, Instant createdAt) {}

    private static final String SELECT = """
            SELECT n.id, n.contact_id, n.content, n.conversation_id, n.author_user_id,
                   coalesce(u.full_name, '') AS author_name, n.is_pinned, n.edited_at, n.created_at
            FROM engagement.contact_notes n
            LEFT JOIN platform.users u ON u.id = n.author_user_id AND u.tenant_id = n.tenant_id
            """;

    private final NamedParameterJdbcTemplate jdbc;

    public NoteRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** Ghi chú chưa xoá của một khách: ghim trước, trong mỗi nhóm mới nhất trước. */
    public List<NoteRow> list(UUID tenantId, UUID contactId) {
        return jdbc.query(SELECT + """
                WHERE n.tenant_id = :tenantId AND n.contact_id = :contactId AND n.deleted_at IS NULL
                ORDER BY n.is_pinned DESC, n.created_at DESC
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("contactId", contactId),
                NoteRepository::map);
    }

    public Optional<NoteRow> find(UUID tenantId, UUID contactId, UUID noteId) {
        return jdbc.query(SELECT + """
                WHERE n.tenant_id = :tenantId AND n.contact_id = :contactId AND n.id = :noteId
                  AND n.deleted_at IS NULL
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("contactId", contactId)
                        .addValue("noteId", noteId),
                NoteRepository::map).stream().findFirst();
    }

    public UUID insert(UUID tenantId, UUID contactId, UUID authorUserId, String content, UUID conversationId) {
        return jdbc.queryForObject("""
                INSERT INTO engagement.contact_notes (tenant_id, contact_id, author_user_id, content, conversation_id)
                VALUES (:tenantId, :contactId, :author, :content, :conversationId)
                RETURNING id
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("contactId", contactId)
                        .addValue("author", authorUserId).addValue("content", content)
                        .addValue("conversationId", conversationId),
                UUID.class);
    }

    /** Đổi NỘI DUNG thì đặt {@code edited_at} — ghim không đi qua đây. */
    public void updateContent(UUID tenantId, UUID noteId, String content) {
        jdbc.update("""
                UPDATE engagement.contact_notes SET content = :content, edited_at = now()
                WHERE tenant_id = :tenantId AND id = :noteId AND deleted_at IS NULL
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("noteId", noteId).addValue("content", content));
    }

    public void updatePinned(UUID tenantId, UUID noteId, boolean pinned) {
        jdbc.update("""
                UPDATE engagement.contact_notes SET is_pinned = :pinned
                WHERE tenant_id = :tenantId AND id = :noteId AND deleted_at IS NULL
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("noteId", noteId).addValue("pinned", pinned));
    }

    public void softDelete(UUID tenantId, UUID noteId) {
        jdbc.update("""
                UPDATE engagement.contact_notes SET deleted_at = now()
                WHERE tenant_id = :tenantId AND id = :noteId AND deleted_at IS NULL
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("noteId", noteId));
    }

    /** Hội thoại phải thuộc ĐÚNG khách này, cùng tenant — không gắn ghi chú sang hội thoại của người khác. */
    public boolean conversationBelongsToContact(UUID tenantId, UUID conversationId, UUID contactId) {
        Boolean ok = jdbc.queryForObject("""
                SELECT EXISTS (SELECT 1 FROM engagement.conversations
                                WHERE tenant_id = :tenantId AND id = :conversationId AND contact_id = :contactId)
                """,
                new MapSqlParameterSource("tenantId", tenantId).addValue("conversationId", conversationId)
                        .addValue("contactId", contactId),
                Boolean.class);
        return Boolean.TRUE.equals(ok);
    }

    private static NoteRow map(ResultSet rs, int i) throws SQLException {
        return new NoteRow(
                rs.getObject("id", UUID.class),
                rs.getObject("contact_id", UUID.class),
                rs.getString("content"),
                rs.getObject("conversation_id", UUID.class),
                rs.getObject("author_user_id", UUID.class),
                rs.getString("author_name"),
                rs.getBoolean("is_pinned"),
                instant(rs, "edited_at"),
                instant(rs, "created_at"));
    }

    private static Instant instant(ResultSet rs, String column) throws SQLException {
        Timestamp ts = rs.getTimestamp(column);
        return ts == null ? null : ts.toInstant();
    }
}
