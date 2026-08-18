package com.aicrm.business.service;

import com.aicrm.business.dto.request.UpdateBusinessRequest;
import com.aicrm.business.dto.response.BusinessResponse;
import com.aicrm.business.entity.Business;
import com.aicrm.business.repository.BusinessRepository;
import com.aicrm.common.exception.ResourceNotFoundException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class BusinessService {

    @Autowired
    private BusinessRepository businessRepository;

    public BusinessResponse getBusinessById(Long id) {
        Business business = businessRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Business not found with id: " + id));
        return mapToResponse(business);
    }

    public BusinessResponse updateBusiness(Long id, UpdateBusinessRequest request) {
        Business business = businessRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Business not found with id: " + id));

        if (request.getName() != null) business.setName(request.getName());
        if (request.getEmail() != null) business.setEmail(request.getEmail());
        if (request.getPhone() != null) business.setPhone(request.getPhone());
        if (request.getAddress() != null) business.setAddress(request.getAddress());
        if (request.getWebsite() != null) business.setWebsite(request.getWebsite());

        Business saved = businessRepository.save(business);
        return mapToResponse(saved);
    }

    private BusinessResponse mapToResponse(Business business) {
        return BusinessResponse.builder()
                .id(business.getId())
                .name(business.getName())
                .slug(business.getSlug())
                .email(business.getEmail())
                .phone(business.getPhone())
                .address(business.getAddress())
                .website(business.getWebsite())
                .status(business.getStatus().name())
                .createdAt(business.getCreatedAt())
                .updatedAt(business.getUpdatedAt())
                .build();
    }
}
