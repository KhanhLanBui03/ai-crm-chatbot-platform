package com.thesis.crm.engagement.widget;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.common.enums.ConversationStatus;
import com.thesis.crm.common.enums.SenderType;
import com.thesis.crm.engagement.entity.Channel;
import com.thesis.crm.engagement.entity.Contact;
import com.thesis.crm.engagement.entity.Conversation;
import com.thesis.crm.engagement.entity.Message;
import com.thesis.crm.platform.entity.Tenant;
import com.thesis.crm.platform.entity.UsageRecord;
import jakarta.persistence.EntityManager;
import jakarta.persistence.LockModeType;
import jakarta.persistence.TypedQuery;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Repository;

/**
 * Truy cập dữ liệu luồng widget (UC009/UC010) qua Entity (JPA). Mọi truy vấn chạy trong transaction đã
 * {@code TenantTransactionScope.apply()} VÀ lọc {@code tenantId} tường minh — hai lớp bảo vệ.
 *
 * <p><b>Hai câu cố ý giữ native SQL:</b>
 * <ul>
 *   <li>{@link #resolveKey} gọi hàm {@code SECURITY DEFINER} {@code engagement.resolve_widget_key} (V112) —
 *       chạy TRƯỚC khi biết tenant nên không thể đi qua Entity có RLS.</li>
 *   <li>{@link #insertIdentityIfAbsent} cần {@code ON CONFLICT DO NOTHING}: hai tin của cùng một khách gửi
 *       gần như cùng lúc, đi bằng {@code persist()} thì người sau vấp UNIQUE và hỏng cả transaction.</li>
 * </ul>
 *
 * <p>Hội thoại đọc bằng phép chiếu và sửa bằng {@code UPDATE} JPQL — lý do ở {@code InboxRepository}.
 * Giữ nguyên chữ ký các hàm từ bản SQL tay, nên {@code WidgetService} không phải đổi.
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

    private static final TypeReference<Map<String, Object>> MAP = new TypeReference<>() {};
    private static final List<String> THUE_BAO_HIEU_LUC = List.of("TRIALING", "ACTIVE", "PAST_DUE");

    private final EntityManager em;
    private final ObjectMapper json;

    public WidgetRepository(EntityManager em, ObjectMapper json) {
        this.em = em;
        this.json = json;
    }

    /** Tra khoá công khai → kênh + tenant. Chạy được khi chưa đặt tenant (V112). Native có chủ đích. */
    public Optional<ChannelRow> resolveKey(String widgetKey) {
        List<?> rows = em.createNativeQuery(
                        "SELECT channel_id, tenant_id, config::text, status FROM engagement.resolve_widget_key(:k)")
                .setParameter("k", widgetKey)
                .getResultList();
        return rows.stream().findFirst().map(o -> {
            Object[] r = (Object[]) o;
            return new ChannelRow((UUID) r[0], (UUID) r[1], (String) r[2], (String) r[3]);
        });
    }

    public Optional<ChannelRow> channel(UUID tenantId, UUID channelId) {
        return em.createQuery("""
                SELECT ch FROM Channel ch
                WHERE ch.tenantId = :t AND ch.id = :c AND ch.type = 'WEB_WIDGET'""", Channel.class)
                .setParameter("t", tenantId)
                .setParameter("c", channelId)
                .getResultStream().findFirst()
                .map(ch -> new ChannelRow(ch.getId(), ch.getTenantId(), toJson(ch.getConfig()), ch.getStatus()));
    }

    /** Trạng thái doanh nghiệp + có thuê bao còn hiệu lực không (UC009 11.1). */
    public Optional<TenantState> tenantState(UUID tenantId) {
        return em.createQuery("""
                SELECT t,
                       (SELECT count(s) FROM TenantSubscription s WHERE s.tenantId = t.id AND s.status IN :live)
                FROM Tenant t WHERE t.id = :t""", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("live", THUE_BAO_HIEU_LUC)
                .getResultStream().findFirst()
                .map(r -> {
                    Tenant t = (Tenant) r[0];
                    return new TenantState(t.getStatus(), ((Number) r[1]).longValue() > 0, t.getTimezone(),
                            t.getBusinessHours(), t.getName());
                });
    }

    /**
     * Danh tính kênh của khách, KHOÁ dòng ({@code FOR UPDATE}) để hai tin gửi gần như cùng lúc của
     * một khách không mở hai hội thoại song song.
     */
    public Optional<IdentityRow> lockIdentity(UUID tenantId, UUID channelId, String externalUserId) {
        // Khoá trước, đọc sau bằng phép chiếu: Entity đã nạp từ trước có thể giữ contact_id cũ
        em.createQuery("""
                SELECT i FROM ChannelIdentity i
                WHERE i.tenantId = :t AND i.channelId = :c AND i.externalUserId = :e""")
                .setParameter("t", tenantId)
                .setParameter("c", channelId)
                .setParameter("e", externalUserId)
                .setLockMode(LockModeType.PESSIMISTIC_WRITE)
                .getResultList();
        return em.createQuery("""
                SELECT i.id, i.contactId FROM ChannelIdentity i
                WHERE i.tenantId = :t AND i.channelId = :c AND i.externalUserId = :e""", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("c", channelId)
                .setParameter("e", externalUserId)
                .getResultStream().findFirst()
                .map(r -> new IdentityRow((UUID) r[0], (UUID) r[1]));
    }

    /** Tạo danh tính; trùng (request song song) thì không làm gì — bên gọi khoá lại để đọc. Native có chủ đích. */
    public void insertIdentityIfAbsent(UUID tenantId, UUID channelId, String externalUserId, String displayName) {
        em.createNativeQuery("""
                INSERT INTO engagement.channel_identities (tenant_id, channel_id, external_user_id, display_name)
                VALUES (:t, :c, :e, :n)
                ON CONFLICT (tenant_id, channel_id, external_user_id) DO NOTHING""")
                .setParameter("t", tenantId)
                .setParameter("c", channelId)
                .setParameter("e", externalUserId)
                .setParameter("n", displayName)
                .executeUpdate();
    }

    /** Khách web này đã để lại thông tin (đã đồng ý) chưa — widget dựa vào đây để không hỏi lại. */
    public boolean visitorShared(UUID tenantId, UUID channelId, String externalUserId) {
        return em.createQuery("""
                SELECT k.consentGranted FROM ChannelIdentity i
                JOIN Contact k ON k.id = i.contactId AND k.tenantId = i.tenantId
                WHERE i.tenantId = :t AND i.channelId = :c AND i.externalUserId = :e""", Boolean.class)
                .setParameter("t", tenantId)
                .setParameter("c", channelId)
                .setParameter("e", externalUserId)
                .getResultStream().findFirst().orElse(false);
    }

    /**
     * Khách tự để lại thông tin: tên chỉ thay khi hồ sơ còn tên tạm "Khách web #…" (không ghi đè tên nhân
     * viên đã sửa); SĐT/email chỉ điền vào ô trống; đồng ý dữ liệu → nguồn WIDGET. Trả các trường đã thực
     * sự được ghi.
     */
    public List<String> applyVisitorInfo(UUID tenantId, UUID contactId, String name, String phone, String email) {
        Contact k = em.find(Contact.class, contactId);
        if (k == null || !tenantId.equals(k.getTenantId())) {
            return List.of();
        }
        // Nạp lại TỪ CSDL kèm khoá dòng — bản trong bộ nhớ có thể đã cũ
        em.refresh(k, LockModeType.PESSIMISTIC_WRITE);
        List<String> doi = new ArrayList<>();
        String tenCu = k.getFullName();
        if (name != null && (tenCu == null || tenCu.startsWith("Khách web #")) && !name.equals(tenCu)) {
            k.setFullName(name);
            doi.add("fullName");
        }
        if (k.getPhone() == null && phone != null) {
            k.setPhone(phone);
            doi.add("phone");
        }
        if (k.getEmail() == null && email != null) {
            k.setEmail(email);
            doi.add("email");
        }
        k.setConsent(true, "WIDGET", Instant.now());
        em.flush();
        return doi;
    }

    public UUID insertVisitorContact(UUID tenantId, String fullName) {
        Contact k = new Contact();
        k.setTenantId(tenantId);
        k.setFullName(fullName);
        k.setPrimaryChannel("WEB_WIDGET");
        k.setLastContactedAt(Instant.now());
        em.persist(k);
        em.flush();
        return k.getId();
    }

    public void linkIdentityContact(UUID tenantId, UUID identityId, UUID contactId) {
        em.createQuery("""
                UPDATE ChannelIdentity i SET i.contactId = :k
                WHERE i.tenantId = :t AND i.id = :i AND i.contactId IS NULL""")
                .setParameter("t", tenantId)
                .setParameter("i", identityId)
                .setParameter("k", contactId)
                .executeUpdate();
    }

    public void touch(UUID tenantId, UUID identityId, UUID contactId) {
        em.createQuery("UPDATE ChannelIdentity i SET i.lastSeenAt = current_timestamp WHERE i.tenantId = :t AND i.id = :i")
                .setParameter("t", tenantId)
                .setParameter("i", identityId)
                .executeUpdate();
        if (contactId != null) {
            em.createQuery("UPDATE Contact k SET k.lastContactedAt = current_timestamp WHERE k.tenantId = :t AND k.id = :k")
                    .setParameter("t", tenantId)
                    .setParameter("k", contactId)
                    .executeUpdate();
        }
    }

    public Optional<ConversationRow> latestConversation(UUID tenantId, UUID identityId) {
        return em.createQuery("""
                SELECT c.id, c.status, coalesce(c.lastMessageAt, c.createdAt) FROM Conversation c
                WHERE c.tenantId = :t AND c.channelIdentityId = :i
                ORDER BY c.createdAt DESC""", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("i", identityId)
                .setMaxResults(1)
                .getResultStream().findFirst().map(WidgetRepository::conversationRow);
    }

    /** Hội thoại gần nhất của khách theo mã khách trong token — dùng khi chưa khoá danh tính. */
    public Optional<ConversationRow> latestConversationOfVisitor(UUID tenantId, UUID channelId, String externalUserId) {
        return em.createQuery("""
                SELECT c.id, c.status, coalesce(c.lastMessageAt, c.createdAt) FROM Conversation c
                JOIN ChannelIdentity i ON i.id = c.channelIdentityId AND i.tenantId = c.tenantId
                WHERE c.tenantId = :t AND i.channelId = :c AND i.externalUserId = :e
                ORDER BY c.createdAt DESC""", Object[].class)
                .setParameter("t", tenantId)
                .setParameter("c", channelId)
                .setParameter("e", externalUserId)
                .setMaxResults(1)
                .getResultStream().findFirst().map(WidgetRepository::conversationRow);
    }

    public UUID insertConversation(UUID tenantId, UUID channelId, UUID identityId, UUID contactId, String subject) {
        Conversation c = new Conversation(tenantId, channelId, identityId, contactId);
        c.setSubject(subject);
        em.persist(c);
        em.flush();
        return c.getId();
    }

    /** Trạng thái hiện tại, KHOÁ dòng — để quyết định trong cùng transaction có còn được ghi trả lời AI không. */
    public Optional<String> lockConversationStatus(UUID tenantId, UUID conversationId) {
        em.createQuery("SELECT c FROM Conversation c WHERE c.tenantId = :t AND c.id = :c")
                .setParameter("t", tenantId)
                .setParameter("c", conversationId)
                .setLockMode(LockModeType.PESSIMISTIC_WRITE)
                .getResultList();
        // Đọc trạng thái bằng phép chiếu sau khi đã khoá — không tin bản Entity trong bộ nhớ
        return em.createQuery("SELECT c.status FROM Conversation c WHERE c.tenantId = :t AND c.id = :c",
                        ConversationStatus.class)
                .setParameter("t", tenantId)
                .setParameter("c", conversationId)
                .getResultStream().findFirst().map(Enum::name);
    }

    /** Chuyển cho nhân viên — chỉ khi AI đang giữ, để không ghi đè hội thoại đã có người nhận. */
    public boolean handoff(UUID tenantId, UUID conversationId, String reason) {
        return em.createQuery("""
                UPDATE Conversation c
                SET c.status = :moi, c.handoverAt = current_timestamp, c.handoverReason = :r,
                    c.queuedAt = current_timestamp
                WHERE c.tenantId = :t AND c.id = :c AND c.status = :ai""")
                .setParameter("t", tenantId)
                .setParameter("c", conversationId)
                .setParameter("r", reason)
                .setParameter("moi", ConversationStatus.PENDING_AGENT)
                .setParameter("ai", ConversationStatus.BOT_HANDLING)
                .executeUpdate() > 0;
    }

    /**
     * Bộ đếm hội thoại của thuê bao đang hiệu lực, KHOÁ dòng để hai hội thoại mới cùng lúc không
     * cùng lọt qua mức cuối cùng của hạn mức.
     */
    public Optional<QuotaRow> lockConversationQuota(UUID tenantId) {
        Optional<UUID> id = em.createQuery("""
                SELECT u.id FROM UsageRecord u, TenantSubscription s
                WHERE s.id = u.subscriptionId AND s.tenantId = u.tenantId AND u.tenantId = :t
                  AND u.metric = 'CONVERSATION' AND s.status IN :live
                ORDER BY s.periodStart DESC""", UUID.class)
                .setParameter("t", tenantId)
                .setParameter("live", THUE_BAO_HIEU_LUC)
                .setMaxResults(1)
                .getResultStream().findFirst();
        return id.map(uid -> {
            UsageRecord u = em.find(UsageRecord.class, uid);
            // Khoá rồi mới đọc số đã dùng — đọc trước khi khoá là hai request cùng thấy "còn 1 lượt"
            em.refresh(u, LockModeType.PESSIMISTIC_WRITE);
            return new QuotaRow(u.getId(), u.getUsedValue(), u.getQuotaValue());
        });
    }

    public void incrementUsage(UUID tenantId, UUID usageId) {
        em.createQuery("""
                UPDATE UsageRecord u SET u.usedValue = u.usedValue + 1, u.lastCalculatedAt = current_timestamp
                WHERE u.tenantId = :t AND u.id = :u""")
                .setParameter("t", tenantId)
                .setParameter("u", usageId)
                .executeUpdate();
    }

    /**
     * Giờ gửi lấy giờ thật lúc ghi (như {@code clock_timestamp()} trước đây), không phải mốc đầu
     * transaction: hai tin ghi trong cùng transaction (tin khách + tin hệ thống báo chuyển giao) phải có
     * thứ tự thời gian phân biệt được.
     */
    public MessageRow insertMessage(UUID tenantId, UUID conversationId, String senderType, String direction,
                                    String content, String metadataJson) {
        Message m = new Message(tenantId, conversationId, SenderType.valueOf(senderType), null, direction, content);
        m.setMetadata(metadataJson == null ? new java.util.HashMap<>() : fromJson(metadataJson));
        m.setDeliveryStatus("DELIVERED");
        m.setSentAt(Instant.now());
        em.persist(m);
        em.flush(); // trigger cộng số tin của hội thoại chạy ngay tại đây
        return messageRow(m);
    }

    /** Tin của một hội thoại theo thứ tự thời gian; {@code after} để widget hỏi tin mới. */
    public List<MessageRow> messages(UUID tenantId, UUID conversationId, Instant after, int limit) {
        TypedQuery<Message> q = em.createQuery("SELECT m FROM Message m"
                        + " WHERE m.tenantId = :t AND m.conversationId = :c AND m.contentType <> 'SYSTEM_NOTE'"
                        + (after != null ? " AND m.sentAt > :after" : "")
                        + " ORDER BY m.sentAt DESC", Message.class)
                .setParameter("t", tenantId)
                .setParameter("c", conversationId)
                .setMaxResults(limit);
        if (after != null) {
            q.setParameter("after", after);
        }
        // Lấy N tin MỚI NHẤT rồi đảo lại theo thời gian tăng dần
        List<MessageRow> out = new ArrayList<>(q.getResultStream().map(this::messageRow).toList());
        Collections.reverse(out);
        return out;
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private static ConversationRow conversationRow(Object[] r) {
        return new ConversationRow((UUID) r[0], ((ConversationStatus) r[1]).name(), (Instant) r[2]);
    }

    private MessageRow messageRow(Message m) {
        return new MessageRow(m.getId(), m.getSenderType().name(), m.getContent(), toJson(m.getMetadata()),
                m.getSentAt());
    }

    private String toJson(Object value) {
        try {
            return json.writeValueAsString(Objects.requireNonNullElse(value, Map.of()));
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Không chuyển được JSON", e);
        }
    }

    private Map<String, Object> fromJson(String s) {
        try {
            return json.readValue(s, MAP);
        } catch (JsonProcessingException e) {
            throw new IllegalArgumentException("metadata không phải JSON object", e);
        }
    }
}
