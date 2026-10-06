package com.thesis.crm.security;

import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * Đặt {@code app.tenant_id} cho RLS TRONG transaction hiện tại — {@code set_config(..., true)}
 * tương đương {@code SET LOCAL}: tự hết hiệu lực khi transaction kết thúc, không rò sang request
 * khác đang dùng lại cùng kết nối trong pool.
 *
 * <p>Vì sao cần, dù đã có {@link TenantRlsFilter}: filter đặt biến ở mức phiên, NGOÀI transaction
 * (và {@code open-in-view: false}), nên không có gì bảo đảm kết nối của service là kết nối đã được
 * đặt biến. CLAUDE.md luật 3: "SET LOCAL app.tenant_id trong CÙNG transaction với truy vấn".
 *
 * <p>Gọi ở đầu mọi phương thức {@code @Transactional} chạm bảng có RLS. Gọi ngoài transaction là
 * lỗi lập trình — ném ngay thay vì âm thầm không có tác dụng.
 */
@Component
public class TenantTransactionScope {

    private final JdbcTemplate jdbcTemplate;

    public TenantTransactionScope(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public void apply(UUID tenantId) {
        if (tenantId == null) {
            throw new IllegalStateException("Thiếu tenantId — không bao giờ chạy truy vấn nghiệp vụ không có tenant.");
        }
        if (!TransactionSynchronizationManager.isActualTransactionActive()) {
            throw new IllegalStateException("TenantTransactionScope.apply() phải gọi bên trong @Transactional.");
        }
        jdbcTemplate.queryForObject(
                "SELECT set_config('app.tenant_id', ?, true)", String.class, tenantId.toString());
    }
}
