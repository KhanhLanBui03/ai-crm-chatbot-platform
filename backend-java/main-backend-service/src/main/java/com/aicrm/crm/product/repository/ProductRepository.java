package com.aicrm.crm.product.repository;

import com.aicrm.common.enums.ProductStatus;
import com.aicrm.crm.product.entity.Product;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ProductRepository extends JpaRepository<Product, Long> {
    List<Product> findByBusinessId(Long businessId);
    List<Product> findByBusinessIdAndStatus(Long businessId, ProductStatus status);
    Optional<Product> findByBusinessIdAndSku(Long businessId, String sku);
    Optional<Product> findBySku(String sku);
}
