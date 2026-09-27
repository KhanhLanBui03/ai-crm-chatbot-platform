package com.thesis.crm.platform.repository;

import com.thesis.crm.platform.entity.UsageRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface UsageRecordRepository extends JpaRepository<UsageRecord, UUID> {
    List<UsageRecord> findBySubscriptionId(UUID subscriptionId);
    Optional<UsageRecord> findBySubscriptionIdAndMetric(UUID subscriptionId, String metric);
}
