package com.aicrm.dashboard.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class RecentLeadResponse {
    private Long id;
    private String name;
    private String email;
    private String phone;
    private String status;
    private LocalDateTime createdAt;
}
