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

## Cập nhật 06/10/2026 — số ứng viên, kết quả E3, giữ quyết định

**Số ứng viên: 30 mỗi làn, không phải top-20.** Kế hoạch 21 ngày (Ngày 6, `hybrid_search(pool=30)`)
chốt 30; code ở `ai-service/src/ai/rag/retrieve/hybrid.py` (`UNG_VIEN_MOI_LAN = 30`). Rerank vẫn
nhận **12** ứng viên đầu sau RRF (Ngày 8), không phải 20.

**Kết quả E3 trên bộ vàng v1** (100 câu có đáp án; bge-m3 INT8 qua `ai-embed` container; báo cáo
`docs/report/uc023-ngay6-2026-10-06.md` §6):

| | recall@5 | nDCG@5 |
|---|---|---|
| dense | 0,800 | 0,678 |
| sparse | 0,530 | 0,410 |
| hybrid (RRF k = 60) | 0,740 | 0,631 |

- Hybrid − dense = **−6,0 điểm, KTC 95% [−13; +1]**. Cổng Ngày 6 "hybrid ≥ dense + 5" **trượt**.
- Lập luận ở trên ("vector trượt số liệu, mã sản phẩm") **không thấy** trên bộ này: với câu hỏi con
  số, dense vẫn hơn hybrid.
- Lập luận "hai làn bù nhau" **có thấy**, nhưng chỉ ở câu không dấu: dense 0,29, hybrid 0,43.
  Phần chẩn đoán theo kiểu gõ đo trên đường chạy tay macOS (báo cáo §4); hai đường lệch nhau 1 câu.
- Ở câu có dấu, làn từ khoá yếu (0,53) kéo RRF xuống: 0,88 → 0,82.

**Quyết định giữ nguyên (người dùng chốt 06/10):** ship hybrid RRF, không đổi sang dense-only, không
đổi RRF thành tổng có trọng số. Ba lý do:
1. Hiệu số chưa có ý nghĩa thống kê.
2. Khách nhắn chat thật gõ không dấu nhiều, mà bộ vàng chỉ có 14% câu không dấu. Kho mẫu có
   `cau-hoi-giao-hang-khong-dau.txt`, tổng hợp từ tin nhắn fanpage.
3. Chỉnh trọng số trên chính bộ vàng là overfit phép đo.

**Rerank không bị cắt** dù điều kiện thoát M1 #3 trượt. Luật cắt của kế hoạch viết cho trường hợp
trễ lịch, còn rerank là tầng có thể sửa nhiễu khi gộp hai làn. Vẫn đặt sau feature flag, mặc định
TẮT, cổng bật ≥ 5 điểm nDCG@5 và p95 chat < 4 s.

**Đánh đổi thêm:** ship cấu hình có điểm ước lượng thấp hơn phương án thay thế 6 điểm recall@5 trên
bộ vàng hiện có. Nếu bộ vàng mở rộng ở Ngày 13 vẫn cho hybrid < dense với KTC không chứa 0, thì
phải mở lại quyết định này bằng một ADR thay thế.
