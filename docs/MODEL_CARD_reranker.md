---
language:
- vi
license: apache-2.0
library_name: onnxruntime
tags:
- text-ranking
- cross-encoder
- onnx
- quantization-int8
- crm
pipeline_tag: text-ranking
---

# MODEL CARD — Cross-encoder xếp lại (UC023)

> **`bge-reranker-v2-m3-int8`** — `BAAI/bge-reranker-v2-m3` export ONNX, lượng tử hoá INT8 động
> per-channel, phục vụ ở `ai-rerank` (`inference/src/roles/rerank.py`). Ngày 15 Khối A, 11/10/2026.
> **Hệ thống:** Nền tảng AI CRM Chatbot Platform (KLTN)

---

## 1. Thông tin mô hình

- **Gốc:** [`BAAI/bge-reranker-v2-m3`](https://huggingface.co/BAAI/bge-reranker-v2-m3) @ revision
  `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` — `XLMRobertaForSequenceClassification`, 24 tầng,
  ~568M tham số, **một** nhãn đầu ra. Giấy phép Apache-2.0.
- **Sinh ở:** [`notebooks/07_export_reranker.py`](../notebooks/07_export_reranker.py) — Kaggle CPU,
  không GPU. Exporter TorchScript (`dynamo=False`), opset 17, attention eager.
- **Lượng tử hoá:** `quantize_dynamic`, QInt8, per-channel — y hệt `bge-m3-int8` (notebook 06).
- **Đầu vào:** `input_ids`, `attention_mask` của MỘT cặp `<s> câu hỏi </s></s> đoạn </s>`, cắt
  `longest_first` ở 512 token (đoạn bị cắt trước, câu hỏi giữ nguyên).
- **Đầu ra:** `logit`, hình dạng `(batch,)`. `ai-rerank` trả `score = sigmoid(logit)` ∈ (0, 1) và
  sắp theo logit.
- **Chạy:** lô 1, mỗi cặp một lượt — `DynamicQuantizeLinear` tính thang trên cả tensor, ghép lô thì
  điểm của một cặp phụ thuộc cặp đi cùng. Test khoá: `inference/tests/test_rerank_that.py`.

| Tệp (`artifacts/models/`, mount, không COPY vào image) | Cỡ | SHA-256 |
|---|---|---|
| `bge-reranker-v2-m3-int8.onnx` | 2,0 MB | `93cd7fb002528576a3c8d2ccf8b2631a68e36e70930d3ffaccafee8ac1c0fde2` |
| `bge-reranker-v2-m3-int8.onnx.data` | 569 MB | `db41e6b7a9f2cde776e6feb26ddcc6f074258303cf8e1ea12d389816e33eff97` |
| `bge-reranker-v2-m3-tokenizer.json` | 17,1 MB | `69564b696052886ed0ac63fa393e928384e0f8caada38c1f4864a9bfbf379c15` |

`model_version` = `int8-93cd7fb0` (8 ký tự đầu sha256 của `.onnx`). Bản fp32 (2,116 GB) ở lại
Kaggle Output: `.onnx` `4b271ac2…` · `.data` `61f3e722…`. INT8 nhỏ hơn fp32 **3,98 lần**.

Tokenizer là tệp riêng của repo reranker, **không** dùng `tokenizer.json` của bge-m3: cùng bộ từ
vựng XLM-R 250.002 token nhưng khác ba khối cấu hình (normalizer cắt khoảng trắng cuối, cách gộp
nhiều dấu cách, `prepend_scheme`). Notebook 07 §2 kiểm khớp HF từng token, kể cả cặp phải cắt.

Phiên bản lúc export: torch 2.11.0+cpu · transformers 5.16.1 · tokenizers 0.23.1 · onnx 1.22.0 ·
onnxruntime 1.31.0.

---

## 2. Mục đích và phạm vi

Xếp lại N ứng viên đầu của tìm kiếm lai (vector + từ khoá, RRF k = 60) trước khi cắt top-5 đưa vào
lời nhắc — chặng 9 của đường ống UC023 (`ai-service/src/ai/rag/rerank/quyet_dinh.py`). Bật/tắt bằng
`RERANK_ENABLED`; ai-rerank lỗi thì ai-service giữ thứ hạng RRF (§3.8.1).

Không dùng ở bước tìm: cross-encoder phải chạy một lượt cho MỖI cặp (câu hỏi, đoạn), nên chỉ đủ
rẻ trên vài chục ứng viên, không trên cả kho.

---

## 3. Cổng parity INT8 ↔ fp32 — ĐẠT

Đo trong notebook 07 trên `ai-service/tests/eval/rerank_cap_100x20.jsonl` (sha256 `1f6c77ad…`): 100
câu có đáp án của bộ vàng × 20 ứng viên đầu của `e3-hybrid`, chấm lô 1 bằng đúng tokenizer production.
167/2000 cặp (8%) dài quá 512 token và bị cắt đuôi đoạn.

| Chỉ số | Giá trị |
|---|---|
| **Chênh nDCG@5 sau rerank, INT8 − fp32** (cổng: < 1 điểm) | N = 12: **+0,54** · N = 20: **−0,23** |
| Spearman điểm fp32 ↔ INT8, theo câu | mean 0,982 · min 0,893 |
| Độ trùng top-5 fp32 ↔ INT8 | mean 0,922 · min 0,60 |

Cổng đo **thứ hạng**, không đo cosine như encoder: rerank chỉ dùng điểm để sắp xếp. Spearman min
0,893 và độ trùng top-5 min 0,60 cho thấy INT8 có đảo thứ tự ở vài câu, nhưng đảo giữa các đoạn
sai với nhau — chất lượng đầu ra (nDCG@5) giữ nguyên trong 1 điểm.

---

## 4. Chất lượng trên bộ vàng

Harness `tests/eval/danh_gia_truy_hoi.py` gọi ai-rerank thật trên máy dev; bộ vàng 100 câu có đáp án
(sha256 `323baf73…`), mốc so là hybrid RRF không xếp lại (`e3-hybrid`). Paired bootstrap B = 10.000.

| Cấu hình | recall@5 | nDCG@5 | Δ nDCG@5 [KTC 95%] |
|---|---|---|---|
| không xếp lại (mốc) | 0,740 | 0,631 | — |
| 12 ứng viên | 0,800 | 0,705 | +7,5 [+3,0; +12,2] |
| 20 ứng viên, mọi câu | 0,880 | 0,757 | +12,6 [+6,7; +18,9] |
| **20 ứng viên, chỉ khi mơ hồ — cấu hình ship** | **0,870** | **0,752** | **+12,1 [+6,2; +18,5]** |

Chi tiết (trần theo số ứng viên, cổng mơ hồ 93%, câu cứu được / bị đẩy ra):
[`docs/report/rerank-ngay15-2026-10-11.md`](report/rerank-ngay15-2026-10-11.md) §2.

---

## 5. Độ trễ

Một lượt gọi ai-rerank (gồm HTTP), một luồng yêu cầu, máy dev Apple M1 trong Docker. Ngưỡng §5.3 (p95
300 ms) là số kế hoạch, **chưa áp dụng** — người dùng chốt 11/10/2026 độ trễ chưa là cổng.

| vCPU | Số câu | 12 cặp p50 / p95 | 20 cặp p50 / p95 |
|---|---|---|---|
| 2 (cấu hình ship) | 30 | 5,7 / 9,0 s | 10,7 / 13,0 s |
| 4 | 100 | 9,2 / 14,9 s | 15,5 / 36,2 s |

Mỗi cặp 0,15–3 s tuỳ độ dài. ~~4 vCPU không nhanh hơn 2 vCPU trên M1~~ — **đính chính Ngày 15 Khối B**:
đo trực tiếp cùng điều kiện, hai lượt mỗi mức, **4 vCPU nhanh hơn** — 20 cặp p50 7,8 / 9,0 s, p95 10,3 /
10,5 s so với 11,1 / 12,5 s và 13,8 / 18,6 s ở 2 vCPU; ai-rerank chốt **4 vCPU** ([ADR-0034](adr/0034-chot-cap-vcpu-ai-embed-ai-rerank.md),
`docs/report/benchmark-ngay15-2026-10-11.md`). Thứ hạng không đổi theo số luồng: top-5 trùng 30/30 câu. Trên Kaggle CPU (x86): INT8 772 ms/cặp, fp32 1.158 ms/cặp — chỉ tỉ lệ
~1,5 lần là dùng được, con số tuyệt đối không tái lập.

---

## 6. Giới hạn — ghi trung thực

- **Bộ vàng do AI sinh** từ mục lục tài liệu (ADR-0020), kho là tài liệu mẫu tự soạn
  (`data/kb_samples`), không phải dữ liệu doanh nghiệp thật.
- **Đo parity trên Kaggle (x86), chạy production trên máy dev (ARM, Apple M1).** Nhân INT8 của
  onnxruntime khác nhau giữa hai kiến trúc; số chất lượng ở §4 đo lại trên đúng `ai-rerank` của máy
  dev, không lấy từ notebook. Lên cloud x86 thì đo lại (N20).
- 8% cặp bị cắt ở 512 token — đoạn rất dài mất phần cuối.
- Độ trễ đo trên một máy dev, một luồng yêu cầu; dưới tải: chưa đo (N19 hoãn).
