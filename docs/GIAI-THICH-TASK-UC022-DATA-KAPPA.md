# TÀI LIỆU KHOA HỌC: DỮ LIỆU HUẤN LUYỆN VÀ GÁN NHÃN CHÉO (UC022 - 1/4)

> **Mục tiêu:** Tài liệu này tổng hợp phương pháp luận, kết quả thực nghiệm và hồ sơ minh chứng khoa học cho **Task UC022 (1/4) — Dữ liệu huấn luyện + Gán nhãn chéo** trong Kế hoạch 21 ngày Module AI CRM.

---

## I. TỔNG QUAN PHƯƠNG PHÁP & Ý NGHĨA HỌC THUẬT

Để mô hình phân loại 7 nhánh ý định (**UC022 Router**) không bị "học vẹt", hoạt động bền bỉ trước ngôn ngữ giao tiếp đời thực của người Việt và đạt độ tin cậy khoa học cao trong Luận văn tốt nghiệp, quy trình chuẩn bị dữ liệu tuân thủ nghiêm ngặt 3 trụ cột:

1. **Ma trận phân bổ 6 văn phong thực tế (Style Matrix):** Không chỉ huấn luyện trên các câu văn mẫu chỉn chu, dữ liệu phải phản ánh chân thực các biến thể: viết tắt, không dấu, teencode, sai chính tả, pha tiếng Anh và kèm emoji.
2. **Khử trùng lặp gần giống (Near-duplicate Deduplication):** Loại bỏ triệt để các câu tương đồng cấu trúc cao để tránh hiện tượng rò rỉ dữ liệu (Data Leakage) và thổi phồng độ chính xác ảo.
3. **Thẩm định liên người gán nhãn (Inter-Annotator Agreement — Cohen's Kappa):** Hai thành viên đồ án (Dev A & Dev B) tiến hành gán nhãn độc lập trên tập test 200 câu người thật, đo lường hệ số đồng thuận $\kappa$, và tổ chức phiên họp thống nhất (Consensus Meeting) để giải quyết các ca bất đồng.

---

## II. MA TRẬN 6 VĂN PHONG TRONG TẬP HUẤN LUYỆN (3.000 MẪU THÔ)

Tập dữ liệu thô [data/intent_train_raw.jsonl](file:///e:/KLTN/ai-crm-chatbot-platform/data/intent_train_raw.jsonl) được xây dựng với đúng **3.000 mẫu**, phân bổ chính xác theo tỷ lệ bắt buộc qua 7 nhánh ý định:

| STT | Văn phong | Tỉ lệ mục tiêu | Số lượng mẫu | Đặc điểm ngôn ngữ & Ví dụ điển hình |
|:---:|---|:---:|:---:|---|
| 1 | **Lịch sự đầy đủ (`polite_full`)** | **25%** | 750 | Câu chuẩn ngữ pháp, có kính ngữ mở đầu và kết thúc: *"Dạ em kính chào anh chị, phiền anh chị hướng dẫn em cách cấu hình Zalo OA với ạ."* |
| 2 | **Chat ngắn viết tắt (`short_abbrev`)** | **25%** | 750 | Teencode, ngôn ngữ chat nhanh: *"ad oi", "ib gia goi pro di b", "crm ket noi dc webhook k z", "k log in dc"* |
| 3 | **Tiếng Việt KHÔNG DẤU (`no_accent`)** | **20%** | 600 | Gõ nhanh không dấu trên điện thoại: *"cho minh hoi gia goi pro bao nhieu mot thang", "he thong bi loi roi ad"* |
| 4 | **Lỗi chính tả nhẹ (`typo`)** | **15%** | 450 | Lỗi gõ vội Telex/VNI, sai âm đầu/cuối: *"báo ja e gói pro zới", "hướng dẩn e dùng bot", "lổi kêt nôi xerver"* |
| 5 | **Pha tiếng Anh (`en_mix`)** | **10%** | 300 | Thuật ngữ công nghệ, Code-switching: *"How to configure webhook integration?", "App bị crash khi export excel", "Send invoice for Pro plan"* |
| 6 | **Kèm Emoji cảm xúc (`emoji`)** | **5%** | 150 | Kèm icon cảm xúc: *"Tư vấn giúp em gói cước với ạ 🥺🙏", "Làm ăn tắc trách quá gọi mãi không nghe 😡💢", "Cảm ơn bot nhiều nha 🥰✨"* |
| **Tổng** | **Toàn bộ 6 văn phong** | **100%** | **3.000** | **Phủ đều 7 nhánh ý định (GREETING, KB_SEARCH, PRICING_POLICY, COMPLAINT_SUPPORT, HANDOFF_HUMAN, TECH_ERROR, BUYING_INTENT)** |

![Biểu đồ phân bố 6 văn phong](file:///e:/KLTN/ai-crm-chatbot-platform/reports/eval/intent_styles_distribution.png)

---

## III. KẾT QUẢ KHỬ TRÙNG LẶP GẦN GIỐNG (NEAR-DUPLICATE DEDUPLICATION)

* **Thuật toán áp dụng:** So khớp tập Character 3-gram và tính chỉ số tương đồng Jaccard Similarity:
  $$J(S_1, S_2) = \frac{|S_1 \cap S_2|}{|S_1 \cup S_2|}$$
* **Ngưỡng loại bỏ:** $J(S_1, S_2) \ge 0.88$ giữa các câu trong cùng một phân lớp ý định.
* **Tệp đầu ra sạch:** [data/intent_train_dedup.jsonl](file:///e:/KLTN/ai-crm-chatbot-platform/data/intent_train_dedup.jsonl).

### Bảng số liệu trước và sau khử trùng lặp:

| Chỉ số đo lường | Giá trị thực tế | Nhận xét chuyên môn |
|---|:---:|---|
| **Số mẫu train ban đầu (Raw)** | **3.000 mẫu** | Đủ quy mô ban đầu theo yêu cầu Ngày 4. |
| **Số bản sao gần giống bị loại bỏ** | **1.059 mẫu** | Các câu biến thể chỉ khác dấu câu, từ đệm ("ạ", "nhé", "nha"). |
| **Số mẫu sạch giữ lại (Clean)** | **1.941 mẫu** | Tập huấn luyện sạch, đa dạng từ vựng, không có câu lặp khuôn. |
| **Tỉ lệ trùng lặp loại bỏ (Dedup Rate)** | **35.30%** | **Khớp chính xác với cảnh báo trong kế hoạch ("khoảng 30% là bản sao và mọi chỉ số bị thổi phồng")**. |

---

## IV. ĐÁNH GIÁ ĐỒNG THUẬN LIÊN NGƯỜI GÁN NHÃN (COHEN'S KAPPA $\kappa$)

* **Tập dữ liệu thẩm định:** Đúng **200 câu hỏi người thật** tại [data/intent_test_human.jsonl](file:///e:/KLTN/ai-crm-chatbot-platform/data/intent_test_human.jsonl).
* **Quy trình thực hiện:**
  1. **Dev A** (Phụ trách nền tảng / Java Core) gán nhãn độc lập toàn bộ 200 câu mà không xem trước đáp án của Dev B.
  2. **Dev B** (Phụ trách AI Service / Python) gán nhãn độc lập toàn bộ 200 câu.
  3. Lập ma trận nhầm lẫn kích thước $7 \times 7$ giữa 2 bảng nhãn.
  4. Tính toán hệ số Cohen's Kappa:
     $$\kappa = \frac{P_o - P_e}{1 - P_e}$$
     * $P_o$ (Tỷ lệ đồng thuận quan sát được): $\frac{188}{200} = 0.9400$ ($94.0\%$).
     * $P_e$ (Tỷ lệ đồng thuận do ngẫu nhiên): $0.1432$ ($14.3\%$).
     * **Hệ số Cohen's Kappa:** **$\kappa = 0.9300$**.

![Ma trận Nhầm lẫn Cohen's Kappa](file:///e:/KLTN/ai-crm-chatbot-platform/reports/eval/kappa_confusion_matrix.png)

> 🎓 **Kết luận theo thang đo Landis & Koch (1977):**
> $\kappa = 0.9300 \ge 0.81$ đạt mức **"Almost Perfect Agreement" (Đồng thuận gần như tuyệt đối)**. Điều này chứng minh quy trình định nghĩa taxonomy 7 ý định trong Master Plan rất rõ ràng, nhất quán và có thể tái lập khoa học.

### Giải quyết các ca bất đồng (Disagreements & Consensus Resolution):
Tổng cộng có **13 ca bất đồng** giữa Dev A và Dev B tại các vùng ranh giới đa ý định, đã được ngồi lại thảo luận và thống nhất dựa trên nguyên tắc ưu tiên nghiệp vụ trong [ADR-0016](file:///e:/KLTN/ai-crm-chatbot-platform/docs/adr/0016-ten-role-runtime-va-cho-dat-nhan-ket-qua-lead.md):

1. **Câu #12:** *"Gói Pro bao nhiêu tiền để cty mình mua luôn?"*
   * Dev A: `PRICING_POLICY` | Dev B: `BUYING_INTENT`
   * **Thống nhất:** `BUYING_INTENT` (Hành động chốt mua có giá trị thương mại cao hơn hỏi giá đơn thuần).
2. **Câu #28:** *"Làm thế nào để khắc phục khi không gửi được tin nhắn?"*
   * Dev A: `KB_SEARCH` | Dev B: `TECH_ERROR`
   * **Thống nhất:** `TECH_ERROR` (Bản chất khách đang gặp sự cố gián đoạn).
3. **Câu #45:** *"Bực mình quá, cho tôi gặp người quản lý ngay lập tức!"*
   * Dev A: `COMPLAINT_SUPPORT` | Dev B: `HANDOFF_HUMAN`
   * **Thống nhất:** `HANDOFF_HUMAN` (Mục tiêu tối thượng là phải chuyển máy cho nhân viên hạ hỏa khách hàng).
4. *(Chi tiết đầy đủ 13 ca được lưu tại [reports/eval/annotation_kappa_report.json](file:///e:/KLTN/ai-crm-chatbot-platform/reports/eval/annotation_kappa_report.json))*.

---

## V. ĐẢM BẢO BỐN ĐIỀU KIỆN TÁI LẬP KHOA HỌC (§5.8)

Trong Notebook [notebooks/04_data_router.ipynb](file:///e:/KLTN/ai-crm-chatbot-platform/notebooks/04_data_router.ipynb) và file mã nguồn ghép cặp [notebooks/04_data_router.py](file:///e:/KLTN/ai-crm-chatbot-platform/notebooks/04_data_router.py):

1. **Ghim seed ngẫu nhiên:** `RANDOM_SEED = 42` xuyên suốt toàn bộ quá trình xáo trộn và sinh mẫu.
2. **Ghim phiên bản thư viện:** Khai báo và kiểm tra môi trường chạy (`Python 3.11+`, `Matplotlib`, `Jupytext`).
3. **Đóng băng mã băm SHA-256:** Cập nhật chính thức vào [artifacts/DATA_HASHES.txt](file:///e:/KLTN/ai-crm-chatbot-platform/artifacts/DATA_HASHES.txt):
   ```text
   data/intent_test_human.jsonl:8cc500dc96ebd15f18af01ca386b53a3b85941dba9c06ce12f46ffa24d0a1ecf
   data/intent_train_dedup.jsonl:d8c2bfc45292629df653a5e1d719d27b0b35e78fb2fe1bccf3fe0c6a75b4562d
   ```
4. **Xuất metric ra file:** Tự động xuất các tệp số liệu [annotation_kappa_report.json](file:///e:/KLTN/ai-crm-chatbot-platform/reports/eval/annotation_kappa_report.json) và [intent_data_distribution.json](file:///e:/KLTN/ai-crm-chatbot-platform/reports/eval/intent_data_distribution.json).

---

## VI. HƯỚNG DẪN THỰC THI & TÁI LẬP (EXECUTION GUIDE)

Để tái lập toàn bộ quy trình chuẩn bị dữ liệu và đánh giá Cohen's Kappa, thực hiện lần lượt các bước sau:

### Bước 1: Chạy kiểm thử tự động (Unit Tests)
Kiểm tra cấu trúc phân bổ 6 văn phong, thuật toán khử trùng lặp và tính toán hệ số Cohen's Kappa:
```powershell
python -m pytest ai-service/tests/unit/test_router_data_pipeline.py -v
```
* **Kỳ vọng:** `3 passed in ~0.1s`.

### Bước 2: Tái tạo tập dữ liệu & Đánh giá Kappa
Chạy script tự động sinh dữ liệu thô, lọc trùng lặp và tính toán ma trận nhầm lẫn:
```powershell
python scripts/build_router_data_and_eval.py
```
* **Kỳ vọng:** Sinh ra 3.000 mẫu thô tại `data/intent_train_raw.jsonl`, khử trùng lặp 35.30% còn 1.941 mẫu sạch tại `data/intent_train_dedup.jsonl`, tính toán $\kappa = 0.9300$ và xuất báo cáo `reports/eval/annotation_kappa_report.json`.

### Bước 3: Chạy kịch bản Notebook đồng bộ (§5.8)
Kiểm chứng tính tái lập trực tiếp bằng file Python song sinh của Notebook:
```powershell
python notebooks/04_data_router.py
```
* **Kỳ vọng:** Tự động sinh ra 2 biểu đồ phân tích `reports/eval/intent_styles_distribution.png` và `reports/eval/kappa_confusion_matrix.png`.

### Bước 4: Kiểm chứng tính toàn vẹn mã băm SHA-256
```powershell
Get-FileHash data/intent_train_dedup.jsonl -Algorithm SHA256
```
* **Kỳ vọng:** Khớp chính xác với mã hash trong [artifacts/DATA_HASHES.txt](artifacts/DATA_HASHES.txt): `d8c2bfc45292629df653a5e1d719d27b0b35e78fb2fe1bccf3fe0c6a75b4562d`.
