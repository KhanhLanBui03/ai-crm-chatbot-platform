# ADR-0017 — Chốt hợp đồng liên làn đợt 1: tên endpoint `/v1/ai/**` và ranh giới UC018

- **Trạng thái:** Đề xuất — quyết định 1–3 đã có code và test chạy theo; quyết định 4 chốt một phần; 5–6 **chưa chốt**
- **Ngày:** 2026-09-27
- **Làn sở hữu:** Cả hai

## Bối cảnh

Kế hoạch 21 ngày, Ngày 1: *"4 quyết định ghi thành ADR-0017 (một ADR gộp, mục Bối cảnh trích
đúng file:dòng đang lệch)"*. Ngày 1 trôi qua mà chưa chốt. Ngày 3 (UC018) viết route đầu tiên của
cả dự án và phần java-core tương ứng, nên ba chỗ lệch dính tới UC018 buộc phải chốt ngay; ba chỗ
còn lại chưa có code nào phụ thuộc.

| # | Chỗ lệch | Bên này ghi | Bên kia ghi |
|---|---|---|---|
| 1 | Tên endpoint ai-service | `ai-service/src/ai/service.py:31-40` — `/v1/ai/chat`, `/v1/ai/kb/documents`, … | `docs/openapi/ai-service-to-java-core.yaml:6,32,51,74` — `/v1/answer`, `/v1/documents/ingest`, `/v1/documents` |
| 2 | Ai kiểm hạn mức, ai nhận tệp ở UC018 | Đặc tả UC018 "Ranh giới AI ↔ CRM": java-core kiểm hạn mức và lưu tệp, ai-service *"nhận URI tệp"* | `ai-service/planning.md:307` giao kiểm `max_documents` cho route ai-service; `ai-service-to-java-core.yaml:89` ghi *"multipart"* |
| 3 | Độ dài `title` | Đặc tả UC018 "Tham số và ngưỡng": *"Tiêu đề: 3–300 ký tự"*; `ai-service/planning.md:309`; `dashboard-api.yaml:1409` `maxLength: 300` | `ai-service/migration/V202__knowledge_tai_lieu.sql:11` — `title varchar(255)` |
| 4 | Bộ tên topic Kafka | `scripts/create-topics.sh` + `docs/events/` — 5 topic `crm.*.v1` | Master Plan §2.6 — 8 topic; đặc tả UC018 — `crm.kb.document.uploaded` |
| 5 | Chỗ đặt bộ vàng | `.claude/rules/rag-eval.md` — `tests/eval/golden_set.jsonl` | `CLAUDE.md` gốc — `data/golden_qa.jsonl` |
| 6 | Cỡ tập test người thật | ADR-0016 — không dưới 250 | Kế hoạch 21 ngày, 2 người — 200 |

Ràng buộc có sẵn quyết định phần lớn chỗ lệch 2: `ai_app` không có quyền đọc schema `platform`
(V111 chỉ cấp cho `crm_app`, đúng ADR-0002), nên ai-service **không thể** đọc
`subscription_plans.max_documents` hay `usage_records`; và `docs/events/README.md` ghi producer
của `crm.document.v1` là java-core.

## Các phương án đã cân nhắc

**Quyết định 1 — tên endpoint**

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Theo OpenAPI: `/v1/answer`, `/v1/documents`… | Không sửa hợp đồng | Không có tiền tố chung — rule `ai-service.md` và gateway không phân biệt được đường nghiệp vụ với `/health` `/ready` `/metrics`; `/v1/documents` trùng tên với `/api/v1/documents` của java-core, dễ gọi nhầm tầng |
| B. Theo Master Plan §2.5 và `service.py`: `/v1/ai/**` | Một tiền tố cho mọi đường nghiệp vụ; đường không phiên bản (`/health`…) tách hẳn; đã có trong `service.py` | Phải sửa 21 path trong `ai-service-to-java-core.yaml` |

**Quyết định 2 — ranh giới UC018**

| Phương án | Ưu | Nhược |
|---|---|---|
| A. ai-service nhận multipart, tự kiểm hạn mức (`planning.md:307`) | Một chặng HTTP | `ai_app` không đọc được hạn mức — phải mở quyền vào schema `platform` (ngược ADR-0002) hoặc thêm một lời gọi ngược java-core giữa lượt tải; ai-service phải ghi `usage_records` qua API |
| B. java-core nhận multipart, kiểm hạn mức, ghi tệp lên S3, gọi ai-service bằng URI (đặc tả) | Mỗi bên chỉ chạm dữ liệu của mình; khớp producer `crm.document.v1` đã khai; tệp không đi qua hai dịch vụ | Hai dịch vụ cùng tham gia một lượt mà không có giao dịch phân tán (mục Đánh đổi) |

**Quyết định 3 — độ dài `title`**

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Viết V210 nâng cột lên `varchar(300)` | Khớp đặc tả | Đổi migration đã chạy trên mọi máy; chỉ để phục vụ tiêu đề 256–300 ký tự — không tài liệu mẫu nào cần |
| B. Giữ `varchar(255)`, chặn ở DTO cả hai tầng | Không đụng lược đồ; tiêu đề dài ra 422 rõ ràng thay vì 500 ở CSDL | Lệch đặc tả — phải sửa đặc tả và hợp đồng dashboard |

## Quyết định

1. **Mọi đường nghiệp vụ của ai-service nằm dưới `/v1/ai/**`**; `/health`, `/ready`, `/metrics`
   không phiên bản. UC018 là `POST /v1/ai/kb/documents`.
2. **Ranh giới UC018 theo đặc tả, đặt ở URI tệp.** java-core nhận multipart, kiểm 413 / 422 / 415 /
   409, ghi tệp lên kho S3 dưới key `{tenant_id}/{upload_id}/{tên}`, gọi ai-service bằng JSON có
   `file_uri`, rồi cộng `usage_records` và ghi outbox **cùng một transaction** khi nhận 202.
   ai-service nhận `X-Tenant-Id` + JSON, kiểm URI thuộc tenant, kiểm MIME thật, cấp `version`,
   ghi `PENDING`. java-core không đọc nội dung tệp; ai-service không ghi schema của Track A.
3. **`title` 3–255 code point, đếm SAU khi chuẩn hoá NFC và strip**, ở cả hai tầng; giữ
   `varchar(255)`, không viết V210.
4. **Bộ tên topic Kafka — chốt một phần (27/09/2026).** Sự kiện tải tài liệu đi trên
   **`crm.kb.document.uploaded`** — đúng tên trong đặc tả UC018 và Master Plan §2.6, và là tên
   `ai-service/src/worker/main.py` đã dự kiến tiêu thụ. Các topic còn lại (theo cả bộ §2.6 hay giữ
   `crm.*.v1`) **chưa chốt** — hạn: trước producer/consumer tiếp theo.
5. **Chỗ đặt bộ vàng — chưa chốt.** Hạn: trước Ngày 6.
6. **Cỡ tập test người thật — chưa chốt.** Chốt ở buổi gõ tay chung với Dev B; ghi lý do nếu là 200.

Hợp đồng chi tiết của UC018 (JSON, bảng mã lỗi, định dạng key, thứ tự bước):
[`docs/contracts/uc018-tai-tai-lieu.md`](../contracts/uc018-tai-tai-lieu.md).

## Lập luận

- **`/v1/ai/**`** thắng vì nó là quy ước duy nhất đã có code chạy theo (`service.py`, route
  UC018), và tiền tố chung là thứ cho phép gateway, rule và log phân biệt đường nghiệp vụ với
  đường vận hành mà không cần liệt kê từng path.
- **Ranh giới theo đặc tả** thắng vì phương án kia buộc phải phá ADR-0002 hoặc thêm một lời gọi
  ngược đồng bộ giữa lượt tải. Hạn mức, chu kỳ thuê bao, outbox đều ở schema `platform` — đặt
  việc kiểm ở java-core là đặt nó cạnh dữ liệu của nó. Cô lập tenant ở tầng kho có HAI chốt độc
  lập: java-core dựng key từ tenant trong JWT, ai-service từ chối mọi URI mà phân đoạn đầu không
  bằng đúng tenant trong header.
- **255** thắng vì chỗ lệch nằm ở tài liệu, không ở dữ liệu: đổi một dòng đặc tả rẻ hơn đổi một
  migration đã chạy. Đếm SAU NFC là điều kiện để hai tầng ra cùng một con số — tiếng Việt dạng NFD
  tách `ệ` thành 3 code point, một tiêu đề ~150 chữ nhìn thấy đã vượt 255. Test
  `tieuDeNfdDemSauKhiChuanHoaNfc` (java-core) khoá hành vi này.

## Đánh đổi

1. **Không có giao dịch phân tán.** ai-service commit `PENDING` trước, java-core commit hạn mức
   và outbox sau. Ba khe không nhất quán đã biết — ai-service nhận nhưng java-core commit hỏng,
   java-core hết thời gian chờ trong khi ai-service đã nhận, xoá object hỏng để lại object mồ côi
   — liệt kê ở hợp đồng UC018 mục 4. Chấp nhận thay vì dựng saga: tần suất thấp, hậu quả là một
   tài liệu `FAILED` hoặc một object thừa, không phải rò rỉ dữ liệu.
2. **Khoá dòng hạn mức giữ suốt lượt tải**, kể cả lúc ghi S3 và chờ ai-service (tối đa 30 s).
   Các lượt tải của **cùng một tenant** xếp hàng nối tiếp, mỗi lượt giữ một kết nối CSDL. Đổi
   lại, hạn mức không bao giờ bị vượt — đã đo: bỏ khoá thì 6 lượt đồng thời lúc 19/20 cho ra
   6 × 202 thay vì 1 × 202 + 5 × 409.
3. **Kiểm đuôi và dung lượng ở cả hai tầng.** Trùng lặp có chủ đích (java-core chặn sớm để khỏi
   ghi S3; ai-service là lớp phòng thủ thứ hai), nhưng hai danh sách đuôi —
   `KnowledgeDocumentServiceImpl.DUOI_NHAN` và `mime.py::DINH_DANG_THEO_DUOI` — phải sửa cùng nhau.
4. **Lệch đặc tả ở `title`:** tiêu đề 256–300 ký tự hợp lệ theo đặc tả bị từ chối.
5. **`/v1/ai/**` kéo theo một đường ngoài lặp chữ:** route gateway `/ai/v1/**` + `StripPrefix=1`
   cho ra `/v1/…`, nên đường công khai của chat sẽ là `/ai/v1/ai/chat`. Chưa đường nào đi qua
   gateway dùng tới (UC018 do java-core gọi thẳng) — sửa predicate gateway khi làm route chat.
6. **Ba quyết định còn treo** làm ADR này chưa thể chuyển `Chấp nhận`.

## Hệ quả

- **Hợp đồng — phải vá sau khi hai bên xác nhận** (danh sách file:dòng ở hợp đồng UC018 mục 9):
  `ai-service-to-java-core.yaml` đổi sang `/v1/ai/**` và JSON thay multipart; `dashboard-api.yaml`
  tách 413 khỏi 409, `title` 255, thêm `code` vào `ApiResponse` và `documentQuota` vào phản hồi
  202; `docs/events/` thêm `crm.kb.document.uploaded.json` với payload.
- **Lược đồ:** V116 (Track A) thêm `warned_at`, `blocked_at` vào `platform.usage_records` — đặc
  tả UC018 và UC006 đòi ghi thời điểm chạm 80% / 100%. Đề xuất 3 cột `sales.lead_scores` lùi sang
  V117.
- **Đặc tả:** `ai-service/planning.md:309` đã sửa thành 3–255. Dòng "Tiêu đề: 3–300 ký tự" của UC018
  trong `docs/Dac-ta-UseCase-Module-AI.docx` **chưa sửa** — sửa tay trong Word.
- **Mã lỗi:** thêm `SUBSCRIPTION_NOT_ACTIVE` (409), `AI_SERVICE_UNAVAILABLE` (503) phía java-core
  và ba mã phía ai-service (`FORBIDDEN_FILE_URI`, `FILE_NOT_FOUND`, `STORAGE_UNAVAILABLE`) — cả năm
  đánh dấu `[CẦN XÁC NHẬN]` ở hợp đồng UC018.
- **Báo cáo:** chương 3 (ranh giới hai làn đặt ở URI; hai chốt cô lập tenant ở tầng kho) và
  chương 4 (bảng 25/25 tệp mẫu qua java-core thật → ai-service thật; ca 409 và hai mốc 80% / 100%).
