# ADR-0017 — Chốt bốn mâu thuẫn hợp đồng và siết cổng CI dung lượng image

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-09-21
- **Làn sở hữu:** Cả hai (Track A & Track B)
- **Quan hệ:** Tiếp nối [ADR-0014](0014-java-core-lam-mat-tien-duy-nhat-cua-dashboard.md), [ADR-0015](0015-cau-truc-src-hai-tang-theo-master-plan-v8.md) và [ADR-0016](0016-ten-role-runtime-va-cho-dat-nhan-ket-qua-lead.md)

---

## Bối cảnh tổng thể

Khi bước vào Tuần 1 (Giai đoạn hiện thực hoá 17 use case trong 21 ngày của Module AI), quá trình đối chiếu giữa tài liệu đặc tả (`docs/MASTER_PLAN_AI_CRM_v8.md.docx`, `docs/Ke-hoach-21-ngay-Module-AI-CRM.xlsx`), các file giao ước (`docs/openapi/`, `docs/events/`) và mã nguồn khởi tạo (`ai-service/src/`, `scripts/`) phát hiện bốn mâu thuẫn hợp đồng còn treo và một lỗ hổng trong cổng kiểm soát CI.

Nếu không đóng dứt điểm các điểm vênh này ở Ngày 1:
1. Hai làn lập trình (Track A - Java Core và Track B - AI Service) sẽ triển khai lệch tên endpoint và cấu trúc bản tin Kafka, dẫn tới gãy tích hợp ở Ngày 5 khi consumer đầu tiên chạy.
2. Bộ dữ liệu đánh giá và kiểm thử bị phân tán, mất tính tái lập.
3. Kích thước Docker image của `ai-service` có thể âm thầm vượt ngưỡng mà không chặn được build.

ADR này là quyết định gộp chính thức hóa 4 mâu thuẫn và siết chặt cổng kiểm soát dung lượng image.

---

## Quyết định 1 — Thống nhất tiền tố và tên endpoint AI theo họ `/v1/ai/**`

### Bối cảnh và điểm lệch
- Trong `ai-service/src/ai/service.py` (dòng 31–41) định danh các phương thức facade theo URI: `/v1/ai/chat`, `/v1/ai/kb/documents`, `/v1/ai/extract`, `/v1/ai/lead-score`, `/v1/ai/feedback`.
- Trong `docs/openapi/ai-service-to-java-core.yaml` (dòng 32–56) lại định nghĩa: `/v1/answer`, `/v1/summarize`, `/v1/leads/score`, `/v1/documents/ingest`.
- Master Plan §2.5 và quy ước trong `.claude/rules/ai-service.md` quy định: mọi endpoint nghiệp vụ do AI phục vụ phải có phiên bản và tiền tố `/v1/ai/**`; các endpoint kiểm tra trạng thái hạ tầng (`/health`, `/ready`, `/metrics`) nằm ở root và không mang tiền tố phiên bản.

### Quyết định
**Thống nhất sử dụng họ đường dẫn `/v1/ai/**` cho toàn bộ endpoint nghiệp vụ của AI Service.**
Cụ thể, sửa `docs/openapi/ai-service-to-java-core.yaml` cho khớp với `service.py`:
- `/v1/answer` $\rightarrow$ `/v1/ai/chat` (UC022, UC023, UC025)
- `/v1/summarize` $\rightarrow$ `/v1/ai/summarize` (UC026)
- `/v1/leads/score` $\rightarrow$ `/v1/ai/lead-score` (UC030)
- `/v1/documents/ingest` $\rightarrow$ `/v1/ai/kb/documents` (UC018, UC019)
- Bổ sung định nghĩa OpenAPI chuẩn hóa cho `/v1/ai/extract`, `/v1/ai/feedback`, `/v1/ai/kb/documents/{id}`, `/v1/ai/kb/reindex`.
- Các probe hạ tầng giữ nguyên: `/health`, `/metrics`, `/ready`.

### Lập luận & Đánh đổi
- **Ưu điểm:** Nhất quán với cấu hình định tuyến của Spring Cloud Gateway (`/v1/ai/**` được route trực tiếp về `ai-service`), tránh va chạm namespace với các API nghiệp vụ khác của `java-core`.
- **Đánh đổi:** Cần cập nhật lại các lời gọi FeignClient / WebClient ở `java-core` để trỏ vào đúng `/v1/ai/**`.

---

## Quyết định 2 — Chốt bộ 9 topic Kafka chính thức (8 topic Master Plan + `crm.deal.closed`)

### Bối cảnh và điểm lệch
- Trong `scripts/create-topics.sh` (dòng 15–21) và thư mục `docs/events/` chỉ khai báo 5 topic cũ dạng `crm.*.v1` (`crm.conversation.v1`, `crm.lead.v1`, `crm.ai-interaction.v1`, `crm.usage.v1`, `crm.document.v1`).
- Trong Master Plan §2.6 và `ai-service/src/worker/main.py` (dòng 3–7, 25–27) khai báo 8 topic sự kiện chi tiết: 2 topic đầu vào (`crm.kb.document.uploaded`, `crm.conversation.closed`) và 6 topic đầu ra của AI (`ai.kb.document.indexed`, `ai.lead.signal.detected`, `ai.handoff.requested`, `ai.tool_call.audited`, `ai.turn.completed`, `ai.dlq`).
- Tuy nhiên, cả hai bộ đều đang thiếu topic `crm.deal.closed` — sự kiện bắt buộc để cung cấp ground-truth nhãn outcome (Won/Lost) phục vụ vòng lặp huấn luyện lại Lead Scoring của UC030 ở Ngày 18.

### Quyết định
**Chốt danh sách 9 topic chính thức phục vụ kiến trúc hướng sự kiện của Module AI:**
1. `crm.kb.document.uploaded`: Kích hoạt pipeline nạp tài liệu tri thức (UC018/019).
2. `crm.conversation.closed`: Kích hoạt worker tóm tắt hội thoại tự động (UC026).
3. `crm.deal.closed`: Vòng phản hồi kết quả chốt deal để đánh giá lại điểm số lead (UC030).
4. `ai.kb.document.indexed`: Báo cáo trạng thái hoàn tất lập chỉ mục vector (UC019).
5. `ai.lead.signal.detected`: Bắn tín hiệu phát hiện ý định mua hàng / khách tiềm năng (UC029).
6. `ai.handoff.requested`: Yêu cầu chuyển giao phiên chat cho nhân viên hỗ trợ (UC022).
7. `ai.tool_call.audited`: Nhật ký kiểm toán các lượt gọi công cụ MCP (UC024/028).
8. `ai.turn.completed`: Báo cáo kết thúc lượt hội thoại phục vụ tính toán hạn mức / usage (UC006/039).
9. `ai.dlq`: Dead-letter queue chứa các thông điệp lỗi vĩnh viễn không thể retry.

Cập nhật `scripts/create-topics.sh` để khởi tạo đủ 9 topic này (đồng thời duy trì tương thích các topic legacy nếu cần), và bổ sung JSON schema vào `docs/events/`.

---

## Quyết định 3 — Thống nhất vị trí bộ dữ liệu vàng (Golden Set) tại `ai-service/tests/eval/`

### Bối cảnh và điểm lệch
- Trong `CLAUDE.md` (dòng 87, 176) nhắc tới `data/golden_qa.jsonl`.
- Trong rule `.claude/rules/rag-eval.md` và cấu trúc dự án thực tế lại sử dụng `ai-service/tests/eval/golden_set.jsonl`.
- Tồn tại hai đường dẫn song song gây nhầm lẫn: một file rỗng và một file không tồn tại.

### Quyết định
**Chốt vị trí duy nhất: `ai-service/tests/eval/golden_set.jsonl`.**
- Golden Set bản chất là tập dữ liệu test hồi quy (regression test fixture) được nạp trực tiếp bởi bộ chạy kiểm thử `pytest tests/eval/` để tính toán `recall@5` và `faithfulness`. Do đó, đặt trong `tests/eval/` là chuẩn mực module hóa.
- Xóa bỏ mọi tham chiếu tới `data/golden_qa.jsonl` trong `CLAUDE.md` và tài liệu hướng dẫn.

---

## Quyết định 4 — Điều chỉnh kích thước tập test người thật xuống 200 câu cho nhóm 2 người

### Bối cảnh và điểm lệch
- [ADR-0016](0016-ten-role-runtime-va-cho-dat-nhan-ket-qua-lead.md) ghi: kích thước tập test người thật không dưới 250 mẫu.
- Quy mô nhân sự ban đầu trong Master Plan là 3 người / 7 tuần. Thực tế đồ án được tinh giản triển khai bởi **2 người / 21 ngày**.
- Trong buổi làm việc chung ở Ngày 2 (thời lượng ~3 giờ), năng suất gán nhãn thủ công cẩn trọng (bao gồm sinh các biến thể sai chính tả, viết tắt, không dấu cho 7 nhánh ý định) đạt chất lượng cao nhất ở ngưỡng **200 câu**.

### Quyết định
**Chốt kích thước tập test người thật `data/intent_test_human.jsonl` là đúng 200 câu.**
- Minh bạch hóa quyết định này trong ADR và báo cáo đồ án (Chương 5): 200 mẫu chất lượng cao, phản ánh chân thực ngôn ngữ người dùng tự nhiên, tốt hơn 250 mẫu tạo vội hoặc có can thiệp của LLM.
- Sau buổi gõ ở Ngày 2, file `data/intent_test_human.jsonl` sẽ được đóng băng lập tức bằng mã băm SHA-256 lưu tại `artifacts/DATA_HASHES.txt`.

---

## Quyết định 5 — Siết cứng cổng CI dung lượng image `ai-service` (Exit 1 khi $\ge 400$ MB)

### Bối cảnh
- Trong `.github/workflows/ci.yml` (dòng 93–100), kiểm tra kích thước image chỉ mới dừng ở mức cảnh báo:
  `[ "$MB" -lt 400 ] || echo "::warning::vượt ngưỡng 400 MB — xem ADR-0015"`
- Việc này tạo kẽ hở cho các thư viện cồng kềnh hoặc dependency rác chui vào image mà build vẫn xanh.

### Quyết định
**Bật `exit 1` khi kích thước image `ai-service:ci` vượt quá hoặc bằng 400 MB.**
Cổng CI trở thành rào chắn bắt buộc (hard gate) để bảo đảm triết lý tách biệt tầng suy luận của Master Plan §3.2.3.

---

## Hệ quả & Kế hoạch hành động

1. **Tài liệu:**
   - Cập nhật [docs/adr/README.md](README.md) bổ sung ADR-0017.
   - Cập nhật [CLAUDE.md](../../CLAUDE.md) và [docs/contracts/README.md](../contracts/README.md) chuyển các mục "Còn treo" sang "Đã chốt ở ADR-0017".
2. **OpenAPI:**
   - Hoàn thiện `docs/openapi/ai-service-to-java-core.yaml` với tên endpoint `/v1/ai/**` và đầy đủ request/response schema cho 8 path trọng tâm; kiểm tra đạt chuẩn với Redocly.
3. **Kafka:**
   - Cập nhật `scripts/create-topics.sh` tạo 9 topic.
   - Thêm JSON schema `crm.deal.closed.v1.json` và các sự kiện mới vào `docs/events/`.
4. **CI/CD:**
   - Sửa `.github/workflows/ci.yml` để fail build khi image size $\ge 400$ MB.
