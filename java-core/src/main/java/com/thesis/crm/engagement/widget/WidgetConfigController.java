package com.thesis.crm.engagement.widget;

import static com.thesis.crm.security.CurrentActor.isTenantAdmin;
import static com.thesis.crm.security.CurrentActor.requireTenantId;
import static com.thesis.crm.security.CurrentActor.requireUserId;

import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.engagement.widget.WidgetConfigService.SaveRequest;
import com.thesis.crm.engagement.widget.WidgetConfigService.Snippet;
import com.thesis.crm.engagement.widget.WidgetConfigService.TestReply;
import com.thesis.crm.engagement.widget.WidgetConfigService.TestTurn;
import com.thesis.crm.engagement.widget.WidgetConfigService.WidgetConfig;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * UC009 — SCR018 cấu hình Web Widget (nhân viên đã đăng nhập, JWT). Xem thì mọi nhân viên; sinh mã,
 * sửa và thử chatbot thì chỉ quản trị viên (đặc tả: actor chính A03).
 */
@RestController
@RequestMapping("/api/v1/widget-config")
public class WidgetConfigController {

    public record TestChatRequest(String message, List<TestTurn> history) {}

    private final WidgetConfigService service;

    public WidgetConfigController(WidgetConfigService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<WidgetConfig>> get() {
        return ResponseEntity.ok(ApiResponse.ok(service.get(requireTenantId())));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<WidgetConfig>> create() {
        requireAdmin();
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(service.create(requireTenantId(), requireUserId())));
    }

    @PutMapping
    public ResponseEntity<ApiResponse<WidgetConfig>> save(@RequestBody SaveRequest body) {
        requireAdmin();
        return ResponseEntity.ok(ApiResponse.ok(service.save(requireTenantId(), requireUserId(), body)));
    }

    @GetMapping("/snippet")
    public ResponseEntity<ApiResponse<Snippet>> snippet() {
        return ResponseEntity.ok(ApiResponse.ok(service.snippet(requireTenantId())));
    }

    @PostMapping("/test-chat")
    public ResponseEntity<ApiResponse<TestReply>> testChat(
            @RequestBody TestChatRequest body,
            @RequestHeader(value = "X-Trace-Id", required = false) String traceId) {
        requireAdmin();
        String trace = traceId == null || traceId.isBlank() ? UUID.randomUUID().toString() : traceId;
        return ResponseEntity.ok(ApiResponse.ok(
                service.testChat(requireTenantId(), body.message(), body.history(), trace)));
    }

    private static void requireAdmin() {
        if (!isTenantAdmin()) {
            throw new AppException("Chỉ quản trị viên được thay đổi widget.", HttpStatus.FORBIDDEN);
        }
    }
}
