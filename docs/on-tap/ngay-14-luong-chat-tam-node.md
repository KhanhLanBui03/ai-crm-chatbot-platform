# Ôn tập Ngày 14 — Luồng chat chạy trọn, 8 node mỗi node một câu

> Viết 10/10/2026 (lịch gốc 04/10). Số liệu và log: [`docs/report/m2-ngay14-2026-10-10.md`](../report/m2-ngay14-2026-10-10.md).
> Kiến trúc: [ADR-0027](../adr/0027-luot-chat-pipeline-tuan-tu-khong-langgraph.md). Mã:
> `src/api/v1/endpoints/chat.py` → `src/ai/service.py::answer_turn` → `src/ai/orchestrator/turn.py::run_turn`.
>
> **Trạng thái M2: ĐÃ ĐÓNG, 3/3 ngả** (cập nhật 15/10/2026). Ngả trả lời có trích dẫn và ngả từ chối đạt
> 10/10; ngả chuyển giao đạt 15/10 sau khi có `router_model.onnx` của Dev B. Đọc §6: bật router thật thì
> 81% câu bộ vàng vào nhánh hỏi lại.

## 1. Câu mở đầu của buổi bảo vệ — 8 node, mỗi node một câu

| # | Node | Một câu | Ở đâu trong code |
|---|---|---|---|
| 1 | `guard` | Chuẩn hoá tiếng Việt (teencode, dấu) và dò tiêm chỉ thị bằng luật thuần Python; dò thấy thì gắn cờ chứ **không dừng** luồng. | `turn.py` bước 3 · `guardrails/` |
| 2 | `route` | Gọi ai-classify (hạn 1 s, thử lại 1 lần) lấy ý định và độ tin cậy, rồi so hai ngưỡng (τ = 0,65 để hỏi lại, 0,85 để đi nhanh) mà chọn một trong 7 nhánh; phân loại hỏng thì đi RAG. | `orchestrator/router.py` |
| 3 | `fastpath` | Câu chào/cảm ơn/tạm biệt có độ tin cậy ≥ 0,85 được trả bằng mẫu câu soạn sẵn: 0 LLM, ~0 ms. | `orchestrator/templates.py` |
| 4 | `retrieve` | Nhúng câu hỏi bằng bge-m3, rồi truy hồi lai vector + từ khoá trong **một** câu SQL có lọc `tenant_id` và hợp nhất bằng RRF k = 60, xếp lại nếu mơ hồ, bỏ đoạn dưới sàn. | `rag/answerer.py` → `rag/retrieve/hybrid.py` |
| 5 | `generate` | Che PII của khách rồi gửi câu hỏi + 5 đoạn cho Gemini với lời nhắc bắt trích dẫn `[n]`; mô hình được phép trả mã "không đủ căn cứ", và LLM hỏng thì trả câu trích nguyên văn (suy giảm). | `rag/generate/loi_nhac.py` · `integrations/llm/` |
| 6 | `postguard` | Kiểm câu đã sinh: bỏ trích dẫn trỏ sai, đo độ bám nguồn, che PII lạ, nhận ra câu "chưa có thông tin" trá hình rồi đổi thành từ chối `NOT_COVERED`. | `rag/generate/hau_kiem.py` |
| 7 | `handoff` | Bật cờ chuyển nhân viên khi khách xin gặp người (`HANDOFF_HUMAN`), khi cần duyệt thao tác ghi (`BUYING_INTENT`), khi câu cần dữ liệu nghiệp vụ, hoặc khi bị từ chối 2 lần liền; việc phân công thật do java-core làm. | `templates.py` · `rag/tu_choi.py` |
| 8 | `telemetry` | Trong khối `finally`, luôn ghi đúng một dòng `ai.ai_interactions` dưới RLS, kể cả lượt lỗi; ghi hỏng thì chỉ log và đếm, không làm hỏng câu trả lời. | `orchestrator/ghi_luot.py` |

**Câu chốt:** tám node là **bước** trong một hàm tuần tự `run_turn`, không phải node trong graph
LangGraph. Luồng không có vòng lặp và chỉ rẽ nhánh ở đúng một chỗ, sau khi so ngưỡng (ADR-0027).

## 2. Hai lượt thật hôm nay đi qua node nào

| Node | (a) "mất hóa đơn rồi thì còn được bảo hành không" | (b) "có dịch vụ vệ sinh sofa và rèm cửa tại nhà không" |
|---|---|---|
| `guard` | 0 ms, không cờ | 0 ms, không cờ |
| `route` | 62 ms — `CLASSIFIER_UNAVAILABLE` ⇒ RAG | 17 ms — `CLASSIFIER_UNAVAILABLE` ⇒ RAG |
| `fastpath` | bỏ qua | bỏ qua |
| `retrieve` | embed **1145 ms** (nguội) + 169 ms; cosine max 0,693 | embed 192 ms + 22 ms; cosine max 0,508 |
| `generate` | 1527 ms, 1615 → 77 token | 1380 ms, 1498 → **8** token (mã `KHONG_DU_CAN_CU`) |
| `postguard` | 1 ms — giữ 1 trích dẫn, bám nguồn 1,000 | không chạy (mô hình đã tự từ chối) |
| `handoff` | không | không (lần từ chối đầu của hội thoại) |
| `telemetry` | 1 dòng, `is_answered = true` | 1 dòng, `NOT_COVERED` |
| **Tổng** | **2909 ms** | **1638 ms** |

Đọc bảng: thời gian của lượt chat gần như dồn hết vào **LLM** (~1,4–1,5 s) và **lần nhúng đầu tiên sau
khi nghỉ**. Phần Python thuần (guard, postguard) gần 0 ms.

## 3. Quyết định hôm nay và vì sao

1. **Gọi thẳng ai-service, không qua gateway + java-core** (người dùng chốt). Lý do: M2 là cổng của
   module AI; đi qua java-core sẽ vướng các phần Track A còn thiếu, nhưng không chứng minh thêm điều gì
   về luồng AI.
2. **Ngả chuyển giao chờ Dev B** (người dùng chốt), không tự export và không mượn chuyển giao sinh từ
   RAG. Lý do: chuyển giao do khách xin là đường `route → HANDOFF`. Mượn đường khác thì minh chứng không
   đúng với điều kiện thoát.
3. **Câu hỏi lấy từ những câu đã ổn định ở cả hai lượt đo Ngày 13** (G072, T002), không chọn câu mới.
   Lý do: lượt minh chứng là để chứng minh **đường ống**, không phải đo chất lượng. Chọn câu đã biết kết
   quả thì một lượt trượt chỉ có thể do đường ống hỏng.
4. **Mỗi lượt một `conversation_id` mới.** Nếu (b) chạy trong cùng hội thoại với một lần từ chối trước
   đó, nó sẽ thành lần từ chối thứ hai và tự bật chuyển giao, làm lẫn hai ngả.
5. **`LLM_MODE=remote` đặt bằng biến môi trường lúc khởi động**, không sửa `.env`, để harness và test
   vẫn mặc định mock.

## 4. Câu hội đồng dễ hỏi tiếp

**Phân loại hỏng sao lại đi RAG mà không từ chối?** Đi RAG là lựa chọn an toàn nhất: nhánh tri thức tự
có cơ chế từ chối khi thiếu căn cứ, nên câu không có trong kho vẫn bị từ chối (đúng như lượt b). Từ chối
ngay thì mất cả những câu hỏi tri thức hoàn toàn trả lời được, chỉ vì một service phụ chết.

**Vì sao ghi lượt trong `finally`?** Nếu chỉ ghi ở nhánh thành công, bảng UC039 sẽ thiếu đúng những lượt
đáng quan tâm nhất là lượt lỗi. Ngược lại, ghi hỏng thì nuốt lỗi: biến một câu trả lời đúng thành HTTP 500
chỉ vì telemetry hỏng là đổi sai chiều.

**`tenant_id` đi từ đâu tới dòng CSDL?** Header `X-Tenant-Id` do gateway gắn → `api/deps.py` (thiếu thì
lỗi ngay) → tham số `tenant_id` của `answer_turn` → `get_tenant_session` đặt `app.tenant_id` trong cùng
transaction → RLS. Hôm nay đọc lại dòng bằng role `ai_app`, `current_setting('app.tenant_id')` đúng
tenant kho đo.

## 5. Nợ phát hiện hôm nay (chi tiết ở báo cáo §6)

- `route_reason` không được lưu vào CSDL hay dòng log `ai_turn` ⇒ UC039 không đếm được lượt "phân loại
  hỏng".
- `ai.turn.completed` chưa phát; `/metrics` chưa mở ⇒ bộ đếm Prometheus không quan sát được.
- ai-embed nguội: lần nhúng đầu 1145 ms ⇒ đo ở Ngày 15.
- `cost_vnd = 0` do đơn giá mặc định 0 ⇒ đặt đơn giá khi bật thanh toán Ngày 18.
- Câu ngoài kho vẫn tốn một lượt LLM (sàn toàn tập 0) ⇒ số cho buổi đọc số Ngày 16.

## 6. Bổ sung 15/10 — ngả chuyển giao, và điều router thật làm với hai ngả kia

Số liệu và log: báo cáo M2 §8.

### 6.1. Lượt (c) đi qua node nào

| Node | (c) "cho em gặp nhân viên tư vấn với ạ" |
|---|---|
| `guard` | 0 ms, không cờ |
| `route` | 60 ms — `HANDOFF_HUMAN` 0,98, **tầng luật** quyết định (chưa cần ONNX) ⇒ `HANDOFF` |
| `fastpath` · `retrieve` · `generate` · `postguard` | bỏ qua: 0 lần nhúng, 0 LLM |
| `handoff` | bật cờ, trả `HANDOFF_REPLY` |
| `telemetry` | 1 dòng: `branch = HANDOFF`, `model_name = template`, `llm_called = false`, `is_handoff = true` |
| **Tổng** | **60 ms**, so với 1,6–2,9 s của hai lượt RAG ngày 10/10 |

Đọc bảng: chuyển giao do khách xin là ví dụ đúng nhất của triết lý *Rule → ML → LLM*. Một luật bắt được
câu, và lượt không tốn đồng nào.

### 6.2. Chạy lại (a), (b) với router thật: cả hai bị hỏi lại

| | (a) G072 | (b) T002 |
|---|---|---|
| Ý định · độ tin cậy | `COMPLAINT_SUPPORT` 0,554 | `KB_SEARCH` 0,393 |
| So với τ = 0,65 | dưới | dưới |
| Nhánh | `CLARIFY` ("Dạ em chưa hiểu rõ ý…") | `CLARIFY` |

Đo trên toàn bộ câu hỏi: **91/112 câu bộ vàng (81%)** và 28/30 câu ngoài kho vào `CLARIFY`. Bộ vàng gồm
100 câu có đáp án và 12 câu không; trong 100 câu có đáp án, chỉ **14** câu tới được RAG.

**Ba điều phải nói được khi hội đồng hỏi:**

1. **Recall@5 0,870 là chất lượng của nhánh RAG, chưa phải của cả hệ thống.** Harness N13/N15 gọi thẳng
   nhánh RAG, không qua `route`. Bật router thì 86/100 câu có đáp án không tới được nhánh đó.
2. **Thiết kế và code đang lệch ở vùng dưới τ.** ADR-0019 cho câu dưới τ sang *tầng 3 — LLM phân loại
   lại*. Code chọn *hỏi lại* theo luồng phụ 5.1 của UC022. Cả hai đều có căn cứ trong tài liệu. Cùng ngày
   đã chốt cách thứ ba: **cộng xác suất theo ô** (ADR-0035, xem §6.5).
3. **KPI "≥ 55% lượt không gọi LLM" có thể đạt vì lý do sai.** Hỏi lại thì không tốn LLM. Một chỉ số tốt lên
   nhờ khách không được trả lời là lý do không được nhìn KPI này một mình. Phải đọc nó cạnh tỉ lệ lượt vào
   `CLARIFY`.

### 6.3. Câu hội đồng dễ hỏi tiếp

**§4 nói "phân loại hỏng thì đi RAG là an toàn nhất". Vậy sao phân loại chạy được lại tệ hơn phân loại
hỏng?** Vì hai luồng phụ khác nhau. Phân loại hỏng thì hệ thống *không biết gì* và mặc định coi là câu hỏi
tri thức. Phân loại chạy nhưng *không chắc* thì code chọn hỏi lại. Với bộ câu toàn câu hỏi tri thức, mặc
định "coi là câu hỏi tri thức" tình cờ đúng hơn. Đây chính là dữ kiện cho quyết định ADR-0035.

**Vì sao router thiếu tự tin với câu hỏi tri thức?** *Giả thuyết, chưa kiểm:* câu hỏi tri thức cụ thể
("mất hóa đơn còn bảo hành không") nằm giữa `KB_SEARCH`, `PRICING_POLICY` và `COMPLAINT_SUPPORT`, nên xác
suất bị chia ra. Dữ kiện ủng hộ: trên bộ vàng, ý định gán ra trải khá đều (27 · 24 · 20 cho ba nhãn đó).
Coverage trên bộ vàng chỉ 0,19, thấp hơn 0,395 trên tập ý định người thật (ADR-0019 mục 0).

### 6.4. Bẫy môi trường gặp hôm nay — đã sửa

`INFERENCE_CLASSIFY_URL` và `INFERENCE_RERANK_URL` ghi trong `ai-service/.env` từng **không có tác dụng** khi
chạy trên máy chủ. Hai client đọc bằng `os.getenv`, còn pydantic-settings không đẩy `.env` vào `os.environ`.
Lượt đầu tiên hôm nay vì thế mất router lẫn rerank mà response vẫn 200.

**Đã sửa cùng ngày:** hai URL thành trường của `Settings` (`inference_rerank_url`,
`inference_classify_url`), client lấy qua `get_settings()`. Giờ chỉ cần `python -m src.entrypoint`, `.env` là
đủ. Biến môi trường của container vẫn thắng `.env`. Chi tiết và lượt kiểm: báo cáo M2 §8.5.

**Bài học nói được với hội đồng:** lỗi cấu hình kiểu này *không làm hỏng response*, mà chỉ làm hệ thống âm
thầm chạy kém đi. Luồng phụ chịu lỗi (phân loại hỏng → RAG, rerank hỏng → RRF) đã che nó rất kỹ. Đó là lý
do `config.py` bắt mọi biến đi qua một chỗ: đọc rải rác thì không biết ứng dụng thật sự đang dùng giá trị
nào.

### 6.5. Đo tiếp cùng ngày: so các luật định tuyến

Chi tiết ở [`docs/report/dinh-tuyen-duoi-nguong-2026-10-15.md`](../report/dinh-tuyen-duoi-nguong-2026-10-15.md).
Ba điều cần nhớ:

1. **Cách đo được chốt trước khi chạy** (báo cáo §1). Một phương án (F\*) nghĩ ra sau khi thấy số thì đánh dấu
   sao và gọi số của nó là "lạc quan". Hội đồng hỏi "sao biết không tự chọn số đẹp" thì chỉ vào §1.
2. **Hai tập dữ liệu cân nhau:** bộ vàng toàn câu hỏi tri thức, nên "mọi câu đi RAG" chắc chắn đạt 100%. Tập
   200 câu người thật có đủ câu xin người, câu muốn mua, nên mới phạt được phương án đẩy nhầm những câu đó vào RAG.
3. **Router học trên câu phần mềm, tenant demo là cửa hàng điện máy** (0% từ điện máy trong 1.941 câu huấn
   luyện, 45% trong bộ vàng). Không luật ngưỡng nào sửa hết được chuyện lệch lĩnh vực; luật tốt là luật *chịu
   được* nó, bằng cách dựa vào RAG + lối từ chối khi không chắc.

**Quyết định (người dùng chốt 15/10): D — cộng xác suất theo ô**, ghi ở ADR-0035. Câu hội đồng dễ hỏi:

- *"Sao không chọn F\*, số đẹp hơn?"* — Vì luật của F\* nghĩ ra sau khi đã nhìn đúng những câu dùng để chấm; số
  của nó là số lạc quan. D đã chốt từ trước khi đo, và là phương án ít để bot bỏ qua khách xin người hay khách
  muốn mua nhất trong các phương án có cải thiện.
- *"D có làm hỏng quyết định nào luật cũ đang đúng không?"* — Không: với τ > 0,5, câu nào ý định đứng đầu đã ≥ τ
  thì ô của nó cũng ≥ τ. Script kiểm trên 380 câu: D đổi **0** quyết định luật cũ đã đưa ra; chỉ cứu câu luật cũ hỏi lại.
- *"Cái giá là gì?"* — Tenant demo vẫn bị hỏi lại 32/100 câu có đáp án, vì router lệch lĩnh vực. Ước tính lượt
  không gọi LLM giảm từ 72% xuống 48%, nhưng 72% kia có được nhờ hỏi lại khách.
