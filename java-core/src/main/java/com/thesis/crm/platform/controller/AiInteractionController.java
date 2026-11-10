package com.thesis.crm.platform.controller;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.dto.request.DanhGiaAiRequest;
import com.thesis.crm.platform.dto.response.DanhGiaAiResponse;
import com.thesis.crm.platform.dto.response.LuotXuLyAiResponse;
import com.thesis.crm.platform.service.AiInteractionService;
import jakarta.validation.Valid;
import java.time.LocalDate;
import java.util.UUID;
import org.springframework.format.annotation.DateTimeFormat;
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
 * Lượt xử lý của tác tử AI — SCR036 và cột ngữ cảnh hộp thư; đánh giá của nhân viên (UC027). Chỉ nhận,
 * validate, gọi service. Mọi nhân viên của doanh nghiệp đọc và đánh giá được: đặc tả UC027 chỉ đòi
 * "có quyền xem lượt xử lý đó", và nhân viên trực hộp thư là người đánh giá chính.
 */
@RestController
@RequestMapping("/api/v1/ai-interactions")
public class AiInteractionController {

    private final AiInteractionService service;

    public AiInteractionController(AiInteractionService service) {
        this.service = service;
    }

    @GetMapping
    public ApiResponse<PageResponse<LuotXuLyAiResponse>> list(
            @RequestParam(required = false) String route,
            @RequestParam(required = false) Boolean refused,
            @RequestParam(required = false) String rating,
            @RequestParam(required = false) UUID conversationId,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "25") int size) {
        return ApiResponse.ok(service.list(route, refused, rating, conversationId, from, to, page, size));
    }

    /** 201 cả khi đánh giá lại (cập nhật dòng cũ): với người bấm, đó vẫn là "đã ghi đánh giá". */
    @PostMapping("/{interactionId}/feedback")
    public ResponseEntity<ApiResponse<DanhGiaAiResponse>> rate(
            @PathVariable UUID interactionId,
            @Valid @RequestBody DanhGiaAiRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(service.rate(interactionId, request)));
    }
}
