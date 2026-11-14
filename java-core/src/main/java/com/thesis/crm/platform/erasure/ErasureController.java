package com.thesis.crm.platform.erasure;

import static com.thesis.crm.security.CurrentActor.requireTenantId;
import static com.thesis.crm.security.CurrentActor.requireUserId;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.erasure.ErasureDtos.CreateErasureRequest;
import com.thesis.crm.platform.erasure.ErasureDtos.ErasureItem;
import com.thesis.crm.platform.erasure.ErasureDtos.ErasureRequestDetail;
import com.thesis.crm.platform.erasure.ErasureDtos.ErasureRequestDto;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * UC041 — SCR055–SCR058. Tenant và người thao tác chỉ lấy từ JWT (luật 1). Phân quyền ở
 * {@code SecurityConfig}: tạo yêu cầu thì mọi nhân viên (đặc tả: "nhân viên tạo thay mặt khách"); đọc,
 * xem trước, xác minh, thực thi chỉ quản trị viên ("quản trị viên có quyền xử lý yêu cầu xoá").
 *
 * <p>{@code /preview} khai TRƯỚC {@code /{id}} cho dễ đọc; Spring vẫn chọn đường cố định trước đường có
 * tham số bất kể thứ tự khai.
 */
@RestController
@RequestMapping("/api/v1/erasure-requests")
public class ErasureController {

    private final ErasureService service;

    public ErasureController(ErasureService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<ErasureRequestDto>>> list(
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return ResponseEntity.ok(ApiResponse.ok(service.list(requireTenantId(), status, page, size)));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<ErasureRequestDetail>> create(@RequestBody CreateErasureRequest body) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(service.create(requireTenantId(), requireUserId(), body)));
    }

    @GetMapping("/preview")
    public ResponseEntity<ApiResponse<List<ErasureItem>>> preview(@RequestParam UUID contactId) {
        return ResponseEntity.ok(ApiResponse.ok(service.preview(requireTenantId(), contactId)));
    }

    @GetMapping("/{requestId}")
    public ResponseEntity<ApiResponse<ErasureRequestDetail>> detail(@PathVariable UUID requestId) {
        return ResponseEntity.ok(ApiResponse.ok(service.detail(requireTenantId(), requestId)));
    }

    @PostMapping("/{requestId}/verify-identity")
    public ResponseEntity<ApiResponse<ErasureRequestDetail>> verify(@PathVariable UUID requestId) {
        return ResponseEntity.ok(ApiResponse.ok(service.verifyIdentity(requireTenantId(), requireUserId(), requestId)));
    }

    /** Đồng bộ (giảm độ sâu GD3): trả 200 với kết quả cuối, không phải 202. */
    @PostMapping("/{requestId}/execute")
    public ResponseEntity<ApiResponse<ErasureRequestDetail>> execute(@PathVariable UUID requestId) {
        return ResponseEntity.ok(ApiResponse.ok(service.execute(requireTenantId(), requireUserId(), requestId)));
    }
}
