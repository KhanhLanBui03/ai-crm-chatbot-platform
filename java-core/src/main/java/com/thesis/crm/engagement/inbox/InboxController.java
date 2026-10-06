package com.thesis.crm.engagement.inbox;

import static com.thesis.crm.security.CurrentActor.isTenantAdmin;
import static com.thesis.crm.security.CurrentActor.requireTenantId;
import static com.thesis.crm.security.CurrentActor.requireUserId;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.engagement.inbox.InboxDtos.AssignRequest;
import com.thesis.crm.engagement.inbox.InboxDtos.ConversationContext;
import com.thesis.crm.engagement.inbox.InboxDtos.ConversationDetail;
import com.thesis.crm.engagement.inbox.InboxDtos.ConversationSummary;
import com.thesis.crm.engagement.inbox.InboxDtos.HandoffEvent;
import com.thesis.crm.engagement.inbox.InboxDtos.HandoffRequest;
import com.thesis.crm.engagement.inbox.InboxDtos.MessageDto;
import com.thesis.crm.engagement.inbox.InboxDtos.MessagePage;
import com.thesis.crm.engagement.inbox.InboxDtos.SendMessageRequest;
import com.thesis.crm.engagement.inbox.InboxDtos.StatusRequest;
import com.thesis.crm.engagement.inbox.InboxService.Actor;
import java.time.Instant;
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
 * UC012 + UC013 — SCR019/SCR020 hộp thư hợp nhất, cùng các thao tác UC014/UC015 trên một hội thoại.
 * Tenant và người thao tác chỉ lấy từ JWT (luật 1) — {@code scope=mine} không nhận userId từ phía gọi.
 */
@RestController
@RequestMapping("/api/v1/conversations")
public class InboxController {

    private final InboxService service;

    public InboxController(InboxService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<ConversationSummary>>> list(
            @RequestParam(defaultValue = "all") String scope,
            @RequestParam(required = false) List<String> status,
            @RequestParam(required = false) String channelType,
            @RequestParam(required = false) UUID tagId,
            @RequestParam(required = false) String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "25") int size) {
        return ResponseEntity.ok(ApiResponse.ok(service.list(
                requireTenantId(), actor(), scope, status, channelType, tagId, q, page, size)));
    }

    @GetMapping("/{conversationId}")
    public ResponseEntity<ApiResponse<ConversationDetail>> detail(@PathVariable UUID conversationId) {
        return ResponseEntity.ok(ApiResponse.ok(service.detail(requireTenantId(), conversationId)));
    }

    @GetMapping("/{conversationId}/context")
    public ResponseEntity<ApiResponse<ConversationContext>> context(@PathVariable UUID conversationId) {
        return ResponseEntity.ok(ApiResponse.ok(service.context(requireTenantId(), conversationId)));
    }

    @GetMapping("/{conversationId}/messages")
    public ResponseEntity<ApiResponse<MessagePage>> messages(
            @PathVariable UUID conversationId,
            @RequestParam(required = false) Instant before,
            @RequestParam(defaultValue = "30") int size) {
        return ResponseEntity.ok(ApiResponse.ok(service.messages(requireTenantId(), conversationId, before, size)));
    }

    @PostMapping("/{conversationId}/messages")
    public ResponseEntity<ApiResponse<MessageDto>> send(
            @PathVariable UUID conversationId, @RequestBody SendMessageRequest body) {
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(
                service.send(requireTenantId(), actor(), conversationId, body.content(), body.contentType())));
    }

    @PostMapping("/{conversationId}/assign")
    public ResponseEntity<ApiResponse<ConversationSummary>> assign(
            @PathVariable UUID conversationId, @RequestBody(required = false) AssignRequest body) {
        UUID target = body == null ? null : body.assigneeUserId();
        return ResponseEntity.ok(ApiResponse.ok(service.assign(requireTenantId(), actor(), conversationId, target)));
    }

    @PostMapping("/{conversationId}/handoff")
    public ResponseEntity<ApiResponse<HandoffEvent>> handoff(
            @PathVariable UUID conversationId, @RequestBody HandoffRequest body) {
        return ResponseEntity.ok(ApiResponse.ok(service.handoff(
                requireTenantId(), actor(), conversationId, body.direction(), body.reason())));
    }

    @PostMapping("/{conversationId}/status")
    public ResponseEntity<ApiResponse<ConversationSummary>> status(
            @PathVariable UUID conversationId, @RequestBody StatusRequest body) {
        return ResponseEntity.ok(ApiResponse.ok(service.changeStatus(
                requireTenantId(), actor(), conversationId, body.status(), body.reason())));
    }

    @PostMapping("/{conversationId}/read")
    public ResponseEntity<ApiResponse<Void>> read(@PathVariable UUID conversationId) {
        service.markRead(requireTenantId(), conversationId);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    private static Actor actor() {
        return new Actor(requireUserId(), isTenantAdmin());
    }
}
