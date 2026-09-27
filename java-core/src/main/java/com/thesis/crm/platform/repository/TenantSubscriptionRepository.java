package com.thesis.crm.platform.repository;

import com.thesis.crm.platform.entity.TenantSubscription;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface TenantSubscriptionRepository extends JpaRepository<TenantSubscription, UUID> {
    Optional<TenantSubscription> findFirstByTenantIdOrderByCreatedAtDesc(UUID tenantId);
}
