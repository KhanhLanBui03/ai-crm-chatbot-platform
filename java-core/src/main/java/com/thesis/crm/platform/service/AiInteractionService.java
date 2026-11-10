package com.thesis.crm.platform.service;

import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.dto.request.DanhGiaAiRequest;
import com.thesis.crm.platform.dto.response.DanhGiaAiResponse;
import com.thesis.crm.platform.dto.response.KhoangTrongTriThucResponse;
import com.thesis.crm.platform.dto.response.LuotXuLyAiResponse;
import java.time.LocalDate;
import java.util.UUID;

/**
 * Mặt tiền lượt xử lý AI, đánh giá và khoảng trống tri thức (GD2: UC023 bước 10, UC025, UC027) —
 * ADR-0014: dashboard không gọi thẳng ai-service. Cùng chỗ với kho tri thức của GD1 vì cùng một việc:
 * chuyển tiếp sang ai-service, đổi tên trường, tra tên người ở {@code platform.users}. java-core không
 * giữ bản sao nào của {@code ai.ai_interactions}/{@code ai.ai_feedback} (ADR-0002).
 *
 * <p>Tenant luôn lấy từ JWT. Lượt của tenant khác trả 404 như lượt không tồn tại (RLS phía ai-service).
 */
public interface AiInteractionService {

    /**
     * SCR036 + cột ngữ cảnh hộp thư. {@code from}/{@code to} là NGÀY theo múi giờ doanh nghiệp, quy ra
     * nửa khoảng {@code [from 00:00, to+1 00:00)} — cùng cách màn Hiệu quả AI tính.
     *
     * @param rating {@code POSITIVE}/{@code NEGATIVE}: lượt có đánh giá của người mang giá trị đó (bước 8)
     */
    PageResponse<LuotXuLyAiResponse> list(String route, Boolean refused, String rating, UUID conversationId,
            LocalDate from, LocalDate to, int page, int size);

    /**
     * UC027 — nhân viên đánh giá ({@code rater_type = AGENT}, người đánh giá lấy từ JWT). Đánh giá lại
     * cùng lượt thì cập nhật dòng cũ của chính người đó (luồng phụ 2.1).
     */
    DanhGiaAiResponse rate(UUID interactionId, DanhGiaAiRequest request);

    /** SCR034 — sắp theo số khách (xấp xỉ bằng số hội thoại) khác nhau, cửa sổ 30 ngày. */
    PageResponse<KhoangTrongTriThucResponse> knowledgeGaps(String gapType, int page, int size);
}
