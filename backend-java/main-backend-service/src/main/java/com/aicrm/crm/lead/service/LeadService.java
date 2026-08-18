package com.aicrm.crm.lead.service;

import com.aicrm.crm.lead.dto.request.CreateLeadRequest;
import com.aicrm.crm.lead.dto.request.UpdateLeadRequest;
import com.aicrm.crm.lead.dto.response.LeadResponse;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class LeadService {

    /**
     * Chức năng: Tạo mới thông tin khách hàng tiềm năng (Lead)
     * - Được kích hoạt khi bot thu thập đủ thông tin trong cuộc trò chuyện hoặc tạo thủ công.
     */
    public LeadResponse createLead(CreateLeadRequest request) {
        // TODO: Dựng function tạo lead mới
        return null;
    }

    /**
     * Chức năng: Cập nhật thông tin và Trạng thái chăm sóc của Lead (NEW, CONTACTED, QUALIFIED...)
     */
    public LeadResponse updateLead(Long id, UpdateLeadRequest request) {
        // TODO: Dựng function cập nhật trạng thái chăm sóc của lead
        return null;
    }

    /**
     * Chức năng: Lấy danh sách toàn bộ khách hàng tiềm năng của doanh nghiệp
     */
    public List<LeadResponse> getLeadsByBusiness(Long businessId) {
        // TODO: Dựng function lấy danh sách lead
        return null;
    }
}
