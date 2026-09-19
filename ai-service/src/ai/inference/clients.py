"""Ba backend hoán đổi được cho tầng suy luận — Master Plan §3.4.1.

Chọn bằng biến môi trường ``AI_MODE``:

    remote   gọi sang tầng suy luận. MẶC ĐỊNH ở mọi môi trường vận hành.
    mock     trả dữ liệu giả có seed cố định. Dùng cho CI và khi Frontend/Backend
             cần một bản giả lập ổn định để làm song song.
    offline  nạp model nhẹ ngay trong tiến trình. CHỈ dùng khi lập trình viên không
             có mạng. KHÔNG BAO GIỜ bật ở môi trường (D) AWS EKS.

Cùng một interface ở cả ba chế độ — đó là điều làm cho số đo ở môi trường (C)
chuyển được sang (D) mà không phải sửa lời gọi.

BA BẤT BIẾN KIỂM Ở ``/ready``, FAIL-CLOSED NẾU LỆCH — §3.4.2
-------------------------------------------------------------
1. ``model_id`` đang phục vụ phải khớp ``emb_model`` đã ghim trên từng chunk.
   Lệch nghĩa là vector câu hỏi và vector chỉ mục thuộc hai không gian khác nhau —
   truy hồi vẫn chạy, vẫn trả kết quả, nhưng kết quả vô nghĩa. Đây là kiểu hỏng
   im lặng nguy hiểm nhất của RAG (mã lỗi ``EMBEDDING_MODEL_MISMATCH``).
2. Thứ tự cột đặc trưng phải khớp ``lead_scorer.meta.json``. **Thứ tự cột là hợp
   đồng**, không phải chi tiết hiện thực (§5.10.4).
3. ``OMP_NUM_THREADS`` phải khớp số vCPU được cấp (§5.4).

[CẦN XÁC NHẬN] Payload gửi sang tầng suy luận **không được chứa** ``tenant_id``,
``contact_id`` hay bất kỳ định danh nào — kế hoạch Ngày 41 yêu cầu assert điều này
trên body request trong CI (§4.10, §3.6.3).

TODO: ``EmbedClient`` · ``RerankClient`` · ``ClassifyClient`` theo Protocol chung.
TODO: ba lớp hiện thực remote | mock | offline, chọn bằng factory đọc ``AI_MODE``.
"""
