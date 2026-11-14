package com.thesis.crm.engagement.inbox;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.engagement.inbox.InboxDtos.InternalMessageDto;
import com.thesis.crm.engagement.inbox.InboxDtos.WriteSummaryRequest;
import com.thesis.crm.security.InternalCaller;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * UC026 — hai endpoint CHỈ ai-service gọi ({@code X-Internal-Token}, chuỗi bảo mật riêng ở
 * {@code SecurityConfig}). Hợp đồng: {@code docs/contracts/uc026-uc041-tom-tat-va-xoa-du-lieu.md} mục 1–2.
 * Hội thoại không có, hoặc thuộc tenant khác, thì 404 — ai-service coi là rỗng.
 */
@RestController
@RequestMapping("/internal/conversations")
public class InternalConversationController {

    private final SummaryService service;

    public InternalConversationController(SummaryService service) {
        this.service = service;
    }

    @GetMapping("/{id}/messages")
    public ResponseEntity<ApiResponse<PageResponse<InternalMessageDto>>> messages(
            @RequestHeader(value = "X-Tenant-Id", required = false) String tenant,
            @PathVariable UUID id,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "200") int size) {
        return ResponseEntity.ok(ApiResponse.ok(
                service.internalMessages(InternalCaller.requireTenantId(tenant), id, page, size)));
    }

    @PatchMapping("/{id}/summary")
    public ResponseEntity<ApiResponse<Void>> summary(
            @RequestHeader(value = "X-Tenant-Id", required = false) String tenant,
            @PathVariable UUID id,
            @RequestBody WriteSummaryRequest body) {
        service.writeFromAi(InternalCaller.requireTenantId(tenant), id, body);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }
}
