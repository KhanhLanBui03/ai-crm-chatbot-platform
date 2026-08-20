# Flyway — dải V1xx (Track A)

## Quy ước đánh số — BẤT BIẾN

| Dải | Chủ sở hữu | Schema được phép đụng |
|---|---|---|
| **V1xx** | **Track A** (thư mục này) | `platform`, `engagement`, `sales`, `analytics` |
| V2xx | Track B (`ai-service/migration/`) | `knowledge`, `ai`, `integration` |

Hai làn **không bao giờ** ghi vào dải của nhau. Đây là ranh giới sở hữu schema ở mục 1.1
của kế hoạch, và là cách tránh xung đột số hiệu migration khi hai người làm song song.

Ngoại lệ duy nhất: bảng `sales.LEAD_SCORES` do Track B dùng nhưng nằm trong schema `sales`
của Track A — Track A tạo bảng bằng migration V1xx, Track B **ghi qua API** chứ không ghi
thẳng (ADR-0002, kế hoạch mục 9).

## Tên file

```
V1<nn>__<mo_ta_khong_dau>.sql
```

Ví dụ: `V101__create_schema_platform.sql`, `V102__enable_rls_on_tenant_tables.sql`.

## Thứ tự dự kiến

| Số | Nội dung |
|---|---|
| V101 | Tạo 4 schema + extension `pgvector` |
| V102 | `platform`: TENANTS, USERS, ROLES |
| V103 | `platform`: PLANS, SUBSCRIPTIONS, USAGE_RECORDS |
| V104 | `platform`: AUDIT_LOGS |
| V105 | `platform`: OUTBOX_EVENTS + index bộ phận `(published_at) WHERE published_at IS NULL` |
| V106 | `engagement`: CONTACTS, CHANNEL_IDENTITIES, NOTES, TAGS |
| V107 | `engagement`: CHANNEL_INTEGRATIONS |
| V108 | `engagement`: CONVERSATIONS, MESSAGES, HANDOFF_EVENTS |
| V109 | `sales`: LEADS, DEALS, ACTIVITIES, LEAD_SCORES |
| V110 | `analytics`: CONVERSATION_METRICS_DAILY, FUNNEL_SNAPSHOTS, TOPIC_STATS |
| V111 | `analytics`: PROCESSED_EVENTS (chống xử lý trùng — ADR-0003) |
| V112 | Bật RLS + policy trên mọi bảng có `tenant_id` (ADR-0001) |

Chi tiết cột: kế hoạch **phần 9 — Lược đồ dữ liệu**.

## Bẫy cần nhớ

- Migration chạy bằng tài khoản **chủ bảng** (`DB_MIGRATION_USER`), ứng dụng chạy bằng
  tài khoản **khác** (`DB_USERNAME`). Chủ bảng bypass RLS — dùng nó ở runtime là vô hiệu hóa
  toàn bộ cơ chế cô lập tenant.
- Bật `FORCE ROW LEVEL SECURITY` chứ không chỉ `ENABLE`, nếu không chủ bảng vẫn đọc được hết.
- Tạo index HNSW **sau khi** đã nạp dữ liệu (kế hoạch mục 7.1 chặng 6).
