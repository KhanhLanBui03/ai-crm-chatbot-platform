package com.thesis.crm.security;

import jakarta.persistence.EntityManager;
import jakarta.persistence.EntityManagerFactory;
import jakarta.persistence.EntityTransaction;
import org.springframework.orm.jpa.EntityManagerHolder;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.transaction.CannotCreateTransactionException;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/**
 * Đặt biến phiên {@code app.tenant_id} NGAY KHI mở mỗi transaction — ADR-0001, bề mặt T1.
 *
 * <p><b>Vì sao không phải một servlet filter</b> như README ghi ({@code TenantContextFilter}):
 * {@code SET LOCAL} chỉ sống trong transaction đang mở, mà filter chạy TRƯỚC khi có transaction
 * nào. Đặt ở filter bằng {@code SET} (không LOCAL) thì giá trị bám vào kết nối, kết nối quay về
 * pool, và request kế tiếp của tenant khác mượn đúng kết nối đó — rò rỉ chéo tenant, đúng ca (d)
 * mà {@code ai-service/tests/test_rls.py} đã chặn. Móc vào {@code doBegin} thì mọi
 * {@code @Transactional} đều có tenant, không service nào phải nhớ gọi gì.
 *
 * <p>{@code set_config(…, true)} chứ không {@code SET LOCAL}: {@code SET} không nhận tham số bind.
 * Tham số thứ ba {@code true} chính là phần "LOCAL" — hết transaction là biến mất.
 *
 * <p>Không có tenant (job nền, phát outbox) thì KHÔNG đặt gì: mọi truy vấn chạm bảng có RLS khi
 * đó nổ {@code 42501} từ {@code platform.current_tenant()} (V101) — fail-closed. Hai bảng hạ
 * tầng không bật RLS ({@code outbox_events}, {@code processed_events}) vẫn chạy được.
 */
public class TenantAwareJpaTransactionManager extends JpaTransactionManager {

    private static final String SQL_DAT_TENANT = "select set_config('app.tenant_id', :tenant, true)";

    public TenantAwareJpaTransactionManager(EntityManagerFactory emf) {
        super(emf);
    }

    @Override
    protected void doBegin(Object transaction, TransactionDefinition definition) {
        super.doBegin(transaction, definition);
        TenantContext.currentTenantId().ifPresent(tenant -> datTenant(transaction, tenant.toString()));
    }

    private void datTenant(Object transaction, String tenant) {
        EntityManagerHolder holder =
                (EntityManagerHolder) TransactionSynchronizationManager.getResource(obtainEntityManagerFactory());
        EntityManager em = holder.getEntityManager();
        try {
            em.createNativeQuery(SQL_DAT_TENANT).setParameter("tenant", tenant).getSingleResult();
        } catch (RuntimeException ex) {
            // doBegin ném sau khi transaction đã mở thì lớp cha KHÔNG dọn giúp: phải tự rollback
            // và trả EntityManager, nếu không kết nối kẹt lại ngoài pool.
            EntityTransaction tx = em.getTransaction();
            if (tx.isActive()) {
                tx.rollback();
            }
            doCleanupAfterCompletion(transaction);
            throw new CannotCreateTransactionException("Không đặt được app.tenant_id cho transaction", ex);
        }
    }
}
