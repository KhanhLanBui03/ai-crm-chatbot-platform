# ADR-0014 — java-core là mặt tiền duy nhất của dashboard, kể cả với dữ liệu của Track B

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-08-25
- **Làn sở hữu:** Cả hai

## Bối cảnh

`docs/openapi/dashboard-api.yaml` khai 78 đường dẫn, tất cả tiền tố `/api/v1`, và tự mô tả là
"giao ước: web-dashboard **gọi java-core** qua gateway". Gateway hiện thực đúng như vậy:
`/api/v1/**` → `lb://java-core`, chỉ `/ai/v1/**` → `lb://ai-service`.

Nhưng **17 trong 78 đường dẫn đó đọc dữ liệu nằm ở schema của Track B** — `knowledge`, `ai`,
`integration`:

| Nhóm | Đường dẫn | Màn |
|---|---|---|
| Kho tri thức | `/documents` ×4 · `/knowledge/search` · `/ingestion-jobs` · `/knowledge-gaps` | SCR029–034 |
| MCP và công cụ | `/mcp-servers` ×3 · `/tools` ×2 | SCR037–039 |
| Nhật ký tác tử | `/tool-calls` ×2 · `/ai-interactions` ×2 · `/safety-events` | SCR035, 036, 040, 051, 054 |

Và `V111` cấp cho `crm_app` quyền trên đúng bốn schema: `platform`, `engagement`, `sales`,
`analytics`. **Không** có `knowledge`, `ai`, `integration` — cố ý, đúng ADR-0002.

Nên java-core được giao phục vụ 17 đường dẫn mà nó không có quyền đọc dữ liệu, và
`ai-service-to-java-core.yaml` lúc đó chỉ có bốn endpoint **ghi/xử lý**, không endpoint đọc nào.
Hệ quả: **13 màn chỉ chạy được trên tầng mock**, và không lượng SQL nào sửa được — lược đồ đúng và
đủ, thứ thiếu là đường đi.

Ràng buộc kèm theo, và là ràng buộc quyết định: ba trường `uploadedByName`, `approvedByName`,
`contactName` trong hợp đồng dashboard **không bảng nào của Track B có**. Bảng Track B chỉ giữ
`uuid` trần (`uploaded_by`, `approved_by`) vì tham chiếu liên làn không có khoá ngoại, và `ai_app`
cũng không có `USAGE` trên `platform`/`engagement`. Không bên nào tự mình nối được hai đầu.

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| **A. Gateway định tuyến thẳng** — thêm predicate cho các tiền tố Track B → `lb://ai-service` | Rẻ nhất về mã: sửa một file cấu hình, không thêm chặng mạng | **Không giải được tên người** — ai-service vẫn phải gọi ngược java-core để đổi `uuid` → tên, thành phụ thuộc hai chiều. **Không giải được `/safety-events`**, vốn cần cả `audit_logs`. Và trái câu đã viết trong chính hợp đồng dashboard |
| **B. java-core proxy** — ai-service mở bề mặt đọc, java-core gọi xuống rồi làm giàu | Chiều phụ thuộc một hướng; tên người giải ngay tại chỗ; `/safety-events` trộn được ba nguồn; dashboard vẫn chỉ biết một địa chỉ | +1 chặng mạng mỗi request; ~20 endpoint nội bộ phải đặc tả |
| **C. Cấp cho `crm_app` quyền `SELECT` trên schema Track B** | Không thêm chặng mạng nào, không thêm endpoint nào | **Loại bỏ ngay.** Phá ADR-0002 ở đúng chỗ nó được dựng lên; biến ranh giới sở hữu thành quy ước lỏng; và mở lại đường mà `V206` cố tình đóng |
| **D. Nhân bản dữ liệu Track B sang schema Track A qua Kafka** | Đọc cực nhanh, không phụ thuộc lúc chạy | Nhân đôi nguồn sự thật cho dữ liệu người dùng đang sửa; phải xử lý lệch pha; và cần bảng mới — trái nguyên tắc không tăng số bảng |

## Quyết định

Chọn **B**: java-core là mặt tiền duy nhất của dashboard cho cả 78 đường dẫn; ai-service mở một
**bề mặt đọc nội bộ** (mục B của `docs/openapi/ai-service-to-java-core.yaml`) và luôn trả `uuid`
trần, còn java-core làm giàu thành tên người trước khi trả cho dashboard.

## Lập luận

Phương án A rẻ hơn đúng một lần — lúc viết cấu hình. Ngay sau đó nó đòi một đường gọi ngược từ
ai-service về java-core chỉ để tra tên người, tức vẫn phải đặc tả endpoint mới, nhưng lần này
chiều phụ thuộc thành hai hướng và ADR-0002 mất tính một chiều vốn là điểm mạnh của nó.

`/safety-events` là phép thử dứt điểm. UC040 bước 8 đòi xem ba loại sự cố cùng một chỗ, mà ba loại
đó có ba chủ sở hữu: `ai_tool_calls.decision = 'BLOCKED'` và `ai_interactions.safety_flag` thuộc
Track B, `audit_logs.severity = 'CRITICAL'` thuộc Track A. Chỉ java-core đọc được nguồn thứ ba.
Với phương án A, gateway phải trỏ `/safety-events` về java-core trong khi trỏ mọi đường Track B
khác về ai-service — một bảng định tuyến có ngoại lệ mà không ai nhớ nổi lý do sau ba tháng.

Còn lý do không dựng bảng `ai.safety_events` chung để né toàn bộ chuyện này: bảng chung buộc
java-core ghi vào schema của Track B, tức mở đúng cái đường ADR-0002 đóng lại. Hợp nhất ở **tầng
đọc** rẻ hơn và không đụng ranh giới nào.

## Đánh đổi

**Chấp nhận thêm một chặng mạng** cho 17 đường dẫn. Với 13 màn quản trị, tần suất mở thấp và không
có đường nào nằm trên luồng trả lời khách hàng, nên độ trễ thêm không chạm vào chỉ tiêu nào của
chương thực nghiệm. Nếu về sau một màn nào đó thành điểm nóng, đặt cache Redis ở java-core rẻ hơn
đổi kiến trúc.

**Chấp nhận java-core trở thành điểm chết chung**: ai-service sập thì 13 màn quản trị mất dữ liệu,
nhưng hộp thư và CRM vẫn chạy. Đổi lại, trước đây chúng *luôn* không có dữ liệu.

**Chấp nhận ~20 endpoint nội bộ phải đặc tả và giữ đồng bộ** với `dashboard-api.yaml`. Đây là chi
phí thật và định kỳ: đổi một trường ở bề mặt dashboard thì phải sửa hai chỗ. Giảm bớt bằng cách
giữ ánh xạ 1–1 về tên đường dẫn, để chỗ cần sửa luôn đoán được.

**Chấp nhận java-core đọc ghép hai nguồn cho một phản hồi** (dữ liệu Track B + tên người của Track
A), nên một lời gọi hỏng ở giữa cho ra phản hồi thiếu tên chứ không phải lỗi. Quy ước: thiếu tên
thì trả `null`, giao diện hiển thị `uuid` rút gọn — không chặn cả màn vì một cái tên.

## Hệ quả

- **Giao ước:** `docs/openapi/ai-service-to-java-core.yaml` thêm mục B — 20 đường dẫn đọc, ánh xạ
  1–1 với `/api/v1/*`. Đây là **sửa hợp đồng liên làn**, phải được Track B rà soát trước 07/09.
- **Lược đồ:** không đổi gì. Không bảng mới, không cột mới. Đây là lý do ADR này tồn tại: vấn đề
  trông như thiếu bảng nhưng không phải.
- **Gateway:** giữ nguyên hai route. Không thêm ngoại lệ nào vào bảng định tuyến.
- **Vận hành:** java-core cần client HTTP tới `lb://ai-service` (Eureka phân giải), timeout và
  circuit breaker riêng cho nhánh này — nhánh quản trị hỏng không được kéo theo hộp thư.
- **Cùng lúc đó, gỡ `POST /internal/ai-interactions`** khỏi `java-core-to-ai-service.yaml`: nó là
  cùng một loại nhầm lẫn ở chiều ngược lại, giao cho java-core ghi vào `ai.ai_interactions` — bảng
  của Track B mà `crm_app` không có quyền. Số liệu đã đi sang Track A bằng đường khác:
  `crm.ai-interaction.v1` → consumer `analytics-cg` → `analytics.metrics_daily` (V113).
- **Báo cáo:** chương 3, ngay sau ADR-0002 — đây là chỗ nguyên tắc "không nối thẳng CSDL" gặp bề
  mặt đọc của giao diện quản trị, và là câu trả lời cho *"vì sao không cho java-core đọc luôn cho
  nhanh?"*.
