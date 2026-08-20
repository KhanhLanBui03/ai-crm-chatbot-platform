"""Đường ống RAG tiếng Việt — 11 chặng (kế hoạch mục 7.1).

    ingest/    1. trích xuất  2. chuẩn hóa NFC  3. chia đoạn  4. tách từ  5. nhúng  6. đánh chỉ mục
    retrieve/  7. truy hồi song song vector + BM25   8. hợp nhất RRF (k=60)
    rerank/    9. cross-encoder bge-reranker-v2-m3, top-20 -> top-5
    generate/ 10. sinh câu trả lời có trích dẫn  11. xác minh tính bám nguồn

Hai quy tắc dễ quên:
- Hàm chuẩn hóa dùng cho tài liệu lúc nạp PHẢI giống hệt hàm dùng cho câu hỏi lúc truy vấn.
- Mọi truy vấn vector BẮT BUỘC lọc tenant_id (ADR-0007) — đây là ranh giới cô lập tenant.

Thí nghiệm liên quan: E1 (chia đoạn), E2 (mô hình nhúng), E3 (chế độ truy hồi),
E4 (xếp hạng lại), E6 (tỉ lệ bịa đặt), E7 (hành vi từ chối).
"""
