package com.aicrm.business.dto.response;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class BusinessResponse {
    private Long id;
    private String name;
    private String slug;
    private String email;
    private String phone;
    private String address;
    private String website;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
