package com.thesis.crm.engagement.widget;

import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * SQL của luồng widget (UC009/UC010). Trừ {@link #resolveKey} (hàm SECURITY DEFINER, chạy trước khi
 * biết tenant), mọi câu đều gọi trong transaction đã {@code TenantTransactionScope.apply()} VÀ có
 * {@code tenant_id = :tenantId} tường minh — hai lớp bảo vệ như các repository UC016/UC017.
 */
@Repository
public class WidgetRepository {

    public record ChannelRow(UUID channelId, UUID tenantId, String configJson, String status) {}

    public record TenantState(String status, boolean hasLiveSubscription, String timezone,
                              String businessHoursJson, String name) {}

    public record IdentityRow(UUID id, UUID contactId) {}

    public record ConversationRow(UUID id, String status, Instant lastActivityAt) {}

    public record QuotaRow(UUID id, long used, long quota) {}

    public record MessageRow(UUID id, String senderType, String content, String metadataJson,
                             Instant sentAt) {}

    private final NamedParameterJdbcTemplate jdbc;

    public WidgetRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** Tra khoá công khai → kênh + tenant. Chạy được khi chưa đặt tenant (V112). */
    public Optional<ChannelRow> resolveKey(String widgetKey) {
        return jdbc.query(
                "SELECT channel_id, tenant_id, config::text AS config, status FROM engagement.resolve_widget_key(:k)",
                new MapSqlParameterSource("k", widgetKey),
                (rs, i) -> new ChannelRow(rs.getObject("channel_id", UUID.class),
                        rs.getObject("tenant_id", UUID.class), rs.getString("config"), rs.getString("status")))
                .stream().findFirst();
    }

    public Optional<ChannelRow> channel(UUID tenantId, UUID channelId) {
        return jdbc.query("""
                SELECT id, tenant_id, config::text AS config, status FROM engagement.channels
                WHERE tenant_id = :t AND id = :c AND type = 'WEB_WIDGET'
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", channelId),
                (rs, i) -> new ChannelRow(rs.getObject("id", UUID.class), rs.getObject("tenant_id", UUID.class),
                        rs.getString("config"), rs.getString("status")))
                .stream().findFirst();
    }

    /** Trạng thái doanh nghiệp + có thuê bao còn hiệu lực không (UC009 11.1). */
    public Optional<TenantState> tenantState(UUID tenantId) {
        return jdbc.query("""
                SELECT t.status, t.timezone, t.business_hours::text AS hours, t.name,
                       EXISTS (SELECT 1 FROM platform.tenant_subscriptions s
                               WHERE s.tenant_id = t.id
                                 AND s.status IN ('TRIALING','ACTIVE','PAST_DUE')) AS live
                FROM platform.tenants t WHERE t.id = :t
                """,
                new MapSqlParameterSource("t", tenantId),
                (rs, i) -> new TenantState(rs.getString("status"), rs.getBoolean("live"),
                        rs.getString("timezone"), rs.getString("hours"), rs.getString("name")))
                .stream().findFirst();
    }

    /**
     * Danh tính kênh của khách, KHOÁ dòng ({@code FOR UPDATE}) để hai tin gửi gần như cùng lúc của
     * một khách không mở hai hội thoại song song.
     */
    public Optional<IdentityRow> lockIdentity(UUID tenantId, UUID channelId, String externalUserId) {
        return jdbc.query("""
                SELECT id, contact_id FROM engagement.channel_identities
                WHERE tenant_id = :t AND channel_id = :c AND external_user_id = :e
                FOR UPDATE
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", channelId).addValue("e", externalUserId),
                (rs, i) -> new IdentityRow(rs.getObject("id", UUID.class), rs.getObject("contact_id", UUID.class)))
                .stream().findFirst();
    }

    /** Tạo danh tính; trùng (request song song) thì không làm gì — bên gọi khoá lại để đọc. */
    public void insertIdentityIfAbsent(UUID tenantId, UUID channelId, String externalUserId, String displayName) {
        jdbc.update("""
                INSERT INTO engagement.channel_identities (tenant_id, channel_id, external_user_id, display_name)
                VALUES (:t, :c, :e, :n)
                ON CONFLICT (tenant_id, channel_id, external_user_id) DO NOTHING
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", channelId)
                        .addValue("e", externalUserId).addValue("n", displayName));
    }

    /** Hồ sơ khách tên tạm, chưa đồng ý dữ liệu (UC016 vẫn tìm được nhờ trigger search_text). */
    /** Khách web này đã để lại thông tin (đã đồng ý) chưa — widget dựa vào đây để không hỏi lại. */
    public boolean visitorShared(UUID tenantId, UUID channelId, String externalUserId) {
        Boolean b = jdbc.query("""
                SELECT k.consent_granted FROM engagement.channel_identities i
                JOIN engagement.contacts k ON k.id = i.contact_id AND k.tenant_id = i.tenant_id
                WHERE i.tenant_id = :t AND i.channel_id = :c AND i.external_user_id = :e""",
                new MapSqlParameterSource("t", tenantId).addValue("c", channelId).addValue("e", externalUserId),
                rs -> rs.next() ? rs.getBoolean(1) : Boolean.FALSE);
        return Boolean.TRUE.equals(b);
    }

    /**
     * Khách tự để lại thông tin: tên chỉ thay khi hồ sơ còn tên tạm "Khách web #…" (không ghi đè tên nhân
     * viên đã sửa); SĐT/email chỉ điền vào ô trống; đồng ý dữ liệu → nguồn WIDGET. Trả các trường đã thực
     * sự được ghi.
     */
    public java.util.List<String> applyVisitorInfo(UUID tenantId, UUID contactId, String name, String phone,
                                                    String email) {
        return jdbc.query("""
                WITH cu AS (SELECT full_name, phone, email FROM engagement.contacts
                            WHERE tenant_id = :t AND id = :id FOR UPDATE)
                UPDATE engagement.contacts k SET
                    full_name = CASE WHEN CAST(:name AS varchar) IS NOT NULL
                                      AND (cu.full_name IS NULL OR cu.full_name LIKE 'Khách web #%')
                                     THEN :name ELSE k.full_name END,
                    phone = coalesce(k.phone, :phone),
                    email = coalesce(k.email, :email),
                    consent_granted = true, consent_at = now(), consent_source = 'WIDGET'
                FROM cu
                WHERE k.tenant_id = :t AND k.id = :id
                RETURNING (k.full_name IS DISTINCT FROM cu.full_name) AS doi_ten,
                          (k.phone IS DISTINCT FROM cu.phone) AS doi_sdt,
                          (k.email IS DISTINCT FROM cu.email) AS doi_email""",
                new MapSqlParameterSource("t", tenantId).addValue("id", contactId).addValue("name", name)
                        .addValue("phone", phone).addValue("email", email),
                rs -> {
                    java.util.List<String> out = new java.util.ArrayList<>();
                    if (rs.next()) {
                        if (rs.getBoolean("doi_ten")) {
                            out.add("fullName");
                        }
                        if (rs.getBoolean("doi_sdt")) {
                            out.add("phone");
                        }
                        if (rs.getBoolean("doi_email")) {
                            out.add("email");
                        }
                    }
                    return out;
                });
    }

    public UUID insertVisitorContact(UUID tenantId, String fullName) {
        return jdbc.queryForObject("""
                INSERT INTO engagement.contacts (tenant_id, full_name, primary_channel, last_contacted_at)
                VALUES (:t, :n, 'WEB_WIDGET', now()) RETURNING id
                """,
                new MapSqlParameterSource("t", tenantId).addValue("n", fullName), UUID.class);
    }

    public void linkIdentityContact(UUID tenantId, UUID identityId, UUID contactId) {
        jdbc.update("""
                UPDATE engagement.channel_identities SET contact_id = :k
                WHERE tenant_id = :t AND id = :i AND contact_id IS NULL
                """,
                new MapSqlParameterSource("t", tenantId).addValue("i", identityId).addValue("k", contactId));
    }

    public void touch(UUID tenantId, UUID identityId, UUID contactId) {
        MapSqlParameterSource p = new MapSqlParameterSource("t", tenantId).addValue("i", identityId)
                .addValue("k", contactId);
        jdbc.update("UPDATE engagement.channel_identities SET last_seen_at = now() WHERE tenant_id = :t AND id = :i", p);
        if (contactId != null) {
            jdbc.update("UPDATE engagement.contacts SET last_contacted_at = now() WHERE tenant_id = :t AND id = :k", p);
        }
    }

    public Optional<ConversationRow> latestConversation(UUID tenantId, UUID identityId) {
        return jdbc.query("""
                SELECT id, status, coalesce(last_message_at, created_at) AS last_at
                FROM engagement.conversations
                WHERE tenant_id = :t AND channel_identity_id = :i
                ORDER BY created_at DESC LIMIT 1
                """,
                new MapSqlParameterSource("t", tenantId).addValue("i", identityId),
                (rs, i) -> new ConversationRow(rs.getObject("id", UUID.class), rs.getString("status"),
                        rs.getTimestamp("last_at").toInstant()))
                .stream().findFirst();
    }

    /** Hội thoại gần nhất của khách theo mã khách trong token — dùng khi chưa khoá danh tính. */
    public Optional<ConversationRow> latestConversationOfVisitor(UUID tenantId, UUID channelId, String externalUserId) {
        return jdbc.query("""
                SELECT c.id, c.status, coalesce(c.last_message_at, c.created_at) AS last_at
                FROM engagement.conversations c
                JOIN engagement.channel_identities i ON i.id = c.channel_identity_id AND i.tenant_id = c.tenant_id
                WHERE c.tenant_id = :t AND i.channel_id = :c AND i.external_user_id = :e
                ORDER BY c.created_at DESC LIMIT 1
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", channelId).addValue("e", externalUserId),
                (rs, i) -> new ConversationRow(rs.getObject("id", UUID.class), rs.getString("status"),
                        rs.getTimestamp("last_at").toInstant()))
                .stream().findFirst();
    }

    public UUID insertConversation(UUID tenantId, UUID channelId, UUID identityId, UUID contactId, String subject) {
        return jdbc.queryForObject("""
                INSERT INTO engagement.conversations (tenant_id, channel_id, channel_identity_id, contact_id, subject)
                VALUES (:t, :c, :i, :k, :s) RETURNING id
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", channelId).addValue("i", identityId)
                        .addValue("k", contactId).addValue("s", subject),
                UUID.class);
    }

    /** Trạng thái hiện tại, KHOÁ dòng — để quyết định trong cùng transaction có còn được ghi trả lời AI không. */
    public Optional<String> lockConversationStatus(UUID tenantId, UUID conversationId) {
        return jdbc.query(
                "SELECT status FROM engagement.conversations WHERE tenant_id = :t AND id = :c FOR UPDATE",
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId),
                (rs, i) -> rs.getString(1)).stream().findFirst();
    }

    /** Chuyển cho nhân viên — chỉ khi AI đang giữ, để không ghi đè hội thoại đã có người nhận. */
    public boolean handoff(UUID tenantId, UUID conversationId, String reason) {
        return jdbc.update("""
                UPDATE engagement.conversations
                SET status = 'PENDING_AGENT', handover_at = now(), handover_reason = :r, queued_at = now()
                WHERE tenant_id = :t AND id = :c AND status = 'BOT_HANDLING'
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId).addValue("r", reason)) > 0;
    }

    /**
     * Bộ đếm hội thoại của thuê bao đang hiệu lực, KHOÁ dòng để hai hội thoại mới cùng lúc không
     * cùng lọt qua mức cuối cùng của hạn mức.
     */
    public Optional<QuotaRow> lockConversationQuota(UUID tenantId) {
        return jdbc.query("""
                SELECT u.id, u.used_value, u.quota_value
                FROM platform.usage_records u
                JOIN platform.tenant_subscriptions s ON s.id = u.subscription_id AND s.tenant_id = u.tenant_id
                WHERE u.tenant_id = :t AND u.metric = 'CONVERSATION'
                  AND s.status IN ('TRIALING','ACTIVE','PAST_DUE')
                ORDER BY s.period_start DESC LIMIT 1
                FOR UPDATE OF u
                """,
                new MapSqlParameterSource("t", tenantId),
                (rs, i) -> new QuotaRow(rs.getObject("id", UUID.class), rs.getLong("used_value"),
                        rs.getLong("quota_value")))
                .stream().findFirst();
    }

    public void incrementUsage(UUID tenantId, UUID usageId) {
        jdbc.update("""
                UPDATE platform.usage_records SET used_value = used_value + 1, last_calculated_at = now()
                WHERE tenant_id = :t AND id = :u
                """,
                new MapSqlParameterSource("t", tenantId).addValue("u", usageId));
    }

    /**
     * {@code clock_timestamp()} thay vì mặc định {@code now()}: hai tin ghi trong cùng transaction
     * (tin khách + tin hệ thống báo chuyển giao) phải có thứ tự thời gian phân biệt được.
     */
    public MessageRow insertMessage(UUID tenantId, UUID conversationId, String senderType, String direction,
                                    String content, String metadataJson) {
        return jdbc.queryForObject("""
                INSERT INTO engagement.messages
                    (tenant_id, conversation_id, sender_type, direction, content, metadata, delivery_status, sent_at)
                VALUES (:t, :c, :s, :d, :content, CAST(:m AS jsonb), 'DELIVERED', clock_timestamp())
                RETURNING id, sender_type, content, metadata::text AS metadata, sent_at
                """,
                new MapSqlParameterSource("t", tenantId).addValue("c", conversationId).addValue("s", senderType)
                        .addValue("d", direction).addValue("content", content).addValue("m", metadataJson),
                (rs, i) -> mapMessage(rs));
    }

    /** Tin của một hội thoại theo thứ tự thời gian; {@code after} để widget hỏi tin mới. */
    public List<MessageRow> messages(UUID tenantId, UUID conversationId, Instant after, int limit) {
        MapSqlParameterSource p = new MapSqlParameterSource("t", tenantId).addValue("c", conversationId)
                .addValue("lim", limit);
        String afterClause = "";
        if (after != null) {
            p.addValue("after", Timestamp.from(after));
            afterClause = " AND sent_at > :after";
        }
        // Lấy N tin MỚI NHẤT rồi đảo lại theo thời gian tăng dần
        return jdbc.query("""
                SELECT * FROM (
                    SELECT id, sender_type, content, metadata::text AS metadata, sent_at
                    FROM engagement.messages
                    WHERE tenant_id = :t AND conversation_id = :c AND content_type <> 'SYSTEM_NOTE'
                """ + afterClause + """
                    ORDER BY sent_at DESC LIMIT :lim
                ) x ORDER BY sent_at
                """, p, (rs, i) -> mapMessage(rs));
    }

    private static MessageRow mapMessage(java.sql.ResultSet rs) throws java.sql.SQLException {
        return new MessageRow(rs.getObject("id", UUID.class), rs.getString("sender_type"), rs.getString("content"),
                rs.getString("metadata"), rs.getTimestamp("sent_at").toInstant());
    }
}
