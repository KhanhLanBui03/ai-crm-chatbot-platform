-- V116 — Mốc chạm 80% và mốc chạm 100% của từng hạn mức.
-- UC006 · UC018
--
-- UC018 "Tham số và ngưỡng": "Ngưỡng cảnh báo hạn mức 80% (warned_at), ngưỡng chặn 100%
-- (blocked_at)". UC006 hậu điều kiện: "Mốc chạm 80% và mốc chạm 100% được ghi lại và hiển
-- thị kèm thời điểm". Hợp đồng dashboard đã khai HanMucSuDung.warnedAt / blockedAt từ trước —
-- V102 thì chưa có cột nào để đọc ra hai giá trị đó.
--
-- Vì sao là CỘT chứ không tính lúc đọc: phần trăm thì tính lại được từ used/quota, nhưng
-- THỜI ĐIỂM chạm mốc thì không. Sau khi gỡ bớt tài liệu, tỉ lệ tụt xuống dưới 80% mà lần
-- chạm mốc vẫn là sự kiện đã xảy ra trong chu kỳ.
--
-- Ghi MỘT LẦN mỗi chu kỳ, không ghi đè: chu kỳ mới là dòng usage_records mới (UNIQUE
-- (subscription_id, metric)), nên hai cột tự về NULL mà không cần job nào dọn.

ALTER TABLE platform.usage_records
    ADD COLUMN warned_at  timestamptz,
    ADD COLUMN blocked_at timestamptz;

-- Chạm trần thì chắc chắn đã qua mốc cảnh báo — dòng nào có blocked_at mà thiếu warned_at
-- là dấu hiệu code ghi sai thứ tự.
ALTER TABLE platform.usage_records
    ADD CONSTRAINT ck_usage_moc_theo_thu_tu
        CHECK (blocked_at IS NULL OR warned_at IS NOT NULL);

COMMENT ON COLUMN platform.usage_records.warned_at IS
    'Lần đầu used_value chạm 80% quota_value trong chu kỳ. UC006 4.1 — hiển thị kèm thời điểm.';
COMMENT ON COLUMN platform.usage_records.blocked_at IS
    'Lần đầu used_value chạm 100% quota_value trong chu kỳ. Từ đây lượt tiêu thụ mới bị từ chối '
    '(UC018: 409 DOCUMENT_QUOTA_EXCEEDED). UC006 4.2.';

-- Không GRANT, không bật RLS, không gắn trigger: ADD COLUMN kế thừa cả ba từ bảng
-- (V111 GRANT, V112 RLS + trg_touch_updated_at). Bẫy 0 của README chỉ áp cho bảng MỚI.
