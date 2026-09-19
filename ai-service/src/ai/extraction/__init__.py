"""UC029 — Trích xuất tín hiệu quan tâm bằng JSON Schema nghiêm ngặt (§5.11).

Ranh giới với UC030, đừng lẫn:
    UC029: LLM  →  đặc trưng   (thư mục này)
    UC030: XGBoost → điểm 0–100 (``src/ai/scoring/``)

NGƯỠNG NGHIỆM THU: tỉ lệ lỗi xác thực < **2%** trên 30 hội thoại test (Ngày 31).

Lược đồ ``LeadSignal`` — ``extra='forbid'``, trường lạ gây LỖI chứ không bị bỏ qua:

    intent_level   cold | warm | hot
    budget_vnd     >= 0
    timeline_days  0–1095
    company_size   >= 1
    contact_phone  theo mẫu số Việt Nam
    products       tối đa 10
    evidence       1–5 TRÍCH DẪN NGUYÊN VĂN, BẮT BUỘC

**Không có ``evidence`` thì trường tương ứng bị coi là bịa và loại ở bước validate.**
Đây là cơ chế chống bịa đặt của UC029 — không phải một trường tuỳ chọn cho đẹp.

VÒNG SỬA LỖI ĐÚNG MỘT LẦN, không phải retry mù
------------------------------------------------
Pydantic ném ``ValidationError`` → gửi lại cho LLM **đúng thông báo lỗi đó** và yêu
cầu sửa. Lần thứ hai vẫn hỏng thì **bỏ**, ghi telemetry, **không cố sửa bằng regex**.

Vá bằng regex là cách biến một lỗi nhìn thấy được thành một lỗi im lặng: dữ liệu
vẫn vào được DB nhưng không còn tương ứng với điều mô hình thực sự đọc ra.
"""
