package com.thesis.crm.common.audit;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

/**
 * Che dữ liệu cá nhân trong phần trước/sau của nhật ký kiểm toán (UC040) — đủ để người đọc nhận ra "đổi số
 * điện thoại" hay "đổi tên" mà không đọc được giá trị thật.
 *
 * <p>Kiểu che đoán theo TÊN trường: có {@code phone} → giữ 3 số đầu + 3 số cuối; có {@code email} → giữ ký tự
 * đầu và tên miền; có {@code name} → giữ chữ cái đầu mỗi từ; còn lại → giữ 2 ký tự đầu. Trường không nằm trong
 * danh sách dữ liệu cá nhân thì giữ nguyên.
 */
public final class PersonalDataMasker {

    private static final String SAO = "***";

    private PersonalDataMasker() {
    }

    /** Bản sao đã che các trường trong {@code personalKeys}; {@code null} vẫn là {@code null}. */
    public static Map<String, Object> mask(Map<String, Object> data, Set<String> personalKeys) {
        if (data == null) {
            return null;
        }
        Map<String, Object> out = new LinkedHashMap<>();
        data.forEach((k, v) -> out.put(k, personalKeys.contains(k) && v != null ? maskValue(k, v.toString()) : v));
        return out;
    }

    static String maskValue(String key, String v) {
        String k = key.toLowerCase(Locale.ROOT);
        if (v.isEmpty()) {
            return v;
        }
        if (k.contains("phone")) {
            return v.length() <= 6 ? SAO : v.substring(0, 3) + SAO + v.substring(v.length() - 3);
        }
        if (k.contains("email")) {
            int at = v.indexOf('@');
            return at <= 0 ? SAO : v.charAt(0) + SAO + v.substring(at);
        }
        if (k.contains("name")) {
            StringBuilder b = new StringBuilder();
            for (String tu : v.trim().split("\\s+")) {
                if (!tu.isEmpty()) {
                    b.append(b.isEmpty() ? "" : " ").append(tu.charAt(0)).append(SAO);
                }
            }
            return b.toString();
        }
        return v.length() <= 2 ? SAO : v.substring(0, 2) + SAO;
    }
}
