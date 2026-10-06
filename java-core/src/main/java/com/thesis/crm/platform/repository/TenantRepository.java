package com.thesis.crm.platform.repository;

import com.thesis.crm.platform.entity.Tenant;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface TenantRepository extends JpaRepository<Tenant, UUID> {
    Optional<Tenant> findBySlug(String slug);

    @Query(value = "SELECT platform.slug_is_taken(:slug)", nativeQuery = true)
    boolean isSlugTaken(@Param("slug") String slug);

    @Query("SELECT t FROM Tenant t WHERE " +
            "(:q IS NULL OR :q = '' OR " +
            "LOWER(t.name) LIKE LOWER(CONCAT('%', :q, '%')) OR " +
            "LOWER(t.contactEmail) LIKE LOWER(CONCAT('%', :q, '%')) OR " +
            "LOWER(t.slug) LIKE LOWER(CONCAT('%', :q, '%')) OR " +
            "LOWER(t.industry) LIKE LOWER(CONCAT('%', :q, '%'))) AND " +
            "(:status IS NULL OR :status = '' OR t.status = :status)")
    Page<Tenant> searchTenants(
            @Param("q") String q,
            @Param("status") String status,
            Pageable pageable
    );
}
