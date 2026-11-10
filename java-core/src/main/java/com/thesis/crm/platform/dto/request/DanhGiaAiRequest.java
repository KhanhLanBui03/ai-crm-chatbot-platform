package com.thesis.crm.platform.dto.request;

import com.thesis.crm.common.util.Texts;
import com.thesis.crm.common.validation.CodePointLength;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

/**
 * Đánh giá một câu trả lời của tác tử AI — UC027 bước 2–4. Dùng chung cho nhân viên (hộp thư, giám sát
 * lượt) và khách (widget); {@code correctedAnswer} chỉ nhận từ nhân viên.
 *
 * <p>"Chê thì phải chọn lý do" kiểm ở service (422 {@code REASON_REQUIRED}, đúng mã đặc tả), không ở
 * đây — Bean Validation chỉ trả mã lỗi chung.
 *
 * @param rating          {@code POSITIVE} | {@code NEGATIVE}
 * @param reasonCode      một trong bốn lý do chê; bỏ qua khi khen (bước 3.1)
 * @param comment         nhận xét tự do, tối đa 2.000 ký tự
 * @param correctedAnswer câu trả lời đúng, tối đa 4.000 ký tự
 */
public record DanhGiaAiRequest(
        @NotNull(message = "bắt buộc")
        @Pattern(regexp = "POSITIVE|NEGATIVE", message = "chỉ nhận POSITIVE hoặc NEGATIVE")
        String rating,

        @Pattern(regexp = "WRONG_INFO|IRRELEVANT|INCOMPLETE|BAD_TONE", message = "lý do không hợp lệ")
        String reasonCode,

        @CodePointLength(max = 2000)
        String comment,

        @CodePointLength(max = 4000)
        String correctedAnswer) {

    public DanhGiaAiRequest {
        comment = rongLaNull(Texts.nfcStrip(comment));
        correctedAnswer = rongLaNull(Texts.nfcStrip(correctedAnswer));
    }

    private static String rongLaNull(String s) {
        return s == null || s.isEmpty() ? null : s;
    }
}
