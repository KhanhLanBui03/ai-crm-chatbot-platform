package com.aicrm.dashboard.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DashboardSummaryResponse {
    private Long totalCustomers;
    private Long totalLeads;
    private Long totalConversations;
    private Long totalChatbots;
    private Long totalDocuments;
}
