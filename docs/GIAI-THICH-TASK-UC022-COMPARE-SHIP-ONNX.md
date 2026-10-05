# SO SÁNH NHÁNH ROUTER, CHỐT SHIP VÀ EXPORT ONNX (UC022 — 3/4)

- **Quyết định liên quan:** [ADR-0019](adr/0019-chot-nhanh-ship-intent-router-va-nguong-abstention.md) (có đính chính mục 0)
- **Số liệu gốc:** [`docs/report/router_branches_comparison_report.json`](report/router_branches_comparison_report.json)
- **Tái lập:** `python scripts/evaluate_router_branches_comparison.py --no-export`

> ⚠️ **Viết lại 2026-10-05.** Bản trước trình bày bảng đối đầu "XLM-R 0,8947 vs nhánh C 0,7582",
> KTC bootstrap của hai nhánh, Δ = +0,1381 (p < 0,001), độ trễ 168,2 ms vs 0,182 ms và kết luận
> "nhánh C nhẹ hơn 31.000 lần". **Không con số nào trong đó là số đo về nhánh B:** script sinh dự
> đoán nhánh B ngẫu nhiên (xác suất đúng 88,5%) và gán cứng mọi độ trễ. 0,7582 là của kNN, trong
> khi mô hình export sang ONNX là LogisticRegression.

---

## 1. Yêu cầu của task (kế hoạch 21 ngày) và trạng thái

| Yêu cầu | Trạng thái |
|---|---|
| Đánh giá CẢ HAI nhánh trên cùng 200 câu test, Macro-F1 + KTC 95% bootstrap | **Một nửa** — chỉ nhánh C; nhánh B không có checkpoint trong repo |
| So sánh theo cặp (paired bootstrap) | **Chưa** — cần dự đoán thật của nhánh B |
| Chọn ngưỡng bỏ phiếu trắng từ đường cong, tại điểm ≈ 0,95 | **Có đường cong**; τ đang chạy (0,65) chưa đạt 0,95 — mục 3 |
| Export ONNX INT8 + cổng parity | **Đạt** |
| Ghi ADR chốt nhánh | **Có**, nhưng căn cứ số liệu đã thu hồi — ADR-0019 mục 0 |

---

## 2. Nhánh C — số đo thật

Kiến trúc: `SemanticDenseEmbedder` (feature hashing n-gram ký tự + IDF, 1024 chiều — **không phải
BGE-M3**) → LogisticRegression → ONNX INT8 (35,93 KB).

| Chỉ số (200 câu test) | Giá trị |
|---|---|
| Macro-F1 — LogisticRegression (mô hình ship) | **0,6755** |
| KTC 95% (bootstrap B = 1.000, seed 42) | [0,6131 ; 0,7327] |
| Accuracy | 0,675 |
| Tham khảo: kNN k = 9 cosine (không ship) | Macro-F1 0,7582 |
| Router 3 tầng thật (luật + ONNX + τ) | Macro-F1 0,712 |

**Câu hỏi còn mở:** kNN tốt hơn LogisticRegression 8 điểm Macro-F1 trên cùng embedding, nhưng
LogisticRegression được export. Cần ghi lý do (vd: skl2onnx/kích thước/xác suất hiệu chỉnh) hoặc
đổi mô hình export.

---

## 3. Đường cong bỏ phiếu trắng (tầng 2, LogisticRegression)

| τ | 0,40 | 0,50 | 0,60 | **0,65** | 0,70 | 0,75 | 0,80 |
|---|---|---|---|---|---|---|---|
| Độ chính xác phần giữ lại | 0,794 | 0,850 | 0,911 | **0,924** | 0,937 | 0,943 | 1,000 |
| Coverage | 0,775 | 0,565 | 0,450 | **0,395** | 0,315 | 0,265 | 0,210 |

- Đặc tả UC022: chọn τ tại điểm độ chính xác phần giữ lại ≈ 0,95 → **τ = 0,80**, coverage chỉ 21%.
- Hệ thống đang chạy **τ = 0,65**: 0,924 / 39,5%. Đây là đánh đổi có chủ ý để không đẩy 79% lượt
  sang hỏi lại, và phải trình bày đúng như vậy — **không** ghi "đạt 95%".
- Đồ thị: `reports/eval/router_abstention_curve.png`.

---

## 4. Cổng parity ONNX

| | Giá trị |
|---|---|
| max \|P_sklearn − P_onnx\| | 2,98 × 10⁻⁷ (ngưỡng 10⁻⁴) |
| Khớp nhãn | 200/200 |
| SHA-256 `router_model.onnx` | `0cc5f770af0c6d2b49417021244d6d5d20d7453e87f614855e9aa7b1478ec95e` |
| Trạng thái | **PASSED** |

---

## 5. Độ trễ nhánh C — đo thật

| Phép đo | p50 | p95 |
|---|---|---|
| Embedder băm + ONNX, một câu, CPU Intel/Windows | 0,18 ms | 0,33 ms |
| Riêng ONNX | — | 0,05 ms |

Số dao động giữa các lần chạy (một lần khác: p95 1,66 ms) và chỉ đúng cho embedder băm. Ngân sách
§5.3 (≤ 60 ms) dư rất xa — nhưng lợi thế đó đến từ việc embedder không phải mô hình neural.

---

## 6. Quyết định ship — lý do đúng

**Ship nhánh C** vì đây là **nhánh duy nhất đã được đánh giá** trên tập test và nằm trong ngân sách
độ trễ. Chưa được nói "nhánh C thắng nhánh B theo quy tắc §5.9" — quy tắc đó cần p95 CPU **đo thật**
của XLM-R.

Để hoàn tất so sánh trước ngày nộp:
1. Chạy notebook 05 trên Kaggle (GPU, qua đêm).
2. Xuất `reports/eval/router_branch_b_predictions.jsonl` — mỗi dòng `{"id": ..., "pred": "<INTENT>"}`, đủ 200 câu.
3. Đo p95 suy luận một câu trên CPU, ghi `reports/eval/router_branch_b_latency.json`
   (`{"p95_cpu_ms": ..., "model_size_mb": ..., "measured_on": "..."}`).
4. Chạy lại `python scripts/evaluate_router_branches_comparison.py --no-export` — script tự thêm
   bootstrap theo cặp và áp quy tắc §5.9.

Nếu không kịp: báo cáo ghi "nhánh B chưa đánh giá do giới hạn thời gian" là giới hạn thực nghiệm.
