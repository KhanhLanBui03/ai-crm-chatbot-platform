package com.thesis.crm.engagement.widget;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.List;

/**
 * Giờ làm việc của doanh nghiệp ({@code platform.tenants.business_hours}), dạng
 * {@code {"mon": {"open": "08:00", "close": "17:30"}, ..., "sun": null}} — như màn hồ sơ doanh
 * nghiệp UC004 đang lưu. Phục vụ UC010 7.1–7.2: ngoài giờ AI vẫn trả lời, nhưng câu báo chuyển giao
 * nói rõ khung giờ nhân viên phản hồi.
 *
 * <p>Chưa khai giờ nào (mặc định {@code {}}) = coi như luôn trong giờ: không có căn cứ để bảo khách
 * là ngoài giờ.
 */
public final class BusinessHours {

    private static final String[] KEYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"};
    private static final String[] NHAN = {"Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"};

    private final JsonNode hours;
    private final ZoneId zone;

    public BusinessHours(JsonNode hours, String timezone) {
        this.hours = hours;
        ZoneId z;
        try {
            z = ZoneId.of(timezone == null ? "Asia/Ho_Chi_Minh" : timezone);
        } catch (RuntimeException e) {
            z = ZoneId.of("Asia/Ho_Chi_Minh");
        }
        this.zone = z;
    }

    private boolean configured() {
        if (hours == null || !hours.isObject()) {
            return false;
        }
        for (String k : KEYS) {
            if (hours.hasNonNull(k)) {
                return true;
            }
        }
        return false;
    }

    public boolean isOpen(ZonedDateTime at) {
        if (!configured()) {
            return true;
        }
        ZonedDateTime local = at.withZoneSameInstant(zone);
        JsonNode day = hours.get(KEYS[local.getDayOfWeek().getValue() - 1]);
        LocalTime[] span = span(day);
        if (span == null) {
            return false;
        }
        LocalTime t = local.toLocalTime();
        return !t.isBefore(span[0]) && t.isBefore(span[1]);
    }

    public boolean isOpenNow() {
        return isOpen(ZonedDateTime.now(zone));
    }

    /** "Thứ Hai–Thứ Sáu 08:00–17:30; Thứ Bảy 08:00–12:00" — gộp các ngày liền nhau cùng giờ. */
    public String describe() {
        if (!configured()) {
            return "";
        }
        List<String> parts = new ArrayList<>();
        int i = 0;
        while (i < KEYS.length) {
            String label = label(hours.get(KEYS[i]));
            if (label == null) {
                i++;
                continue;
            }
            int j = i;
            while (j + 1 < KEYS.length && label.equals(label(hours.get(KEYS[j + 1])))) {
                j++;
            }
            parts.add((i == j ? NHAN[i] : NHAN[i] + "–" + NHAN[j]) + " " + label);
            i = j + 1;
        }
        return String.join("; ", parts);
    }

    private static String label(JsonNode day) {
        LocalTime[] s = span(day);
        return s == null ? null : s[0] + "–" + s[1];
    }

    private static LocalTime[] span(JsonNode day) {
        if (day == null || !day.isObject()) {
            return null;
        }
        try {
            LocalTime open = LocalTime.parse(day.path("open").asText());
            LocalTime close = LocalTime.parse(day.path("close").asText());
            return close.isAfter(open) ? new LocalTime[] {open, close} : null;
        } catch (RuntimeException e) {
            return null;
        }
    }
}
