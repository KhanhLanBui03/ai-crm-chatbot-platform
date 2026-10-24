package com.thesis.crm.platform.service;

import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.dto.request.UpdateDocumentRequest;
import com.thesis.crm.platform.dto.request.UploadDocumentRequest;
import com.thesis.crm.platform.dto.response.CongViecNapResponse;
import com.thesis.crm.platform.dto.response.DoanTaiLieuResponse;
import com.thesis.crm.platform.dto.response.DocumentUploadResponse;
import com.thesis.crm.platform.dto.response.TaiLieuChiTietResponse;
import com.thesis.crm.platform.dto.response.TaiLieuResponse;
import java.util.UUID;
import org.springframework.web.multipart.MultipartFile;

/**
 * Mặt tiền kho tri thức phía java-core — ADR-0014: dashboard không gọi thẳng ai-service.
 *
 * <p>Ở context {@code platform} chứ không phải context riêng: phần việc của java-core trong UC018
 * là hạn mức gói, ghi tệp và outbox — cả ba đều là của {@code platform}. Nội dung tài liệu thuộc
 * schema {@code knowledge} của Track B, java-core chỉ giữ URI.
 *
 * <p>UC019/UC020 (GD1): java-core không giữ bản sao nào của tài liệu — mọi lượt đọc chuyển tiếp
 * sang ai-service, mọi lượt đổi chỉ mục cũng vậy rồi ghi {@code platform.audit_logs}. Tenant luôn
 * lấy từ JWT. Tài liệu của tenant khác trả 404 như tài liệu không tồn tại (RLS phía ai-service).
 */
public interface KnowledgeDocumentService {

    /**
     * UC018 — nhận tệp, ghi lên kho S3, nhờ ai-service tạo bản ghi {@code PENDING}, cộng hạn mức
     * và ghi sự kiện {@code DocumentUploaded}. Kết thúc ngay khi tài liệu được xếp hàng, không chờ
     * lập chỉ mục (UC019 chạy nền).
     */
    DocumentUploadResponse upload(MultipartFile file, UploadDocumentRequest request);

    /** UC020 bước 2 — SCR030. Không lọc {@code status} thì ẩn {@code ARCHIVED}. */
    PageResponse<TaiLieuResponse> list(String q, String status, String sourceType, int page, int size);

    /** UC020 bước 4 — chi tiết kèm việc nạp gần nhất (của bản bóng nếu đang nạp lại). */
    TaiLieuChiTietResponse get(UUID documentId);

    /** UC020 bước 4 — các đoạn kèm mô hình nhúng của từng đoạn. */
    PageResponse<DoanTaiLieuResponse> chunks(UUID documentId, int page, int size);

    /** UC020 bước 5 — sửa tiêu đề + mô tả, chỉ mục vector giữ nguyên. Ghi kiểm toán. */
    TaiLieuChiTietResponse update(UUID documentId, UpdateDocumentRequest request);

    /** UC020 bước 6 — xếp bản bóng vào hàng đợi, trả việc nạp của bản bóng. Ghi kiểm toán. */
    CongViecNapResponse reindex(UUID documentId);

    /** UC020 bước 7 — gỡ đoạn khỏi chỉ mục rồi mới {@code ARCHIVED}. Ghi kiểm toán. */
    void archive(UUID documentId);

    /** UC019 bước 12 — hàng đợi nạp SCR033, mới nhất trước. */
    PageResponse<CongViecNapResponse> ingestionJobs(String state, int page, int size);
}
