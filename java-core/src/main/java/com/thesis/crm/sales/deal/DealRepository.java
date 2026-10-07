package com.thesis.crm.sales.deal;

import com.thesis.crm.sales.deal.DealDtos.HistoryDto;
import java.math.BigDecimal;
import java.sql.Array;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * SQL của UC033 + UC034. Mọi câu có {@code tenant_id = :t} tường minh — lớp thứ hai cạnh RLS. Gọi
 * trong transaction đã {@code TenantTransactionScope.apply()}.
 */
@Repository
public class DealRepository {

    public record PipelineRow(UUID id, String name, boolean isDefault, boolean isActive) {}

    public record StageRow(UUID id, UUID pipelineId, String name, int position, Integer probability,
                           boolean won, boolean lost, List<String> requiredFields, int dealCount,
                           BigDecimal dealValueTotal) {
        boolean closing() {
            return won || lost;
        }
    }

    public record DealRow(
            UUID id, UUID contactId, String contactName, UUID leadId, UUID pipelineId, UUID stageId,
            String stageName, String title, BigDecimal amount, String currency, LocalDate expectedCloseDate,
            boolean overdue, String status, String source, UUID ownerUserId, String ownerName,
            Instant stageChangedAt, Instant createdAt, String closeReason, Instant closedAt) {}

    public record Filter(UUID pipelineId, UUID stageId, String status, UUID ownerUserId, UUID contactId, int page,
                         int size) {}

    public record NewDeal(UUID contactId, UUID leadId, UUID pipelineId, UUID stageId, String title,
                          BigDecimal amount, LocalDate expectedCloseDate, String source, UUID ownerUserId) {}

    /** "Quá hạn" theo ngày ở Việt Nam — tính một chỗ cho mọi màn hình (hợp đồng {@code isOverdue}). */
    private static final String SELECT = """
            SELECT d.id, d.contact_id, coalesce(k.full_name, 'Khách chưa có tên') AS contact_name, d.lead_id,
                   d.pipeline_id, d.stage_id, s.name AS stage_name, d.title, d.amount, d.currency,
                   d.expected_close_date,
                   (d.status = 'OPEN' AND d.expected_close_date < (now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date)
                       AS overdue,
                   d.status, d.source, d.owner_user_id, u.full_name AS owner_name, d.stage_changed_at,
                   d.created_at, d.close_reason, d.closed_at
            FROM sales.deals d
            JOIN sales.deal_stages s ON s.id = d.stage_id AND s.tenant_id = d.tenant_id
            JOIN engagement.contacts k ON k.id = d.contact_id AND k.tenant_id = d.tenant_id
            LEFT JOIN platform.users u ON u.id = d.owner_user_id AND u.tenant_id = d.tenant_id
            """;

    private final NamedParameterJdbcTemplate jdbc;

    public DealRepository(NamedParameterJdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    // ── phễu ────────────────────────────────────────────────────────────────────

    public List<PipelineRow> pipelines(UUID tenantId, boolean includeInactive) {
        return jdbc.query("""
                SELECT id, name, is_default, is_active FROM sales.pipelines
                WHERE tenant_id = :t AND (:all OR is_active)
                ORDER BY is_default DESC, name""",
                new MapSqlParameterSource("t", tenantId).addValue("all", includeInactive),
                (rs, i) -> new PipelineRow(rs.getObject("id", UUID.class), rs.getString("name"),
                        rs.getBoolean("is_default"), rs.getBoolean("is_active")));
    }

    /** Giai đoạn kèm số deal và tổng giá trị — cột Kanban cần cả hai trước khi vẽ. */
    public List<StageRow> stagesWithTotals(UUID tenantId) {
        return jdbc.query("""
                SELECT s.id, s.pipeline_id, s.name, s.position, s.probability, s.is_won, s.is_lost,
                       s.required_fields, count(d.id)::int AS cnt, coalesce(sum(d.amount), 0) AS total
                FROM sales.deal_stages s
                LEFT JOIN sales.deals d ON d.stage_id = s.id AND d.tenant_id = s.tenant_id
                WHERE s.tenant_id = :t
                GROUP BY s.id
                ORDER BY s.pipeline_id, s.position""",
                new MapSqlParameterSource("t", tenantId), DealRepository::mapStage);
    }

    public Optional<StageRow> stage(UUID tenantId, UUID stageId) {
        return jdbc.query("""
                SELECT s.id, s.pipeline_id, s.name, s.position, s.probability, s.is_won, s.is_lost,
                       s.required_fields, 0 AS cnt, 0 AS total
                FROM sales.deal_stages s
                JOIN sales.pipelines p ON p.id = s.pipeline_id AND p.tenant_id = s.tenant_id AND p.is_active
                WHERE s.tenant_id = :t AND s.id = :id""",
                new MapSqlParameterSource("t", tenantId).addValue("id", stageId), DealRepository::mapStage)
                .stream().findFirst();
    }

    /** Giai đoạn MỞ đầu tiên của phễu mặc định — nơi deal mới vào khi không chỉ định. */
    public Optional<StageRow> defaultFirstStage(UUID tenantId) {
        return jdbc.query("""
                SELECT s.id, s.pipeline_id, s.name, s.position, s.probability, s.is_won, s.is_lost,
                       s.required_fields, 0 AS cnt, 0 AS total
                FROM sales.deal_stages s
                JOIN sales.pipelines p ON p.id = s.pipeline_id AND p.tenant_id = s.tenant_id
                WHERE s.tenant_id = :t AND p.is_default AND p.is_active AND NOT s.is_won AND NOT s.is_lost
                ORDER BY s.position LIMIT 1""",
                new MapSqlParameterSource("t", tenantId), DealRepository::mapStage)
                .stream().findFirst();
    }

    // ── deal: đọc ───────────────────────────────────────────────────────────────

    public List<DealRow> search(UUID tenantId, Filter f) {
        MapSqlParameterSource p = new MapSqlParameterSource("t", tenantId);
        String where = where(f, p);
        p.addValue("lim", f.size()).addValue("off", (long) f.page() * f.size());
        return jdbc.query(SELECT + where + " " + """
                 ORDER BY s.position, d.expected_close_date NULLS LAST, d.created_at DESC, d.id
                 LIMIT :lim OFFSET :off""", p, DealRepository::map);
    }

    public long count(UUID tenantId, Filter f) {
        MapSqlParameterSource p = new MapSqlParameterSource("t", tenantId);
        Long n = jdbc.queryForObject("SELECT count(*) FROM sales.deals d" + where(f, p), p, Long.class);
        return n == null ? 0 : n;
    }

    private static String where(Filter f, MapSqlParameterSource p) {
        StringBuilder w = new StringBuilder(" WHERE d.tenant_id = :t");
        if (f.pipelineId() != null) {
            w.append(" AND d.pipeline_id = :pipeline");
            p.addValue("pipeline", f.pipelineId());
        }
        if (f.stageId() != null) {
            w.append(" AND d.stage_id = :stage");
            p.addValue("stage", f.stageId());
        }
        if (f.status() != null) {
            w.append(" AND d.status = :status");
            p.addValue("status", f.status());
        }
        if (f.ownerUserId() != null) {
            w.append(" AND d.owner_user_id = :owner");
            p.addValue("owner", f.ownerUserId());
        }
        if (f.contactId() != null) {
            w.append(" AND d.contact_id = :contact");
            p.addValue("contact", f.contactId());
        }
        return w.toString();
    }

    public Optional<DealRow> find(UUID tenantId, UUID dealId) {
        return jdbc.query(SELECT + " WHERE d.tenant_id = :t AND d.id = :id",
                new MapSqlParameterSource("t", tenantId).addValue("id", dealId), DealRepository::map)
                .stream().findFirst();
    }

    public boolean lock(UUID tenantId, UUID dealId) {
        return !jdbc.queryForList("SELECT id FROM sales.deals WHERE tenant_id = :t AND id = :id FOR UPDATE",
                new MapSqlParameterSource("t", tenantId).addValue("id", dealId), UUID.class).isEmpty();
    }

    /** Số deal ĐANG MỞ của khách — UC033: có thì cảnh báo, không chặn. */
    public int openDealsOfContact(UUID tenantId, UUID contactId) {
        Integer n = jdbc.queryForObject("""
                SELECT count(*)::int FROM sales.deals WHERE tenant_id = :t AND contact_id = :c AND status = 'OPEN'""",
                new MapSqlParameterSource("t", tenantId).addValue("c", contactId), Integer.class);
        return n == null ? 0 : n;
    }

    public List<HistoryDto> history(UUID tenantId, UUID dealId) {
        return jdbc.query("""
                SELECT h.from_stage_id, f.name AS from_name, h.to_stage_id, t2.name AS to_name,
                       h.duration_seconds, u.full_name AS by_name, h.changed_at
                FROM sales.deal_stage_history h
                JOIN sales.deal_stages t2 ON t2.id = h.to_stage_id AND t2.tenant_id = h.tenant_id
                LEFT JOIN sales.deal_stages f ON f.id = h.from_stage_id AND f.tenant_id = h.tenant_id
                LEFT JOIN platform.users u ON u.id = h.changed_by AND u.tenant_id = h.tenant_id
                WHERE h.tenant_id = :t AND h.deal_id = :id
                ORDER BY h.changed_at, h.id""",
                new MapSqlParameterSource("t", tenantId).addValue("id", dealId),
                (rs, i) -> {
                    long dur = rs.getLong("duration_seconds");
                    Long duration = rs.wasNull() ? null : dur;
                    return new HistoryDto(rs.getObject("from_stage_id", UUID.class), rs.getString("from_name"),
                            rs.getObject("to_stage_id", UUID.class), rs.getString("to_name"), duration,
                            rs.getString("by_name"), instant(rs, "changed_at"));
                });
    }

    // ── deal: ghi ───────────────────────────────────────────────────────────────

    public UUID insert(UUID tenantId, NewDeal d) {
        return jdbc.queryForObject("""
                INSERT INTO sales.deals (tenant_id, lead_id, contact_id, pipeline_id, stage_id, title, status, source,
                                         amount, currency, expected_close_date, owner_user_id)
                VALUES (:t, :lead, :contact, :pipeline, :stage, :title, 'OPEN', :source,
                        :amount, 'VND', :date, :owner)
                RETURNING id""",
                new MapSqlParameterSource("t", tenantId).addValue("lead", d.leadId()).addValue("contact", d.contactId())
                        .addValue("pipeline", d.pipelineId()).addValue("stage", d.stageId())
                        .addValue("title", d.title()).addValue("source", d.source()).addValue("amount", d.amount())
                        .addValue("date", d.expectedCloseDate()).addValue("owner", d.ownerUserId()), UUID.class);
    }

    public void updateFields(UUID tenantId, UUID dealId, String title, BigDecimal amount, LocalDate date, UUID owner) {
        jdbc.update("""
                UPDATE sales.deals SET title = :title, amount = :amount, expected_close_date = :date,
                       owner_user_id = :owner
                WHERE tenant_id = :t AND id = :id""",
                new MapSqlParameterSource("t", tenantId).addValue("id", dealId).addValue("title", title)
                        .addValue("amount", amount).addValue("date", date).addValue("owner", owner));
    }

    /** Đổi giai đoạn và trạng thái đóng/mở trong MỘT câu — ck_deals_closed không bao giờ thấy trạng thái lưng chừng. */
    public void moveStage(UUID tenantId, UUID dealId, UUID stageId, String status, String closeReason, UUID owner) {
        jdbc.update("""
                UPDATE sales.deals SET stage_id = :stage, status = :status, stage_changed_at = now(),
                       closed_at = CASE WHEN :status = 'OPEN' THEN NULL ELSE now() END,
                       close_reason = :reason, owner_user_id = :owner
                WHERE tenant_id = :t AND id = :id""",
                new MapSqlParameterSource("t", tenantId).addValue("id", dealId).addValue("stage", stageId)
                        .addValue("status", status).addValue("reason", closeReason).addValue("owner", owner));
    }

    /** Đổi lý do thua khi deal vẫn ở cột Thua — không đụng mốc vào giai đoạn, không sinh dòng lịch sử. */
    public void updateCloseReason(UUID tenantId, UUID dealId, String reason) {
        jdbc.update("UPDATE sales.deals SET close_reason = :reason WHERE tenant_id = :t AND id = :id",
                new MapSqlParameterSource("t", tenantId).addValue("id", dealId).addValue("reason", reason));
    }

    /** Ghi lịch sử; {@code from = null} là dòng tạo deal. Thời gian ở giai đoạn trước tính bằng giây. */
    public void insertHistory(UUID tenantId, UUID dealId, UUID fromStageId, UUID toStageId, Instant enteredFromAt,
                              UUID changedBy) {
        jdbc.update("""
                INSERT INTO sales.deal_stage_history (tenant_id, deal_id, from_stage_id, to_stage_id, duration_seconds,
                                                      changed_by)
                VALUES (:t, :deal, :from, :to,
                        CASE WHEN CAST(:from AS uuid) IS NULL THEN NULL
                             ELSE greatest(0, floor(extract(epoch FROM now() - CAST(:entered AS timestamptz))))::bigint
                        END,
                        :by)""",
                new MapSqlParameterSource("t", tenantId).addValue("deal", dealId).addValue("from", fromStageId)
                        .addValue("to", toStageId)
                        .addValue("entered", enteredFromAt == null ? null : Timestamp.from(enteredFromAt))
                        .addValue("by", changedBy));
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private static StageRow mapStage(ResultSet rs, int i) throws SQLException {
        int prob = rs.getInt("probability");
        Integer probability = rs.wasNull() ? null : prob;
        Array arr = rs.getArray("required_fields");
        List<String> required = arr == null ? List.of() : Arrays.asList((String[]) arr.getArray());
        return new StageRow(rs.getObject("id", UUID.class), rs.getObject("pipeline_id", UUID.class),
                rs.getString("name"), rs.getInt("position"), probability, rs.getBoolean("is_won"),
                rs.getBoolean("is_lost"), required, rs.getInt("cnt"), rs.getBigDecimal("total"));
    }

    private static DealRow map(ResultSet rs, int i) throws SQLException {
        return new DealRow(rs.getObject("id", UUID.class), rs.getObject("contact_id", UUID.class),
                rs.getString("contact_name"), rs.getObject("lead_id", UUID.class),
                rs.getObject("pipeline_id", UUID.class), rs.getObject("stage_id", UUID.class),
                rs.getString("stage_name"), rs.getString("title"), rs.getBigDecimal("amount"),
                rs.getString("currency"), rs.getObject("expected_close_date", LocalDate.class),
                rs.getBoolean("overdue"), rs.getString("status"), rs.getString("source"),
                rs.getObject("owner_user_id", UUID.class), rs.getString("owner_name"),
                instant(rs, "stage_changed_at"), instant(rs, "created_at"), rs.getString("close_reason"),
                instant(rs, "closed_at"));
    }

    private static Instant instant(ResultSet rs, String col) throws SQLException {
        Timestamp ts = rs.getTimestamp(col);
        return ts == null ? null : ts.toInstant();
    }
}
