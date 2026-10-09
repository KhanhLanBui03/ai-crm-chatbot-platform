# docs/contracts/ — bản nháp hợp đồng phía module AI

⚠️ **Đây KHÔNG phải nguồn sự thật của hợp đồng liên làn.**

| Nơi | Vai trò | Ai được sửa |
|---|---|---|
| `docs/openapi/*.yaml` | **Nguồn sự thật** — hợp đồng REST giữa hai làn | Sửa là **đơn phương đổi hợp đồng** — phải báo Track A trước |
| `docs/events/*.json` | **Nguồn sự thật** — lược đồ sự kiện Kafka | Như trên |
| `docs/contracts/` (thư mục này) | Bản nháp, ghi chú, đề xuất thay đổi **chưa chốt** | `integration-engineer` ghi tự do |

Quy trình: soạn đề xuất ở đây → báo Track A → thống nhất → **rồi mới** sửa `docs/openapi/`
hoặc `docs/events/`. Không đi tắt.

`.claude/rules/docs-adr.md`: *"Sửa một file ở đây là đơn phương đổi hợp đồng — phải báo làn
kia trước, không tự sửa cho khớp code của mình."*

## Đề xuất đang mở — chờ Track A

| Đề xuất | Trạng thái |
|---|---|
| [Thêm 3 cột `rule_score` · `outcome` · `outcome_at` vào `sales.lead_scores`](de-xuat-track-a-lead-scores-outcome.md) | Đã soạn **19/09/2026**, ⏳ **chưa gửi Track A**. Căn cứ ADR-0016. Ước lượng 2 giờ |
| [Hợp đồng UC018 — tải lên tài liệu tri thức](uc018-tai-tai-lieu.md) | Soạn **27/09/2026**, code hai phía đã chạy theo (25/25 tệp mẫu + ca 409 đầu-cuối). ⏳ Chờ xác nhận rồi vá `ai-service-to-java-core.yaml`, `dashboard-api.yaml`, `crm.document.v1.json` — danh sách ở mục 9 của file. Căn cứ ADR-0020, ADR-0022 |
| [Hợp đồng UC023 — `/v1/ai/chat` thêm `degraded` + `latency_breakdown`](uc023-chat-tra-loi.md) | Soạn **08/10/2026**, code đã chạy theo; trường thêm vào, `AiChatClient` không vỡ. ⏳ Chờ Dev B xác nhận rồi vá `ai-service-to-java-core.yaml`. Căn cứ ADR-0027, ADR-0028 |
| [Hợp đồng UC025 + UC027 — từ chối có lý do, đánh giá, khoảng trống tri thức](uc025-uc027-tu-choi-danh-gia.md) | Soạn **08/10/2026**, code ai-service đã chạy theo: `ChatResponse` thêm `interaction_id` + `refusal_reason`; `FeedbackRequest` thêm 3 trường; `GET /v1/knowledge-gaps` trả trang; `GET /v1/ai/quality` mới. ⏳ Chờ Dev B trả lời 4 câu ở mục 6 (quan trọng nhất: `AiChatClient` lưu `interaction_id`). Căn cứ ADR-0029, ADR-0030 |
| [Hợp đồng UC020 — quản lý kho tri thức](uc020-quan-ly-kho.md) | Soạn **09/10/2026**, code ai-service đã chạy theo: đường dẫn có sẵn trong hợp đồng + thêm `PATCH /v1/documents/{id}` và các trường giao diện cần. ⏳ Chờ Dev B: vá hợp đồng, proxy java-core SCR030–SCR032 + `audit_logs`. Căn cứ ADR-0031 |

## Đã chốt phía Track B

| Vấn đề | Chốt | ADR |
|---|---|---|
| Tên role runtime | **`ai_app`** — Master Plan §4.2 ghi `ai_service`, tên đó sai | 0016 |
| Nhãn huấn luyện UC030 | **`sales.lead_scores` + 3 cột**, KHÔNG tạo `ai.lead_features` | 0016 |
| Số chiều vector · schema kho tri thức | **1024** · **`knowledge.knowledge_*`** | 0015 |
| Cổng chặn CI | **3 gói** `onnxruntime\|torch\|xgboost` + **exit 1 khi $\ge 400$ MB** | 0015, 0017 |
| Bộ tên endpoint AI | **`/v1/ai/**`** theo Master Plan §2.5 | 0017 |
| Bộ tên topic Kafka | **9 topic** (8 topic Master Plan §2.6 + `crm.deal.closed`) | 0017 |
| Chỗ đặt bộ vàng | **`ai-service/tests/eval/golden_set.jsonl`** | 0017 |
| Cỡ tập test người thật | **200 câu** cho nhóm 2 người trong 21 ngày | 0017 |

## Còn treo

| # | Vấn đề | Hai nguồn |
|---|---|---|
| 1 | ~~**Mã lỗi hạn mức UC018**~~ — **đã tách** trong [hợp đồng UC018](uc018-tai-tai-lieu.md) mục 1.3 (413 dung lượng, 409 hạn mức); còn chờ vá `dashboard-api.yaml` | `dashboard-api.yaml` gộp "vượt hạn mức" và "vượt dung lượng" vào 409; đặc tả UC đề xuất tách 409 / 413 / 415 |
| 2 | **Enum vận chuyển và xác thực MCP** | Hợp đồng khai `HTTP_SSE`/`STREAMABLE_HTTP` + `BEARER`; `V205` khai `HTTP`/`SSE`/`STDIO`, không có `BEARER` |
