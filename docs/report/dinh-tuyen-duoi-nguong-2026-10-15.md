# Định tuyến câu dưới ngưỡng τ — so các phương án bằng số (15/10/2026)

> Bối cảnh: báo cáo M2 §8.4. Bật router thật thì phần lớn câu hỏi tri thức có độ tin cậy dưới
> τ = 0,65 và bị đưa vào nhánh hỏi lại `CLARIFY`. Người dùng nghiêng về phương án **D — cộng xác suất
> theo ô**, và yêu cầu đo lại toàn bộ, không thiên vị. Nếu D kém thì đề xuất cách khác.
> Kết quả của báo cáo này là đầu vào cho ADR-0035.

## 1. Cách đo — CHỐT TRƯỚC KHI CHẠY

Mục này viết xong **trước** khi có bất kỳ con số nào. Không sửa định nghĩa, tiêu chí hay τ sau khi
thấy số.

### 1.1. Ba ô

Router chỉ cần chọn đúng **ô** trong bản đồ luồng. Bảy ý định dẫn về ba ô:

| Ô | Ý định | Nhánh |
|---|---|---|
| **giữa** — tra tri thức | KB_SEARCH · PRICING_POLICY · COMPLAINT_SUPPORT · TECH_ERROR | `RAG` |
| **phải** — chuyển giao | HANDOFF_HUMAN · BUYING_INTENT | `HANDOFF` · `TOOL_CALL` |
| **trái** — mẫu câu | GREETING | `SMALL_TALK` |
| *(không ô nào)* | — | `CLARIFY` (hỏi lại) |

### 1.2. Các phương án

Mọi phương án dùng **cùng một lượt gọi ai-classify** cho mỗi câu (cùng 7 xác suất). Chỉ khác nhau ở
luật chọn nhánh. τ = **0,65** cố định theo ADR-0019. Ngưỡng đi nhanh 0,85 cho câu chào giữ nguyên ở mọi
phương án.

| Mã | Tên | Luật |
|---|---|---|
| **R0** | Không router (mốc so) | Mọi câu đi `RAG`. Đây là hành vi khi ai-classify chết, cũng là hành vi ngày 10/10 |
| **A** | Hiện tại | Đúng `decide_route` của `router.py`: nhãn đứng đầu ≥ τ thì theo nhãn, dưới τ thì `CLARIFY` |
| **B** | Dưới τ đi RAG | Như A, nhưng dưới τ thì `RAG` thay cho `CLARIFY` |
| **D** | Cộng theo ô | Cộng xác suất từng ô. Ô **phải** ≥ τ thì chuyển giao (chọn `HANDOFF`/`TOOL_CALL` theo ý định lớn hơn trong ô). Ô **trái** ≥ 0,85 thì `SMALL_TALK`. Ô **giữa** ≥ τ thì `RAG`. Không ô nào đạt thì `CLARIFY` |
| **E** | Cộng theo ô, dưới τ đi RAG | Như D, nhưng không ô nào đạt thì `RAG` thay cho `CLARIFY` |

Chi tiết giữ giống A ở mọi phương án để so công bằng: câu chào có xác suất từ 0,65 tới dưới 0,85 rơi
xuống `RAG` (đúng hành vi hiện tại của `router.py`, xem M2 §8.4).

**Không đo trong lượt này:** C — gọi Gemini phân loại lại câu dưới τ (thiết kế gốc ADR-0019 §3.3). Lý do:
chưa có lời nhắc phân loại nào trong code, và mỗi câu dưới τ tốn một lượt Gemini có hạn mức. Ghi rõ ở
kết luận nếu C cần đo.

### 1.3. Dữ liệu (chỉ đọc)

| Mã | Tệp | n | Nhãn đúng | Vai trò |
|---|---|---|---|---|
| **H** | `data/intent_test_human.jsonl` (tập test người thật, đóng băng) | 200 | ý định do người gán ⇒ ô đúng | **Tập chính.** Đủ 7 ý định (28–30 câu mỗi ý định) |
| **G+** | `golden_set.jsonl`, câu có `can_cu` | 100 | ô giữa | Câu hỏi tri thức có đáp án |
| **G0** | `golden_set.jsonl`, câu `can_cu` rỗng | 12 | không có đáp án | Tham khảo |
| **N** | `ngoai_pham_vi.jsonl` | 30 | không có đáp án | Tham khảo |
| **T** | `tu_choi_mo_rong.jsonl` | 38 | không có đáp án | Tham khảo |

**Vì sao H là tập chính:** G+ toàn câu hỏi tri thức, nên R0 (mọi câu đi RAG) *chắc chắn* đạt 100% trên G+.
Một phương án càng giống R0 càng đẹp trên G+. Chỉ H có đủ câu chào, câu xin gặp người, câu muốn mua, nên
chỉ H phạt được phương án đẩy nhầm những câu đó vào RAG.

**Hạn chế đã biết của H:** phân bố đều 7 ý định, không phải phân bố lưu lượng thật. Tỉ lệ không gọi LLM
tính trên H chỉ là ước tính.

**Sổ hash:** sha256 của `data/intent_test_human.jsonl` là `80a5f713ce7d0c1a…`, **không khớp** dòng 3 của
`artifacts/DATA_HASHES.txt` (`8cc500dc…`). Git cho thấy tệp này và dòng sổ được thêm **cùng một commit**
`870b150` (04/10) và chưa từng sửa sau đó. Vậy không có dấu hiệu tệp bị sửa để nâng điểm. Nhưng không
chứng minh được tệp trùng với bản đã băm lúc đóng băng. Đây cũng là tệp mà ADR-0019 dùng để đo, nên các số
ở đây so được với ADR-0019. Báo Dev B; không sửa sổ (tệp bị chặn cứng).

### 1.4. Chỉ số

Trên **H** (mỗi câu rơi vào đúng một trong ba loại):

- **Đúng ô** — đi đúng ô của nhãn người gán;
- **Sai ô** — đi một ô khác;
- **Hỏi lại** — `CLARIFY`.

Thêm bốn số:

- **Độ chính xác khi không hỏi lại** = đúng ô ÷ (đúng ô + sai ô). Là bản "theo ô" của số 0,924 của ADR-0019;
- **Khách xin người mà bot tự trả lời**: trong 28 câu `HANDOFF_HUMAN`, số câu đi ô giữa hoặc ô trái;
- **Câu tri thức bị đẩy cho nhân viên**: trong 116 câu nhãn ô giữa, số câu đi ô phải;
- **Ước tính lượt không gọi LLM**: tỉ lệ câu không đi `RAG` (`RAG` gần như luôn gọi LLM vì sàn toàn tập = 0,
  M2 §6.5).

Trên **G+**: tỉ lệ tới `RAG`, tỉ lệ hỏi lại, tỉ lệ sai ô. Trên **G0, N, T**: phân bố nhánh, chỉ để đọc.

### 1.5. Tiêu chí chọn

1. **Chính:** đúng ô trên H và tỉ lệ tới RAG trên G+, cả hai càng cao càng tốt.
2. **Rào chắn an toàn:** "khách xin người mà bot tự trả lời". Phương án nào làm số này **tăng so với A**
   thì không tự chọn, mà trình số để người dùng chốt đánh đổi.
3. **Rào chắn chi phí:** "câu tri thức bị đẩy cho nhân viên" và "ước tính lượt không gọi LLM". Chỉ báo, không
   loại phương án.
4. Nếu D không phải phương án tốt nhất theo 1–2 thì nói thẳng, và đề xuất phương án tốt hơn kèm số.

**Độ nhạy theo τ** (0,50 → 0,90) chỉ để xem kết luận có đổi khi τ đổi hay không. **Không dùng để chọn τ**:
chọn τ trên chính tập test là tự chấm bài của mình.

## 2. Kết quả — các phương án đã chốt trước (R0, A, B, D, E)

Chạy `python -m tests.eval.danh_gia_dinh_tuyen` (commit `66642b8` + script mới), ai-classify :8083
`intent-router-v1`, τ = 0,65, ngưỡng đi nhanh 0,85. **Chạy hai lần, số của R0/A/B/D/E giống hệt nhau**
(ai-classify chấm bằng luật + ONNX, không ngẫu nhiên).

Kiểm giả định của D/E trên đầu ra ai-classify: 380 câu khác nhau; bảy xác suất cộng lệch 1 quá 0,01: **0**
câu; nhãn khác xác suất lớn nhất: **0** câu. Tầng quyết định: luật 92 · ONNX 54 · dưới τ 234.

### 2.1. Tập H — 200 câu người thật

| Phương án | Đúng ô | Sai ô | Hỏi lại | Chính xác khi không hỏi lại | Xin người → bot tự trả lời | Xin người → hỏi lại | Tri thức → nhân viên | Ước tính không gọi LLM |
|---|---|---|---|---|---|---|---|---|
| R0 | 116 (58%) | 84 (42%) | 0 | 0,580 | 28/28 | 0/28 | 0/116 | 0% |
| A | 107 (54%) | 14 (7%) | 79 (40%) | 0,884 | **1/28** | 7/28 | 8/116 | 72% |
| B | 162 (81%) | 38 (19%) | 0 | 0,810 | 8/28 | 0/28 | 8/116 | 32% |
| **D** | 152 (76%) | 19 (10%) | 29 (14%) | **0,889** | 2/28 | 3/28 | 8/116 | 48% |
| E | 165 (82%) | 35 (18%) | 0 | 0,825 | 5/28 | 0/28 | 8/116 | 34% |

Câu đi sai ô, theo nhãn người gán → ô đã đi:

| | BUYING → giữa | GREETING → giữa | GREETING → phải | HANDOFF → giữa | HANDOFF → trái | COMPLAINT → phải | PRICING → phải |
|---|---|---|---|---|---|---|---|
| A | 3 | 0 | 2 | 0 | 1 | 3 | 5 |
| B | 15 | 5 | 2 | 7 | 1 | 3 | 5 |
| D | 7 | 0 | 2 | 1 | 1 | 3 | 5 |
| E | 15 | 5 | 2 | 4 | 1 | 3 | 5 |

### 2.2. Tập G+ — 100 câu bộ vàng có đáp án

| Phương án | Tới RAG | Hỏi lại | Sai ô |
|---|---|---|---|
| R0 | 100 | 0 | 0 |
| A | **14** | 79 | 7 |
| B | 93 | 0 | 7 |
| **D** | **60** | 32 | 8 |
| E | 92 | 0 | 8 |

### 2.3. Tập không có đáp án — phân bố ô (giữa · phải · trái · hỏi lại)

| Phương án | G0 (12) | N (30) | T (38) |
|---|---|---|---|
| A | 0 · 0 · 0 · 12 | 1 · 1 · 0 · 28 | 2 · 0 · 0 · 36 |
| B, E | 12 · 0 · 0 · 0 | 29 · 1 · 0 · 0 | 38 · 0 · 0 · 0 |
| D | 3 · 0 · 0 · 9 | 14 · 1 · 0 · 15 | 18 · 0 · 0 · 20 |

Câu không có đáp án đi ô giữa thì RAG từ chối ("chưa tìm thấy thông tin… có muốn em chuyển nhân viên không").
Đi ô hỏi lại thì khách nhận "em chưa hiểu ý", sai với câu đã hỏi rõ.

### 2.4. Độ nhạy theo τ (không dùng để chọn τ)

H: đúng · sai · hỏi lại | G+: tới RAG.

| τ | A | B | D | E |
|---|---|---|---|---|
| 0,50 | 128 · 17 · 55 \| 22 | 164 · 36 · 0 \| 93 | 164 · 26 · 10 \| 82 | 167 · 33 · 0 \| 91 |
| 0,60 | 115 · 14 · 71 \| 18 | 162 · 38 · 0 \| 93 | 154 · 19 · 27 \| 67 | 165 · 35 · 0 \| 91 |
| **0,65** | 107 · 14 · 79 \| 14 | 162 · 38 · 0 \| 93 | 152 · 19 · 29 \| 60 | 165 · 35 · 0 \| 92 |
| 0,70 | 96 · 14 · 90 \| 13 | 159 · 41 · 0 \| 93 | 149 · 16 · 35 \| 50 | 163 · 37 · 0 \| 93 |
| 0,80 | 85 · 14 · 101 \| 11 | 157 · 43 · 0 \| 94 | 128 · 14 · 58 \| 27 | 158 · 42 · 0 \| 94 |

Trong cả dải τ, A luôn thấp nhất, và trên G+ D luôn dưới B và E. Kết luận ở §5 vì thế không phụ thuộc việc
chọn đúng 0,65. Riêng D rất nhạy với τ trên G+ (82 ở 0,50 → 27 ở 0,80): D đứng ngay trên mép ngưỡng với tenant
demo.

## 3. Ba phát hiện ngoài bảng

### 3.1. Router lệch lĩnh vực so với tenant demo — phát hiện quan trọng nhất

| Tệp | n | Câu có từ điện máy (máy giặt, tủ lạnh, bảo hành, lắp đặt…) | Câu có từ phần mềm (gói, token, tài khoản, chatbot…) |
|---|---|---|---|
| `intent_train_dedup.jsonl` (dữ liệu huấn luyện router) | 1.941 | **0 (0%)** | 491 (25%) |
| `intent_test_human.jsonl` (H) | 200 | 1 (0%) | 53 (26%) |
| `golden_set.jsonl` (kho của tenant demo) | 112 | **50 (45%)** | 3 (3%) |

Router học trên câu của một **nền tảng phần mềm**, còn tenant demo là **cửa hàng điện máy**. Hệ quả:

- H đo router **trong lĩnh vực nó đã học**, nên số trên H là số lạc quan cho tenant demo. G+ mới phản ánh tenant demo;
- nền tảng phục vụ nhiều doanh nghiệp vừa và nhỏ, mỗi doanh nghiệp một lĩnh vực. **Ngoài lĩnh vực là tình huống
  thường, không phải ngoại lệ.** Luật định tuyến tốt phải chịu được điều đó;
- RAG + lối từ chối thì *không* phụ thuộc lĩnh vực: nó tra đúng kho của từng tenant. Đây là lý do các phương án
  dựa vào RAG khi không chắc (B, E) mạnh hẳn trên G+.

### 3.2. Tầng luật bắt nhầm từ khoá — không phụ thuộc τ

7/8 câu G+ mà D đưa sai ô đến từ tầng luật hoặc ONNX với độ tin cậy cao. Ví dụ:
"**nhân viên** lắp đặt có khoan đục tường giúp không" → HANDOFF_HUMAN 0,98 (luật), "**đặt hàng** trên
website như thế nào" → BUYING_INTENT 0,93 (luật), "có **thanh toán** bằng ví điện tử được không" →
BUYING_INTENT 0,93 (luật). Trên H, "alo co nguoi that o day k" → GREETING 0,96 (luật): đây là câu duy nhất
mà A để bot tự trả lời khách xin người. Mọi phương án đều dính các lỗi này. Sửa luật (code của Dev B,
`inference/`) thì mọi phương án cùng tốt lên. **Nợ của Dev B, báo, không sửa hộ.**

### 3.3. Vì sao D vẫn hỏi lại 32/100 câu G+

Trong 32 câu này, xác suất ô giữa có trung vị **0,53**, cao nhất **0,646** (sát ngưỡng). Phần còn lại rò đều
sang ô trái (chào, trung bình 0,23) và ô phải (trung bình 0,26): 16 câu rò sang trái nhiều hơn, 16 câu rò
sang phải nhiều hơn. Router ngoài lĩnh vực không biết đặt xác suất vào đâu, nên rải ra cả ba ô.

## 4. Phương án F\* — THÊM SAU KHI THẤY SỐ

> ⚠️ F\* được thiết kế **sau khi** đọc §2–§3, nên số của nó trên H và G+ là **số lạc quan**: luật được nghĩ
> ra khi đã nhìn đúng những câu này. Không có tham số mới nào được chỉnh (chỉ dùng τ đã chốt), nhưng điều đó
> không xoá được thiên lệch chọn luật.

**Luật:** như D. Khi không ô nào đạt τ thì xem ô lớn nhất. Ô **phải** lớn nhất thì hỏi lại, vì khách có thể đang
xin người hay muốn mua, và hỏi lại rẻ hơn bỏ qua họ. Còn lại thì **RAG**, lối từ chối UC025 làm lưới.

| Tập | Đúng ô / tới RAG | Sai ô | Hỏi lại | Chính xác khi không hỏi lại | Xin người → bot tự trả lời | BUYING → giữa |
|---|---|---|---|---|---|---|
| H | 163 (82%) | 29 (14%) | 8 (4%) | 0,849 | 3/28 | 12/28 |
| G+ | **90/100** | 8 | 2 | | | |
| G0 · N · T | giữa 10/12 · 28/30 · 37/38 | | | | | |

Độ nhạy: F\* trên G+ giữ **90** ở mọi τ từ 0,50 tới 0,90 — không đứng trên mép ngưỡng như D.

Ba câu xin người mà bot tự trả lời, theo phương án:

| Câu (H) | ai-classify | A | D | F\* |
|---|---|---|---|---|
| "alo co nguoi that o day k" | GREETING 0,96 — **lỗi tầng luật** (§3.2) | trái | trái | trái |
| "Co nhan vien nao online ko giup minh voi" | HANDOFF_HUMAN 0,32; ô giữa 0,651 | hỏi lại | giữa | giữa |
| "Cho e xin so dien thoai cua quan ly truc tiep" | GREETING 0,52; ô trái lớn nhất | hỏi lại | hỏi lại | giữa |

## 5. Kết luận theo tiêu chí §1.5

**Rào chắn an toàn:** A để bot tự trả lời 1/28 câu xin người, và câu đó do lỗi tầng luật. **Không phương án nào
giữ được mức đó**: D 2 · F\* 3 · E 5 · B 8. Theo §1.5 thì **không tự chọn**, mà trình bảng đánh đổi để người dùng chốt.

| | A (hiện tại) | **D (người dùng chọn)** | **F\*** (thêm sau) | E |
|---|---|---|---|---|
| H — đúng ô | 54% | 76% | 82% | 82% |
| H — chính xác khi không hỏi lại | 0,884 | **0,889** | 0,849 | 0,825 |
| **G+ — câu có đáp án tới RAG** | 14 | **60** | **90** | 92 |
| G+ — hỏi lại | 79 | 32 | 2 | 0 |
| Xin người → bot tự trả lời | 1/28 | 2/28 | 3/28 | 5/28 |
| Muốn mua → bot tự trả lời | 3/28 | 7/28 | 12/28 | 15/28 |
| Ước tính không gọi LLM (H) | 72% | 48% | 38% | 34% |
| Đã chốt trước khi đo? | có | có | **không** | có |

**Đánh giá D, không thiên vị:**

- Trên H, D **tốt hơn A ở mọi chỉ số trừ một**: đúng ô 54% → 76%, hỏi lại 40% → 14%, độ chính xác khi không hỏi lại
  giữ nguyên (0,884 → 0,889). Đổi lại, thêm 1 câu xin người bị bot trả lời. Cộng theo ô là **đúng hướng**;
- trên tenant demo (G+), D **chưa đủ**: vẫn hỏi lại 32/100 câu có đáp án. Đây đúng là tình huống ngoài lĩnh
  vực (§3.1), và D đứng sát mép ngưỡng (82 → 27 khi τ đi từ 0,50 lên 0,80);
- vậy D **kém hiệu quả với chính tenant demo**. Yêu cầu "nếu kém hiệu quả thì đề xuất cách mới" áp dụng ở đây.

**Đề xuất:** F\*, với điều kiện **kiểm lại trên một tập mới** trước khi chốt, vì số hiện có của F\* là số lạc
quan. Lý do chọn F\* thay vì E: E chỉ hơn F\* 2 câu trên G+, nhưng để bot tự trả lời 5/28 câu xin người (F\* 3/28),
vì E không bao giờ hỏi lại, kể cả khi câu nghiêng về ô phải.

**Đánh đổi của F\* phải nói rõ:**

1. **Muốn mua → bot tự trả lời 12/28** (D: 7, A: 3). Câu như "Cho em mua gói nâng cao và thêm 20 account" đi RAG thay
   vì chuyển nhân viên kinh doanh. Nếu kho không có đáp án, RAG từ chối và mời chuyển nhân viên. Hệ quả này
   **chưa đo** trên lượt thật (LLM giả không tái hiện được lối từ chối của Gemini);
2. **Ước tính không gọi LLM 38%**, dưới KPI 55%. A đạt 72% nhờ hỏi lại khách, không phải nhờ trả lời rẻ. Số này tính
   trên H (phân bố đều 7 ý định), không phải lưu lượng thật;
3. Hai câu xin người bị bot trả lời đi RAG. Theo thiết kế (M2 §4), RAG không tìm thấy căn cứ thì từ chối kèm câu mời
   chuyển nhân viên, và từ chối 2 lần liền thì tự chuyển. Điều này giảm nhẹ hệ quả nhưng **chưa kiểm trên lượt thật**.

**Chưa đo: C — gọi Gemini phân loại lại** (thiết kế gốc ADR-0019). 234/380 câu (62%) rơi vào vùng dưới τ, tức khoảng
6/10 lượt chat sẽ tốn thêm một lượt Gemini **trước** lượt sinh câu trả lời. Chi phí và độ trễ đều cao hơn mọi
phương án ở trên. Chỉ nên đo nếu người dùng muốn có số đối chứng cho chương 5.

**Gốc của vấn đề không nằm ở luật định tuyến** mà ở §3.1: router không biết lĩnh vực của tenant. Không luật ngưỡng
nào sửa hết được điều đó. Hướng sửa gốc (huấn luyện router với dữ liệu nhiều lĩnh vực) là việc của Dev B, ngoài
phạm vi đợt này.

## 6. Việc tiếp theo

1. **Người dùng chốt** giữa D · F\* · E, hoặc kiểm F\* trên tập mới trước.
2. Nếu kiểm F\*: tập kiểm **mới**, lĩnh vực điện máy, đủ 7 ý định. Viết xong và khoá sha256 **trước** lần chạy đầu,
   giống quy trình bộ vàng (ADR-0020). So D · E · F\* trên tập đó với đúng tiêu chí §1.5.
3. Ghi quyết định vào **ADR-0035**, rồi mới sửa `router.py` và test.
4. Báo Dev B: lỗi tầng luật (§3.2); sổ hash `intent_test_human.jsonl` lệch (§1.3); router lệch lĩnh vực (§3.1).

## 7. Quyết định và kiểm sau khi sửa (15/10)

**Người dùng chốt D**: ưu tiên không để bot tự trả lời người xin gặp nhân viên hay người muốn mua, chấp nhận
tenant demo còn bị hỏi lại 32/100 câu có đáp án. Ghi ở [ADR-0035](../adr/0035-dinh-tuyen-duoi-nguong-cong-xac-suat-theo-o.md).
F\* không kiểm tiếp; nó và E là hai ứng viên đã có số nếu sau này mở lại (router huấn luyện lại, tầng luật được sửa).

**Sửa:** `src/ai/orchestrator/router.py`. `Classification` mang thêm `probabilities` (bảy xác suất ai-classify đã
trả, trước đây bị bỏ); `decide_route` cộng theo ô. Trường `probabilities` thiếu hay hỏng định dạng thì bỏ, quay về
ý định đứng đầu (kết quả trùng luật cũ), không biến thành lỗi phân loại. Script đánh giá chép nguyên luật cũ làm
phương án A.

**Kiểm:**

| Kiểm | Kết quả |
|---|---|
| `decide_route` production so với D trong script, trên 380 câu | khác **0** câu |
| D đổi quyết định mà luật cũ đã đưa ra (không phải hỏi lại) | **0** câu — D chỉ cứu câu luật cũ hỏi lại |
| Chạy lại script sau khi sửa: mọi bảng §2 và §4 | giống hệt lần đo trước khi sửa (18/18 dòng) |
| `ruff check src tests` · `pytest tests/unit` | sạch · 555 passed, 1 skipped, 1 failed (`test_intent_train_dedup_integrity`, hash lệch sổ — nợ có sẵn của Dev B) |
| `tests/unit/test_chat_routing.py` | 46 passed: thêm bảng cộng theo ô (câu (a), (b) với xác suất thật), thiếu xác suất thì trùng luật cũ, xác suất hỏng thì bỏ |

Lượt thật qua `POST /v1/ai/chat` (ai-service chạy lại với code mới, `.env` mặc định, LLM **giả**, rerank bật):

| Câu | Trace | Luật cũ (15/10 sáng) | Sau ADR-0035 |
|---|---|---|---|
| (a) "mất hóa đơn rồi thì còn được bảo hành không" | `adr35-a-222630` | `CLARIFY` | **`RAG`**, 1 trích dẫn, `rerank_ms` 9484 |
| (b) "có dịch vụ vệ sinh sofa và rèm cửa tại nhà không" | `adr35-b-222641` | `CLARIFY` | **`RAG`** |
| (c) "cho em gặp nhân viên tư vấn với ạ" | `adr35-c-222651` | `HANDOFF` | `HANDOFF` (không đổi) |
| "Co ai truc tong dai truc tiep khong a" (ô chuyển giao 0,582 < τ) | `adr35-c2-222651` | `CLARIFY` | `CLARIFY` (không đổi — đúng ý D) |

Giới hạn: với LLM giả, (b) không tái hiện được lối từ chối `NOT_COVERED` mà Gemini thật cho ngày 10/10; LLM giả luôn
"trả lời" kèm trích dẫn. Lượt này chỉ kiểm **định tuyến**. Lối từ chối sau định tuyến cần một lượt Gemini thật.
