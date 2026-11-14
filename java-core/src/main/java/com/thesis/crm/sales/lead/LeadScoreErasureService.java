package com.thesis.crm.sales.lead;

import com.thesis.crm.security.TenantTransactionScope;
import java.util.UUID;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC041 — xoá lịch sử điểm tiềm năng của một khách ({@code sales.lead_scores}, cột {@code features}
 * chứa vector đặc trưng có dữ liệu cá nhân). Quyền DELETE của {@code crm_app} trên bảng này giữ lại chính
 * vì việc này (V113 thu hồi UPDATE, giữ DELETE — ADR-0016). Lead vẫn còn (đặc tả UC041: "cơ hội tiềm năng
 * vẫn còn"), chỉ lịch sử điểm bị xoá.
 *
 * <p>Tách khỏi {@code LeadService} (phần UC030/UC032) vì đây là việc của luồng xoá dữ liệu, không phải
 * nghiệp vụ lead.
 */
@Service
public class LeadScoreErasureService {

    private final NamedParameterJdbcTemplate jdbc;
    private final TenantTransactionScope scope;

    public LeadScoreErasureService(NamedParameterJdbcTemplate jdbc, TenantTransactionScope scope) {
        this.jdbc = jdbc;
        this.scope = scope;
    }

    /** Số dòng đã xoá. LUỸ ĐẲNG — lần hai trả 0. */
    @Transactional
    public int deleteScoresOfContact(UUID tenantId, UUID contactId) {
        scope.apply(tenantId);
        return jdbc.update("DELETE FROM sales.lead_scores WHERE tenant_id = :t AND contact_id = :c",
                new MapSqlParameterSource("t", tenantId).addValue("c", contactId));
    }

    /** Số dòng sẽ bị xoá — cho màn xem trước (UC041 bước 5). */
    @Transactional(readOnly = true)
    public long countScoresOfContact(UUID tenantId, UUID contactId) {
        scope.apply(tenantId);
        Long n = jdbc.queryForObject(
                "SELECT count(*) FROM sales.lead_scores WHERE tenant_id = :t AND contact_id = :c",
                new MapSqlParameterSource("t", tenantId).addValue("c", contactId), Long.class);
        return n == null ? 0 : n;
    }
}
