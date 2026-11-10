package com.thesis.crm.platform.controller;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.dto.response.KhoangTrongTriThucResponse;
import com.thesis.crm.platform.service.AiInteractionService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Khoảng trống tri thức — SCR034, UC025 bước 8. Chỉ đọc: không use case nào cho đánh dấu một khoảng
 * trống là "đã xử lý" — nó tự rơi khỏi danh sách khi tài liệu mới đã nạp và lượt từ chối thôi phát sinh
 * (cửa sổ 30 ngày phía ai-service).
 */
@RestController
@RequestMapping("/api/v1/knowledge-gaps")
public class KnowledgeGapController {

    private final AiInteractionService service;

    public KnowledgeGapController(AiInteractionService service) {
        this.service = service;
    }

    @GetMapping
    public ApiResponse<PageResponse<KhoangTrongTriThucResponse>> list(
            @RequestParam(required = false) String gapType,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "25") int size) {
        return ApiResponse.ok(service.knowledgeGaps(gapType, page, size));
    }
}
