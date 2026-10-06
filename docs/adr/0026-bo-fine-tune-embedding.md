# ADR-0026 — Bỏ fine-tune embedding: ship bge-m3 pretrained INT8

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-09-27 (quyết định) · ghi thành ADR 2026-10-06
- **Làn sở hữu:** Track B (module AI)
- **Quan hệ:** sửa kế hoạch Ngày 6–7 của `ai-service/planning.md` · liên quan
  [ADR-0021](0021-cong-parity-int8-truot-phan-xu-bang-recall.md) (encoder INT8) ·
  [ADR-0006](0006-hybrid-search-rrf-rerank.md) (truy hồi lai)

## Bối cảnh

Kế hoạch 21 ngày dành Ngày 6–7 cho một vòng fine-tune `BAAI/bge-m3` trên chính kho tri thức:
1. **Ngày 6:** khai thác cặp huấn luyện. Positive là (câu hỏi sinh từ đoạn, đoạn đó); hard negative là
   đoạn lọt top-5 hybrid nhưng sai. Tách tập giữ lại theo **tài liệu**. Phóng notebook
   `07_finetune_embedding.ipynb` lên Kaggle GPU qua đêm.
2. **Ngày 7:** export ONNX, lượng tử hoá INT8, cổng parity, nhúng lại toàn kho, rồi so Recall@5 và
   nDCG@5 giữa fine-tune và pretrained bằng paired bootstrap.

Ngày 27/09 lịch đã trễ: Ngày 6 chưa có ai-embed thật, chưa có bộ vàng, chưa có baseline. Người dùng
quyết định **bỏ hẳn** phần fine-tune, không phải hoãn, với lý do "mục tiêu chạy ra kết quả trước đã".

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Fine-tune như kế hoạch | Có một chương thực nghiệm riêng (fine-tune ↔ pretrained, kèm KTC 95%) | Cần bộ vàng, hybrid chạy được (để lấy hard negative) và Kaggle GPU trước tiên. Ngày 6–7 không có thứ nào sẵn |
| B. **Bỏ hẳn** | Dồn thời gian cho luồng chính (UC023 end-to-end). Không còn nhánh model thứ hai phải quản lý | Mất chương thực nghiệm fine-tune |
| C. Hoãn sang sau 11/10 | Giữ được khả năng có chương đó | Treo một nhánh dở dang trong kế hoạch. Các ngày sau vẫn phải viết hai đường (có/không fine-tune) |

## Quyết định

Không fine-tune encoder. Ship `BAAI/bge-m3` **pretrained**, lượng tử hoá INT8, chạy lô 1 trong
`ai-embed`.

## Lập luận

Lý do chính là lý do của người dùng: ưu tiên luồng chính chạy được. Hai lập luận kỹ thuật bổ sung
(AI ghi 06/10, sau khi có số đo):

- **Kho mẫu nhỏ so với model.** Kho có 19 tài liệu, 190 đoạn; model có ~568 triệu tham số. Tách tập
  giữ lại theo tài liệu để khỏi thổi phồng chỉ số thì phía huấn luyện chỉ còn vài trăm cặp. Như vậy dễ
  học thuộc văn phong của chính mấy tài liệu đó hơn là học được điều tổng quát.
- **Baseline pretrained đã dùng được:** recall@5 dense 0,800 trên bộ vàng v1 (ADR-0006, cập nhật
  06/10). Chỗ yếu đo được tập trung ở câu không dấu (0,29). Đây là việc hẹp, có thể nhắm riêng về
  sau, không cần cả một vòng fine-tune toàn kho.

## Đánh đổi

- **Mất một chương thực nghiệm** (fine-tune ↔ pretrained, biểu đồ hiệu số kèm KTC 95%). Chương 5 bù
  bằng E3 (dense / sparse / hybrid, 1 ↔ 20 tenant) và phát hiện về INT8 ghép lô và INT8 theo nền tảng
  (ADR-0021).
- **Không thử được cách sửa trực tiếp nhất cho câu không dấu.** Fine-tune có tăng cường dữ liệu bỏ dấu
  nhắm đúng điểm yếu 0,29 → ghi vào *Hướng phát triển*.
- Cùng hướng ưu tiên, ngày 06/10 người dùng bỏ luôn phép đo fp32 ↔ INT8 (ADR-0021 cập nhật 2). Vì
  vậy encoder ship mà **không có đối chứng nào**: chỉ có số tuyệt đối trên bộ vàng.

## Hệ quả

- `ai-service/planning.md`:
  - Ngày 6: bỏ các ô khai thác cặp, tách tập giữ lại, notebook 07 (gạch 27/09);
  - Ngày 7: viết lại thành chốt encoder và bảng thoát M1;
  - Ngày 8: bỏ dòng "truy hồi chạy trên embedding đã fine-tune".
- Không tạo `notebooks/07_finetune_embedding.ipynb`. Không có `MODEL_CARD_embedding` v2.
  `artifacts/MODEL_REGISTRY.md` chỉ có dòng pretrained.
- Cột `embedding_model` / `embedding_version` trên `knowledge.knowledge_chunks` (V203) vẫn giữ: nó vẫn
  cần cho mock → INT8, fp32 ↔ INT8, và đổi nền tảng `ai-embed`.
- Báo cáo: chương 5 không có mục fine-tune. *Hướng phát triển* ghi fine-tune có tăng cường câu không
  dấu, cùng điều kiện tiên quyết: một tập phát triển tách khỏi bộ vàng.
