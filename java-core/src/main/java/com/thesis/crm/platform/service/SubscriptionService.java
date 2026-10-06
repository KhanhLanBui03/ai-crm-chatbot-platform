package com.thesis.crm.platform.service;

import com.thesis.crm.platform.dto.request.ChangePlanRequest;
import com.thesis.crm.platform.dto.response.GoiDichVuResponse;
import com.thesis.crm.platform.dto.response.HanMucSuDungResponse;
import com.thesis.crm.platform.dto.response.ThueBaoResponse;

import java.util.List;

public interface SubscriptionService {
    List<GoiDichVuResponse> getPlans();
    ThueBaoResponse getCurrentSubscription();
    ThueBaoResponse changePlan(ChangePlanRequest request);
    HanMucSuDungResponse getCurrentUsage();
}
