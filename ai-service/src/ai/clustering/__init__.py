"""UC038 — phân cụm chủ đề hội thoại. [PRODUCTION]

Lớp 2 của SCR052 "Chủ đề hội thoại": bộ phân loại chỉ nhận ra 7 ý định định sẵn, phân cụm cho thấy
khách THẬT SỰ hỏi gì. Mỗi kỳ (hằng tuần, tách riêng từng doanh nghiệp):

    kho.py         đọc câu hỏi đầu của mỗi hội thoại · ghi kết quả kỳ (V215) · đọc kỳ mới nhất
    dat_ten.py     đặt tên cụm — LLM nếu có, luật từ khoá nếu không (Rule → ML → LLM)
    cong_viec.py   một kỳ cho một doanh nghiệp: ngưỡng → vector → phân cụm → đặt tên → ghi
    __main__.py    chạy tay: ``python -m src.ai.clustering [--tenant <uuid>]``

Phần tính toán (giảm chiều 50, k-means k = 5…25, silhouette, hạt giống ghim) chạy ở image ai-inference
(``POST /v1/topics/cluster``), KHÔNG ở đây: ai-service không mang thư viện học máy (luật 5).
"""
