package com.thesis.crm.engagement.util;

import java.text.Normalizer;
import java.util.Arrays;
import java.util.Locale;
import java.util.Objects;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Chuẩn hoá dữ liệu danh bạ — UC016. Thuần hàm, không phụ thuộc Spring, để test dễ.
 *
 * <p><b>Số điện thoại</b> quy về một dạng duy nhất {@code 0xxxxxxxxx} trước khi lưu: cùng một số
 * có thể được gõ "0912 345 678", "0912.345.678", "+84 912 345 678". Lưu nguyên thì kiểm trùng
 * bỏ sót và luồng gợi ý hợp nhất không chạy.
 *
 * <p><b>Chuỗi tìm kiếm</b> = tên + thư + số điện thoại, bỏ dấu tiếng Việt, viết thường. Cột
 * {@code search_text} (V124) lưu chuỗi này để tìm "nguyen" ra "Nguyễn" mà không cần extension
 * {@code unaccent} trong CSDL. Phép bỏ dấu ở đây PHẢI cho cùng kết quả với {@code translate()}
 * trong V124 (bảng ký tự điền dữ liệu cũ).
 */
public final class ContactNormalizer {

    private static final Pattern PHONE_SEPARATORS = Pattern.compile("[\\s.\\-()]");
    private static final Pattern VN_PHONE = Pattern.compile("^0\\d{9,10}$");
    private static final Pattern COMBINING_MARKS = Pattern.compile("\\p{M}+");

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

    /** Bỏ dấu tiếng Việt và viết thường: "Nguyễn Đức" → "nguyen duc". */
    public static String foldAccents(String s) {
        if (s == null) {
            return "";
        }
        String noD = s.replace('đ', 'd').replace('Đ', 'D');
        String nfd = Normalizer.normalize(noD, Normalizer.Form.NFD);
        return COMBINING_MARKS.matcher(nfd).replaceAll("").toLowerCase(Locale.ROOT);
    }

    /** Giá trị cột {@code search_text}: tên + thư + số điện thoại đã bỏ dấu, viết thường. */
    public static String searchText(String fullName, String email, String phone) {
        return Arrays.stream(new String[] {fullName, email, phone})
                .filter(Objects::nonNull)
                .map(String::trim)
                .filter(v -> !v.isEmpty())
                .map(ContactNormalizer::foldAccents)
                .collect(Collectors.joining(" "));
    }

    /**
     * Từ khoá người dùng gõ → chuỗi dùng để so với {@code search_text}.
     * Từ khoá trông như số điện thoại ("+84 912…") được quy về {@code 0912…} để khớp cách lưu.
     */
    public static String searchKeyword(String q) {
        if (q == null || q.isBlank()) {
            return null;
        }
        String trimmed = q.trim();
        String digitsOnly = PHONE_SEPARATORS.matcher(trimmed).replaceAll("");
        if (digitsOnly.matches("^\\+?\\d{6,}$")) {
            if (digitsOnly.startsWith("+84")) {
                return "0" + digitsOnly.substring(3);
            }
            return digitsOnly.replace("+", "");
        }
        return foldAccents(trimmed);
    }
}
