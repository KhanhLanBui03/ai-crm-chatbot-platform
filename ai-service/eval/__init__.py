"""Khung đánh giá tự động — 11 thí nghiệm E1..E11 (kế hoạch phần 8).

    golden_set.jsonl    150 câu — tài sản giá trị nhất của đồ án
    adversarial.jsonl   60-80 kịch bản tấn công, dùng cho E9
    configs/            mỗi cấu hình thí nghiệm một file .yaml
    reports/            CSV và HTML sinh tự động (KHÔNG commit)

Quy tắc chạy (mục 8.1):
- Mỗi cấu hình lặp 3 lần, báo cáo trung bình VÀ độ lệch chuẩn.
- temperature = 0, ghim phiên bản mô hình, ghi cả hai vào báo cáo.
- Thay đúng MỘT biến mỗi lần.
- Ghi nhận cả kết quả âm tính — "đắt hơn nhưng không tốt hơn đáng kể" là phát hiện có giá trị.

Dùng thư viện có sẵn (ranx) cho Recall/MRR/nDCG thay vì tự cài đặt công thức (mục 1.2).
"""
