package com.thesis.crm.engagement.widget;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.engagement.widget.WidgetDtos.SendMessageRequest;
import com.thesis.crm.engagement.widget.WidgetDtos.SessionResponse;
import com.thesis.crm.engagement.widget.WidgetDtos.StartSessionRequest;
import com.thesis.crm.engagement.widget.WidgetDtos.TurnResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import java.time.Instant;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * API CÔNG KHAI cho widget nhúng trên website doanh nghiệp (UC009 bước 10–11, UC010) — khách vãng
 * lai, không có JWT. Bề mặt T2 trong {@code docs/threat-model.md}.
 *
 * <p>Phiên đi bằng header {@code X-Widget-Token} (không dùng {@code Authorization: Bearer} để không
 * bị nhầm với JWT nhân viên ở bất kỳ tầng nào). {@code Origin} do trình duyệt tự gắn — trang khác
 * không giả được khi gọi từ trình duyệt; kẻ gọi ngoài trình duyệt giả được, nên Origin chỉ là lớp
 * chặn nhúng trái phép, còn quyền đọc hội thoại nằm ở chữ ký token.
 */
@RestController
@RequestMapping("/api/v1/widget")
public class WidgetController {

    private final WidgetService service;

    public WidgetController(WidgetService service) {
        this.service = service;
    }

    @PostMapping("/session")
    public ResponseEntity<ApiResponse<SessionResponse>> start(
            @Valid @RequestBody StartSessionRequest body,
            @RequestHeader(value = "Origin", required = false) String origin,
            HttpServletRequest request) {
        return ResponseEntity.ok(ApiResponse.ok(
                service.startSession(body.widgetKey(), origin, body.token(), clientIp(request))));
    }

    @PostMapping("/messages")
    public ResponseEntity<ApiResponse<TurnResponse>> send(
            @RequestBody SendMessageRequest body,
            @RequestHeader(value = "X-Widget-Token", required = false) String token,
            @RequestHeader(value = "Origin", required = false) String origin,
            @RequestHeader(value = "X-Trace-Id", required = false) String traceId) {
        String trace = traceId == null || traceId.isBlank() ? UUID.randomUUID().toString() : traceId;
        return ResponseEntity.ok(ApiResponse.ok(service.sendMessage(token, origin, body.content(), trace)));
    }

    @GetMapping("/messages")
    public ResponseEntity<ApiResponse<TurnResponse>> poll(
            @RequestParam(required = false) Instant after,
            @RequestHeader(value = "X-Widget-Token", required = false) String token,
            @RequestHeader(value = "Origin", required = false) String origin) {
        return ResponseEntity.ok(ApiResponse.ok(service.poll(token, origin, after)));
    }

    /** Khách để lại tên / SĐT / email kèm đồng ý lưu dữ liệu (bổ sung UC010). */
    @PostMapping("/contact-info")
    public ResponseEntity<ApiResponse<WidgetDtos.ContactInfoResponse>> contactInfo(
            @RequestBody(required = false) WidgetDtos.ContactInfoRequest body,
            @RequestHeader(value = "X-Widget-Token", required = false) String token,
            @RequestHeader(value = "Origin", required = false) String origin) {
        return ResponseEntity.ok(ApiResponse.ok(service.shareContactInfo(token, origin, body)));
    }

    @PostMapping("/handoff")
    public ResponseEntity<ApiResponse<TurnResponse>> handoff(
            @RequestHeader(value = "X-Widget-Token", required = false) String token,
            @RequestHeader(value = "Origin", required = false) String origin) {
        return ResponseEntity.ok(ApiResponse.ok(service.requestAgent(token, origin)));
    }

    /**
     * IP thật của khách. Gateway (Spring Cloud Gateway) NỐI địa chỉ nó thấy vào CUỐI
     * {@code X-Forwarded-For}; phần đầu do client tự gửi được, nên lấy phần tử cuối.
     */
    static String clientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            String[] parts = xff.split(",");
            return parts[parts.length - 1].trim();
        }
        return request.getRemoteAddr();
    }
}
