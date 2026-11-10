package com.thesis.crm.client;

import com.thesis.crm.common.exception.BusinessException;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;

/**
 * Dịch {@link AiServiceException} thành lỗi cho người dùng — bảng chung của lớp chuyển tiếp
 * (kế hoạch tích hợp giao diện mục 3). Giữ nguyên {@code code} của ai-service để giao diện rẽ
 * nhánh theo đúng mã đặc tả ghi.
 *
 * <pre>
 * ai-service              java-core trả
 * 404                     404, giữ code (DOCUMENT_NOT_FOUND …)
 * 409 · 422               giữ mã và code (DOCUMENT_BUSY, INVALID_METADATA …)
 * 400 · 401 · 403 · khác  500 — java-core gửi sai hoặc cấu hình lệch, người dùng không sửa được gì
 * 5xx · hết giờ · mất nối 502 AI_SERVICE_UNAVAILABLE (đặc tả UC020)
 * </pre>
 *
 * <p>Đường tải lên UC018 có bảng riêng ({@code KnowledgeDocumentServiceImpl#dichLoiAiService},
 * trả 503 khi ai-service không phản hồi) — giữ nguyên, không gộp vào đây.
 */
public final class AiServiceErrors {

    private static final Logger log = LoggerFactory.getLogger(AiServiceErrors.class);

    /**
     * Câu cho người đọc thay cho câu của ai-service ở những mã hay gặp: câu gốc viết cho người vận
     * hành, có mã UUID tài liệu. Mã không có ở đây thì dùng nguyên câu của ai-service.
     */
    private static final Map<String, String> CAU_THAY = Map.of(
            "DOCUMENT_NOT_FOUND", "Không tìm thấy tài liệu.",
            "DOCUMENT_BUSY", "Tài liệu đang được xử lý (nạp hoặc nạp lại). Thử lại khi việc nạp xong.",
            "DOCUMENT_ARCHIVED", "Tài liệu đã được gỡ khỏi kho tri thức.");

    private AiServiceErrors() {
    }

    public static BusinessException dich(AiServiceException ex) {
        if (ex.isUnreachable() || ex.getStatus() >= 500) {
            log.error("ai-service không phản hồi được: {} {} — {}", ex.getStatus(), ex.getCode(), ex.getMessage());
            return new BusinessException(HttpStatus.BAD_GATEWAY, "AI_SERVICE_UNAVAILABLE",
                    "Dịch vụ AI tạm thời không phản hồi. Thao tác chưa được thực hiện, thử lại sau.");
        }
        int status = ex.getStatus();
        if (status == 404 || status == 409 || status == 422) {
            String code = ex.getCode() != null ? ex.getCode() : switch (status) {
                case 404 -> "NOT_FOUND";
                case 409 -> "CONFLICT";
                default -> "INVALID_REQUEST";
            };
            return new BusinessException(HttpStatus.valueOf(status), code,
                    CAU_THAY.getOrDefault(code, ex.getMessage()));
        }
        log.error("ai-service từ chối vì lệch hợp đồng: {} {} — {}", status, ex.getCode(), ex.getMessage());
        return new BusinessException(HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Lỗi nội bộ");
    }
}
