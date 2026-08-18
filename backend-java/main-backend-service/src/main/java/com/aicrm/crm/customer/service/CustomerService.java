package com.aicrm.crm.customer.service;

import com.aicrm.crm.customer.dto.request.CreateCustomerRequest;
import com.aicrm.crm.customer.dto.request.UpdateCustomerRequest;
import com.aicrm.crm.customer.dto.response.CustomerDetailResponse;
import com.aicrm.crm.customer.dto.response.CustomerResponse;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class CustomerService {

    /**
     * Chức năng: Lưu trữ thông tin khách hàng mới
     */
    public CustomerResponse createCustomer(CreateCustomerRequest request) {
        // TODO: Dựng function lưu thông tin khách hàng
        return null;
    }

    /**
     * Chức năng: Cập nhật hồ sơ thông tin và Trạng thái chăm sóc của khách hàng
     */
    public CustomerResponse updateCustomer(Long id, UpdateCustomerRequest request) {
        // TODO: Dựng function cập nhật thông tin và trạng thái khách hàng
        return null;
    }

    /**
     * Chức năng: Lấy thông tin chi tiết một khách hàng
     */
    public CustomerDetailResponse getCustomerById(Long id) {
        // TODO: Dựng function lấy chi tiết khách hàng
        return null;
    }

    /**
     * Chức năng: Lấy toàn bộ danh sách khách hàng của doanh nghiệp
     */
    public List<CustomerResponse> getCustomersByBusiness(Long businessId) {
        // TODO: Dựng function lấy danh sách khách hàng
        return null;
    }
}
