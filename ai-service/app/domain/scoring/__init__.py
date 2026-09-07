"""Chấm điểm Lead — trích xuất tín hiệu, gán nhãn, huấn luyện, đánh giá.

Baseline để so là bảng điểm theo luật. Chỉ số: AUC-ROC, Precision@20 (thí nghiệm E8).
Một trong ba con số phải có bằng mọi giá (kế hoạch mục 8.2).

Lưu vector đặc trưng và phiên bản mô hình CÙNG với điểm số vào sales.LEAD_SCORES, để trả lời
được câu hỏi kinh điển của hội đồng: vì sao khách này được 92 điểm?

Ghi qua API của java-core, KHÔNG ghi thẳng vào schema sales (ADR-0002).

Module dự kiến: extract.py, features.py, rules_baseline.py, train.py, evaluate.py
"""
