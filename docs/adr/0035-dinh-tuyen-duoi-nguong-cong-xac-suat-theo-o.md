# ADR-0035 — Định tuyến câu dưới τ: cộng xác suất theo ô thay cho ngưỡng trên từng ý định

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-15
- **Làn sở hữu:** Track B (module AI)
- **Quan hệ:** sửa một phần [ADR-0019](0019-chot-nhanh-ship-intent-router-va-nguong-abstention.md) §3.3
  (vùng dưới τ) · đặc tả UC022 luồng phụ 5.1 · số đo:
  [`docs/report/dinh-tuyen-duoi-nguong-2026-10-15.md`](../report/dinh-tuyen-duoi-nguong-2026-10-15.md) ·
  phát hiện gốc: [`docs/report/m2-ngay14-2026-10-10.md`](../report/m2-ngay14-2026-10-10.md) §8.4

## Bối cảnh

- Ngày 15/10, router thật (`intent-router-v1`) được bật lần đầu trong lượt chat. Luật cũ của
  `decide_route`: ý định đứng đầu có xác suất **≥ τ = 0,65** thì theo ý định đó, **dưới τ thì hỏi lại khách**
  (`CLARIFY`). Kết quả: 79/100 câu có đáp án của bộ vàng bị hỏi lại, chỉ 14 câu tới được RAG.
- ADR-0019 §3.3 thiết kế vùng dưới τ đi *tầng 3 — gọi LLM phân loại lại*; code lại chọn hỏi lại theo luồng
  phụ 5.1 của UC022. Hai nguồn lệch nhau từ trước.
- Router học trên 1.941 câu về **nền tảng phần mềm** (0% từ vựng điện máy); tenant demo là **cửa hàng điện máy**
  (45% câu bộ vàng có từ điện máy). Nền tảng phục vụ nhiều doanh nghiệp vừa và nhỏ, mỗi doanh nghiệp một lĩnh
  vực, nên router gặp câu ngoài lĩnh vực là chuyện thường.
- Router không cần biết câu là *khiếu nại* hay *tra cứu*: bảy ý định chỉ dẫn về **ba ô** của bản đồ luồng —
  tra tri thức (KB_SEARCH, PRICING_POLICY, COMPLAINT_SUPPORT, TECH_ERROR) · chuyển giao (HANDOFF_HUMAN,
  BUYING_INTENT) · mẫu câu (GREETING). Câu "mất hóa đơn còn bảo hành không" có ý định đứng đầu chỉ 0,554,
  nhưng bốn ý định tra tri thức cộng lại 0,698.

## Các phương án đã cân nhắc

Cách đo và tiêu chí chọn chốt **trước khi chạy** (báo cáo §1). Mọi phương án chấm trên cùng đầu ra ai-classify.
H = 200 câu người thật (`data/intent_test_human.jsonl`); G+ = 100 câu bộ vàng có đáp án.

| Phương án | H: đúng ô | H: chính xác khi không hỏi lại | G+: tới RAG | Xin người → bot tự trả lời | Muốn mua → bot tự trả lời | Ưu | Nhược |
|---|---|---|---|---|---|---|---|
| A — ngưỡng trên từng ý định, dưới τ hỏi lại (cũ) | 54% | 0,884 | 14 | 1/28 | 3/28 | An toàn nhất cho câu xin người | Hỏi lại 4/5 câu tri thức của tenant demo |
| B — như A, dưới τ đi RAG | 81% | 0,810 | 93 | 8/28 | 15/28 | Gần như mọi câu tri thức tới RAG | Bỏ qua nhiều khách xin người nhất |
| **D — cộng theo ô, không ô nào đạt τ thì hỏi lại** | **76%** | **0,889** | **60** | **2/28** | **7/28** | Độ chính xác giữ như A; chỉ thêm 1 câu xin người bị bỏ qua | Vẫn hỏi lại 32/100 câu tri thức của tenant demo |
| E — cộng theo ô, không ô nào đạt τ thì đi RAG | 82% | 0,825 | 92 | 5/28 | 15/28 | Nhiều câu tri thức tới RAG | Không bao giờ hỏi lại, kể cả câu nghiêng về chuyển giao |
| F\* — như D, không ô nào đạt τ thì ô phải lớn nhất mới hỏi lại, còn lại đi RAG | 82% | 0,849 | 90 | 3/28 | 12/28 | Cân bằng nhất trên số đo | **Thiết kế sau khi thấy số** — số lạc quan, chưa kiểm trên dữ liệu mới |
| C — dưới τ gọi Gemini phân loại lại (ADR-0019) | chưa đo | | | | | Đúng thiết kế gốc | ~6/10 lượt tốn thêm 1 lượt LLM trước khi trả lời |

## Quyết định

**Router chọn ô bằng tổng xác suất của các ý định trong ô (phương án D):** ô chuyển giao ≥ τ thì chuyển giao;
ô mẫu câu ≥ 0,85 thì trả mẫu câu; ô tra tri thức ≥ τ thì đi RAG; không ô nào đạt thì hỏi lại khách.
τ giữ 0,65, ngưỡng đi nhanh giữ 0,85.

## Lập luận

- **D chỉ đổi những câu mà luật cũ đang hỏi lại.** Câu nào ý định đứng đầu đã ≥ τ thì ô của nó cũng ≥ τ, nên mọi
  quyết định mà A đã đưa ra được D giữ nguyên. D chỉ cứu những câu A bỏ phiếu trắng. Vì vậy độ chính xác khi
  không hỏi lại giữ nguyên (0,884 → 0,889), trong khi đúng ô tăng từ 54% lên 76% và câu hỏi lại giảm từ 40%
  xuống 14%.
- **Người dùng chốt D (15/10) vì ưu tiên không bỏ qua khách.** Hai sai lầm đắt nhất của chatbot chăm sóc khách
  là để bot tự trả lời người đang xin gặp nhân viên, và để bot tự trả lời người đang muốn mua (mất lead). Trong
  các phương án làm tăng số câu tri thức tới RAG, D là phương án tăng hai sai lầm đó ít nhất: 2/28 và 7/28,
  so với 3 và 12 của F\*, 5 và 15 của E.
- **F\* không được chọn dù cân bằng hơn trên số**, vì luật của F\* nghĩ ra sau khi đã nhìn đúng những câu dùng
  để chấm. Chọn nó là chọn theo số lạc quan.
- **Không chọn C** vì chi phí: 234/380 câu (62%) rơi vào vùng dưới τ, tức khoảng 6/10 lượt tốn thêm một lượt
  Gemini trước khi sinh câu trả lời, ngược với triết lý *Rule → ML → LLM*.
- **Không đổi τ.** τ = 0,65 chốt ở ADR-0019; chọn lại τ trên chính tập test là tự chấm bài. Bảng độ nhạy (báo
  cáo §2.4) cho thấy thứ hạng giữa các phương án không đổi theo τ.

## Đánh đổi

- **Tenant demo vẫn bị hỏi lại 32/100 câu có đáp án.** Đây là cái giá lớn nhất, chấp nhận có ý thức. Các câu này
  có xác suất ô tra tri thức trung vị 0,53, phần còn lại rò sang ô chào và ô chuyển giao, vì router không quen
  lĩnh vực điện máy. Khi tích hợp giao diện, khách của tenant demo sẽ gặp câu "em chưa hiểu ý" khá thường xuyên.
  Demo nên dùng câu hỏi mà router nhận ra được, hoặc nói rõ giới hạn này.
- **D đứng sát mép ngưỡng với tenant demo:** số câu G+ tới RAG đi từ 82 (τ = 0,50) xuống 27 (τ = 0,80). Router đổi
  phiên bản mà xác suất dịch đi một chút là con số này đổi mạnh. Phải đo lại `danh_gia_dinh_tuyen.py` mỗi khi
  đổi `router_model.onnx`.
- **Thêm 1/28 câu xin người bị bot tự trả lời** so với luật cũ ("Co nhan vien nao online ko giup minh voi", ô tra
  tri thức 0,651) và **thêm 4/28 câu muốn mua đi RAG**. Theo thiết kế, RAG không tìm thấy căn cứ thì từ chối kèm câu
  mời chuyển nhân viên, và từ chối hai lần liền thì tự chuyển. Điều này giảm nhẹ hệ quả nhưng **chưa kiểm trên lượt
  thật** (LLM giả không tái hiện lối từ chối của Gemini).
- **Tỉ lệ lượt không gọi LLM giảm**: ước tính trên H từ 72% xuống 48%, dưới KPI 55%. Con số 72% của luật cũ đạt
  được nhờ hỏi lại khách, không phải nhờ trả lời rẻ. Số tính trên H (phân bố đều 7 ý định), không phải lưu lượng
  thật.
- **Không sửa được gốc.** Router lệch lĩnh vực; tầng luật của ai-classify bắt nhầm từ khoá ("**nhân viên** lắp đặt…"
  → HANDOFF_HUMAN 0,98, "alo co nguoi that o day k" → GREETING 0,96). Hai việc này thuộc `inference/` của Dev B,
  phương án định tuyến nào cũng dính.
- Bản thân tập H lệch sổ hash `artifacts/DATA_HASHES.txt` ngay từ commit đầu (báo cáo §1.3). Không có dấu hiệu bị
  sửa, nhưng không chứng minh được tệp trùng bản đã băm lúc đóng băng.

## Hệ quả

- `src/ai/orchestrator/router.py`: `Classification` mang thêm `probabilities` (bảy xác suất ai-classify đã trả,
  trước đây bị bỏ); `decide_route` cộng theo ô. Ý định không thuộc ô chuyển giao hay ô mẫu câu tính vào ô tra tri
  thức, giữ đúng mặc định "còn lại đi RAG" của luật cũ. Thiếu `probabilities` (client giả) thì coi như chỉ có ý định
  đứng đầu: kết quả trùng luật cũ.
- **Không đổi** schema `ai.ai_interactions`, hợp đồng `ChatResponse`, tên nhánh hay `route_reason`. `intent` và
  `intent_confidence` vẫn ghi ý định đứng đầu.
- `tests/eval/danh_gia_dinh_tuyen.py` giữ luật cũ làm mốc so (A) và kiểm rằng `decide_route` production cho đúng
  kết quả của D trên cả 380 câu.
- Chương 5: số recall@5 0,870 là chất lượng của nhánh RAG; chất lượng đầu-cuối khi bật router phải kèm tỉ lệ câu
  tới được RAG (60/100 trên tenant demo với D).
- Mở lại khi: router được huấn luyện lại với dữ liệu nhiều lĩnh vực, hoặc tầng luật được sửa. Khi đó đo lại; F\*
  và E là hai ứng viên đã có số.
