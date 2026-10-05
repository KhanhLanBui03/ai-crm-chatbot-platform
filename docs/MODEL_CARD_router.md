---
language:
- vi
- en
license: mit
library_name: onnxruntime
tags:
- text-classification
- intent-detection
- onnx
- quantization-int8
- crm
pipeline_tag: text-classification
---

# MODEL CARD — Intent Router (UC022)

> **Mô hình định tuyến ý định 7 nhánh — tầng 2 của router 3 tầng**
> **Kiến trúc thật:** feature hashing n-gram ký tự + IDF (1024 chiều) → LogisticRegression → ONNX INT8
> **Hệ thống:** Nền tảng AI CRM Chatbot Platform (KLTN)

> ⚠️ **Đính chính 2026-10-05.** Bản trước của model card này ghi kiến trúc "BGE-M3 Semantic
> Embeddings", Macro-F1 0,7582, so sánh với một nhánh B XLM-R (0,8947, p95 168,2 ms) và
> Cohen's Kappa 0,892. Các con số đó **không phải số đo**: nhánh B được sinh ngẫu nhiên trong
> script, Kappa được dựng từ nhãn vàng, 0,7582 là của kNN (không được ship), và embedder là
> feature hashing chứ không phải BGE-M3. Toàn bộ số liệu dưới đây đo lại ngày 2026-10-05 bằng
> `python scripts/evaluate_router_branches_comparison.py --no-export`
> (báo cáo: [`docs/report/router_branches_comparison_report.json`](report/router_branches_comparison_report.json)).

---

## 1. Thông tin mô hình

- **Tên:** `intent-router-v1` (nhánh C)
- **Tệp runtime:** `artifacts/router_model.onnx`
- **SHA-256:** `0cc5f770af0c6d2b49417021244d6d5d20d7453e87f614855e9aa7b1478ec95e` (đóng băng tại [`artifacts/DATA_HASHES.txt`](../artifacts/DATA_HASHES.txt))
- **Định dạng:** ONNX opset 15, dynamic quantization `QUInt8`, 35,93 KB
- **Bộ phân loại trong ONNX:** `LogisticRegression` (7 lớp × 1024 chiều)
- **Embedder:** `SemanticDenseEmbedder` ([`ai-service/src/ai/inference/embedder.py`](../ai-service/src/ai/inference/embedder.py)) —
  từ + n-gram ký tự 3/4, băm MD5/SHA-1 vào 1024 chiều, trọng số IDF học trên tập train, chuẩn hoá L2.
  **Đây không phải vector BGE-M3 của `ai-embed`**; docstring của nó tự ghi là "mô phỏng".
  Về bản chất đây là một biểu diễn túi-n-gram kiểu TF-IDF đã băm.

---

## 2. Mục đích và phạm vi

Phân loại câu khách hàng vào 7 ý định: `GREETING`, `KB_SEARCH`, `PRICING_POLICY`,
`COMPLAINT_SUPPORT`, `HANDOFF_HUMAN`, `TECH_ERROR`, `BUYING_INTENT`.

Mô hình chạy ở **tầng 2** của `ai-classify` ([`inference/src/roles/classify.py`](../inference/src/roles/classify.py)):

1. **Tầng 1 — luật từ khoá:** khớp thì trả nhãn với confidence 0,93–0,98, không gọi mô hình.
2. **Tầng 2 — mô hình này.**
3. **Cổng bỏ phiếu trắng:** confidence < τ = 0,65 thì gắn `fallback_to_llm = True`;
   `ai-service` định tuyến lượt đó sang nhánh hỏi lại (CLARIFY).

Không dùng để sinh câu trả lời. Chưa đánh giá trên ngôn ngữ ngoài tiếng Việt / tiếng Anh pha trộn.

---

## 3. Dữ liệu

- **Train:** `data/intent_train_dedup.jsonl` — 1.941 câu, SHA-256 `d8c2bfc4…4562d`.
  Sinh bằng **tổ hợp template** (`scripts/build_router_data_and_eval.py`, seed 42), không gọi LLM.
  Phân bố văn phong sau khử trùng lặp: `short_abbrev` 639 · `no_accent` 426 · `polite_full` 384 ·
  `typo` 249 · `en_mix` 172 · `emoji` 71. Tập thô 3.000 câu gồm các bản sao do chính script chèn
  vào; tỉ lệ khử trùng lặp 35,3% vì vậy không phải số đo về dữ liệu tự nhiên.
- **Test:** `data/intent_test_human.jsonl` — 200 câu, 28–30 câu mỗi ý định, SHA-256 `8cc500dc…a1ecf`.
- **Đồng thuận gán nhãn (Cohen's Kappa):** **chưa đo.** Hai người gán nhãn độc lập vào
  `data/annotations/dev_a.csv` và `dev_b.csv`, rồi chạy `python scripts/compute_annotation_kappa.py`.

---

## 4. Kết quả trên 200 câu test

### 4.1. Riêng mô hình (tầng 2 trên toàn bộ 200 câu)

| Chỉ số | Giá trị |
|---|---|
| Macro-F1 | **0,6755** |
| Accuracy | 0,675 |
| KTC 95% Macro-F1 (bootstrap B = 1.000) | [0,6131 ; 0,7327] |
| Tham khảo: kNN trên cùng embedding (không ship) | Macro-F1 0,7582 |

kNN cho Macro-F1 cao hơn mô hình đang ship. Lý do chọn LogisticRegression để export chưa được ghi
trong ADR nào — cần quyết định: giữ, hoặc export kNN / huấn luyện lại.

### 4.2. Cả router 3 tầng (luật + mô hình + cổng τ), đúng như `ai-classify` chạy

| Chỉ số | Giá trị |
|---|---|
| Macro-F1 nhãn router | **0,712** |
| Tầng 1 (luật) | 72 câu, đúng 79% |
| Tầng 2, confidence ≥ 0,65 | 49 câu, đúng 92% |
| Dưới τ (chuyển sang hỏi lại) | 79 câu (39,5%), nhãn đoán đúng 52% |

### 4.3. Đường cong bỏ phiếu trắng (riêng tầng 2)

| τ | 0,40 | 0,50 | 0,60 | **0,65** | 0,70 | 0,75 | 0,80 |
|---|---|---|---|---|---|---|---|
| Độ chính xác phần giữ lại | 0,794 | 0,850 | 0,911 | **0,924** | 0,937 | 0,943 | 1,000 |
| Coverage | 0,775 | 0,565 | 0,450 | **0,395** | 0,315 | 0,265 | 0,210 |

τ nhỏ nhất đạt độ chính xác phần giữ lại ≥ 0,95 là **0,80** (coverage 21%). Hệ thống đang chạy
τ = 0,65 (0,924 / 39,5%) — thấp hơn mục tiêu 0,95 của đặc tả UC022. Đồ thị:
`reports/eval/router_abstention_curve.png`.

### 4.4. Cổng parity (scikit-learn ↔ ONNX INT8)

max |ΔP| = 2,98 × 10⁻⁷ < 10⁻⁴, khớp nhãn 200/200 — **PASSED**.

### 4.5. So sánh với nhánh B (XLM-R)

**Chưa có.** Không có checkpoint nhánh B trong repo và chưa có dự đoán trên tập test (log Kaggle
trong `docs/report/` mâu thuẫn nội tại, chưa xác minh). Script so sánh
chỉ tính nhánh B khi có `reports/eval/router_branch_b_predictions.jsonl` do notebook 05 xuất ra.

---

## 5. Độ trễ

Đo trên một CPU Intel (Windows, AMD64), 200 câu × 3 lượt, embedder trong tiến trình + ONNX:

| | p50 | p95 |
|---|---|---|
| Embedder + phân loại | 0,18 ms | 0,33 ms |
| Riêng phân loại ONNX | — | 0,05 ms |

Con số dao động giữa các lần chạy (một lần khác đo p95 1,66 ms) và **chỉ đúng cho embedder băm
hiện tại**. Nếu thay bằng vector BGE-M3 thật từ `ai-embed` qua HTTP, độ trễ do chặng nhúng chi phối.
Chưa đo RAM và thông lượng.

---

## 6. Giới hạn

1. **Embedder không ngữ nghĩa:** hai câu đồng nghĩa nhưng khác từ có vector xa nhau. Đây là lý do
   chính khiến chỉ 39,5% câu vượt τ.
2. **Lệch phân phối train/test:** train sinh từ template, test là câu người thật. Luật đạt 100% trên
   train chỉ đạt 87% trên test (thí nghiệm siết luật 05/10).
3. **Confidence của tầng 1 không hiệu chỉnh:** luật gán 0,93–0,98 cố định nhưng chỉ đúng 79%.
4. **Router không dùng ngữ cảnh hội thoại** — mỗi câu được phân loại độc lập.

---

## 7. Tái lập

```powershell
# Đánh giá, KHÔNG export lại ONNX và KHÔNG sửa DATA_HASHES.txt
python scripts/evaluate_router_branches_comparison.py --no-export

# Kiểm thử
python -m pytest ai-service/tests/unit/test_router_onnx_classify.py -v

# Kappa (sau khi hai người đã gán nhãn)
python scripts/compute_annotation_kappa.py
```
