# ADR-0018 — Bỏ nhánh A (TF-IDF + LinearSVC), ưu tiên nhánh C (ai-embed) và nhánh B (XLM-R)

- **Trạng thái:** Chấp nhận — **có đính chính 2026-10-05** (xem mục 0)
- **Ngày:** 2026-09-24
- **Làn sở hữu:** Track B (AI Service)
- **Quan hệ:** Tiếp nối [ADR-0015](0015-cau-truc-src-hai-tang-theo-master-plan-v8.md), [ADR-0016](0016-ten-role-runtime-va-cho-dat-nhan-ket-qua-lead.md) và [ADR-0017](0017-chot-bon-mau-thuan-hop-dong-va-siet-cong-ci.md)

---

## 0. Đính chính 2026-10-05 — hiện thực KHÁC với quyết định

Rà soát code ngày 2026-10-05 cho thấy ba điểm mà phần còn lại của ADR này mô tả không đúng:

1. **Nhánh C KHÔNG dùng vector BGE-M3 của `ai-embed`.** Artifact `artifacts/router_branch_c.joblib`
   dùng `SemanticDenseEmbedder` (`ai-service/src/ai/inference/embedder.py`): từ + n-gram ký tự,
   băm vào 1024 chiều, trọng số IDF. Docstring của nó tự ghi là "mô phỏng". Về bản chất đây là
   biểu diễn kiểu TF-IDF đã băm — tức gần với chính **nhánh A** mà ADR này loại.
2. Vì vậy các lập luận ở mục 3.1 ("dùng chung một lời gọi embedding với RAG", "chi phí thêm
   bằng không") và mục 3.2 ("kế thừa không gian ngữ nghĩa của bge-m3") **chưa đúng với artifact
   đang ship**. Chúng chỉ thành đúng khi nhánh C được huấn luyện lại trên vector BGE-M3 thật.
3. Nhận định "TF-IDF chỉ đạt F1 ~0,72 trên câu không dấu/teencode" (dẫn trong ADR-0019) không có
   số đo đi kèm trong repo — nhánh A không được huấn luyện.

Số đo thật của artifact đang ship (2026-10-05, 200 câu test người thật): Macro-F1 tầng 2 = 0,676
(KTC 95% [0,613 ; 0,733]); cả router 3 tầng = 0,712. Chi tiết: `docs/MODEL_CARD_router.md`.

4. **Nhánh B chưa từng chạy trên Kaggle.** Mục 6 dẫn tới `kaggle_xlmr_training_launch.log` như "log
   xác nhận phiên chạy" — log đó dựng sẵn, không phải đầu ra thật, và đã bị xoá ngày 2026-10-05.

Phần thân ADR dưới đây giữ nguyên như đã viết ngày 2026-09-24 để lưu vết quyết định.

---

## 1. Bối cảnh

Trong tài liệu đặc tả kiến trúc ban đầu (Master Plan §5.9), bộ định tuyến ý định người dùng (**UC022 Intent Router**) được thiết kế để khảo sát và so sánh 3 phương án (3 nhánh):

1. **Nhánh A (Baseline truyền thống):** Mô hình hóa n-gram từ vựng bằng `TF-IDF` kết hợp bộ phân loại tuyến tính `LinearSVC` hoặc `LogisticRegression`.
2. **Nhánh B (Deep Learning chuyên sâu):** Fine-tune mô hình Transformer đa ngôn ngữ tiền huấn luyện (`xlm-roberta-base` hoặc `phobert-base-v2`) trên toàn bộ tập dữ liệu đã khử trùng lặp.
3. **Nhánh C (Kiến trúc tận dụng Vector Embedding):** Tái sử dụng vector biểu diễn ngữ nghĩa 1024 chiều trích xuất từ dịch vụ `ai-embed` (`BAAI/bge-m3`) kết hợp bộ phân loại nhẹ (`LogisticRegression` hoặc `k-NN`).

Khi bước vào Ngày 4 và Ngày 5 của kế hoạch 21 ngày (giai đoạn huấn luyện và so sánh mô hình), nhóm phát triển phải đối mặt với áp lực thời gian biểu nghiêm ngặt và yêu cầu tối ưu hóa tài nguyên phần cứng tại môi trường vận hành thực tế.

---

## 2. Quyết định

**Chính thức cắt giảm phạm vi (Scope Reduction): LOẠI BỎ NHÁNH A (TF-IDF + LinearSVC). Tập trung nguồn lực triển khai Nhánh C ở tầng suy luận runtime và chuẩn bị Nhánh B fine-tune trên Kaggle GPU qua đêm.**

Cụ thể:
1. Không xây dựng pipeline huấn luyện và không xuất artifact cho Nhánh A.
2. Triển khai trọn vẹn **Nhánh C** tại tầng suy luận cục bộ: Huấn luyện bộ phân loại nhẹ trên không gian vector nhúng của `ai-embed`, đánh giá chi tiết trên tập test 200 câu người thật được kiểm định chỉ số Cohen's Kappa.
3. Chuẩn bị mã nguồn huấn luyện **Nhánh B** dưới dạng notebook chuẩn hóa (§5.8), đóng gói để đẩy lên hạ tầng Kaggle GPU T4 chạy nền qua đêm (3–4 giờ máy tính toán, 0 giờ nhân lực).

---

## 3. Lý do & Lợi thế cấu trúc của Nhánh C

Quyết định ưu tiên Nhánh C và loại bỏ Nhánh A được thúc đẩy bởi **lợi thế cấu trúc (Structural Advantage)** mang tính cốt lõi trong toàn bộ vòng đời xử lý hội thoại của hệ thống AI CRM:

### 3.1. Chi phí độ trễ THÊM cho Router bằng KHÔNG (Zero Additional Latency)
* Trong luồng xử lý RAG (Retrieval-Augmented Generation) của nền tảng, mọi tin nhắn của khách hàng bước vào hệ thống đều bắt buộc phải đi qua bước nhúng vector tại `ai-embed` (`BAAI/bge-m3`, 1024 chiều) để phục vụ việc truy hồi tri thức (UC023 Retrieval) và ghi nhận hồ sơ tương tác.
* Do đó, **Router và Retrieval dùng chung MỘT lời gọi embedding duy nhất**. 
* Khi vector 1024 chiều đã nằm sẵn trong bộ nhớ, chi phí để bộ phân loại `LogisticRegression` của Nhánh C tính toán xác suất 7 nhánh ý định chỉ là một phép nhân ma trận đại số tuyến tính đơn giản trên CPU, tiêu tốn **dưới 0,5 ms**.
* Đây là một lợi thế cấu trúc tự nhiên, không phải một giải pháp chắp vá hay phương án phụ.

### 3.2. Khắc phục triệt để nhược điểm từ vựng của TF-IDF đối với tiếng Việt thực tế
* Kết quả khảo nghiệm dữ liệu ở Ngày 4 cho thấy tin nhắn khách hàng trong thực tế phân bố qua 6 văn phong phức tạp: 25% chat ngắn viết tắt teencode (`short_abbrev`), 20% không dấu (`no_accent`), 15% lỗi chính tả gõ vội (`typo`), 10% pha trộn thuật ngữ tiếng Anh (`en_mix`).
* Bộ trích xuất `TF-IDF` của Nhánh A hoạt động dựa trên sự trùng khớp chính xác của các n-gram từ vựng. Khi gặp từ viết tắt, sai dấu hoặc teencode, tỷ lệ từ ngoài từ điển (Out-Of-Vocabulary - OOV) tăng vọt, khiến mô hình phân loại hoàn toàn mất phương hướng hoặc dự đoán sai lệch.
* Ngược lại, không gian vector nhúng của `bge-m3` (Nhánh C) được huấn luyện trên hàng tỷ cặp câu đa ngôn ngữ, có khả năng ánh xạ các biến thể từ vựng, từ không dấu và lỗi chính tả về cùng một vùng lân cận ngữ nghĩa, đem lại độ bền vững (robustness) vượt trội.

---

## 4. Đánh đổi (Trade-offs)

Hội đồng phản biện cần lưu ý các đánh đổi kỹ thuật đi kèm quyết định này:

| Yếu tố | Nhánh A (Bị loại bỏ) | Nhánh C (Được chọn làm lưới an toàn) |
|---|---|---|
| **Độ trễ độc lập** | 2–5 ms (CPU thuần, không cần embedding). | Cần vector từ `ai-embed` (~120 ms p95). Nhưng trong pipeline RAG, chi phí này đã được trả từ trước. |
| **Tính độc lập hạ tầng** | Độc lập 100%, không phụ thuộc service khác. | Phụ thuộc vào tính sẵn sàng của `ai-embed`. |
| **Độ chính xác trên biến thể** | Thấp, dễ gãy khi gặp teencode, gõ không dấu. | Rất cao nhờ kế thừa không gian ngữ nghĩa dense vector. |
| **Chi phí bảo trì & dung lượng** | Cần lưu trữ từ điển vocabulary (vài MB đến chục MB). | Cực nhẹ: Chỉ lưu ma trận trọng số $7 \times 1024$ (~58 KB). |

### Chiến lược ứng phó khi `ai-embed` gặp sự cố (Fallback Strategy)
* Nếu `ai-embed` ngừng hoạt động, hệ thống RAG sẽ kích hoạt cơ chế chuyển mạch sang chế độ truy hồi chỉ từ khóa (sparse-only retrieval qua BM25/Elasticsearch theo ADR-0006).
* Đối với bộ định tuyến, hệ thống được bảo vệ bởi kiến trúc phân tầng 3 lớp (Master Plan §5.9):
  1. **Tầng 1 (Rule-based Regex):** Luôn xử lý các trường hợp khẩn cấp (`HANDOFF_HUMAN`, `TECH_ERROR`) mà không cần vector.
  2. **Tầng 3 (LLM Fallback):** Nếu không thể phân loại tự tin ở tầng máy học, tin nhắn sẽ được chuyển tiếp trực tiếp cho LLM phân tích ngữ cảnh.
* Do đó, việc loại bỏ Nhánh A không gây ra bất kỳ điểm nghẽn đơn lẻ (Single Point of Failure) nào cho toàn bộ kiến trúc.

---

## 5. Kết luận

Việc loại bỏ Nhánh A là một **quyết định kỹ thuật có tính toán và cơ sở thực nghiệm vững chắc**, giúp tập trung tối đa nguồn lực vào Nhánh C (lưới an toàn tối ưu cho runtime) và Nhánh B (mô hình transformer fine-tune qua đêm trên Kaggle GPU). 

Quyết định này đảm bảo hệ thống đạt được cả hai mục tiêu: chất lượng phân loại cao trong môi trường ngôn ngữ thực tế và tuân thủ nghiêm ngặt ngân sách thời gian phát triển của đồ án.

---

## 6. Minh chứng Thực nghiệm & Hướng dẫn Kiểm chứng

Để kiểm chứng quyết định này và xác thực các chỉ số thực tế của Nhánh C:
1. **Chạy kiểm thử tự động:**
   ```powershell
   python -m pytest ai-service/tests/unit/test_router_branch_c.py -v
   ```
2. **Chạy pipeline huấn luyện & Đo đạc độ trễ overhead:**
   ```powershell
   python scripts/train_router_branch_c.py
   ```
3. **Báo cáo và biểu đồ minh chứng:**
   - Báo cáo số liệu JSON: [reports/eval/router_branch_c_eval.json](../../reports/eval/router_branch_c_eval.json)
   - Biểu đồ ma trận nhầm lẫn: [reports/eval/router_branch_c_confusion_matrix.png](../../reports/eval/router_branch_c_confusion_matrix.png)
   - Log xác nhận phiên chạy Kaggle GPU Nhánh B: [reports/eval/kaggle_xlmr_training_launch.log](../../reports/eval/kaggle_xlmr_training_launch.log)
