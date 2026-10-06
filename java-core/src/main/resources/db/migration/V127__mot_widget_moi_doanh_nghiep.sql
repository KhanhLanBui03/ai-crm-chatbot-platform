-- ═════════════════════════════════════════════════════════════════════════════
-- V127 — UC009: mỗi doanh nghiệp đúng MỘT Web Widget
-- ═════════════════════════════════════════════════════════════════════════════
-- WidgetConfigService.create() kiểm "đã có widget chưa" rồi mới chèn. Hai quản trị viên bấm
-- "Sinh mã nhúng" cùng lúc thì cả hai cùng thấy "chưa có" → hai widget; màn cấu hình chỉ hiện một,
-- khoá kia mồ côi nhưng vẫn nhận khách. Kiểm-rồi-chèn ở tầng ứng dụng không chống được đua nhau —
-- ràng buộc phải nằm ở CSDL.

CREATE UNIQUE INDEX uq_channels_one_widget
    ON engagement.channels (tenant_id)
    WHERE type = 'WEB_WIDGET';
