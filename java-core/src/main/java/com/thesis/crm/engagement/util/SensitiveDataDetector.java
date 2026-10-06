package com.thesis.crm.engagement.util;

import java.util.regex.Pattern;

/**
 * Nhận diện dấu hiệu dữ liệu cá nhân nhạy cảm trong ghi chú nội bộ — UC017, NĐ 13/2023.
 *
 * <p>Chỉ để NHẮC ({@code flaggedSensitive}), không chặn: hợp đồng ghi "quyết định là của người
 * nhập". Vì vậy ưu tiên ít báo nhầm hơn là bắt hết — mã đơn hàng, số tiền không được bật cờ.
 *
 * <p>Cùng tinh thần với lớp guardrails PII của module AI ({@code ai-service/src/ai/guardrails/pii.py}):
 * số điện thoại có phân cách, CCCD 12 số, CMND 9 số CHỈ khi có từ khoá đi kèm, email; thêm số thẻ
 * (13–19 chữ số) và số tài khoản ngân hàng (có từ khoá).
 */
public final class SensitiveDataDetector {

    private static final Pattern PHONE = Pattern.compile(
            "(?<![\\d+])(?:\\+?84[.\\-\\s]?|0)[35789](?:[.\\-\\s]?\\d){8}(?!\\d)");
    private static final Pattern CCCD = Pattern.compile("(?<!\\d)0\\d{11}(?!\\d)");
    private static final Pattern EMAIL = Pattern.compile("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}");
    /** Số thẻ: 13–19 chữ số, cho phép nhóm 4 số cách nhau bằng khoảng trắng/gạch. */
    private static final Pattern CARD = Pattern.compile("(?<!\\d)\\d(?:[ \\-]?\\d){12,18}(?!\\d)");
    /** 9–14 chữ số liền — chỉ tính khi có từ khoá CMND hoặc tài khoản ngay phía trước. */
    private static final Pattern KEYWORD_NUMBER = Pattern.compile(
            "\\b(?:cmnd|cmt|chung minh(?: nhan dan| thu)?|stk|so tai khoan|tai khoan|tk ngan hang)\\b"
                    + "[^\\d]{0,20}\\d{9,14}(?!\\d)");

    private SensitiveDataDetector() {}

    public static boolean containsSensitive(String text) {
        if (text == null || text.isBlank()) {
            return false;
        }
        if (PHONE.matcher(text).find() || CCCD.matcher(text).find() || EMAIL.matcher(text).find()
                || CARD.matcher(text).find()) {
            return true;
        }
        return KEYWORD_NUMBER.matcher(ContactNormalizer.foldAccents(text)).find();
    }
}
