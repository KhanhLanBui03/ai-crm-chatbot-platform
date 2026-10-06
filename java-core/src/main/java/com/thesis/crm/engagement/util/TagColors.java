package com.thesis.crm.engagement.util;

import java.util.List;

/**
 * Màu tự gán cho thẻ mới — UC017. Không thêm bước chọn màu: cùng tên (đã bỏ dấu, viết thường)
 * luôn ra cùng màu, nên "Khách quen" tạo ở đâu cũng một màu. Định dạng {@code #RRGGBB} khớp
 * ràng buộc CHECK của {@code engagement.tags.color} (V105).
 */
public final class TagColors {

    /** 8 màu đủ tương phản trên nền sáng lẫn tối. */
    public static final List<String> PALETTE = List.of(
            "#6366F1", "#0EA5E9", "#10B981", "#F59E0B",
            "#EF4444", "#EC4899", "#8B5CF6", "#14B8A6");

    private TagColors() {}

    public static String forName(String name) {
        String key = ContactNormalizer.foldAccents(name == null ? "" : name.trim());
        return PALETTE.get(Math.floorMod(key.hashCode(), PALETTE.size()));
    }
}
