package com.thesis.crm.security;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.file.Path;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.utility.DockerImageName;
import org.testcontainers.utility.MountableFile;

/**
 * {@link TenantTransactionScope} trên Postgres THẬT với role runtime {@code crm_app} — RLS và
 * {@code platform.current_tenant()} (V123) chỉ có ở Postgres.
 *
 * <p>Ca cần khoá: kết nối trong pool còn mang {@code app.is_platform_admin = 'true'} ở MỨC PHIÊN do
 * một request quản trị nền tảng trước đó để lại. {@code current_tenant()} khi đó trả NULL và policy
 * cho thấy MỌI tenant — request tenant tiếp theo lấy trúng kết nối ấy sẽ đọc dữ liệu người khác.
 */
@SpringBootTest
class TenantTransactionScopeIntegrationTest {

    static final PostgreSQLContainer<?> PG = new PostgreSQLContainer<>(
            DockerImageName.parse("pgvector/pgvector:pg16").asCompatibleSubstituteFor("postgres"))
            .withDatabaseName("thesis_crm")
            .withUsername("crm_owner")
            .withPassword("changeme")
            .withCopyFileToContainer(
                    MountableFile.forHostPath(Path.of("..", "scripts", "init-db.sql").toAbsolutePath()),
                    "/docker-entrypoint-initdb.d/00-init.sql");

    static {
        PG.start();
    }

    @DynamicPropertySource
    static void props(DynamicPropertyRegistry r) {
        r.add("spring.datasource.url", PG::getJdbcUrl);
        r.add("spring.datasource.username", () -> "crm_app");
        r.add("spring.datasource.password", () -> "changeme");
        r.add("spring.flyway.user", () -> "crm_owner");
        r.add("spring.flyway.password", () -> "changeme");
        r.add("eureka.client.enabled", () -> "false");
        r.add("crm.outbox.publisher.enabled", () -> "false");
    }

    @Autowired TenantTransactionScope tenantScope;
    @Autowired JdbcTemplate jdbc;
    @Autowired PlatformTransactionManager transactionManager;

    @Test
    void coPlatformAdminSotTuPhienTruocKhongMoKhoaMoiTenant() {
        UUID tenant = UUID.fromString("11111111-1111-1111-1111-111111111111");
        new TransactionTemplate(transactionManager).executeWithoutResult(tx -> {
            // Kết nối "bẩn": cờ đặt ở mức phiên (is_local = false), như AdminTenantService để lại.
            jdbc.queryForObject("SELECT set_config('app.is_platform_admin', 'true', false)", String.class);

            tenantScope.apply(tenant);

            assertThat(jdbc.queryForObject("SELECT platform.current_tenant()", UUID.class)).isEqualTo(tenant);
            // Rollback hoàn luôn SET mức phiên ở trên — kết nối về pool sạch, không ảnh hưởng test khác.
            tx.setRollbackOnly();
        });
    }
}
