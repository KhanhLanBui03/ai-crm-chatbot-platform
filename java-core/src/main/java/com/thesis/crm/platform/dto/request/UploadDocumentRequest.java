package com.thesis.crm.platform.dto.request;

import com.thesis.crm.common.util.Texts;
import com.thesis.crm.common.validation.CodePointLength;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;

/**
 * Siêu dữ liệu đi kèm tệp khi tải lên — UC018 bước 3. Tệp đi riêng ở part {@code file}.
 *
 * <p>KHÔNG có {@code tenantId}: tenant lấy từ JWT (ADR-0001). Form gửi thêm trường
 * {@code tenantId} thì bị bỏ qua — record không có chỗ nào để bind nó vào.
 *
 * <p>Constructor chuẩn hoá TRƯỚC khi Bean Validation đếm độ dài: Spring dựng record qua
 * constructor rồi mới validate, nên {@code @CodePointLength} luôn thấy chuỗi đã NFC + strip — đúng
 * thứ tự ai-service làm ({@code schemas.py::_nfc_roi_strip} chạy {@code mode="before"}).
 *
 * @param title       3–255 code point. Đặc tả ghi 3–300; 255 khớp {@code varchar(255)} của V202
 *                    (ADR-0017 quyết định 3)
 * @param description tối đa 500 code point; rỗng hoặc toàn khoảng trắng thành {@code null}
 * @param language    {@code vi} | {@code en}; thiếu hoặc rỗng thành {@code vi}
 */
public record UploadDocumentRequest(
        @NotNull(message = "bắt buộc")
        @CodePointLength(min = 3, max = 255)
        String title,

        @CodePointLength(max = 500)
        String description,

        @Pattern(regexp = "vi|en", message = "chỉ nhận vi hoặc en")
        String language) {

    public UploadDocumentRequest {
        title = Texts.nfcStrip(title);
        description = Texts.nfcStrip(description);
        if (description != null && description.isEmpty()) {
            description = null;
        }
        language = (language == null || language.isBlank()) ? "vi" : language.strip();
    }
}
