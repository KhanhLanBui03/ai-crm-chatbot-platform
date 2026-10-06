package com.thesis.crm.engagement.controller;

import static com.thesis.crm.security.CurrentActor.requireTenantId;
import static com.thesis.crm.security.CurrentActor.requireUserId;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.engagement.dto.request.CreateTagRequest;
import com.thesis.crm.engagement.dto.response.ContactDtos.TagDto;
import com.thesis.crm.engagement.service.TagService;
import com.thesis.crm.engagement.service.TagService.CreateTagResult;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** UC017 — {@code /api/v1/tags} và {@code /api/v1/contacts/{contactId}/tags/{tagId}}. */
@RestController
public class TagController {

    private final TagService tagService;

    public TagController(TagService tagService) {
        this.tagService = tagService;
    }

    @GetMapping("/api/v1/tags")
    public ResponseEntity<ApiResponse<List<TagDto>>> list() {
        return ResponseEntity.ok(ApiResponse.ok(tagService.list(requireTenantId())));
    }

    /** 201 khi tạo mới; 200 kèm thẻ cũ khi trùng tên (khác hoa thường/khác dấu); 409 khi chạm trần gói. */
    @PostMapping("/api/v1/tags")
    public ResponseEntity<ApiResponse<TagDto>> create(@Valid @RequestBody CreateTagRequest request) {
        CreateTagResult r = tagService.create(requireTenantId(), requireUserId(), request);
        return ResponseEntity.status(r.created() ? HttpStatus.CREATED : HttpStatus.OK).body(ApiResponse.ok(r.tag()));
    }

    /** Gắn thẻ — gắn lại thẻ đã gắn không lỗi. */
    @PutMapping("/api/v1/contacts/{contactId}/tags/{tagId}")
    public ResponseEntity<ApiResponse<Void>> attach(@PathVariable UUID contactId, @PathVariable UUID tagId) {
        tagService.attach(requireTenantId(), requireUserId(), contactId, tagId);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    /** Gỡ thẻ — gỡ thẻ chưa gắn không lỗi. */
    @DeleteMapping("/api/v1/contacts/{contactId}/tags/{tagId}")
    public ResponseEntity<ApiResponse<Void>> detach(@PathVariable UUID contactId, @PathVariable UUID tagId) {
        tagService.detach(requireTenantId(), requireUserId(), contactId, tagId);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }
}
