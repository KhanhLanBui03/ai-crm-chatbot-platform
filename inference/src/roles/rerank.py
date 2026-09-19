"""``MODEL_ROLE=rerank`` — cross-encoder. UC023.

Endpoint: ``POST /v1/rerank`` · ``GET /ready`` · ``GET /v1/model``

Ngân sách độ trễ: p95 **300 ms** (§5.3). Tần suất: ~30-40% của nhánh RAG.

CHẠY CÓ ĐIỀU KIỆN, KHÔNG CHẠY MỌI LƯỢT
----------------------------------------
Bên gọi (``ai-service/src/ai/rag/``) chỉ gọi khi ``AMBIGUITY_GAP`` < **0,15** —
chênh điểm RRF giữa hạng 1 và hạng 3. Rerank trên **12 ứng viên** đầu, không phải 20.

CỔNG QUYẾT ĐỊNH BẬT RERANK — Ngày 25
-------------------------------------
Chỉ bật nếu đồng thời: thêm >= **5 điểm nDCG@5** VÀ p95 ``/chat`` vẫn < **4 s**.
Đặt sau feature flag ``RERANK_ENABLED`` để cắt được ngay nếu Ngày 28 chưa demo kịp
(đường lùi đã định trước: cắt rerank + UC024/UC028, dồn sang Tuần 6).

TODO: nạp session, chấm cặp (query, chunk), trả thứ hạng mới.
"""
