# ADR-0021 — Nạp tài liệu commit theo chặng, chống trùng sự kiện trong schema của Track B, bộ quét job kẹt

- **Trạng thái:** Đề xuất. Phương án 2 (commit sớm) do người dùng chốt ngày 27/09/2026. Chi tiết
  bộ quét (Quyết định 3–4) đã hiện thực và qua test, nhưng chờ người dùng xác nhận.
- **Ngày:** 2026-09-27
- **Làn sở hữu:** Track B

## Bối cảnh

UC019 nhận sự kiện `DocumentUploaded` từ java-core qua `crm.kb.document.uploaded` rồi nạp tài liệu
qua bốn chặng: phân tích tệp → chia đoạn → nhúng → lập chỉ mục. Ngày 4 dựng hai chặng đầu trong
**một** transaction (`service.phan_tich_tai_lieu`): nhận việc, phân tích, trả đoạn trong bộ nhớ. Ngày 5
phải nối thêm hai chặng sau, và bốn ràng buộc buộc phải ra quyết định:

1. **SCR033 hiển thị 6 bước** `QUEUED → EXTRACTING → CHUNKING → EMBEDDING → INDEXING → DONE` (enum
   `TrangThaiCongViecNap`, `docs/openapi/dashboard-api.yaml:3080`). Nếu cả lượt nạp nằm trong một
   transaction thì bên ngoài chỉ thấy `PENDING` rồi nhảy thẳng sang `READY`.
2. **Tài liệu dài chạy lâu.** 3.000 đoạn là ~94 lô 32 đoạn. Với ai-embed trên CPU, cỡ đó mất vài
   phút. Giữ một transaction mở chừng ấy là giữ khoá dòng, giữ một kết nối của pool, và chặn
   VACUUM trên bảng đoạn.
3. **Kafka giao ít nhất một lần.** Luật chung (`.claude/rules/kafka-events.md` mục 5) bắt chống trùng
   bằng `analytics.processed_events`. Nhưng bảng đó thuộc schema của Track A, và `ai_app` **không có
   USAGE** trên `analytics` — cố ý, đó là lớp chặn cuối của ADR-0002 (V206).
4. **Worker có thể chết giữa chừng:** OOM-kill, rolling deploy, node bị thu hồi. Khi đó tài liệu phải
   được nạp lại, không được nằm kẹt mãi.

## Các phương án đã cân nhắc

**Quyết định 1 — ranh giới transaction của một lượt nạp**

| Phương án | Ưu | Nhược |
|---|---|---|
| 1. Một transaction cho cả lượt | Nguyên tử: chết giữa chừng là rollback về `PENDING`, Kafka giao lại, không cần gì thêm | SCR033 không thấy tiến độ (ràng buộc 1); giữ transaction hàng phút (ràng buộc 2) |
| **2. Commit sớm, mỗi chặng một transaction** | Thấy được tiến độ từng chặng và từng lô; transaction ngắn | Chết giữa chừng để lại `PROCESSING` → cần bộ quét, thẻ sở hữu, và dọn đoạn dở |

**Quyết định 2 — chống trùng sự kiện**

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Dùng `analytics.processed_events` như luật ghi | Một bảng cho cả hệ thống | Phải cấp `ai_app` quyền vào schema `analytics` — mở lỗ ngay trên ranh giới ADR-0002 |
| B. Gọi API java-core để ghi nhận | Không đụng quyền CSDL | Không nằm cùng transaction với bước nhận việc — chết giữa hai bước là mất việc hoặc làm trùng |
| **C. Bảng riêng `ai.processed_events` (V211)** | Cùng transaction với bước nhận việc; không đụng Track A | Hai bảng cùng một vai trò ở hai schema |

**Quyết định 3 — bộ quét nhìn xuyên tenant**

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Role runtime có `BYPASSRLS` | Đơn giản | Mọi câu lệnh của `ai_app` đều vượt RLS — xoá bỏ ADR-0001 |
| B. Lặp qua danh sách tenant | Không lỗ nào | ai-service không biết danh sách tenant (`platform.tenants` là của Track A) |
| **C. Hàm `SECURITY DEFINER` chỉ trả định danh** | Lỗ hẹp nhất: 4 cột, không nội dung; mọi thao tác sau đó vẫn dưới RLS | Là một lỗ có chủ đích — phải soát và ghim `search_path` |

**Quyết định 3b — bộ quét làm gì với job kẹt** (đề xuất ban đầu bị sửa trước khi code)

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Chuyển thẳng `FAILED` | Không vòng lặp | Một lần rolling deploy làm hỏng mọi tài liệu tốt đang nạp dở |
| **B. Còn lượt thì về `PENDING` rồi nạp lại; hết 3 lượt thì `FAILED` `INGEST_STALLED`** | Tài liệu tốt sống sót khi worker chết; tệp làm worker chết cũng không kéo nó vào vòng lặp vô hạn | Cần đếm lượt bền vững (`attempt_count`) |

## Quyết định

1. **Mỗi chặng một transaction** (phương án 2). V211 thêm vào `knowledge_documents`:
   - `attempt_count`: số lần nhận xử lý, trần 3.
   - `ingest_step`: chặng đang chạy, hoặc chặng đã hỏng.
   - `ingest_started_at`: lúc lượt hiện tại bắt đầu.

   Mọi câu ghi sau bước nhận việc đều kèm điều kiện
   `status = 'PROCESSING' AND attempt_count = <lượt của mình>`. Đó là **thẻ sở hữu**: câu `UPDATE` nào
   cập nhật 0 dòng thì lượt đó đã mất quyền và phải dừng. Mỗi lô ghi đoạn đi cùng một lần làm mới
   thẻ; lần làm mới đó cũng chính là **nhịp tim** (`updated_at`, trigger của V207). Bước nhận việc
   xoá đoạn dở dang của lượt trước. Lượt nào kết thúc ở `FAILED` hay trả về hàng đợi cũng dọn đoạn
   của mình.
2. **`ai.processed_events (consumer_group, event_id)`** — cùng khoá với V110, nhưng có RLS. Dòng
   được ghi bằng `INSERT … ON CONFLICT DO NOTHING` trong **cùng transaction** với bước nhận việc; ghi
   được 0 dòng thì bỏ qua sự kiện. Từ lúc đó, việc hoàn tất tài liệu thuộc về máy trạng thái của nó
   (và bộ quét), không còn phụ thuộc offset Kafka.
3. **Bộ quét job kẹt** chạy trong worker, 60 s một lần. Nó gọi `knowledge.tim_job_ket(interval, int)`
   (`SECURITY DEFINER`, `search_path` ghim ở `pg_catalog, pg_temp`, chỉ `ai_app` được EXECUTE), rồi
   xử lý từng tài liệu trong phiên đã gắn đúng tenant:
   - `PROCESSING` không có nhịp tim quá 5 phút: nếu `attempt_count < 3` thì trả về `PENDING`, dọn
     đoạn, nạp lại ngay qua cùng semaphore; nếu đã đủ 3 thì chuyển `FAILED` `INGEST_STALLED`.
   - `PENDING` có `attempt_count > 0` quá 5 phút: nạp lại. Đây là tài liệu đã được trả về hàng đợi
     rồi worker chết trước khi kịp nhận lại.
   - `PENDING` có `attempt_count = 0`: **không đụng**. Đó là tài liệu chưa từng có sự kiện nào nhận.
4. **Lỗi tạm thời** (S3, ai-embed, CSDL) → tài liệu về `PENDING`, giữ nguyên `attempt_count`. Worker
   thử lại sau 5 s rồi 30 s. Lượt thứ 3 vẫn hỏng thì chuyển `FAILED`
   `INGEST_RETRY_EXHAUSTED: <mã lỗi tạm thời>`. **Lỗi vĩnh viễn** (`PARSE_*`, `FILE_NOT_FOUND`,
   `FORBIDDEN_FILE_URI`, `EMBEDDING_REJECTED`, `EMBEDDING_MODEL_MISMATCH`) → `FAILED` ngay, không thử
   lại.
5. **`ai.dlq`** (giữ 30 ngày) chỉ nhận sự kiện **không biến được thành trạng thái tài liệu**:
   - sai lược đồ, hoặc `event_type`/`event_version` chưa hỗ trợ — đẩy ngay;
   - ngoại lệ thoát khỏi facade 3 lần liền, thường vì CSDL chết.

   Giá trị và khoá giữ nguyên byte của bản tin gốc; lý do ghi ở header `dlq.*`. Tài liệu đã
   `FAILED` thì **không** vào DLQ.
6. **Đúng một job nạp mỗi tiến trình worker**: một semaphore dùng chung cho luồng Kafka, bộ quét, và
   UC020 sau này. Muốn nạp nhanh hơn thì tăng replica, không tăng số job.

## Lập luận

- **Commit sớm** thắng vì hai nhược điểm của phương án 1 đều không có cách vá, còn nhược điểm của
  phương án 2 thì vá được — ba cơ chế ở Quyết định 1 và 3 làm đúng việc đó. Mỗi cơ chế có test ép
  đúng ca của nó đỏ: bỏ `attempt_count` khỏi thẻ sở hữu, bỏ ghi nhận sự kiện, xác nhận offset
  trước khi xử lý, bỏ phát DLQ, quét cả `PENDING` lượt 0, biến lỗi tạm thời thành `FAILED` ngay,
  không dọn đoạn khi trả về hàng đợi. Cả 7 lần phá đều đỏ đúng test tương ứng.
- **Thẻ sở hữu phải có `attempt_count`**, không chỉ `status = 'PROCESSING'`. Ca khó nhất diễn ra
  theo thứ tự: bộ quét trả tài liệu về hàng đợi → lượt mới nhận lại (status lại là `PROCESSING`) →
  lượt cũ tỉnh dậy. Chỉ so trạng thái thì lượt cũ vẫn qua được và ghi chồng lên lượt mới
  (`test_luot_cu_tinh_lai_khong_ghi_de_luot_moi_da_nhan_lai`).
- **Ghi nhận sự kiện cùng transaction với bước nhận việc**, không sớm hơn và không muộn hơn:
  - Sớm hơn (commit riêng trước): worker chết giữa hai bước thì sự kiện đã "xong" mà tài liệu chưa
    ai nhận — mất việc.
  - Muộn hơn (lúc `READY`): lượt thử lại do lỗi tạm thời sẽ phải tự phân biệt với một bản tin trùng.

  Nhận việc và ghi nhận nằm cùng transaction thì hai câu hỏi "sự kiện đã xử lý chưa" và "tài liệu
  đã vào tay worker chưa" luôn có cùng câu trả lời.
- **Bộ quét không phát lại sự kiện Kafka**: sự kiện gốc đã được xác nhận offset, và
  `crm.kb.document.uploaded` là topic của java-core. Gọi thẳng `nap_tai_lieu` là đủ.
- **DLQ hẹp**: tài liệu `FAILED` đã hiện lý do trên SCR033 để người dùng tự sửa. Đẩy thêm vào DLQ là
  báo cùng một lỗi ở hai nơi, và phát lại từ DLQ cũng vô ích vì `ai.processed_events` sẽ chặn.

## Đánh đổi

1. **Đoạn dở dang nhìn thấy được trong lúc nạp.** Lô 1 đã nằm trong `knowledge_chunks` khi lô 2 còn
   đang nhúng. **Truy hồi ở Ngày 6 BẮT BUỘC chỉ lấy đoạn của tài liệu `READY`**. Quên điều kiện đó
   thì câu trả lời có thể trích dẫn nửa tài liệu đang nạp, hoặc nửa tài liệu của một lượt sắp hỏng.
   Test hiện chỉ khoá việc tài liệu `FAILED` không còn đoạn nào; chưa có gì khoá phía truy hồi.
2. **Một lỗ có chủ đích trong RLS.** `knowledge.tim_job_ket` nhìn xuyên tenant. Nó hẹp: chỉ trả 4
   cột định danh, không dùng SQL động, `search_path` đã ghim, chỉ `ai_app` gọi được — có test khoá cả
   bốn. Nhưng hàm chỉ vượt được RLS khi **chủ hàm** có `BYPASSRLS`. Trên dev và test thì `crm_owner`
   là superuser nên chạy được. Trên RDS, role chạy Flyway không phải superuser thật, nên hàm sẽ ném
   42501 — hỏng ồn ào, không im lặng. **[CẦN XÁC NHẬN]** cách cấp quyền trên RDS — xử lý ở Ngày 18.
3. **Tài liệu bị kẹt lâu nhất ~6 phút** (5 phút quá hạn + 1 chu kỳ quét) sau khi worker chết, rồi
   mới được nạp tiếp. Hạ ngưỡng quá hạn thì có nguy cơ tước quyền một lượt đang chạy thật: ngưỡng
   phải lớn hơn hẳn chặng dài nhất không có nhịp tim, tức trần phân tích 120 s.
4. **`ai.processed_events` lớn dần**, mỗi sự kiện một dòng, và chưa có job dọn. Dọn dòng cũ hơn thời
   gian giữ của Kafka (30 ngày) là an toàn, nhưng `ai_app` không có quyền `DELETE` — cần một role bảo
   trì.
5. **Hai bảng chống trùng ở hai schema.** Luật chung trỏ `analytics.processed_events`; Track B dùng
   `ai.processed_events`. Rule `kafka-events.md` đã sửa để ghi rõ ngoại lệ này.
6. **Trong lúc nạp, `chunk_count` là số đoạn DỰ KIẾN** (mẫu số của thanh tiến độ). Chỉ từ `READY`
   trở đi nó mới là số đoạn thật đã kiểm đếm. Nếu đọc `chunk_count` của tài liệu chưa `READY` như
   kích thước kho thì sẽ sai.
7. **Nạp lại do bộ quét không mang `X-Trace-Id` của lượt tải gốc** — log của lượt đó không nối được
   về request ban đầu. Trace đầy đủ để lại cho UC039.
8. **Chưa có ai-embed thật.** Worker đang chạy `AI_MODE=mock` (vector sinh bằng hash, seed cố định).
   Mọi đoạn nạp bằng mock mang `embedding_model = 'mock-hash-1024'`, nên đổi sang model thật thì biết
   chính xác dòng nào phải nhúng lại. Số đoạn/giây đo được vì thế **không gồm** thời gian nhúng thật.

## Hệ quả

- **Lược đồ:** V211 thêm 3 cột trên `knowledge_documents`, chỉ mục bộ phận `ix_doc_dang_nap`, bảng
  `ai.processed_events` (có RLS), và hàm `knowledge.tim_job_ket`. Đã cập nhật ERD và
  `ai-service/migration/README.md`.
- **Mã nguồn:**
  - `service.nap_tai_lieu` thay `phan_tich_tai_lieu`; thêm `service.quet_job_ket` và
    `service.tien_do_nap`.
  - Worker thật ở `src/worker/{main.py, consumers/tai_lieu.py}`.
  - Endpoint `GET /v1/ai/kb/ingestion-jobs/{job_id}`.
  - Client nhúng `mock`/`remote` ở `src/ai/inference/`.
- **Hợp đồng — chưa vá vào nguồn sự thật:**
  - `/v1/ingestion-jobs` trong `ai-service-to-java-core.yaml` vẫn là TODO. DTO ở
    `schemas.IngestionJobProgress` đã bám `CongViecNap`.
  - `POST /v1/embed/batch` với Dev B: hình dạng ghi ở `src/ai/inference/remote.py`, đánh dấu
    **[CẦN XÁC NHẬN]**.
  - Topic `ai.dlq` và header `dlq.*` chưa có trong `docs/events/`.
- **Vận hành:** `docker-compose.yml` có service `ai-worker` với `stop_grace_period: 60s`.
  `scripts/create-topics.sh` tạo thêm `ai.dlq`, giữ 30 ngày.
- **Báo cáo:**
  - Chương 3: bảng ba tầng thử lại (lượt nạp / bản tin / tiến trình); vì sao thẻ sở hữu cần
    `attempt_count`; lỗ `SECURITY DEFINER` và bốn chốt giữ cho nó hẹp.
  - Chương 4: thời gian nạp tài liệu 100 trang, số đoạn/giây, RSS khi nạp tài liệu 3.000 đoạn, bản
    tin trong DLQ, kịch bản khởi động lại worker (`docs/report/uc019-ngay5-2026-09-27.md`).
