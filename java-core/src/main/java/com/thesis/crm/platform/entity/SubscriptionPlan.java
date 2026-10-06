package com.thesis.crm.platform.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "subscription_plans", schema = "platform")
public class SubscriptionPlan {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, length = 30, unique = true)
    private String code;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(name = "monthly_price_vnd", nullable = false, precision = 14, scale = 2)
    private BigDecimal monthlyPriceVnd;

    @Column(name = "conversation_quota", nullable = false)
    private int conversationQuota;

    @Column(name = "ai_token_quota", nullable = false)
    private long aiTokenQuota;

    @Column(name = "max_users", nullable = false)
    private int maxUsers;

    @Column(name = "max_documents", nullable = false)
    private int maxDocuments;

    @Column(name = "max_channels", nullable = false)
    private short maxChannels;

    @Column(name = "storage_mb", nullable = false)
    private int storageMb;

    @Column(name = "is_active", nullable = false)
    private boolean isActive = true;

    @Column(name = "sort_order", nullable = false)
    private short sortOrder;

    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    public SubscriptionPlan() {}

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public BigDecimal getMonthlyPriceVnd() { return monthlyPriceVnd; }
    public void setMonthlyPriceVnd(BigDecimal monthlyPriceVnd) { this.monthlyPriceVnd = monthlyPriceVnd; }

    public int getConversationQuota() { return conversationQuota; }
    public void setConversationQuota(int conversationQuota) { this.conversationQuota = conversationQuota; }

    public long getAiTokenQuota() { return aiTokenQuota; }
    public void setAiTokenQuota(long aiTokenQuota) { this.aiTokenQuota = aiTokenQuota; }

    public int getMaxUsers() { return maxUsers; }
    public void setMaxUsers(int maxUsers) { this.maxUsers = maxUsers; }

    public int getMaxDocuments() { return maxDocuments; }
    public void setMaxDocuments(int maxDocuments) { this.maxDocuments = maxDocuments; }

    public short getMaxChannels() { return maxChannels; }
    public void setMaxChannels(short maxChannels) { this.maxChannels = maxChannels; }

    public int getStorageMb() { return storageMb; }
    public void setStorageMb(int storageMb) { this.storageMb = storageMb; }

    public boolean isActive() { return isActive; }
    public void setActive(boolean active) { isActive = active; }

    public short getSortOrder() { return sortOrder; }
    public void setSortOrder(short sortOrder) { this.sortOrder = sortOrder; }

    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
}
