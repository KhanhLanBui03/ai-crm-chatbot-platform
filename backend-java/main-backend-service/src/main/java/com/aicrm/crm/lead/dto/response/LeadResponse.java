package com.aicrm.crm.lead.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class LeadResponse {
    private Long id;
    private String name;
    private String email;
    private String phone;
    private String status;
    private String notes;
    private Long businessId;
    private Long conversationId;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
