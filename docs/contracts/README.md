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

## Đang chờ chốt

| # | Vấn đề | Hai nguồn |
|---|---|---|
| 1 | **Bộ tên topic Kafka** | §2.6 khai 8 topic (`crm.kb.document.uploaded`, `crm.conversation.closed`, `ai.kb.document.indexed`, `ai.lead.signal.detected`, `ai.handoff.requested`, `ai.tool_call.audited`, `ai.turn.completed`, `ai.dlq`); `scripts/create-topics.sh` + `docs/events/` vẫn ở 5 topic `crm.*.v1`. `Dac-ta-UseCase-Module-AI.docx` điểm #7 đề xuất theo bộ của kế hoạch |
| 2 | **Tên role runtime** | Master Plan §4.2/§4.3 ghi `ai_service`; `docker-compose.yml:239` + `.claude/CLAUDE.md` luật #5 ghi `ai_app` |
| 3 | **Bảng `ai.lead_features`** | Kế hoạch Ngày 3 + Ngày 29 đều cần; **không migration nào tạo** (đã kiểm V201–V209). UC030 chưa có chỗ ghi `outcome` |
| 4 | **Mã lỗi hạn mức UC018** | `dashboard-api.yaml` gộp "vượt hạn mức" và "vượt dung lượng" vào 409; đặc tả UC đề xuất tách 409 / 413 / 415 |
| 5 | **Enum vận chuyển và xác thực MCP** | Hợp đồng khai `HTTP_SSE`/`STREAMABLE_HTTP` + `BEARER`; `V205` khai `HTTP`/`SSE`/`STDIO`, không có `BEARER` |
