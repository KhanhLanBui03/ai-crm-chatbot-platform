package com.thesis.crm.engagement.widget;

import java.net.IDN;
import java.net.URI;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Set;

/**
 * UC009 bước 10 — đối chiếu tên miền gốc của trang đang nhúng widget với danh sách được phép.
 *
 * <p>Quy tắc đã chốt với nhóm:
 * <ul>
 *   <li>{@code congtya.vn} nhận {@code congtya.vn} và {@code www.congtya.vn}, KHÔNG nhận
 *       {@code shop.congtya.vn};</li>
 *   <li>{@code *.congtya.vn} nhận mọi tên miền con và cả {@code congtya.vn};</li>
 *   <li>{@code localhost} chỉ được nhận khi khai rõ — không có ngoại lệ ngầm cho môi trường dev;</li>
 *   <li>danh sách rỗng = từ chối hết (an toàn mặc định).</li>
 * </ul>
 * Bỏ qua cổng và giao thức: người dùng hay dán cả {@code https://congtya.vn/} vào ô khai báo.
 */
public final class WidgetOriginPolicy {

    /**
     * Đuôi "dùng chung" ở Việt Nam: {@code *.com.vn} nghĩa là mọi công ty .com.vn, không phải tên miền
     * con của MỘT doanh nghiệp. Không phải danh sách Public Suffix đầy đủ — chỉ các đuôi hay gặp.
     */
    private static final Set<String> SHARED_SECOND_LEVEL =
            Set.of("com", "net", "org", "edu", "gov", "ac", "co", "info", "biz", "name", "pro", "health", "int");

    private WidgetOriginPolicy() {}

    /**
     * {@code *.vn}, {@code *.com}, {@code *.com.vn}… phủ hàng triệu website — gõ nhầm một dòng là mất
     * toàn bộ lớp chặn nhúng trái phép. Ký tự sao phải đứng trước tên miền CỦA doanh nghiệp.
     */
    public static boolean isTooBroadWildcard(String rule) {
        if (!rule.startsWith("*.")) {
            return false;
        }
        String[] labels = rule.substring(2).split("\\.");
        return labels.length < 2 || (labels.length == 2 && SHARED_SECOND_LEVEL.contains(labels[0]));
    }

    /** Tên máy của header {@code Origin}; rỗng khi thiếu hoặc không đọc được. */
    public static Optional<String> hostOf(String origin) {
        if (origin == null || origin.isBlank() || "null".equals(origin.trim())) {
            return Optional.empty();
        }
        try {
            String host = URI.create(origin.trim()).getHost();
            return host == null || host.isBlank()
                    ? Optional.empty()
                    : Optional.of(host.toLowerCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            return Optional.empty();
        }
    }

    public static boolean allowed(String origin, List<String> allowedDomains) {
        Optional<String> host = hostOf(origin);
        if (host.isEmpty() || allowedDomains == null) {
            return false;
        }
        for (String raw : allowedDomains) {
            String rule = normalize(raw);
            if (rule.isEmpty()) {
                continue;
            }
            if (isTooBroadWildcard(rule)) {
                continue;   // lớp thứ hai: dữ liệu cũ lưu trước khi có kiểm tra ở WidgetConfigService
            }
            if (rule.startsWith("*.")) {
                String apex = rule.substring(2);
                if (host.get().equals(apex) || host.get().endsWith("." + apex)) {
                    return true;
                }
            } else if (host.get().equals(rule) || host.get().equals("www." + rule)) {
                return true;
            }
        }
        return false;
    }

    /** "https://WWW.CongtyA.vn:443/lien-he" → "www.congtya.vn". */
    static String normalize(String raw) {
        if (raw == null) {
            return "";
        }
        String s = raw.trim().toLowerCase(Locale.ROOT);
        int scheme = s.indexOf("://");
        if (scheme >= 0) {
            s = s.substring(scheme + 3);
        }
        int cut = s.length();
        for (char c : new char[] {'/', ':', '?', '#'}) {
            int i = s.indexOf(c);
            if (i >= 0 && i < cut) {
                cut = i;
            }
        }
        s = s.substring(0, cut);
        // Trình duyệt luôn gửi Origin dạng punycode ("xn--…"); người dùng hay gõ có dấu ("cửahàng.vn")
        boolean wild = s.startsWith("*.");
        String body = wild ? s.substring(2) : s;
        try {
            body = IDN.toASCII(body).toLowerCase(Locale.ROOT);
        } catch (IllegalArgumentException e) {
            // để nguyên — WidgetConfigService sẽ từ chối vì sai dạng
        }
        return wild ? "*." + body : body;
    }
}
