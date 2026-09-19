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

## Đã chốt phía Track B

| Vấn đề | Chốt | ADR |
|---|---|---|
| Tên role runtime | **`ai_app`** — Master Plan §4.2 ghi `ai_service`, tên đó sai | 0016 |
| Nhãn huấn luyện UC030 | **`sales.lead_scores` + 3 cột**, KHÔNG tạo `ai.lead_features` | 0016 |
| Số chiều vector · schema kho tri thức | **1024** · **`knowledge.knowledge_*`** | 0015 |
| Cổng chặn CI | **3 gói** `onnxruntime\|torch\|xgboost` | 0015 |

## Còn treo

| # | Vấn đề | Hai nguồn |
|---|---|---|
| 1 | **Bộ tên topic Kafka** — *hoãn có chủ đích, chốt ở Ngày 12* | §2.6 khai 8 topic (`crm.kb.document.uploaded`, `crm.conversation.closed`, `ai.kb.document.indexed`, `ai.lead.signal.detected`, `ai.handoff.requested`, `ai.tool_call.audited`, `ai.turn.completed`, `ai.dlq`); `scripts/create-topics.sh` + `docs/events/` vẫn ở 5 topic `crm.*.v1`. `Dac-ta-UseCase-Module-AI.docx` điểm #7 đề xuất theo bộ của kế hoạch. **`crm.deal.closed` chưa có trong cả hai bộ** — cần cho vòng phản hồi UC030 |
| 2 | **Mã lỗi hạn mức UC018** | `dashboard-api.yaml` gộp "vượt hạn mức" và "vượt dung lượng" vào 409; đặc tả UC đề xuất tách 409 / 413 / 415 |
| 3 | **Enum vận chuyển và xác thực MCP** | Hợp đồng khai `HTTP_SSE`/`STREAMABLE_HTTP` + `BEARER`; `V205` khai `HTTP`/`SSE`/`STDIO`, không có `BEARER` |
