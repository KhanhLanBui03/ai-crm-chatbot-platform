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
- bge-m3
- crm
- customer-support
pipeline_tag: text-classification
---

# MODEL CARD — Intent Router (UC022)

> **Mô hình định tuyến ý định hội thoại khách hàng 7 nhánh (3-Tier Intent Router)**  
> **Kiến trúc:** BGE-M3 Semantic Embeddings (1024-dim) + ONNX INT8 Linear Classifier  
> **Hệ thống:** Nền tảng AI CRM Chatbot Platform (KLTN Đại học Bách Khoa)

---

## 1. Thông tin Mô hình (Model Details)

- **Tên mô hình:** `intent-router-v1` (Branch C Production Release)
- **Phiên bản:** `v1.0.0-onnx-int8`
- **Ngày phát hành:** 2026-10-04
- **Đơn vị phát triển:** Nhóm KLTN AI CRM Chatbot Platform (Track B — AI Service)
- **Tệp phân phối runtime:** `artifacts/router_model.onnx`
- **Mã băm SHA-256:** `c70cfccbf70c9ea255aa3272a2192d251bc1dedf467c4157230b3874688da834` (đã đóng băng tại [`artifacts/DATA_HASHES.txt`](../artifacts/DATA_HASHES.txt))
- **Định dạng:** ONNX Opset 15, Dynamic Quantization `QUInt8`
- **Kích thước tệp:** 36.8 KB (35.94 KiB)
- **Khung công tác suy luận:** ONNX Runtime (`onnxruntime >= 1.20.0`), CPU Execution Provider

---

## 2. Mục đích Sử dụng & Phạm vi Áp dụng (Intended Uses & Scope)

### 2.1. Mục đích chính (Primary Uses)
- Phân loại tức thì phát ngôn của khách hàng thành 1 trong **7 nhánh ý định kinh doanh chuẩn** (Master Plan §5.9):
  1. `GREETING`: Chào hỏi, xã giao, cảm ơn, tạm biệt.
  2. `KB_SEARCH`: Tra cứu tài liệu tri thức, hỏi đáp thông tin sản phẩm/dịch vụ (điều hướng sang RAG).
  3. `PRICING_POLICY`: Hỏi bảng giá, gói cước, chi phí định kỳ, chính sách ưu đãi chiết khấu.
  4. `COMPLAINT_SUPPORT`: Phàn nàn chất lượng dịch vụ, khiếu nại thời gian chờ, thái độ nhân viên.
  5. `HANDOFF_HUMAN`: Yêu cầu chuyển máy gặp trực tiếp nhân viên tư vấn / tổng đài viên người thật.
  6. `TECH_ERROR`: Báo sự cố kỹ thuật phần mềm, lỗi kết nối, lỗi ứng dụng.
  7. `BUYING_INTENT`: Thể hiện nhu cầu đặt mua ngay, chốt hợp đồng, nâng cấp tài khoản trả phí.

### 2.2. Kiến trúc Định tuyến 3 Tầng (3-Tier Architecture)
Mô hình hoạt động tại **Tầng 2** trong quy trình định tuyến khép kín:
1. **Tầng 1 (Rule-based Regex):** Bắt nhanh các từ khóa khẩn cấp (`HANDOFF_HUMAN`, `TECH_ERROR`) hoặc xã giao thuần túy (`GREETING`) với độ tự tin $0.95+$.
2. **Tầng 2 (ONNX Model INT8):** Tái sử dụng vector biểu diễn ngữ nghĩa 1024 chiều từ `ai-embed` (`BAAI/bge-m3`) để suy luận xác suất phân bố trên 7 nhãn.
3. **Tầng 3 (Abstention Gate Fallback):** Nếu độ tự tin của mô hình $< \tau^*$ ($\tau^* = 0.65$), hệ thống tự động bỏ phiếu trắng (`fallback_to_llm = True`) và chuyển câu nói sang mô hình ngôn ngữ lớn (LLM) để suy luận ngữ cảnh sâu.

### 2.3. Phạm vi không áp dụng (Out-of-Scope)
- Không dùng để sinh nội dung câu trả lời tự động cho khách hàng.
- Không dùng cho ngôn ngữ ngoài Tiếng Việt và Tiếng Anh (không tối ưu hóa cho tiếng Trung, Nhật, Hàn).

---

## 3. Dữ liệu Huấn luyện & Đánh giá (Data & Preprocessing)

- **Dữ liệu huấn luyện đã khử trùng lặp:** `data/intent_train_dedup.jsonl` (SHA-256: `d8c2bfc45292629df653a5e1d719d27b0b35e78fb2fe1bccf3fe0c6a75b4562d`).
  - Gồm các mẫu sinh có kiểm soát bao phủ 6 dạng văn phong thực tế: chuẩn mực (`standard`), chat ngắn viết tắt (`short_abbrev`), không dấu (`no_accent`), gõ vội sai chính tả (`typo`), đa ý định (`multi_intent`), pha trộn tiếng Anh (`en_mix`).
- **Tập kiểm thử người thật (Golden Test Set):** `data/intent_test_human.jsonl` (SHA-256: `8cc500dc96ebd15f18af01ca386b53a3b85941dba9c06ce12f46ffa24d0a1ecf`).
  - Gồm đúng 200 câu do con người gán nhãn độc lập (chỉ số thống nhất Cohen's Kappa $\kappa = 0.892$).

---

## 4. Kết quả Thực nghiệm & So sánh 2 Nhánh (Benchmarks)

Thực hiện kiểm định thực nghiệm Paired Bootstrap $B = 1000$ vòng lặp theo đặc tả Master Plan §5.9:

### 4.1. Bảng đối đầu 5 chiều (Benchmark Table)

| Nhánh khảo sát | Kiến trúc | Macro-F1 (Điểm ước lượng) | KTC 95% Bootstrap ($B=1000$) | Độ trễ CPU ($p95$) | Dung lượng Model | Trạng thái Chốt |
|---|---|---|---|---|---|---|
| **Nhánh B** | `xlm-roberta-base` (278M params) | **0.8947** | [0.8483, 0.9334] | 168.2 ms | 1,112.0 MB | **LOẠI BỎ** (Vi phạm ngân sách $\le 60\text{ ms}$) |
| **Nhánh C (Ship)** | `ai-embed` + ONNX INT8 | 0.7582 | [0.6948, 0.8112] | **0.182 ms** | **0.035 MB (36 KB)** | **CHỐT VẬN HÀNH** (Thắng áp đảo độ trễ) |

* **Kiểm định Paired Bootstrap:** $\Delta = \text{Macro-F1}_B - \text{Macro-F1}_C = +0.1381$, KTC 95%: $[0.0647, 0.2070]$, $p$-value $< 0.001$.
* **Quy tắc phá thế hòa (§5.9):** Nhánh B vi phạm nghiêm trọng ngân sách $60\text{ ms}$ trên CPU thực tế. Nhánh C thắng áp đảo nhờ lợi thế cấu trúc: độ trễ thêm chỉ $0.182\text{ ms}$, tiết kiệm RAM 93 lần và dung lượng nhẹ hơn 31.000 lần.

### 4.2. Phân tích Đường cong Bỏ Phiếu Trắng (Abstention Analysis)
Đồ thị phân tích: [`reports/eval/router_abstention_curve.png`](../reports/eval/router_abstention_curve.png)
- Tại ngưỡng tự tin **$\tau^* = 0.80$**: Độ chính xác phần giữ lại đạt **$97.62\%$** (vượt xa mục tiêu $\ge 95\%$), độ bao phủ $21\%$.
- Tại ngưỡng thực dụng **$\tau^* = 0.65$**: Độ chính xác đạt **$95.20\%$**, độ bao phủ đạt **$78\%$** (chỉ cần điều hướng $22\%$ các ca khó sang LLM).

### 4.3. Kiểm định Cổng Parity (Parity Gate)
- So sánh sai số xác suất giữa Scikit-Learn gốc và ONNX INT8:
  $$\max |P_{\text{sklearn}} - P_{\text{onnx}}| = 2.98 \times 10^{-7} < 10^{-4}$$
- **Trạng thái:** **PASSED**.

---

## 5. Độ trễ & Tiêu hao Tài nguyên (Latency & Resources)

Đo đạc trên môi trường CPU Intel Core i7 / AMD Ryzen (không cần GPU):
- **Độ trễ trung vị ($p50$):** $0.125\text{ ms}$ (125 micro-giây)
- **Độ trễ phân vị cao ($p95$):** $0.182\text{ ms}$ (182 micro-giây)
- **Thông lượng (Throughput):** $\approx 5.500\text{ req/s}$ trên 1 CPU core đơn lẻ.
- **Mức tiêu hao bộ nhớ (RAM):** $\approx 15\text{ MB}$ khi nạp vào bộ nhớ.

---

## 6. Giới hạn Kỹ thuật & Khía cạnh Đạo đức (Limitations & Ethics)

1. **Phụ thuộc vào vector `ai-embed`:** Mô hình Nhánh C không nhận văn bản thô trực tiếp mà nhận vector 1024 chiều. Nếu `ai-embed` offline, hệ thống tự động kích hoạt Rule-based Fallback.
2. **Thiên vị nhãn phổ biến:** Trong các câu hội thoại ngắn không rõ ngữ cảnh (dưới 3 từ), mô hình có xu hướng thiên về `KB_SEARCH` hoặc `GREETING`. Cơ chế Abstention Gate ($\tau < 0.65$) giải quyết triệt để vấn đề này bằng cách gửi câu mơ hồ lên LLM.
3. **Bảo mật dữ liệu:** Vector 1024 chiều là biểu diễn toán học một chiều, không thể giải mã ngược lại danh tính (PII) người dùng, đảm bảo tuân thủ GDPR và an toàn thông tin doanh nghiệp.

---

## 7. Hướng dẫn Chạy & Kiểm thử Chi tiết (How to Run & Verify)

### 7.1. Chạy đánh giá so sánh và tái lập KTC 95%
Thực thi script tái lập toàn bộ kết quả thực nghiệm:
```powershell
python scripts/evaluate_router_branches_comparison.py
```

### 7.2. Chạy bộ kiểm thử tự động (Unit Tests)
```powershell
python -m pytest ai-service/tests/unit/test_router_onnx_classify.py -v
```

### 7.3. Sử dụng mô hình trực tiếp qua Python SDK
```python
import joblib
import onnxruntime as ort
import numpy as np

# 1. Nạp embedder và mô hình ONNX
embedder = joblib.load("artifacts/router_branch_c.joblib")["embedder"]
sess = ort.InferenceSession("artifacts/router_model.onnx", providers=["CPUExecutionProvider"])

# 2. Vector hóa câu nói người dùng
text = "Gói CRM cho công ty 50 nhân sự giá bao nhiêu?"
vec = embedder.transform_single(text).reshape(1, -1).astype(np.float32)

# 3. Suy luận phân loại
input_name = sess.get_inputs()[0].name
res = sess.run(None, {input_name: vec})
predicted_intent = res[0][0]
probabilities = res[1][0]

print(f"Ý định dự đoán: {predicted_intent}")
print(f"Độ tự tin: {probabilities[predicted_intent]:.4f}")
```

### 7.4. Kiểm thử qua API REST của Microservice `ai-classify`
```powershell
# Khởi chạy microservice
$env:MODEL_ROLE="classify"
python inference/src/entrypoint.py

# Gửi request HTTP POST
curl -X POST "http://localhost:8000/v1/classify" `
  -H "Content-Type: application/json" `
  -d '{"text": "Cho mình gặp nhân viên tư vấn trực tiếp"}'
```
