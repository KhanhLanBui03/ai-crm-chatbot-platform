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
| Đánh giá CẢ HAI nhánh trên cùng 200 câu test, Macro-F1 + KTC 95% bootstrap | **Đạt** (2026-10-05) — xem mục 2b |
| So sánh theo cặp (paired bootstrap) | **Đạt** — Δ không có ý nghĩa thống kê |
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

## 2b. Nhánh B và so sánh theo cặp

| Tiêu chí (200 câu test người thật) | Nhánh C — embedder băm + LogReg (ship) | Nhánh B — XLM-R base fine-tune |
|---|---|---|
| Macro-F1 | 0,6755 | **0,7210** |
| KTC 95% bootstrap (B = 1.000) | [0,6131 ; 0,7327] | [0,6606 ; 0,7747] |
| Accuracy | 0,675 | 0,725 |
| p95 CPU một câu, 2 luồng | 0,33 ms (embed + ONNX) | **72,4 ms** (INT8 dynamic) · 91,8 ms (FP32) |
| Kích thước | 35,9 KB ONNX + 72 KB bảng IDF | 1.077 MB |
| Macro-F1 trên validation (dữ liệu template) | — | 0,975 |

**Paired bootstrap B − C** (B = 1.000, seed 42): Δ trung bình +0,044, KTC 95% **[−0,040 ; +0,131]**,
p = 0,151 — **không có ý nghĩa thống kê**.

**Quyết định theo §5.9 — cả hai quy tắc cùng chỉ về nhánh C:**
1. Nhánh B vượt ngân sách độ trễ (p95 72,4 ms > 60 ms, ngay cả bản INT8 nhanh hơn) → loại.
2. Chênh lệch chất lượng không có ý nghĩa → ship nhánh có p95 thấp hơn → nhánh C.

**Lưu ý khi trích dẫn:** nhánh B huấn luyện trên CPU laptop (i5-1235U, 38,8 phút, transformers 4.46.3,
seed 42) bằng `notebooks/05_train_router_xlmr.py`; độ trễ đo trên cùng laptop, batch 1, gồm tokenize
— chưa phải CPU production. Validation 0,975 nhưng test 0,721: cùng hiện tượng lệch phân phối
template ↔ câu người thật như nhánh C. Kết quả gốc: `docs/report/router_branch_b_*.json(l)`.

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

## 6. Quyết định ship

**Ship nhánh C**, theo cả hai quy tắc §5.9 (mục 2b): nhánh B vượt ngân sách độ trễ, và chênh
lệch chất lượng không có ý nghĩa thống kê.
