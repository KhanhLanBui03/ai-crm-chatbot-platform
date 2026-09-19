"""``MODEL_ROLE=embed`` — encoder. UC019 (lập chỉ mục) và UC023 (truy hồi).

Endpoint: ``POST /v1/embed`` · ``POST /v1/embed/batch`` · ``GET /ready`` · ``GET /v1/model``

Ngân sách độ trễ: p95 **120 ms** (§5.3). Tần suất: ~45% lượt chat + toàn bộ luồng index.

BẤT BIẾN 1 — ``model_id`` phải khớp ``emb_model`` đã ghim trên từng chunk
-------------------------------------------------------------------------
Lệch nghĩa là vector câu hỏi và vector chỉ mục thuộc hai không gian khác nhau. Truy
hồi vẫn chạy, vẫn trả về 5 đoạn, nhưng 5 đoạn đó vô nghĩa. Chặn ở ``/ready``, trả
``EMBEDDING_MODEL_MISMATCH``, KHÔNG truy hồi (UC023).

CỔNG CHẶN PARITY — §5.8, Ngày 8
--------------------------------
cosine(fp32, int8) >= **0,995** trên 500 mẫu tiếng Việt. Đây là CỔNG CHẶN, không
phải báo cáo: lượng tử hoá INT8 khi hỏng thì hỏng âm thầm — model vẫn trả vector
đúng số chiều, chỉ là vector sai.

Đo thêm recall@5 trên golden set với cả hai phiên bản, chênh lệch phải < 1 điểm.

[CẦN XÁC NHẬN] Số chiều vector: Master Plan §4.2 ghi 768 (theo e5-base); UC019 và
migration V203 thật ghi **1024**. Kế hoạch Ngày 3 bắt chốt một con số rồi ghi ADR —
chốt muộn thì toàn bộ chỉ mục HNSW phải dựng lại.

TODO: nạp session qua ``session.make_session``, batch 32, chuẩn hoá L2.
"""
