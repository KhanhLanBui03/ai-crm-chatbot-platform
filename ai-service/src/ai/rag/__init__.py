"""Đường ống RAG tiếng Việt — 11 chặng (kế hoạch mục 7.1).

    ingest/    1. trích xuất  2. chuẩn hóa NFC  3. chia đoạn ~500 token  4. tách từ
               5. nhúng theo lô 32  6. đánh chỉ mục
    retrieve/  7. truy hồi song song vector + BM25, mỗi làn 30 ứng viên
               8. hợp nhất RRF hằng số 60 — CHỈ dùng thứ hạng, không dùng điểm thô
                  nên không phải chuẩn hoá hai thang điểm khác nhau
    rerank/    9. cross-encoder, CÓ ĐIỀU KIỆN — chỉ chạy khi AMBIGUITY_GAP < 0,15
                  (chênh điểm RRF giữa hạng 1 và hạng 3). Chạy trên 12 ỨNG VIÊN đầu.
    generate/ 10. đưa 5 đoạn vào lời nhắc, sinh câu trả lời có trích dẫn
              11. xác minh tính bám nguồn

Ngưỡng — kế hoạch 49 ngày, Ngày 19 và Ngày 25:
    Sàn liên quan toàn tập 0,25 · sàn từng đoạn 0,15
    Hybrid phải thắng dense-only >= 5 điểm recall@5
    Cổng bật rerank: >= 5 điểm nDCG@5 VÀ p95 /chat vẫn < 4 s
    Tỉ lệ lượt kích hoạt rerank kỳ vọng 30-40%
    recall@5 >= 0,85 · độ phủ trích dẫn >= 0,80 (§1.6)
    Chênh recall@5 giữa 1 tenant và 20 tenant < 3 điểm (§4.5)

Ba quy tắc dễ quên:
- Hàm chuẩn hóa dùng cho tài liệu lúc nạp PHẢI giống hệt hàm dùng cho câu hỏi lúc truy vấn.
- Mọi truy vấn vector BẮT BUỘC lọc tenant_id (ADR-0007) — đây là ranh giới cô lập tenant.
- SET LOCAL hnsw.ef_search = 100 và hnsw.iterative_scan = 'relaxed_order' phải đặt
  trong CÙNG transaction với truy vấn, nếu không HNSW quét xong mới lọc RLS và
  recall sụp đổ mà không có cảnh báo nào (§4.5).

Thí nghiệm liên quan: E1 (chia đoạn), E2 (mô hình nhúng), E3 (chế độ truy hồi),
E4 (xếp hạng lại), E6 (tỉ lệ bịa đặt), E7 (hành vi từ chối).
"""
