# Ôn tập Ngày 14 — Luồng chat chạy trọn, 8 node mỗi node một câu

> Viết 10/10/2026 (lịch gốc 04/10). Số liệu và log: [`docs/report/m2-ngay14-2026-10-10.md`](../report/m2-ngay14-2026-10-10.md).
> Kiến trúc: [ADR-0027](../adr/0027-luot-chat-pipeline-tuan-tu-khong-langgraph.md). Mã:
> `src/api/v1/endpoints/chat.py` → `src/ai/service.py::answer_turn` → `src/ai/orchestrator/turn.py::run_turn`.
>
> **Trạng thái M2: 2/3 ngả đạt** (trả lời có trích dẫn, từ chối). Ngả chuyển giao chờ `router_model.onnx`
> của Dev B.

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
