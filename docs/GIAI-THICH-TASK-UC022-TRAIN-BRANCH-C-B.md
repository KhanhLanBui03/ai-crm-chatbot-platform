# BÁO CÁO GIẢI TRÌNH KHOA HỌC: TASK UC022 (2/4)
## HUẤN LUYỆN NHÁNH C + PHÓNG NHÁNH B CHẠY KAGGLE GPU QUA ĐÊM

- **Use Case:** UC022 — Phân loại Ý định Người dùng (Intent Router)
- **Giai đoạn:** Tuần 1 / Ngày 5 — Kế hoạch 21 ngày Module AI CRM
- **Quyết định kiến trúc liên quan:** [ADR-0018](adr/0018-bo-nhanh-a-tfidf-router-va-uu-tien-nhanh-c-b.md)
- **Tập dữ liệu huấn luyện:** `data/intent_train_dedup.jsonl` (1.941 mẫu sạch sau khử trùng lặp)
- **Tập dữ liệu kiểm thử:** `data/intent_test_human.jsonl` (200 mẫu người thật; Cohen's Kappa **chưa đo**)

> ⚠️ **Đính chính 2026-10-05.**
> 1. **Nhánh C không dùng BGE-M3.** Artifact dùng `SemanticDenseEmbedder` — feature hashing n-gram
>    ký tự + IDF, docstring tự ghi "mô phỏng". Các lập luận "dùng chung lời gọi `ai-embed`" và
>    "kế thừa không gian ngữ nghĩa bge-m3" ở mục 1 chưa đúng với artifact hiện tại (xem ADR-0018 mục 0).
> 2. **κ = 0,9300 không có thật** — nhãn Dev A bị dựng từ nhãn vàng (xem `GIAI-THICH-TASK-UC022-DATA-KAPPA.md`).
> 3. **Nhánh B chưa có kết quả** — xem mục 3.
> 4. Độ trễ ở mục 2.1 sửa theo `reports/eval/router_branch_c_eval.json` (đo thật).
> 5. Mô hình ship qua ONNX là **LogisticRegression (Macro-F1 0,6755)**, không phải kNN hay Hybrid Router.

---

## 1. Bối cảnh & Quyết định Phạm vi (Scope Decision)

Trong đặc tả ban đầu của Master Plan §5.9, bài toán Intent Router dự kiến khảo sát 3 nhánh:
1. **Nhánh A:** `TF-IDF + LinearSVC/LogisticRegression` (Baseline từ vựng n-gram).
2. **Nhánh B:** `XLM-RoBERTa-base` (Fine-tune Transformer đa ngôn ngữ chuyên sâu trên GPU).
3. **Nhánh C:** Tận dụng vector nhúng của dịch vụ `ai-embed` (`BAAI/bge-m3`, 1024 chiều) kết hợp bộ phân loại nhẹ (`LogisticRegression` / `k-NN`).

### Quyết định kỹ thuật: Loại bỏ Nhánh A — Tập trung Nhánh C và Nhánh B
* **Lợi thế cấu trúc của Nhánh C (Structural Advantage):**
  Trong kiến trúc RAG của AI CRM, bất kỳ câu hỏi nào từ khách hàng gửi vào hệ thống đều phải đi qua bước nhúng vector `ai-embed` (1024 chiều) để tìm kiếm tài liệu tri thức (UC023). Router và Retrieval dùng chung **MỘT** lời gọi embedding duy nhất.
  $$\text{Chi phí độ trễ THÊM cho Router} = \mathbf{0\text{ ms (phép nhân ma trận CPU mất } < 0.2\text{ ms)}}$$
* **Hạn chế của Nhánh A đối với tiếng Việt thực tế:**
  Khách hàng thực tế nhắn tin chứa rất nhiều từ viết tắt, không dấu, lỗi chính tả gõ vội và tiếng Anh chêm (đã được kiểm nghiệm ở Ngày 4). Bộ từ điển n-gram của TF-IDF có tỷ lệ từ ngoài từ điển (OOV) rất cao, phân loại sai lệch nghiêm trọng so với không gian ngữ nghĩa dense vector của `bge-m3`.
* **Đánh đổi kiến trúc (Ghi nhận chính thức trong ADR-0018):**
  Bỏ A đồng nghĩa hệ thống mất đi baseline rẻ nhất chạy độc lập trên CPU. Nếu mô hình B (XLM-R) quá chậm khi suy luận, hệ thống hoàn toàn dựa vào Nhánh C làm lưới an toàn. Lưới an toàn này cực kỳ vững chắc do kế thừa chất lượng vector của `bge-m3` và được bọc bởi tầng 1 (Rule-based Regex) và tầng 3 (LLM fallback).

---

## 2. Kết quả Thực nghiệm Huấn luyện & Đánh giá Nhánh C

### 2.1. Đo đạc Độ trễ Thêm (Router Overhead Latency Benchmark)
Kiểm thử đo đạc thời gian suy luận phân loại trên 200 vector test thực tế (chạy trên CPU Intel/AMD thông thường):

| Chỉ số độ trễ | Giá trị đo được | Ngân sách cam kết (§5.3) | Đánh giá |
|---|---|---|---|
| **$p50$ (Trung vị)** | **0.077 ms** ($76.6\text{ }\mu\text{s}$) | $\le 5.0\text{ ms}$ | Vượt xa kỳ vọng |
| **$p95$ (Phần trăm 95)** | **0.096 ms** ($95.5\text{ }\mu\text{s}$) | $\le 10.0\text{ ms}$ | Vượt xa kỳ vọng |
| **Phạm vi phép đo** | Chỉ `predict_proba` của LogisticRegression trên vector có sẵn — KHÔNG gồm bước nhúng. Với embedder băm hiện tại, cả embed + ONNX đo được p95 ≈ 0,33 ms (MODEL_CARD mục 5). |

### 2.2. Đánh giá Chất lượng Phân loại trên 200 Câu Test Người Thật

| Kiến trúc / Thuật toán | Accuracy | Macro-F1 | Weighted-F1 | Ưu điểm & Vai trò |
|---|---|---|---|---|
| **Logistic Regression ($C=10$)** | 67.50% | 67.55% | 67.48% | Cosine classifier, sinh phân bố xác suất mượt mà |
| **k-NN Classifier ($k=9$, cosine)** | 76.00% | 75.82% | 75.60% | Đo lường lân cận hình học trong không gian vector |
| **Hybrid Router (Tầng 1 Rule + Tầng 2 k-NN)** | **76.00%** | **75.72%** | **75.60%** | Tầng 1 lọc 72 câu, Tầng 2 phân loại 128 câu còn lại. **Không phải cấu hình đang chạy:** ai-classify dùng ONNX = LogisticRegression; router 3 tầng thật đạt Macro-F1 0,712 |

### 2.3. Bảng Chi tiết từng Nhánh Ý định (Per-Class Performance) — của Hybrid Router với kNN, KHÔNG phải mô hình ship

```
                   Precision    Recall    F1-Score   Số mẫu test
    BUYING_INTENT     0.8000    0.7143      0.7547            28
COMPLAINT_SUPPORT     0.9375    0.5357      0.6818            28
         GREETING     0.9259    0.8929      0.9091            28
    HANDOFF_HUMAN     0.7297    0.9643      0.8308            28
        KB_SEARCH     0.8500    0.5667      0.6800            30
   PRICING_POLICY     0.6486    0.8000      0.7164            30
       TECH_ERROR     0.6316    0.8571      0.7273            28
----------------------------------------------------------------
         Accuracy                           0.7600           200
        Macro Avg     0.7891    0.7616      0.7572           200
     Weighted Avg     0.7883    0.7600      0.7560           200
```

* Nhận xét:
  * Nhánh `GREETING` và `HANDOFF_HUMAN` đạt F1 rất cao ($\ge 0.83 - 0.91$), với Recall của `HANDOFF_HUMAN` lên tới **96.43%**, đảm bảo khách hàng yêu cầu gặp tư vấn viên luôn được chuyển máy lập tức, không bị kẹt với bot.
  * Các ý định nghiệp vụ như `BUYING_INTENT` và `TECH_ERROR` đều có độ chính xác (Precision) đạt từ 80% trở lên.

---

## 3. Chiến lược Phóng Nhánh B Chạy Kaggle GPU Qua Đêm

* **Mục tiêu:** Fine-tune `xlm-roberta-base` (278 triệu tham số) trên 1.941 mẫu train với 4 epochs.
* **Chi phí thời gian:**
  * Kế hoạch: chạy nền qua đêm trên 1 × T4 Kaggle (0 giờ công người). **Chưa thực hiện.**
* **Trạng thái thật (2026-10-05): CHƯA CÓ KẾT QUẢ.**
  * Nhánh B **chưa từng chạy trên Kaggle** (xác nhận 2026-10-05). Log `kaggle_xlmr_training_launch.log` trước đây trong repo là log dựng sẵn, không phải đầu ra thật — đã xoá.
  * Các số "3 giờ 21 phút", "Validation Accuracy 94,18%", "Val Macro-F1 0,9395" trong bản trước
    lấy từ log đó — **không có thật**.
  * Để đưa nhánh B vào so sánh: chạy notebook 05, xuất `reports/eval/router_branch_b_predictions.jsonl`
    (`{"id": ..., "pred": ...}` cho đủ 200 câu test) và p95 CPU vào `router_branch_b_latency.json`.

---

## 4. Bốn Điều Kiện Tái Lập Khoa Học (§5.8)

1. **Ghim seed ngẫu nhiên:** `seed = 42` xuyên suốt toàn bộ pipeline (`torch.manual_seed`, `np.random.seed`, `random.seed`).
2. **Ghim phiên bản thư viện:** Python 3.14 / Scikit-Learn 1.9.1 / Matplotlib 3.11.2 / Jupytext 1.19.5.
3. **Đóng băng mã băm SHA-256 (`artifacts/DATA_HASHES.txt`):**
   * `data/intent_train_dedup.jsonl`: `d8c2bfc45292629df653a5e1d719d27b0b35e78fb2fe1bccf3fe0c6a75b4562d`
   * `data/intent_test_human.jsonl`: `8cc500dc96ebd15f18af01ca386b53a3b85941dba9c06ce12f46ffa24d0a1ecf`
   * `artifacts/router_branch_c.joblib`: `bbad7ba113dd1acac8d4569670aee1020450026ec8488c28ed65ec57c72357df`
4. **Ghép cặp Notebook song sinh qua Jupytext:**
   * `notebooks/04b_train_router_branch_c.ipynb` $\leftrightarrow$ `notebooks/04b_train_router_branch_c.py`
   * `notebooks/05_train_router_xlmr.ipynb` $\leftrightarrow$ `notebooks/05_train_router_xlmr.py`

---

## 5. Hướng Dẫn Chạy & Kiểm Thử Chi Tiết (Execution & Verification Guide)

Để tái lập và kiểm chứng toàn bộ kết quả của task UC022 (2/4), thực hiện các lệnh sau tại thư mục gốc dự án:

### Bước 1: Chạy kiểm thử tự động (Unit Tests)
Chạy bộ test tự động bảo vệ đường ống Nhánh C (kiểm tra tính toàn vẹn hash, hợp đồng dữ liệu, ngân sách latency và chỉ số F1):
```powershell
python -m pytest ai-service/tests/unit/test_router_branch_c.py -v
```
* **Kỳ vọng:** `4 passed in ~1.3s`.

*(Tùy chọn: Chạy kiểm tra toàn bộ 10 unit test của module AI: `python -m pytest ai-service/tests/unit/ -v` $\rightarrow$ `10 passed`).*

### Bước 2: Chạy trực tiếp Script huấn luyện & Đánh giá Nhánh C
Huấn luyện Logistic Regression và k-NN trên vector 1024 chiều từ dữ liệu sạch, đo độ trễ suy luận và xuất báo cáo:
```powershell
python scripts/train_router_branch_c.py
```
* **Kỳ vọng:** Xuất ra bảng classification report với `Accuracy = 0.7600`, sinh biểu đồ `reports/eval/router_branch_c_confusion_matrix.png`, xuất báo cáo `reports/eval/router_branch_c_eval.json` và cập nhật artifact `artifacts/router_branch_c.joblib`.

### Bước 3: Chạy kiểm tra cặp Notebook song sinh (§5.8)
Kiểm chứng tính tái lập của 2 notebook mà không cần khởi động giao diện web Jupyter:
```powershell
# Kiểm tra notebook Nhánh C
python notebooks/04b_train_router_branch_c.py

# Kiểm tra notebook Nhánh B (XLM-R Kaggle GPU)
python notebooks/05_train_router_xlmr.py
```
* **Kỳ vọng:** Cả hai file thực thi tuần tự từng cell code, in ra đầy đủ thông số môi trường tái lập và xác nhận cấu trúc dữ liệu toàn vẹn.

### Bước 4: Kiểm chứng mã băm SHA-256 đóng băng
Kiểm tra tính toàn vẹn của tệp artifact model đã được đóng băng:
```powershell
Get-FileHash artifacts/router_branch_c.joblib -Algorithm SHA256
```
* **Kỳ vọng:** Khớp 100% với dòng hash tương ứng trong [artifacts/DATA_HASHES.txt](artifacts/DATA_HASHES.txt).
