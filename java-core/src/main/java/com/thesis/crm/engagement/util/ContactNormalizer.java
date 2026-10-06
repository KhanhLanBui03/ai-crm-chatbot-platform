package com.thesis.crm.engagement.util;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * Chuẩn hoá dữ liệu danh bạ — UC016. Thuần hàm, không phụ thuộc Spring, để test dễ.
 *
 * <p><b>Số điện thoại</b> quy về một dạng duy nhất {@code 0xxxxxxxxx} trước khi lưu: cùng một số
 * có thể được gõ "0912 345 678", "0912.345.678", "+84 912 345 678", "+84 0912…", "912345678".
 * Lưu nguyên thì kiểm trùng bỏ sót và luồng gợi ý hợp nhất không chạy.
 *
 * <p><b>Bỏ dấu</b> ({@link #foldAccents}) phải cho CÙNG kết quả với trigger
 * {@code engagement.contacts_fill_search_text} (V124) — trigger tính cột {@code search_text} lúc
 * lưu, hàm này tính từ khoá lúc tìm. Hai bên lệch nhau là tìm hụt mà không có lỗi nào báo ra.
 */
public final class ContactNormalizer {

    private static final Pattern PHONE_SEPARATORS = Pattern.compile("[\\s.\\-()]");
    /** Di động 10 số (03/05/07/08/09) hoặc cố định 11 số (02x) — kế hoạch đánh số hiện hành. */
    private static final Pattern VN_PHONE = Pattern.compile("^(0[35789]\\d{8}|02\\d{9})$");
    /** Số di động gõ thiếu số 0 đầu: đầu số 3/5/7/8/9 + 8 chữ số. */
    private static final Pattern MOBILE_WITHOUT_ZERO = Pattern.compile("^[35789]\\d{8}$");
    private static final Pattern PHONE_LIKE = Pattern.compile("^\\+?\\d{6,}$");
    private static final Pattern COMBINING_MARKS = Pattern.compile("\\p{M}+");
    private static final Pattern WHITESPACE = Pattern.compile("\\s+");

    private ContactNormalizer() {}

    /**
     * Chuẩn hoá số điện thoại Việt Nam về dạng {@code 0xxxxxxxxx}.
     *
     * @return {@code null} khi đầu vào rỗng
     * @throws IllegalArgumentException khi không phải số điện thoại Việt Nam hợp lệ
     */
    public static String normalizePhone(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        String s = PHONE_SEPARATORS.matcher(raw.trim()).replaceAll("");
        if (s.startsWith("+84")) {
            s = "0" + s.substring(3);
        } else if (s.startsWith("84") && s.length() >= 11) {
            s = "0" + s.substring(2);
        } else if (MOBILE_WITHOUT_ZERO.matcher(s).matches()) {
            s = "0" + s;
        }
        // "+84 0912…" → "00912…": người dùng gõ cả mã quốc gia lẫn số 0 đầu
        if (s.startsWith("00")) {
            s = s.substring(1);
        }
        if (!VN_PHONE.matcher(s).matches()) {
            throw new IllegalArgumentException("Số điện thoại không hợp lệ: " + raw.trim());
        }
        return s;
    }

    /** Địa chỉ thư: bỏ khoảng trắng hai đầu, viết thường; rỗng thành {@code null}. */
    public static String normalizeEmail(String raw) {
        if (raw == null || raw.isBlank()) {
            return null;
        }
        return raw.trim().toLowerCase(Locale.ROOT);
    }

    /**
     * Bỏ dấu tiếng Việt và viết thường: "Nguyễn Đức" → "nguyen duc". Nhận cả chữ dựng sẵn (NFC)
     * lẫn chữ tách dấu (NFD, bàn phím macOS/iOS) — cùng kết quả.
     */
    public static String foldAccents(String s) {
        if (s == null) {
            return "";
        }
        String noD = s.replace('đ', 'd').replace('Đ', 'D');
        String nfd = Normalizer.normalize(noD, Normalizer.Form.NFD);
        return COMBINING_MARKS.matcher(nfd).replaceAll("").toLowerCase(Locale.ROOT);
    }

    /**
     * Từ khoá người dùng gõ → các từ để so với {@code search_text}; khách khớp khi chứa ĐỦ mọi từ
     * (không cần đứng liền nhau — "bao 0977" tìm được "Vũ Quốc Bảo … 0977888999").
     *
     * <p>Cả chuỗi trông như số điện thoại ("+84 912 345 678") thì giữ làm MỘT từ và quy về dạng
     * đã lưu; không thì tách theo khoảng trắng, từ toàn số bỏ dấu chấm/gạch ("0912.345").
     */
    public static List<String> searchTokens(String q) {
        if (q == null || q.isBlank()) {
            return List.of();
        }
        String compact = PHONE_SEPARATORS.matcher(q.trim()).replaceAll("");
        if (PHONE_LIKE.matcher(compact).matches()) {
            return List.of(phoneQuery(compact));
        }
        List<String> tokens = new ArrayList<>();
        for (String part : WHITESPACE.split(q.trim())) {
            String digits = PHONE_SEPARATORS.matcher(part).replaceAll("");
            String token = PHONE_LIKE.matcher(digits).matches() ? phoneQuery(digits) : foldAccents(part);
            if (!token.isEmpty()) {
                tokens.add(token);
            }
        }
        return tokens;
    }

    /** Số đầy đủ thì quy về dạng lưu; số dở dang ("0912345") giữ nguyên chữ số để khớp một phần. */
    private static String phoneQuery(String compact) {
        try {
            return normalizePhone(compact);
        } catch (IllegalArgumentException partial) {
            String digits = compact.replace("+", "");
            return digits.startsWith("84") && compact.startsWith("+") ? "0" + digits.substring(2) : digits;
        }
    }
}
