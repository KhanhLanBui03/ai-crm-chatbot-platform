package com.aicrm.dashboard.controller;

import com.aicrm.common.response.ApiResponse;
import com.aicrm.dashboard.dto.response.ConversationChartResponse;
import com.aicrm.dashboard.dto.response.DashboardSummaryResponse;
import com.aicrm.dashboard.dto.response.LeadChartResponse;
import com.aicrm.dashboard.dto.response.RecentLeadResponse;
import com.aicrm.dashboard.service.DashboardService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {

    @Autowired
    private DashboardService dashboardService;

    @GetMapping("/{businessId}/summary")
    public ResponseEntity<ApiResponse<DashboardSummaryResponse>> getSummary(@PathVariable Long businessId) {
        DashboardSummaryResponse response = dashboardService.getSummary(businessId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/{businessId}/conversation-chart")
    public ResponseEntity<ApiResponse<ConversationChartResponse>> getConversationChart(@PathVariable Long businessId) {
        ConversationChartResponse response = dashboardService.getConversationChart(businessId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/{businessId}/lead-chart")
    public ResponseEntity<ApiResponse<LeadChartResponse>> getLeadChart(@PathVariable Long businessId) {
        LeadChartResponse response = dashboardService.getLeadChart(businessId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    @GetMapping("/{businessId}/recent-leads")
    public ResponseEntity<ApiResponse<List<RecentLeadResponse>>> getRecentLeads(@PathVariable Long businessId) {
        List<RecentLeadResponse> response = dashboardService.getRecentLeads(businessId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
