package com.thesis.crm.sales.repository;

import com.thesis.crm.sales.entity.Lead;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

/**
 * MẪU — repository chuẩn. Chỉ khai báo truy vấn, không chứa logic nghiệp vụ.
 *
 * <p>Không cần viết {@code findByTenantIdAnd...}: RLS đã lọc ở tầng cơ sở dữ liệu dựa trên
 * biến phiên {@code app.tenant_id}. Viết thêm điều kiện tenant ở đây là thừa và dễ tạo cảm
 * giác an toàn giả — nếu quên một chỗ thì tưởng là rò rỉ, trong khi thật ra RLS vẫn chặn.
 */
@Repository
public interface LeadRepository extends JpaRepository<Lead, UUID> {
}
