"""``bench_cpu.py`` — DELIVERABLE Tuần 3 (Master Plan §5.6, kế hoạch Ngày 20).

Mục đích: tìm "điểm ngọt" phần cứng bằng SỐ ĐO, không bằng phỏng đoán. Bảng sinh ra
từ đây là căn cứ để chốt cấp vCPU S/M/L ở Ngày 21.

CÁCH CHẠY — quan trọng
-----------------------
Chạy **TỪNG SERVICE MỘT, không song song**. Chạy song song thì ba service tranh vCPU
của nhau và mọi con số p95 đo được đều vô nghĩa.

HAI MA TRẬN BẮT BUỘC QUÉT
--------------------------
Ma trận 1 — model × số luồng (cho encoder):
    e5-small · e5-base · bge-m3   ×   2 / 4 / 8 vCPU

Ma trận 2 — khối lượng công việc (cho reranker):
    ce-MiniLM 22M · PhoRanker 135M · bge-reranker 568M
    ×  {12 cặp seq192, 20 cặp seq256, 6 cặp seq128}

Cột bắt buộc điền: model · tham số · vCPU · threads · p50 · p95 · RSS · đạt/không đạt.

HAI ĐIỀU BẢNG NÀY PHẢI CHỨNG MINH ĐƯỢC
---------------------------------------
1. Model nhỏ: tăng vCPU **không** cải thiện p95 (overhead threading lấn át).
2. Model lớn: cấu hình đúng đưa p95 từ vượt ngưỡng về trong ngưỡng.

Nếu bảng không cho thấy hai điều này thì phép đo đang sai ở đâu đó, không phải
"model nào cũng như nhau".

NGƯỠNG
------
Tổng p95 ba service < **480 ms** (§1.6) · p95 phân loại ý định ≤ **60 ms** (§5.3).

Mỗi model BỊ LOẠI phải có ADR ghi rõ **đã thử đòn bẩy nào trong 5 đòn bẩy §5.4.1**
kèm số đo. Một dòng "quá chậm" không có bảng số là KHÔNG ĐỦ để loại một model —
đây là một trong ba điều dễ mất điểm nhất khi nghiệm thu.

TODO: vòng lặp quét hai ma trận, đo p50/p95/RSS, xuất Markdown vào reports/eval/.
"""
