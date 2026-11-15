package com.thesis.crm.engagement.inbox;

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
 * Năm cột tóm tắt của {@code engagement.conversations} (V107 {@code summary}, {@code summarized_at};
 * V114 {@code summary_data}, {@code summary_trigger}, {@code summary_model_version}) và trang tin nhắn
 * cho bề mặt nội bộ — UC026.
 *
 * <p>SQL thẳng chứ không qua Entity {@code Conversation}: Entity chưa map năm cột này và ràng buộc
 * {@code ck_conv_summary_complete} đòi năm cột đổi CÙNG một câu {@code UPDATE} — một câu SQL bảo đảm
 * điều đó trực tiếp. Mọi câu lọc {@code tenant_id} tường minh (lớp thứ hai cạnh RLS); gọi trong
 * transaction đã {@code TenantTransactionScope.apply()}.
 */
@Repository
public class SummaryRepository {

    /** Bản tóm tắt đang lưu. {@code stale}: đã có tin của người (không phải SYSTEM) sau thời điểm sinh. */
    public record SummaryRow(String dataJson, String trigger, String modelVersion, Instant summarizedAt,
                             boolean stale) {}

    /** Một tin cho ai-service — cũ trước. */
    public record MessageRow(String senderType, String content, Instant sentAt, boolean redacted) {}

    private final NamedParameterJdbcTemplate jdbc;

    public SummaryRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public boolean exists(UUID tenantId, UUID conversationId) {
        return Boolean.TRUE.equals(jdbc.queryForObject("""
                SELECT EXISTS (SELECT 1 FROM engagement.conversations WHERE tenant_id = :t AND id = :c)""",
                p(tenantId, conversationId), Boolean.class));
    }

    public long countMessages(UUID tenantId, UUID conversationId) {
        Long n = jdbc.queryForObject("""
                SELECT count(*) FROM engagement.messages WHERE tenant_id = :t AND conversation_id = :c""",
                p(tenantId, conversationId), Long.class);
        return n == null ? 0 : n;
    }

    /** Thứ tự đọc của hội thoại: {@code sent_at} rồi {@code id} — giống hộp thư, ổn định khi trùng giờ. */
    public List<MessageRow> messages(UUID tenantId, UUID conversationId, int offset, int limit) {
        return jdbc.query("""
                SELECT sender_type, content, sent_at, is_redacted
                FROM engagement.messages
                WHERE tenant_id = :t AND conversation_id = :c
                ORDER BY sent_at, id
                OFFSET :o LIMIT :l""",
                p(tenantId, conversationId).addValue("o", offset).addValue("l", limit),
                (rs, i) -> new MessageRow(rs.getString(1), rs.getString(2), instant(rs, 3), rs.getBoolean(4)));
    }

    /**
     * Ghi đè bản mới nhất (UC026 luồng phụ 4.1) — LUỸ ĐẲNG và không lùi: chỉ ghi khi bản đang lưu
     * không mới hơn bản gửi tới. Sự kiện {@code CLOSING} giao lại muộn (Kafka giao ít nhất một lần)
     * sau khi nhân viên đã bấm "Tóm tắt lại" thì không đè bản mới bằng bản cũ.
     *
     * @return số dòng đã ghi — 0 khi bản đang lưu mới hơn (hội thoại có tồn tại hay không thì nơi gọi
     *         kiểm bằng {@link #exists})
     */
    public int writeSummary(UUID tenantId, UUID conversationId, String dataJson, String trigger,
                            String modelVersion, Instant generatedAt, String summaryText) {
        return jdbc.update("""
                UPDATE engagement.conversations
                SET summary_data = CAST(:data AS jsonb), summary_trigger = :tr, summary_model_version = :mv,
                    summarized_at = :at, summary = :txt
                WHERE tenant_id = :t AND id = :c
                  AND (summarized_at IS NULL OR summarized_at <= :at)""",
                p(tenantId, conversationId)
                        .addValue("data", dataJson)
                        .addValue("tr", trigger)
                        .addValue("mv", modelVersion)
                        .addValue("at", Timestamp.from(generatedAt))
                        .addValue("txt", summaryText));
    }

    public Optional<SummaryRow> summary(UUID tenantId, UUID conversationId) {
        return jdbc.query("""
                SELECT c.summary_data::text, c.summary_trigger, c.summary_model_version, c.summarized_at,
                       EXISTS (SELECT 1 FROM engagement.messages m
                               WHERE m.tenant_id = c.tenant_id AND m.conversation_id = c.id
                                 AND m.sender_type <> 'SYSTEM' AND m.sent_at > c.summarized_at)
                FROM engagement.conversations c
                WHERE c.tenant_id = :t AND c.id = :c AND c.summarized_at IS NOT NULL""",
                p(tenantId, conversationId),
                (rs, i) -> new SummaryRow(rs.getString(1), rs.getString(2), rs.getString(3), instant(rs, 4),
                        rs.getBoolean(5)))
                .stream().findFirst();
    }

    private static MapSqlParameterSource p(UUID tenantId, UUID conversationId) {
        return new MapSqlParameterSource("t", tenantId).addValue("c", conversationId);
    }

    private static Instant instant(ResultSet rs, int col) throws SQLException {
        Timestamp ts = rs.getTimestamp(col);
        return ts == null ? null : ts.toInstant();
    }
}
