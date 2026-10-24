package com.thesis.crm.platform.dto.request;

import com.thesis.crm.common.util.Texts;
import com.thesis.crm.common.validation.CodePointLength;
import jakarta.validation.constraints.NotNull;

/**
 * Sửa siêu dữ liệu — UC020 bước 5. Chỉ hai trường người dùng nhập lúc tải lên (UC018 bước 3);
 * {@code language} không sửa được vì nó quyết định cách tách từ, đổi nó là phải nạp lại.
 *
 * <p>Thay CẢ HAI trường mỗi lần: hộp thoại luôn gửi đủ. Mô tả rỗng nghĩa là xoá mô tả. Cùng giới
 * hạn và cùng chuẩn hoá NFC + strip với {@link UploadDocumentRequest}.
 *
 * @param title       3–255 code point
 * @param description tối đa 500 code point; rỗng hoặc toàn khoảng trắng thành {@code null}
 */
public record UpdateDocumentRequest(
        @NotNull(message = "bắt buộc")
        @CodePointLength(min = 3, max = 255)
        String title,

        @CodePointLength(max = 500)
        String description) {

    public UpdateDocumentRequest {
        title = Texts.nfcStrip(title);
        description = Texts.nfcStrip(description);
        if (description != null && description.isEmpty()) {
            description = null;
        }
    }
}
