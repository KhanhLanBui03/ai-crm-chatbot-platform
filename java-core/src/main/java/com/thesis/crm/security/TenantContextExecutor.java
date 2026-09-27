package com.thesis.crm.security;

import jakarta.persistence.EntityManager;
import org.hibernate.Session;
import org.springframework.stereotype.Component;

import java.sql.PreparedStatement;
import java.util.UUID;

@Component
public class TenantContextExecutor {

    private final EntityManager entityManager;

    public TenantContextExecutor(EntityManager entityManager) {
        this.entityManager = entityManager;
    }

    public void setTenantContext(UUID tenantId) {
        if (tenantId != null) {
            Session session = entityManager.unwrap(Session.class);
            session.doWork(connection -> {
                try (PreparedStatement ps = connection.prepareStatement("SELECT set_config('app.tenant_id', ?, false)")) {
                    ps.setString(1, tenantId.toString());
                    ps.execute();
                }
            });
        }
    }

    public void setPlatformAdminContext() {
        Session session = entityManager.unwrap(Session.class);
        session.doWork(connection -> {
            try (PreparedStatement ps = connection.prepareStatement("SELECT set_config('app.is_platform_admin', 'true', false)")) {
                ps.execute();
            }
        });
    }

    public void clearPlatformAdminContext() {
        try {
            Session session = entityManager.unwrap(Session.class);
            session.doWork(connection -> {
                try (PreparedStatement ps = connection.prepareStatement("SELECT set_config('app.is_platform_admin', '', false)")) {
                    ps.execute();
                }
            });
        } catch (Exception ignored) {
        }
    }

    public void clearTenantContext() {
        try {
            Session session = entityManager.unwrap(Session.class);
            session.doWork(connection -> {
                try (PreparedStatement ps = connection.prepareStatement("SELECT set_config('app.tenant_id', '', false)")) {
                    ps.execute();
                }
            });
        } catch (Exception ignored) {
        }
    }
}
