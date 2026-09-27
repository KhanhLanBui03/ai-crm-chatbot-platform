package com.thesis.crm.config;

import com.thesis.crm.security.TenantAwareJpaTransactionManager;
import jakarta.persistence.EntityManagerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.transaction.TransactionManagerCustomizers;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionManager;

/**
 * Thay transaction manager mặc định của Spring Boot bằng bản đặt {@code app.tenant_id} mỗi khi mở
 * transaction. Boot chỉ tạo bản của nó khi chưa có bean {@code TransactionManager} nào, nên khai
 * ở đây là đủ — không có hai transaction manager song song để lỡ dùng nhầm bản không có tenant.
 */
@Configuration
public class PersistenceConfig {

    @Bean
    public PlatformTransactionManager transactionManager(EntityManagerFactory emf,
            ObjectProvider<TransactionManagerCustomizers> customizers) {
        TenantAwareJpaTransactionManager tm = new TenantAwareJpaTransactionManager(emf);
        // Giữ nguyên các tuỳ chỉnh Boot vẫn áp cho bản mặc định (spring.transaction.*).
        // Ép kiểu để gọi bản customize(TransactionManager); bản nhận PlatformTransactionManager
        // đã deprecated từ Boot 3.2.
        customizers.ifAvailable(c -> c.customize((TransactionManager) tm));
        return tm;
    }
}
