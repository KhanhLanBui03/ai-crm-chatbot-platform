package com.thesis.crm.platform.repository;

import com.thesis.crm.platform.dto.LoginIdentityProjection;
import com.thesis.crm.platform.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface UserRepository extends JpaRepository<User, UUID> {

    @Query(value = "SELECT user_id, tenant_id, tenant_slug, tenant_status, password_hash, scope, status, " +
            "email_verified_at, failed_login_count, locked_until " +
            "FROM platform.find_login_identity(:email)", nativeQuery = true)
    Optional<LoginIdentityProjection> findLoginIdentity(@Param("email") String email);

    @Query(value = "SELECT platform.email_is_taken(:email)", nativeQuery = true)
    boolean existsByEmailAcrossSystem(@Param("email") String email);

    @Query(value = "SELECT platform.update_failed_login(:id, :count, :lockedUntil)", nativeQuery = true)
    boolean updateFailedLogin(@Param("id") UUID id, @Param("count") short count, @Param("lockedUntil") Instant lockedUntil);

    @Query(value = "SELECT platform.reset_failed_login(:id, :lastLoginAt)", nativeQuery = true)
    boolean resetFailedLoginAndSetLastLogin(@Param("id") UUID id, @Param("lastLoginAt") Instant lastLoginAt);

    @Query(value = "SELECT platform.activate_user(:id, :verifiedAt)", nativeQuery = true)
    boolean activateUser(@Param("id") UUID id, @Param("verifiedAt") Instant verifiedAt);

    @Query(value = "SELECT platform.verify_email(:userId)", nativeQuery = true)
    boolean verifyEmail(@Param("userId") UUID userId);

    @Query(value = "SELECT platform.reset_password(:email, :passwordHash)", nativeQuery = true)
    boolean resetPasswordByEmail(@Param("email") String email, @Param("passwordHash") String passwordHash);

    @Query("SELECT count(u) FROM User u WHERE u.tenantId = :tenantId AND u.status <> 'DISABLED' AND u.deletedAt IS NULL")
    long countActiveUsersByTenantId(@Param("tenantId") UUID tenantId);

    Optional<User> findByIdAndTenantIdAndDeletedAtIsNull(UUID id, UUID tenantId);

    boolean existsByTenantIdAndEmailIgnoreCaseAndDeletedAtIsNull(UUID tenantId, String email);

    @Query("SELECT u FROM User u WHERE u.tenantId = :tenantId AND u.deletedAt IS NULL " +
            "AND (:q IS NULL OR :q = '' OR LOWER(u.fullName) LIKE LOWER(CONCAT('%', :q, '%')) OR LOWER(u.email) LIKE LOWER(CONCAT('%', :q, '%'))) " +
            "AND (:status IS NULL OR :status = '' OR u.status = :status)")
    org.springframework.data.domain.Page<User> searchUsers(
            @Param("tenantId") UUID tenantId,
            @Param("q") String q,
            @Param("status") String status,
            org.springframework.data.domain.Pageable pageable
    );
}
