package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.thesis.crm.common.enums.ActorType;
import com.thesis.crm.common.enums.AuditSeverity;
import com.thesis.crm.common.enums.ConversationStatus;
import com.thesis.crm.common.enums.SenderType;
import com.thesis.crm.engagement.entity.Conversation;
import com.thesis.crm.engagement.entity.Message;
import com.thesis.crm.engagement.repository.ConversationRepository;
import com.thesis.crm.engagement.repository.MessageRepository;
import com.thesis.crm.platform.entity.AuditLog;
import com.thesis.crm.platform.repository.AuditLogRepository;
import com.thesis.crm.security.TenantTransactionScope;
import java.net.InetAddress;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Supplier;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Entity {@link Conversation}, {@link Message}, {@link AuditLog} khớp CSDL thật (Flyway + RLS, role
 * {@code crm_app}) và migration V135.
 *
 * <p>Context khởi động được đã là một phép thử: {@code ddl-auto: validate} từ chối Entity khai sai kiểu
 * cột. Các test dưới đây bắt những lỗi {@code validate} không bắt: cột trigger bị ghi đè, JSON đọc ra
 * sai dạng, RLS không lọc khi đi qua JPA.
 */
class EntityMappingIntegrationTest extends EngagementIntegrationTestBase {

    private static final UUID CHANNEL = UUID.randomUUID();
    private static boolean seeded;

    @Autowired TransactionTemplate tx;
    @Autowired TenantTransactionScope scope;
    @Autowired ConversationRepository conversations;
    @Autowired MessageRepository messages;
    @Autowired AuditLogRepository auditLogs;

    @BeforeEach
    void seedChannel() throws Exception {
        if (seeded) {
            return;
        }
        seeded = true;
        try (Connection c = owner()) {
            exec(c, "INSERT INTO engagement.channels (id, tenant_id, type, name, status) VALUES (?, ?, 'ZALO', 'Zalo', 'ACTIVE')",
                    CHANNEL, TENANT_A);
        }
    }

    @Test
    void luuVaDocHoiThoai_quaJpa_dungTrangThaiEnum() throws Exception {
        UUID conv = hoiThoaiMoi();

        Conversation doc = trongTenant(TENANT_A, () -> conversations.findByIdAndTenantId(conv, TENANT_A).orElseThrow());
        assertThat(doc.getStatus()).isEqualTo(ConversationStatus.BOT_HANDLING);
        assertThat(doc.getPriority()).isEqualTo("NORMAL");
        assertThat(doc.getMessageCount()).isZero();
    }

    @Test
    void doiTrangThai_khongDeSoTinDoTriggerVuaCong() throws Exception {
        UUID conv = hoiThoaiMoi();
        guiTin(conv, "Tin thứ nhất");

        // Nạp hội thoại (thấy 1 tin), giữa chừng có tin mới đến từ kết nối khác, rồi mới lưu trạng thái.
        trongTenant(TENANT_A, () -> {
            Conversation c = conversations.findByIdAndTenantId(conv, TENANT_A).orElseThrow();
            assertThat(c.getMessageCount()).isEqualTo(1);
            try (Connection o = owner()) {
                exec(o, """
                        INSERT INTO engagement.messages (tenant_id, conversation_id, sender_type, direction, content)
                        VALUES (?, ?, 'CUSTOMER', 'INBOUND', 'Tin đến giữa chừng')""", TENANT_A, conv);
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
            c.setStatus(ConversationStatus.PENDING_AGENT);
            c.markHandover("CUSTOMER_REQUEST", java.time.Instant.now());
            return conversations.saveAndFlush(c);
        });

        assertThat(motCot("SELECT message_count FROM engagement.conversations WHERE id = ?", conv)).isEqualTo("2");
        assertThat(motCot("SELECT last_message_preview FROM engagement.conversations WHERE id = ?", conv))
                .isEqualTo("Tin đến giữa chừng");
        assertThat(motCot("SELECT status FROM engagement.conversations WHERE id = ?", conv)).isEqualTo("PENDING_AGENT");
    }

    @Test
    void tinNhan_metadataJsonb_luuVaDocLaiDungDang() throws Exception {
        UUID conv = hoiThoaiMoi();
        UUID id = trongTenant(TENANT_A, () -> {
            Message m = new Message(TENANT_A, conv, SenderType.BOT, null, "OUTBOUND", "Giá gói Tăng trưởng là 1.490.000đ.");
            m.setMetadata(Map.of("citations", List.of(Map.of("chunkId", "c-1", "score", 0.91)), "feedback", "UP"));
            return messages.saveAndFlush(m).getId();
        });

        assertThat(motCot("SELECT jsonb_typeof(metadata) FROM engagement.messages WHERE id = ?", id)).isEqualTo("object");
        assertThat(motCot("SELECT metadata->>'feedback' FROM engagement.messages WHERE id = ?", id)).isEqualTo("UP");
        assertThat(motCot("SELECT jsonb_typeof(attachments) FROM engagement.messages WHERE id = ?", id)).isEqualTo("array");

        Message doc = trongTenant(TENANT_A, () -> messages.findByIdAndTenantId(id, TENANT_A).orElseThrow());
        assertThat(doc.getSenderType()).isEqualTo(SenderType.BOT);
        assertThat(doc.getMetadata()).containsEntry("feedback", "UP");
        // Phải là List của Java: mapper riêng của Hibernate từng trả scala.collection.List (HibernateJsonConfig)
        assertThat(doc.getMetadata().get("citations")).isInstanceOf(java.util.List.class);
        // Ngoài transaction đã đặt tenant: RLS báo lỗi ngay (fail-closed), không lặng lẽ trả rỗng hay trả hết
        assertThatThrownBy(() -> messages.findByTenantIdAndConversationIdOrderBySentAtAsc(TENANT_A, conv))
                .hasStackTraceContaining("app.tenant_id");
    }

    @Test
    void tinNhanVien_batBuocCoNguoiGui_tinKhachThiKhongDuocCo() {
        UUID conv = UUID.randomUUID();
        assertThatThrownBy(() -> new Message(TENANT_A, conv, SenderType.AGENT, null, "OUTBOUND", "x"))
                .isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> new Message(TENANT_A, conv, SenderType.CUSTOMER, USER_A, "INBOUND", "x"))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void doanhNghiepKhac_khongThayHoiThoaiQuaJpa() throws Exception {
        UUID conv = hoiThoaiMoi();
        // Cố tình KHÔNG lọc tenant trong câu — chỉ còn RLS chặn
        assertThat(trongTenant(TENANT_B, () -> conversations.findById(conv))).isEmpty();
        assertThat(trongTenant(TENANT_A, () -> conversations.findById(conv))).isPresent();
    }

    @Test
    void nhatKyKiemToan_luuDuJsonVaDiaChiIp_actorNguoiBatBuocCoUserId() throws Exception {
        UUID entity = UUID.randomUUID();
        trongTenant(TENANT_A, () -> auditLogs.saveAndFlush(
                new AuditLog(TENANT_A, ActorType.USER, USER_A, "CONVERSATION_CLOSED", "CONVERSATION", entity,
                        AuditSeverity.INFO)
                        .withData(Map.of("status", "AGENT_HANDLING"), Map.of("status", "CLOSED"))
                        .withRequest(diaChi("10.0.0.7"), "JUnit", "req-1")));

        List<AuditLog> ds = trongTenant(TENANT_A, () ->
                auditLogs.findByTenantIdAndEntityTypeAndEntityIdOrderByCreatedAtAsc(TENANT_A, "CONVERSATION", entity));
        assertThat(ds).hasSize(1);
        AuditLog a = ds.get(0);
        assertThat(a.getId()).isNotNull();
        assertThat(a.getActorType()).isEqualTo(ActorType.USER);
        assertThat(a.getAfterData()).containsEntry("status", "CLOSED");
        assertThat(a.getIpAddress().getHostAddress()).isEqualTo("10.0.0.7");

        assertThatThrownBy(() -> new AuditLog(TENANT_A, ActorType.USER, null, "X", "Y", null, null))
                .isInstanceOf(IllegalArgumentException.class);
        assertThat(new AuditLog(TENANT_A, ActorType.SYSTEM, null, "X", "Y", null, null).getSeverity())
                .isEqualTo(AuditSeverity.INFO);
    }

    @Test
    void v135_xoaHoiThoaiCoGhiChu_giuGhiChu_goLienKet() throws Exception {
        UUID conv = hoiThoaiMoi();
        UUID contact = UUID.fromString(motCot("SELECT contact_id FROM engagement.conversations WHERE id = ?", conv));
        UUID note = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, """
                    INSERT INTO engagement.contact_notes (id, tenant_id, contact_id, author_user_id, content, conversation_id)
                    VALUES (?, ?, ?, ?, 'Khách hẹn gọi lại thứ Hai', ?)""", note, TENANT_A, contact, USER_A, conv);
            exec(c, "DELETE FROM engagement.conversations WHERE id = ?", conv);
        }

        assertThat(motCot("SELECT count(*) FROM engagement.conversations WHERE id = ?", conv)).isEqualTo("0");
        assertThat(motCot("SELECT conversation_id FROM engagement.contact_notes WHERE id = ?", note)).isNull();
        assertThat(motCot("SELECT tenant_id FROM engagement.contact_notes WHERE id = ?", note)).isEqualTo(TENANT_A.toString());
    }

    // ── tiện ích ─────────────────────────────────────────────────────────────────

    private <T> T trongTenant(UUID tenantId, Supplier<T> viec) {
        return tx.execute(s -> {
            scope.apply(tenantId);
            return viec.get();
        });
    }

    private static UUID hoiThoaiMoi() throws Exception {
        UUID contact = UUID.randomUUID();
        UUID identity = UUID.randomUUID();
        UUID conv = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO engagement.contacts (id, tenant_id, full_name, primary_channel) VALUES (?, ?, 'Khách Entity', 'ZALO')",
                    contact, TENANT_A);
            exec(c, """
                    INSERT INTO engagement.channel_identities (id, tenant_id, channel_id, contact_id, external_user_id)
                    VALUES (?, ?, ?, ?, ?)""", identity, TENANT_A, CHANNEL, contact, "zl-" + identity);
            exec(c, """
                    INSERT INTO engagement.conversations (id, tenant_id, channel_id, channel_identity_id, contact_id)
                    VALUES (?, ?, ?, ?, ?)""", conv, TENANT_A, CHANNEL, identity, contact);
        }
        return conv;
    }

    private static void guiTin(UUID conv, String noiDung) throws Exception {
        try (Connection c = owner()) {
            exec(c, """
                    INSERT INTO engagement.messages (tenant_id, conversation_id, sender_type, direction, content)
                    VALUES (?, ?, 'CUSTOMER', 'INBOUND', ?)""", TENANT_A, conv, noiDung);
        }
    }

    private static InetAddress diaChi(String ip) {
        try {
            return InetAddress.getByName(ip);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    private static String motCot(String query, Object... args) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(query)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString(1) : null;
            }
        }
    }

    private static void exec(Connection c, String query, Object... args) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement(query)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            ps.executeUpdate();
        }
    }
}
