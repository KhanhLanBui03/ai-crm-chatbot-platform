package com.thesis.crm.platform.service;

import com.thesis.crm.platform.dto.request.UpdateTenantProfileRequest;
import com.thesis.crm.platform.dto.response.TenantProfileResponse;

public interface TenantService {
    TenantProfileResponse getProfile();
    TenantProfileResponse updateProfile(UpdateTenantProfileRequest request);
}
