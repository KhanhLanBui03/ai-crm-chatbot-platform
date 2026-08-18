package com.aicrm.dashboard.service;

import com.aicrm.dashboard.dto.response.ConversationChartResponse;
import com.aicrm.dashboard.dto.response.DashboardSummaryResponse;
import com.aicrm.dashboard.dto.response.LeadChartResponse;
import com.aicrm.dashboard.dto.response.RecentLeadResponse;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class DashboardService {

    public DashboardSummaryResponse getSummary(Long businessId) {
        return null;
    }

    public ConversationChartResponse getConversationChart(Long businessId) {
        return null;
    }

    public LeadChartResponse getLeadChart(Long businessId) {
        return null;
    }

    public List<RecentLeadResponse> getRecentLeads(Long businessId) {
        return null;
    }
}
