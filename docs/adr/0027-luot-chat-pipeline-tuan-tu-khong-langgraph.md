# ADR-0027 — Lượt chat chạy bằng pipeline tuần tự `run_turn`, không dùng LangGraph 8 node

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-08
- **Làn sở hữu:** Track B (module AI) — chạm file chung của Dev A và Dev B
- **Quan hệ:** sửa kế hoạch Ngày 8 của `ai-service/planning.md` · Master Plan §3.9.2 (sơ đồ
  orchestrator) · liên quan [ADR-0006](0006-hybrid-search-rrf-rerank.md) (đường ống truy hồi) ·
  [ADR-0028](0028-llm-gemini-flash-lite-client-trung-lap.md) (LLM sinh câu trả lời)

## Bối cảnh

Kế hoạch Ngày 8 dựng một `StateGraph` LangGraph 8 node (`guard`, `route`, `fastpath`, `retrieve`,
`generate`, `postguard`, `handoff`, `telemetry`). Hai người phải ngồi chốt `AgentState` trước khi ai
viết node nào, và mỗi người chỉ đăng ký node của mình vào registry.

Khi tới Ngày 8 (thực tế 08/10, trễ ~10 ngày), code đã đi đường khác:
- Dev B viết luồng UC022 dạng **tuần tự** trong `src/ai/orchestrator/turn.py::run_turn`:
  guardrails → phân loại → so ngưỡng → mẫu câu | nhánh tri thức → ghi lượt. Có test (17 hàm, 26 ca
  trong `tests/unit/test_chat_routing.py`).
- Chỗ cắm nhánh tri thức là Protocol `KnowledgeAnswerer`. Dev A chỉ cần hiện thực nó (UC023).
- Gói `langgraph` có trong `requirements/base.txt` nhưng **không file nào import**.

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Dựng LangGraph 8 node như kế hoạch | Khớp Master Plan §3.9.2; có sơ đồ máy trạng thái sinh từ code | Viết lại luồng Dev B đã có test; phải chốt `AgentState` chung — điểm conflict lớn nhất của tuần; thêm một tầng trừu tượng cho một luồng hầu như thẳng |
| B. **Giữ `run_turn`, cắm `RagAnswerer` qua Protocol** | Không đụng luồng của Dev B; một chỗ nối duy nhất (`service.py`); test cũ giữ nguyên | Không có "graph" để trình bày; sơ đồ 8 bước phải vẽ tay |
| C. Bọc `run_turn` trong một LangGraph 1 node | Có chữ "LangGraph" | Hình thức thuần tuý, thêm phụ thuộc mà không thêm năng lực nào |

## Quyết định

Phương án B. Lượt chat là pipeline tuần tự `run_turn`; nhánh tri thức là `RagAnswerer`
(`src/ai/rag/answerer.py`) cắm qua Protocol `KnowledgeAnswerer`. Tám "node" của kế hoạch vẫn tồn tại,
nhưng là **bước** trong code chứ không phải node trong graph:

| Node kế hoạch | Ở đâu trong code |
|---|---|
| `guard` | `run_turn` bước 3 — `guardrails/` (Dev B) |
| `route` | `run_turn` bước 4–5 — `orchestrator/router.py` (Dev B) |
| `fastpath` · `handoff` | `run_turn` bước 6 — `orchestrator/templates.py` (Dev B) |
| `retrieve` | `RagAnswerer`: nhúng → `hybrid.tim_kiem_lai` → `rerank/quyet_dinh.py` → sàn liên quan |
| `generate` | `RagAnswerer`: `rag/generate/loi_nhac.py` + `integrations/llm/` |
| `postguard` | `rag/generate/hau_kiem.py` |
| `telemetry` | `run_turn` khối `finally` — `TurnRecorder` (Dev B) |

## Lập luận

- **Luồng không có vòng lặp và không có rẽ nhánh động.** Một đường chính, ba nhánh mẫu câu rẽ ra ở
  đúng một chỗ (sau so ngưỡng). Giá trị của LangGraph — trạng thái bền, vòng lặp tác tử, gọi công cụ
  nhiều bước, điểm dừng chờ người duyệt — đều thuộc nhóm MCP (UC021/024/028) đã hoãn sang sau đồ án.
- **Ưu tiên luồng chính chạy được trước** (người dùng chốt 06/10). Viết lại `run_turn` thành graph
  là làm lại việc đã xong và đã có test, đúng lúc lịch trễ 10 ngày.
- **Ranh giới sở hữu tự nhiên hơn.** Protocol `KnowledgeAnswerer` là hợp đồng hẹp giữa phần của Dev B
  (định tuyến) và phần của Dev A (tri thức). `AgentState` chung là hợp đồng rộng, đổi một trường là
  chạm cả hai người.

## Đánh đổi

- **Không có sơ đồ máy trạng thái sinh tự động** cho minh chứng Ngày 8. Báo cáo vẽ tay sơ đồ 8 bước
  theo bảng trên — phải giữ khớp với code bằng kỷ luật, không bằng công cụ.
- **Mở rộng sau đồ án tốn hơn.** Khi bật MCP (gọi công cụ nhiều bước, chờ duyệt thao tác ghi), luồng
  sẽ cần vòng lặp và trạng thái bền — lúc đó mới đáng dựng graph, và phải chuyển `run_turn` sang. Ghi
  vào *Hướng phát triển*.
- **Lệch Master Plan §3.9.2** — phải giải thích khi bảo vệ (chính ADR này).
- `langgraph` vẫn nằm trong `requirements/base.txt` mà không dùng. Gỡ nó là việc của đợt giảm dung
  lượng image (Ngày 16), không gỡ ở đây để khỏi đụng file của làn hạ tầng.

## Hệ quả

- `src/ai/service.py::answer_turn` mặc định dùng `RagAnswerer` thay `PendingKnowledgeAnswerer`; một
  `RagAnswerer` cho mỗi event loop, dựng trong lifespan (circuit breaker phải nhớ được các lượt trước).
- `KnowledgeAnswer`, `TurnRecord` (`turn.py`) và `ChatResponse` (`schemas.py`) được **thêm** trường,
  không đổi trường cũ — nháp hợp đồng ở `docs/contracts/uc023-chat-tra-loi.md`.
- `ai-service/planning.md` Ngày 8: các ô `StateGraph`, `AgentState`, registry ghi chú "thay bằng
  ADR-0027".
