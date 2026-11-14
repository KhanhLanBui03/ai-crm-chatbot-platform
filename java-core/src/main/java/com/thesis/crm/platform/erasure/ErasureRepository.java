package com.thesis.crm.platform.erasure;

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
 * UC041 — SQL của quy trình xoá dữ liệu cá nhân: bảng yêu cầu {@code platform.data_erasure_requests}
 * (V109) và các bảng đích phía CRM.
 *
 * <p>Vì sao một kho SQL chạm nhiều schema thay vì gọi qua service từng context: lượt xoá phía CRM phải là
 * MỘT transaction (ẩn danh danh bạ + che tin + gỡ liên kết lead cùng commit hoặc cùng rollback — đặc tả
 * 8.1 "tiến độ cho biết chính xác chỗ nào đã xong"), và các bảng đích chưa có thao tác tương ứng ở service
 * của context nào. Mọi câu lọc {@code tenant_id} tường minh (lớp thứ hai cạnh RLS); gọi trong transaction
 * đã {@code TenantTransactionScope.apply()}.
 *
 * <p>Phạm vi hội thoại của khách luôn là {@code conversations.contact_id = khách} — cùng một câu con cho
 * mọi bảng, nên xem trước và thực thi đếm trên đúng một tập.
 */
@Repository
public class ErasureRepository {

    /** Một dòng yêu cầu, đã nối tên khách và tên người xác minh. */
    public record RequestRow(UUID id, UUID contactId, String contactName, String requestedBy, String legalBasis,
                             String status, String itemsJson, UUID verifiedBy, String verifiedByName,
                             Instant verifiedAt, String externalNote, Instant requestedAt, Instant startedAt,
                             Instant completedAt) {}

    /** Trạng thái danh bạ — để chặn tạo yêu cầu cho hồ sơ đã ẩn danh hoặc đã gộp. */
    public record ContactRow(UUID id, String status) {}

    static final String REDACTED_TEXT = "[Nội dung đã xoá theo yêu cầu của chủ thể dữ liệu]";
    static final String ANONYMIZED_NAME = "Khách đã ẩn danh";

    private static final String CONV_OF_CONTACT =
            "SELECT id FROM engagement.conversations WHERE tenant_id = :t AND contact_id = :k";

    private static final String SELECT_REQUEST = """
            SELECT r.id, r.contact_id, k.full_name, r.requested_by, r.legal_basis, r.status, r.items::text,
                   r.identity_verified_by, u.full_name, r.identity_verified_at, r.external_systems_note,
                   r.requested_at, r.started_at, r.completed_at
            FROM platform.data_erasure_requests r
            LEFT JOIN engagement.contacts k ON k.id = r.contact_id AND k.tenant_id = r.tenant_id
            LEFT JOIN platform.users u ON u.id = r.identity_verified_by AND u.tenant_id = r.tenant_id
            """;

    private final NamedParameterJdbcTemplate jdbc;

    public ErasureRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    // ── yêu cầu ─────────────────────────────────────────────────────────────────

    public List<RequestRow> list(UUID tenantId, String status, int offset, int limit) {
        MapSqlParameterSource p = t(tenantId).addValue("o", offset).addValue("l", limit);
        String where = " WHERE r.tenant_id = :t" + (status == null ? "" : " AND r.status = :st");
        if (status != null) {
            p.addValue("st", status);
        }
        return jdbc.query(SELECT_REQUEST + where + " ORDER BY r.requested_at DESC, r.id OFFSET :o LIMIT :l", p,
                ErasureRepository::mapRequest);
    }

    public long count(UUID tenantId, String status) {
        MapSqlParameterSource p = t(tenantId);
        String where = " WHERE tenant_id = :t" + (status == null ? "" : " AND status = :st");
        if (status != null) {
            p.addValue("st", status);
        }
        Long n = jdbc.queryForObject("SELECT count(*) FROM platform.data_erasure_requests" + where, p, Long.class);
        return n == null ? 0 : n;
    }

    public Optional<RequestRow> find(UUID tenantId, UUID id) {
        return jdbc.query(SELECT_REQUEST + " WHERE r.tenant_id = :t AND r.id = :id", t(tenantId).addValue("id", id),
                ErasureRepository::mapRequest).stream().findFirst();
    }

    /** Khoá dòng yêu cầu: hai người cùng bấm "Thực thi" thì một người thắng, người kia thấy IN_PROGRESS. */
    public boolean lock(UUID tenantId, UUID id) {
        return !jdbc.queryForList("""
                SELECT id FROM platform.data_erasure_requests WHERE tenant_id = :t AND id = :id FOR UPDATE""",
                t(tenantId).addValue("id", id), UUID.class).isEmpty();
    }

    /** Khoá danh bạ — hai yêu cầu tạo cùng lúc cho một khách thì nối đuôi nhau, kiểm "đang mở" mới đúng. */
    public Optional<ContactRow> lockContact(UUID tenantId, UUID contactId) {
        return jdbc.query("""
                SELECT id, status FROM engagement.contacts
                WHERE tenant_id = :t AND id = :k AND deleted_at IS NULL FOR UPDATE""",
                t(tenantId).addValue("k", contactId),
                (rs, i) -> new ContactRow(rs.getObject(1, UUID.class), rs.getString(2))).stream().findFirst();
    }

    /** Như {@link #lockContact} nhưng chỉ đọc — cho màn xem trước. */
    public Optional<ContactRow> findContact(UUID tenantId, UUID contactId) {
        return jdbc.query("""
                SELECT id, status FROM engagement.contacts
                WHERE tenant_id = :t AND id = :k AND deleted_at IS NULL""",
                t(tenantId).addValue("k", contactId),
                (rs, i) -> new ContactRow(rs.getObject(1, UUID.class), rs.getString(2))).stream().findFirst();
    }

    /** Luồng phụ 2.1 — "đang xử lý" gồm cả yêu cầu chờ và yêu cầu hỏng dở chưa chạy lại xong. */
    public boolean hasOpenRequest(UUID tenantId, UUID contactId) {
        return Boolean.TRUE.equals(jdbc.queryForObject("""
                SELECT EXISTS (SELECT 1 FROM platform.data_erasure_requests
                               WHERE tenant_id = :t AND contact_id = :k
                                 AND status IN ('PENDING', 'IN_PROGRESS', 'PARTIALLY_FAILED'))""",
                t(tenantId).addValue("k", contactId), Boolean.class));
    }

    public UUID insert(UUID tenantId, UUID contactId, String requestedBy, String legalBasis, String itemsJson,
                       String externalNote) {
        return jdbc.queryForObject("""
                INSERT INTO platform.data_erasure_requests
                    (tenant_id, contact_id, requested_by, legal_basis, items, external_systems_note)
                VALUES (:t, :k, :by, :lb, CAST(:items AS jsonb), :note)
                RETURNING id""",
                t(tenantId).addValue("k", contactId).addValue("by", requestedBy).addValue("lb", legalBasis)
                        .addValue("items", itemsJson).addValue("note", externalNote),
                UUID.class);
    }

    /** UC041 bước 4 — người và thời điểm đi cùng nhau ({@code ck_erasure_verified}). */
    public void verify(UUID tenantId, UUID id, UUID userId) {
        jdbc.update("""
                UPDATE platform.data_erasure_requests
                SET identity_verified_by = :u, identity_verified_at = now()
                WHERE tenant_id = :t AND id = :id""",
                t(tenantId).addValue("id", id).addValue("u", userId));
    }

    /**
     * UC041 bước 8. Chưa xác minh thì {@code ck_erasure_gate} (V109) làm câu này HỎNG ngay ở CSDL — lớp
     * chặn thứ hai sau phép kiểm ở service (luồng phụ 3.1: "chặn ngay ở tầng cơ sở dữ liệu").
     */
    public void markInProgress(UUID tenantId, UUID id) {
        jdbc.update("""
                UPDATE platform.data_erasure_requests
                SET status = 'IN_PROGRESS', started_at = coalesce(started_at, now())
                WHERE tenant_id = :t AND id = :id""",
                t(tenantId).addValue("id", id));
    }

    public void finish(UUID tenantId, UUID id, String status, String itemsJson, String externalNote) {
        jdbc.update("""
                UPDATE platform.data_erasure_requests
                SET status = :st, items = CAST(:items AS jsonb),
                    external_systems_note = coalesce(:note, external_systems_note),
                    completed_at = CASE WHEN :st = 'COMPLETED' THEN now() ELSE NULL END
                WHERE tenant_id = :t AND id = :id""",
                t(tenantId).addValue("id", id).addValue("st", status).addValue("items", itemsJson)
                        .addValue("note", externalNote));
    }

    // ── phạm vi phía CRM ────────────────────────────────────────────────────────

    public List<UUID> conversationIds(UUID tenantId, UUID contactId) {
        return jdbc.queryForList(CONV_OF_CONTACT + " ORDER BY created_at", k(tenantId, contactId), UUID.class);
    }

    public long countIdentities(UUID tenantId, UUID contactId) {
        return n("SELECT count(*) FROM engagement.channel_identities WHERE tenant_id = :t AND contact_id = :k",
                tenantId, contactId);
    }

    public long countConversations(UUID tenantId, UUID contactId) {
        return n("SELECT count(*) FROM (" + CONV_OF_CONTACT + ") x", tenantId, contactId);
    }

    /** Tin chưa che, trừ câu hệ thống (câu mẫu "Cuộc trò chuyện đã kết thúc…" không chứa gì của khách). */
    public long countMessages(UUID tenantId, UUID contactId) {
        return n("SELECT count(*) FROM engagement.messages WHERE tenant_id = :t AND sender_type <> 'SYSTEM'"
                + " AND NOT is_redacted AND conversation_id IN (" + CONV_OF_CONTACT + ")", tenantId, contactId);
    }

    public long countNotes(UUID tenantId, UUID contactId) {
        return n("SELECT count(*) FROM engagement.contact_notes WHERE tenant_id = :t AND contact_id = :k",
                tenantId, contactId);
    }

    public long countLinkedLeads(UUID tenantId, UUID contactId) {
        return n("SELECT count(*) FROM sales.leads WHERE tenant_id = :t AND source_conversation_id IN ("
                + CONV_OF_CONTACT + ")", tenantId, contactId);
    }

    public long countLeadScores(UUID tenantId, UUID contactId) {
        return n("SELECT count(*) FROM sales.lead_scores WHERE tenant_id = :t AND contact_id = :k",
                tenantId, contactId);
    }

    // ── thực thi phía CRM ───────────────────────────────────────────────────────

    /**
     * Ẩn danh hoá thay cho xoá vật lý (đặc tả UC041, "Lưu ý"): xoá dòng danh bạ kéo sập các tham chiếu
     * lịch sử mà nghĩa vụ kế toán/kiểm toán vẫn cần (deal, lead, hội thoại). {@code status} và
     * {@code anonymized_at} đổi cùng một câu — {@code ck_contacts_anonymized}. {@code search_text} do
     * trigger tính lại từ các cột vừa xoá.
     */
    public int anonymizeContact(UUID tenantId, UUID contactId) {
        return jdbc.update("""
                UPDATE engagement.contacts
                SET full_name = :ten, email = NULL, phone = NULL, company = NULL, consent_marketing = false,
                    status = 'ANONYMIZED', anonymized_at = now()
                WHERE tenant_id = :t AND id = :k AND status <> 'ANONYMIZED'""",
                k(tenantId, contactId).addValue("ten", ANONYMIZED_NAME));
    }

    /** Tên hiển thị, ảnh, hồ sơ thô mà kênh (Zalo/Facebook/widget) gửi về. Giữ liên kết kênh ↔ khách. */
    public int anonymizeIdentities(UUID tenantId, UUID contactId) {
        return jdbc.update("""
                UPDATE engagement.channel_identities
                SET display_name = NULL, avatar_url = NULL, raw_profile = NULL
                WHERE tenant_id = :t AND contact_id = :k""", k(tenantId, contactId));
    }

    /**
     * Che nội dung (cờ {@code is_redacted}). Che CẢ tin của bot và nhân viên, không riêng tin khách: câu
     * trả lời hay nhắc lại tên, số điện thoại của khách. {@code metadata} (trích dẫn, đoạn trích tài liệu
     * riêng của khách) và {@code attachments} xoá theo. Tin hệ thống giữ — là câu mẫu.
     */
    public int redactMessages(UUID tenantId, UUID contactId) {
        return jdbc.update("""
                UPDATE engagement.messages
                SET content = :txt, is_redacted = true, metadata = '{}'::jsonb, attachments = '[]'::jsonb
                WHERE tenant_id = :t AND sender_type <> 'SYSTEM' AND NOT is_redacted
                  AND conversation_id IN (""" + CONV_OF_CONTACT + ")",
                k(tenantId, contactId).addValue("txt", REDACTED_TEXT));
    }

    /**
     * Bản tóm tắt UC026 chứa "thông tin khách đã cung cấp" — xoá cả năm cột cùng lúc
     * ({@code ck_conv_summary_complete}); dòng xem trước và tiêu đề là trích nội dung tin. Hội thoại giữ.
     */
    public int clearConversations(UUID tenantId, UUID contactId) {
        return jdbc.update("""
                UPDATE engagement.conversations
                SET summary = NULL, summary_data = NULL, summary_trigger = NULL, summary_model_version = NULL,
                    summarized_at = NULL, last_message_preview = NULL, subject = NULL
                WHERE tenant_id = :t AND contact_id = :k""", k(tenantId, contactId));
    }

    /** Hậu điều kiện UC041: "cơ hội tiềm năng vẫn còn nhưng mất liên kết về hội thoại nguồn". */
    public int unlinkLeads(UUID tenantId, UUID contactId) {
        return jdbc.update("UPDATE sales.leads SET source_conversation_id = NULL WHERE tenant_id = :t"
                + " AND source_conversation_id IN (" + CONV_OF_CONTACT + ")", k(tenantId, contactId));
    }

    /** Ghi chú nhân viên viết về khách — văn bản tự do, chứa dữ liệu cá nhân là điều thường gặp. */
    public int deleteNotes(UUID tenantId, UUID contactId) {
        return jdbc.update("DELETE FROM engagement.contact_notes WHERE tenant_id = :t AND contact_id = :k",
                k(tenantId, contactId));
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    private long n(String sql, UUID tenantId, UUID contactId) {
        Long v = jdbc.queryForObject(sql, k(tenantId, contactId), Long.class);
        return v == null ? 0 : v;
    }

    private static MapSqlParameterSource t(UUID tenantId) {
        return new MapSqlParameterSource("t", tenantId);
    }

    private static MapSqlParameterSource k(UUID tenantId, UUID contactId) {
        return t(tenantId).addValue("k", contactId);
    }

    private static RequestRow mapRequest(ResultSet rs, int i) throws SQLException {
        return new RequestRow(rs.getObject(1, UUID.class), rs.getObject(2, UUID.class), rs.getString(3),
                rs.getString(4), rs.getString(5), rs.getString(6), rs.getString(7), rs.getObject(8, UUID.class),
                rs.getString(9), instant(rs, 10), rs.getString(11), instant(rs, 12), instant(rs, 13),
                instant(rs, 14));
    }

    private static Instant instant(ResultSet rs, int col) throws SQLException {
        Timestamp ts = rs.getTimestamp(col);
        return ts == null ? null : ts.toInstant();
    }
}
