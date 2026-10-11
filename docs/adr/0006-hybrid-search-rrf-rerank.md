# ADR-0006 — Tìm kiếm lai vector + BM25, hợp nhất RRF, xếp hạng lại bằng cross-encoder

- **Trạng thái:** Chấp nhận — cập nhật 06/10 và 11/10/2026
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

## Cập nhật 11/10/2026 — rerank thật, BẬT, 20 ứng viên

**Người dùng chốt 11/10 (Ngày 15 Khối A).** Số đo đầy đủ: `docs/report/rerank-ngay15-2026-10-11.md`.

**Model:** `BAAI/bge-reranker-v2-m3` @ `953dc6f6`, ONNX INT8 động per-channel (`int8-93cd7fb0`), thay bản
giả Jaccard. Cổng parity đo **thứ hạng**: nDCG@5 sau rerank INT8 − fp32 = +0,54 (N = 12) / −0,23 (N = 20)
điểm, dưới ngưỡng 1 điểm ⇒ ship INT8.

**Kết quả trên bộ vàng v1** (100 câu có đáp án, ai-rerank thật, paired bootstrap B = 10.000):

| | recall@5 | nDCG@5 | Δ nDCG@5 so với không rerank [KTC 95%] |
|---|---|---|---|
| hybrid, không rerank | 0,740 | 0,631 | — |
| rerank 12 ứng viên | 0,800 | 0,705 | +7,5 [+3,0; +12,2] |
| rerank 20 ứng viên, chỉ khi mơ hồ (ship) | **0,870** | **0,752** | **+12,1 [+6,2; +18,5]** |

**Cổng bật của ADR này — "≥ 5 điểm nDCG@5 VÀ p95 chat < 4 s":**
- Nửa chất lượng **ĐẠT** ở cả 12 lẫn 20 ứng viên, KTC không chứa 0.
- Nửa độ trễ **TRƯỢT xa và không áp dụng**: người dùng chốt 11/10/2026 độ trễ chưa là cổng (các ngưỡng độ
  trễ là số kế hoạch). Đo ở máy dev, một lượt rerank 20 cặp p50 10,7 s / p95 13,0 s ở 2 vCPU (30 câu);
  p50 15,5 s / p95 36,2 s ở 4 vCPU (100 câu, tải nền cao hơn). Ghi đủ, không giấu.

**Số ứng viên: 20, không phải 12.** Quay về con số của Quyết định gốc ở trên. Ngày 8 hạ xuống 12 vì giả định
"đoạn đúng ngoài top-12 gần như không bao giờ được rerank kéo về top-5" — đã đo và sai: trần recall@5 khi xếp
hoàn hảo là 0,83 với 12 ứng viên (không bao giờ tới 0,85 của §1.6), 0,95 với 20; đo thật 0,80 so với 0,87.

**Cổng mơ hồ giữ nguyên `AMBIGUITY_GAP = 0,15`** dù đánh dấu 93% câu (kỳ vọng 30–40%): "chỉ khi mơ hồ" mất
đúng 1 câu so với "mọi câu" (0,87 so với 0,88). Hiệu chỉnh là đổi chất lượng lấy độ trễ — để sau.

**Hệ quả:**
- `RERANK_ENABLED` mặc định **bật**; `SO_UNG_VIEN_RERANK = 20`; hạn chờ ai-rerank 60 s (`RERANK_TIMEOUT_S`).
- **ai-rerank lỗi thì giữ thứ hạng RRF** (§3.8.1) — vá ở `answerer.py`; trước đó hỏng cả lượt chat.
- java-core phải chờ ai-service ≥ 90 s (`AI_CHAT_TIMEOUT`, mặc định của nó 10 s). Chuỗi tăng dần: 60 < 90 < 120 s
  (ALB). Giữ 10 s thì phần lớn lượt chat qua widget không có câu trả lời.
- Thêm ~1 GB RAM cho ai-rerank. Trên máy dev 8 GB, cần chat nhanh lúc làm giao diện thì đặt
  `RERANK_ENABLED=false` (recall@5 về 0,74) — đổi biến môi trường, không đổi code.

**Đánh đổi:** chọn chất lượng truy hồi (lần đầu đạt ngưỡng recall@5 của §1.6) đổi lấy lượt chat chậm thêm
~10–15 s trên máy dev. Lên cloud x86 thì đo lại độ trễ; nếu khi đó độ trễ trở thành cổng, đòn bẩy theo thứ
tự đã có số hoặc còn rẻ để thử: hiệu chỉnh cổng mơ hồ · `RERANK_MAX_LENGTH` 512 → 256 · 12 ứng viên (mất ~7
điểm recall@5).
