# Ôn tập Ngày 1 — CSDL thật V201–V209 và test cách ly tenant

> Viết bù 06/10/2026. Code: `ai-service/migration/V201…V209`, `ai-service/tests/integration/test_rls.py`,
> job CI `rls-test`. Quyết định: ADR-0001 (RLS), ADR-0016 (role `ai_app`).

## Hệ thống chạy thế nào

Mỗi bảng của Track B (`knowledge`, `ai`, `integration`) có `tenant_id`, có policy RLS, và bật cả
`ENABLE` lẫn `FORCE ROW LEVEL SECURITY`. Policy so `tenant_id` với `ai.current_tenant()`. Hàm này
đọc `app.tenant_id` của transaction; **chưa đặt thì ném lỗi** chứ không trả `NULL`.

Test cách ly có hai ca:
- **(a)** tenant A đọc đoạn của tenant B thì nhận **rỗng**;
- **(b)** mượn kết nối mà **không** đặt `app.tenant_id` thì bị ném **SQLSTATE 42501**.

## "Phải giải thích được"

**Vì sao ca (b) quan trọng hơn ca (a)?**
- Ca (a) chứng minh policy **chạy** khi mọi thứ đúng.
- Ca (b) chứng minh điều xảy ra khi lập trình viên **quên** đặt tenant:
  - hệ thống **đóng** (fail-closed), báo lỗi ồn ào;
  - không phải **mở toang** (một policy viết kiểu `tenant_id = current_setting(...)` với giá trị rỗng
    có thể khớp sai hoặc trả hết).
- Lỗi thật ngoài đời gần như luôn là "quên một chỗ", không phải "viết policy sai". Vì vậy ca (b) là
  ca canh đúng rủi ro thật.

**`FORCE ROW LEVEL SECURITY` khác `ENABLE` ở chỗ nào, và vì sao vẫn phải tránh `crm_owner`?**
- `ENABLE`: RLS áp cho mọi role **trừ chủ bảng**.
- `FORCE`: áp **cả cho chủ bảng**.
- Nhưng role **superuser** hoặc có thuộc tính **`BYPASSRLS`** thì bỏ qua RLS **kể cả khi đã FORCE**.
  `crm_owner` có `rolsuper = t` và `rolbypassrls = t` (đã đo trên CSDL thật). Nối bằng nó thì mọi
  policy lặng lẽ mất tác dụng: không lỗi, không log.
- Vì vậy runtime dùng `ai_app` (không phải chủ bảng, không `BYPASSRLS`).
  `src/ai/db/session.py::_kiem_role_runtime` từ chối khởi động nếu DSN không phải `ai_app`.
- `crm_owner` chỉ dùng cho Flyway và việc quản trị như dựng HNSW.

## Câu dễ bị hỏi thêm

**"RLS đã chặn rồi, sao truy vấn vector còn lọc `tenant_id` trong câu (ADR-0007)?"**
Đó là lớp thứ hai: nếu RLS bị cấu hình sai (ví dụ nối nhầm role), câu SQL vẫn tự lọc. Hai lớp độc
lập thì phải hỏng cả hai mới rò.
