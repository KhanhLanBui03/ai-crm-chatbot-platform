# ADR-0006 — Tìm kiếm lai vector + BM25, hợp nhất RRF, xếp hạng lại bằng cross-encoder

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-19
- **Làn sở hữu:** Track B

## Bối cảnh

<!-- TODO: điền khi thiết kế chi tiết. Nguồn: kế hoạch mục 4.2 -->

## Quyết định

Chạy song song vector (pgvector/HNSW) top-20 và BM25 (`ts_vector`) top-20, hợp nhất bằng Reciprocal Rank Fusion k=60, rồi xếp hạng lại bằng `bge-reranker-v2-m3` từ top-20 xuống top-5.

## Lập luận

Vector bắt được diễn đạt khác nhau nhưng thường trượt tên riêng, mã sản phẩm và số liệu — vốn chiếm tỉ lệ lớn trong câu hỏi khách hàng. BM25 ngược lại. RRF chỉ dùng thứ hạng nên không cần chuẩn hóa thang điểm giữa hai hệ khác nhau, đó là lý do chọn nó thay vì cộng điểm có trọng số.

## Đánh đổi

Xếp hạng lại là chặng tốn thời gian nhất của đường ống. Phải đo và ghi lại độ trễ; nếu vượt ngưỡng thì giảm đầu vào xuống top-12. Xem thí nghiệm E3, E4.

## Hệ quả

<!-- TODO: ảnh hưởng lên schema / giao ước hai làn / vận hành / chương báo cáo -->
