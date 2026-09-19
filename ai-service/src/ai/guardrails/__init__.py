"""Guardrails — THUẦN PYTHON, không model, không gọi mạng (Master Plan §4.8).

Đây là ràng buộc của §3.9.2, không phải sở thích: guardrails chạy trên **100% lượt
chat** và là cửa vào trước cả bước phân loại ý định. Cho nó phụ thuộc vào một model
hay một lời gọi mạng là đặt một điểm hỏng ngay trước mọi thứ khác.

BA VIỆC
-------
1. ``normalize.py`` — chuẩn hoá tiếng Việt. Xử lý ký tự zero-width, chuẩn hoá
   NFD/NFC, thống nhất ``hoà``/``hòa``, gộp ký tự lặp.

   **Hàm chuẩn hoá dùng cho tài liệu lúc nạp PHẢI giống hệt hàm dùng cho câu hỏi
   lúc truy vấn.** Lệch nhau là truy hồi hụt mà không có lỗi nào báo ra.

2. ``injection.py`` — phát hiện tiêm chỉ thị.
   Ngưỡng: báo nhầm trên câu hỏi bình thường < **1%** (bộ ≥ 60 mẫu, Ngày 22).
   Bộ adversarial: chặn ≥ **90%**, báo nhầm < **2%** (Ngày 41 và Ngày 48).

   Phát hiện tiêm chỉ thị **không chặn luồng**: ghi ``safety_flag`` rồi vẫn định
   tuyến bình thường (UC022, mã ``PROMPT_INJECTION_INPUT`` — "không phải lỗi").

3. ``pii.py`` — PII cho Việt Nam: số điện thoại, CCCD, email.
   **Che ở TẦNG GHI, không phải lúc hiển thị** (UC040, Ngày 37). Che lúc hiển thị
   nghĩa là dữ liệu thật vẫn nằm trong bảng và trong log — chỉ giấu khỏi mắt người
   xem, không giấu khỏi người đọc được DB. Nghị định 13/2023/NĐ-CP, bề mặt T8.

NĂM LỚP PHÒNG THỦ Ở TẦNG KIẾN TRÚC — §4.8, quan trọng hơn regex
-----------------------------------------------------------------
Regex chỉ là lớp ngoài cùng và là lớp yếu nhất. Bốn lớp còn lại — RLS cưỡng bức,
allow-list công cụ ba lớp, validate output bằng Pydantic, và khoá cache có
``tenant_id`` — mới là phần chịu lực.
"""
