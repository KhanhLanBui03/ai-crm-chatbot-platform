# Ôn tập Ngày 5 — UC019 (2/2): nhúng theo lô, worker Kafka, DLQ

> Viết bù 06/10/2026. Code: `ai-service/src/worker/main.py`,
> `src/ai/db/repositories/processed_event_repository.py`, `scripts/create_hnsw_index.sql`.
> Quyết định: ADR-0024 (commit theo chặng, chống trùng, quét job kẹt). Minh chứng:
> `docs/report/uc019-ngay5-2026-09-27.md`.

## "Phải giải thích được"

**Vì sao `enable_auto_commit=False`? Kịch bản mất sự kiện nếu để `True`.**
- Tự động commit thì client xác nhận offset **theo nhịp thời gian** (5 giây một lần) cho mọi bản tin
  đã **đọc**, kể cả bản tin đang xử lý dở.
- Kịch bản mất bản tin:
  1. worker đọc sự kiện "tài liệu X vừa tải lên" và bắt đầu nạp;
  2. tới nhịp 5 giây, offset được xác nhận;
  3. pod chết giữa chừng.
- Kafka tin rằng X đã xong và không giao lại. Tài liệu X nằm `PENDING` mãi mãi, không log nào ghi.
- Tắt tự động và xác nhận **sau khi** xử lý xong thì đổi "mất bản tin" lấy "nhận trùng bản tin"
  (pod chết sau khi xử lý nhưng trước khi xác nhận). Nhận trùng thì xử lý được, xem câu sau.

**`processed_events` chống trùng bằng cách nào? Vì sao `ON CONFLICT DO NOTHING` chứ không SELECT rồi INSERT?**
- Khoá chính là `(consumer_group, event_id)`. Trước khi làm việc, worker chèn một dòng. Chèn được
  (1 dòng) thì làm; chèn không được (0 dòng) tức là đã làm rồi, bỏ qua.
- **SELECT rồi INSERT có cửa sổ tranh chấp:** hai bản sao của cùng sự kiện tới hai consumer cùng lúc,
  cả hai SELECT đều thấy "chưa có", và cả hai xử lý.
- **Một câu INSERT … ON CONFLICT** để khoá chính quyết định: đúng một bên chèn được, bên kia chờ bên
  này commit rồi nhận 0 dòng. Không cần khoá ở tầng ứng dụng.
- Phải chạy **cùng transaction** với việc sự kiện gây ra. Nếu commit riêng trước, pod chết giữa hai
  bước thì sự kiện bị đánh dấu xong mà việc chưa làm.
- ai-service dùng bảng riêng `ai.processed_events` (V211), vì `ai_app` không chạm schema `analytics`.

**`CONCURRENTLY` cho HNSW đánh đổi gì?**
- **Được:** không khoá ghi. `CREATE INDEX` thường giữ khoá chặn INSERT/UPDATE trên bảng suốt lúc
  dựng; với HNSW trên hàng nghìn vector thì tính bằng phút, nên worker nạp tài liệu bị đứng.
- **Mất:**
  - Chậm hơn: quét bảng hai lần, và phải chờ các transaction đang mở kết thúc.
  - **Không chạy được trong transaction block**, nên không nằm trong migration Flyway được. Đó là
    một lý do HNSW dựng bằng script riêng.
  - Dựng hỏng giữa chừng thì để lại chỉ mục **INVALID**, phải `DROP` rồi dựng lại.
- Thêm một lý do HNSW không nằm trong Flyway: Flyway chạy lúc bảng rỗng. Dựng HNSW trên bảng rỗng rồi
  chèn dần cho đồ thị kém hơn dựng một lần trên tập đủ.
