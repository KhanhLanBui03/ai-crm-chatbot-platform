package com.thesis.crm.sales.controller;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.sales.dto.request.CreateLeadRequest;
import com.thesis.crm.sales.dto.response.LeadResponse;
import com.thesis.crm.sales.service.LeadService;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * MẪU — controller chuẩn. Chỉ nhận request, kiểm tra đầu vào, gọi service, trả ApiResponse.
 *
 * <p>Controller KHÔNG chứa logic nghiệp vụ, KHÔNG gọi repository, KHÔNG mở transaction.
 * Nếu thấy mình sắp viết {@code if} về nghiệp vụ ở đây thì chỗ đúng của nó là {@code service/impl/}.
 *
 * <p>Đường dẫn bắt đầu bằng {@code /api/v1} vì gateway định tuyến {@code /api/v1/**} tới
 * {@code lb://java-core} (xem gateway/src/main/resources/application.yml).
 */
@RestController
@RequestMapping("/api/v1/leads")
public class LeadController {

    private final LeadService leadService;

    public LeadController(LeadService leadService) {
        this.leadService = leadService;
    }

    @PostMapping
    public ResponseEntity<ApiResponse<LeadResponse>> create(
            @Valid @RequestBody CreateLeadRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(leadService.create(request)));
    }

    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<LeadResponse>> getById(@PathVariable UUID id) {
        return ResponseEntity.ok(ApiResponse.ok(leadService.getById(id)));
    }
}
