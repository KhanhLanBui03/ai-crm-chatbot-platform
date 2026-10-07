package com.thesis.crm.sales.activity;

import static com.thesis.crm.security.CurrentActor.isTenantAdmin;
import static com.thesis.crm.security.CurrentActor.requireTenantId;
import static com.thesis.crm.security.CurrentActor.requireUserId;

import com.fasterxml.jackson.databind.JsonNode;
import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.sales.activity.ActivityDtos.ActivityDto;
import com.thesis.crm.sales.activity.ActivityDtos.CreateActivityRequest;
import com.thesis.crm.sales.activity.ActivityDtos.TodoCount;
import com.thesis.crm.sales.lead.LeadService.Actor;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * UC035 — SCR047 hoạt động chăm sóc và nhắc việc. Không có DELETE: hoạt động là lịch sử. "Việc của tôi"
 * là {@code mine=true} (+ {@code bucket}); người "tôi" lấy từ JWT, không nhận từ tham số.
 */
@RestController
@RequestMapping("/api/v1/activities")
public class ActivityController {

    private final ActivityService service;

    public ActivityController(ActivityService service) {
        this.service = service;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<PageResponse<ActivityDto>>> list(
            @RequestParam(required = false) UUID contactId,
            @RequestParam(required = false) UUID leadId,
            @RequestParam(required = false) UUID dealId,
            @RequestParam(required = false) String type,
            @RequestParam(required = false) String remindStatus,
            @RequestParam(defaultValue = "false") boolean mine,
            @RequestParam(required = false) String bucket,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        return ResponseEntity.ok(ApiResponse.ok(service.list(requireTenantId(), actor(), contactId, leadId, dealId,
                type, remindStatus, mine, bucket, page, size)));
    }

    @GetMapping("/todo-count")
    public ResponseEntity<ApiResponse<TodoCount>> todoCount() {
        return ResponseEntity.ok(ApiResponse.ok(service.todoCount(requireTenantId(), actor())));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<ActivityDto>> create(@RequestBody CreateActivityRequest body) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(service.create(requireTenantId(), actor(), body)));
    }

    @PatchMapping("/{activityId}")
    public ResponseEntity<ApiResponse<ActivityDto>> update(@PathVariable UUID activityId, @RequestBody JsonNode body) {
        return ResponseEntity.ok(ApiResponse.ok(service.update(requireTenantId(), actor(), activityId, body)));
    }

    private static Actor actor() {
        return new Actor(requireUserId(), isTenantAdmin());
    }
}
