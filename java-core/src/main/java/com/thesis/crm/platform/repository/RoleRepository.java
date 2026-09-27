package com.thesis.crm.platform.repository;

import com.thesis.crm.platform.entity.Role;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface RoleRepository extends JpaRepository<Role, UUID> {
    Optional<Role> findByCodeAndTenantIdIsNull(String code);

    @Query(value = "SELECT r.* FROM platform.roles r " +
            "JOIN platform.user_roles ur ON ur.role_id = r.id " +
            "WHERE ur.user_id = :userId", nativeQuery = true)
    List<Role> findRolesByUserId(@Param("userId") UUID userId);

    @Query(value = "SELECT r.* FROM platform.roles r " +
            "WHERE r.tenant_id IS NULL OR r.tenant_id = :tenantId " +
            "ORDER BY r.code ASC", nativeQuery = true)
    List<Role> findAllByTenantIdOrSystem(@Param("tenantId") UUID tenantId);

    @Query(value = "SELECT COUNT(DISTINCT ur.user_id) FROM platform.user_roles ur " +
            "JOIN platform.users u ON u.id = ur.user_id " +
            "WHERE ur.role_id = :roleId AND ur.tenant_id = :tenantId AND u.deleted_at IS NULL", nativeQuery = true)
    long countUsersByRoleAndTenant(@Param("roleId") UUID roleId, @Param("tenantId") UUID tenantId);
}
