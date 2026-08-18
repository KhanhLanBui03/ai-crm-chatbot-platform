package com.aicrm.crm.product.service;

import com.aicrm.common.enums.ProductStatus;
import com.aicrm.common.exception.BadRequestException;
import com.aicrm.common.exception.ResourceNotFoundException;
import com.aicrm.crm.product.dto.request.CreateProductRequest;
import com.aicrm.crm.product.dto.request.ProductSearchRequest;
import com.aicrm.crm.product.dto.request.UpdateProductRequest;
import com.aicrm.crm.product.dto.response.PriceResponse;
import com.aicrm.crm.product.dto.response.ProductDetailResponse;
import com.aicrm.crm.product.dto.response.ProductResponse;
import com.aicrm.crm.product.dto.response.StockResponse;
import com.aicrm.crm.product.entity.Product;
import com.aicrm.crm.product.repository.ProductRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class ProductService {

    @Autowired
    private ProductRepository productRepository;

    @Transactional
    public ProductResponse createProduct(CreateProductRequest request) {
        if (request.getBusinessId() == null) {
            throw new BadRequestException("Business ID must not be null");
        }
        if (request.getName() == null || request.getName().trim().isEmpty()) {
            throw new BadRequestException("Product name must not be empty");
        }
        if (request.getPrice() == null) {
            throw new BadRequestException("Product price must not be null");
        }

        // Check if SKU already exists for the business
        if (request.getSku() != null && !request.getSku().trim().isEmpty()) {
            if (productRepository.findByBusinessIdAndSku(request.getBusinessId(), request.getSku().trim()).isPresent()) {
                throw new BadRequestException("Product SKU already exists for this business");
            }
        }

        ProductStatus status = ProductStatus.ACTIVE;
        if (request.getStatus() != null) {
            try {
                status = ProductStatus.valueOf(request.getStatus().toUpperCase());
            } catch (IllegalArgumentException e) {
                throw new BadRequestException("Invalid status. Supported: ACTIVE, OUT_OF_STOCK, DISCONTINUED");
            }
        }

        Product product = Product.builder()
                .businessId(request.getBusinessId())
                .name(request.getName().trim())
                .sku(request.getSku() != null ? request.getSku().trim() : null)
                .description(request.getDescription())
                .price(request.getPrice())
                .stockQuantity(request.getStockQuantity() != null ? request.getStockQuantity() : 0)
                .status(status)
                .build();

        product = productRepository.save(product);
        return mapToProductResponse(product);
    }

    @Transactional
    public ProductResponse updateProduct(Long id, UpdateProductRequest request) {
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Product not found with id: " + id));

        if (request.getName() != null && !request.getName().trim().isEmpty()) {
            product.setName(request.getName().trim());
        }
        if (request.getSku() != null) {
            String newSku = request.getSku().trim();
            if (!newSku.equalsIgnoreCase(product.getSku())) {
                if (productRepository.findByBusinessIdAndSku(product.getBusinessId(), newSku).isPresent()) {
                    throw new BadRequestException("Product SKU already exists for this business");
                }
            }
            product.setSku(newSku);
        }
        if (request.getDescription() != null) {
            product.setDescription(request.getDescription());
        }
        if (request.getPrice() != null) {
            product.setPrice(request.getPrice());
        }
        if (request.getStockQuantity() != null) {
            product.setStockQuantity(request.getStockQuantity());
        }
        if (request.getStatus() != null) {
            try {
                product.setStatus(ProductStatus.valueOf(request.getStatus().toUpperCase()));
            } catch (IllegalArgumentException e) {
                throw new BadRequestException("Invalid status. Supported: ACTIVE, OUT_OF_STOCK, DISCONTINUED");
            }
        }

        product = productRepository.save(product);
        return mapToProductResponse(product);
    }

    public ProductDetailResponse getProductById(Long id) {
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Product not found with id: " + id));
        return mapToProductDetailResponse(product);
    }

    public List<ProductResponse> getProductsByBusiness(Long businessId) {
        return productRepository.findByBusinessId(businessId).stream()
                .map(this::mapToProductResponse)
                .collect(Collectors.toList());
    }

    public List<ProductResponse> searchProducts(ProductSearchRequest request) {
        // Implement simple filtering/search. Standard JPA specification or list filter.
        List<Product> products;
        if (request.getBusinessId() != null) {
            products = productRepository.findByBusinessId(request.getBusinessId());
        } else {
            products = productRepository.findAll();
        }

        return products.stream()
                .filter(p -> request.getName() == null || p.getName().toLowerCase().contains(request.getName().toLowerCase()))
                .filter(p -> request.getSku() == null || (p.getSku() != null && p.getSku().toLowerCase().contains(request.getSku().toLowerCase())))
                .filter(p -> request.getStatus() == null || p.getStatus().name().equalsIgnoreCase(request.getStatus()))
                .map(this::mapToProductResponse)
                .collect(Collectors.toList());
    }

    public PriceResponse getProductPrice(Long id) {
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Product not found with id: " + id));
        return PriceResponse.builder()
                .productId(product.getId())
                .sku(product.getSku())
                .price(product.getPrice())
                .build();
    }

    public StockResponse getProductStock(Long id) {
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Product not found with id: " + id));
        return StockResponse.builder()
                .productId(product.getId())
                .sku(product.getSku())
                .stockQuantity(product.getStockQuantity())
                .build();
    }

    @Transactional
    public StockResponse updateProductStock(Long id, Integer quantity) {
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Product not found with id: " + id));
        
        if (quantity == null || quantity < 0) {
            throw new BadRequestException("Stock quantity must be a non-negative integer");
        }
        
        product.setStockQuantity(quantity);
        if (quantity == 0) {
            product.setStatus(ProductStatus.OUT_OF_STOCK);
        } else if (product.getStatus() == ProductStatus.OUT_OF_STOCK) {
            product.setStatus(ProductStatus.ACTIVE);
        }
        
        product = productRepository.save(product);
        return StockResponse.builder()
                .productId(product.getId())
                .sku(product.getSku())
                .stockQuantity(product.getStockQuantity())
                .build();
    }

    private ProductResponse mapToProductResponse(Product product) {
        return ProductResponse.builder()
                .id(product.getId())
                .businessId(product.getBusinessId())
                .name(product.getName())
                .sku(product.getSku())
                .description(product.getDescription())
                .price(product.getPrice())
                .stockQuantity(product.getStockQuantity())
                .status(product.getStatus().name())
                .createdAt(product.getCreatedAt())
                .updatedAt(product.getUpdatedAt())
                .build();
    }

    private ProductDetailResponse mapToProductDetailResponse(Product product) {
        return ProductDetailResponse.builder()
                .id(product.getId())
                .businessId(product.getBusinessId())
                .name(product.getName())
                .sku(product.getSku())
                .description(product.getDescription())
                .price(product.getPrice())
                .stockQuantity(product.getStockQuantity())
                .status(product.getStatus().name())
                .createdAt(product.getCreatedAt())
                .updatedAt(product.getUpdatedAt())
                .build();
    }
}
