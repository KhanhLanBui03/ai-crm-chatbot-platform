# Flyway — dải V1xx (Track A)

## Quy ước đánh số — BẤT BIẾN

| Dải | Chủ sở hữu | Schema được phép đụng |
|---|---|---|
| **V1xx** | **Track A** (thư mục này) | `platform`, `engagement`, `sales`, `analytics` |
| V2xx | Track B (`ai-service/migration/`) | `knowledge`, `ai`, `integration` |

Hai làn **không bao giờ** ghi vào dải của nhau. Đây là cách tránh xung đột số hiệu migration
khi hai người làm song song trên hai máy.

Ngoại lệ duy nhất: bảng **`sales.lead_scores`** và cột `sales.leads.current_score` do Track B
dùng — Track A tạo bằng migration V1xx, Track B **ghi qua API** `PUT /internal/leads/{id}/score`
chứ không ghi thẳng (ADR-0002).

## Tên file

```
V1<nn>__<mo_ta_khong_dau>.sql
```

Không dấu tiếng Việt trong tên file. Nội dung và comment thì viết tiếng Việt bình thường.

## Đã có — 13 file, 26 bảng

Nguồn: `docs/erd-ai-crm.md`. Sửa lược đồ thì sửa ERD trước, migration sau.

| Số | Nội dung | Bảng |
|---|---|---|
| V101 | 4 schema · `touch_updated_at()` · **`current_tenant()`** | — |
| V102 | Doanh nghiệp và gói dịch vụ (+ seed 4 gói) | `tenants` `subscription_plans` `tenant_subscriptions` `usage_records` |
| V103 | Định danh và phân quyền (+ seed 2 vai trò hệ thống) | `users` `roles` `user_roles` |
| V104 | Nhật ký kiểm toán | `audit_logs` |
| V105 | Danh bạ và thẻ | `contacts` `tags` `contact_tags` `contact_notes` |
| V106 | Kênh và danh tính | `channels` `channel_identities` |
| V107 | Hội thoại và tin nhắn (+ trigger đếm) | `conversations` `messages` |
| V108 | Phễu bán hàng và CRM | `pipelines` `deal_stages` `leads` `deals` `activities` |
| V109 | Xoá dữ liệu cá nhân — Nghị định 13 | `data_erasure_requests` |
| V110 | Hạ tầng nhắn tin — ADR-0003 | `outbox_events` `processed_events` |
| V111 | `GRANT` cho `crm_app` | — |
| V112 | **RLS** + ba hàm `SECURITY DEFINER` cho đường đăng nhập | — |
| V113 | Lịch sử điểm + mô hình đọc + quy tắc phân công — xem `docs/traceability-uc-db-api-screen.md` | `lead_scores` `metrics_daily` (+2 cột trên `tenants`) |
| V114 | Tóm tắt hội thoại có cấu trúc — UC026 b3-b4 | — (3 cột + 2 `CHECK` trên `conversations`) |
| V115 | Trần số thẻ theo gói — UC017 9.1 | — (1 cột trên `subscription_plans`) |

Migration chạy tự động khi khởi động java-core (`application.yml` → `spring.flyway`).
Chạy tay bằng Flyway CLI:

```bash
docker run --rm --network thesis-crm-ai_crm \
  -v "$PWD/java-core/src/main/resources/db/migration:/flyway/sql:ro" \
  flyway/flyway:10 -url=jdbc:postgresql://postgres:5432/thesis_crm \
  -user=crm_owner -password=changeme \
  -schemas=platform,engagement,sales,analytics migrate
```

## Bốn cái bẫy

**0. `GRANT ... ON ALL TABLES` ở V111 chỉ áp cho bảng ĐANG tồn tại lúc nó chạy.** Trigger
`updated_at` ở V112 mục 6 cũng vậy. Mỗi migration thêm bảng mới phải **tự** cấp quyền, **tự** bật
RLS và **tự** gắn trigger — V113 làm đủ ba. Quên thì không có lỗi nào nổ lúc migrate, chỉ hỏng
lúc chạy.

**1. `FORCE ROW LEVEL SECURITY`, không chỉ `ENABLE`.** Chỉ `ENABLE` thì chủ bảng vẫn đọc hết mọi
tenant, và test sẽ xanh trong khi cô lập đã hỏng. Kiểm bằng:

```sql
SELECT n.nspname||'.'||c.relname, c.relrowsecurity, c.relforcerowsecurity
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname IN ('platform','engagement','sales','analytics')
   AND c.relkind = 'r' AND NOT (c.relrowsecurity AND c.relforcerowsecurity);
```

Đúng **ba** dòng được phép hiện ra: `subscription_plans` (danh mục cấp nền tảng),
`outbox_events` và `processed_events` (job nền không có ngữ cảnh tenant, bật RLS thì poller
không thấy gì và sự kiện đọng lại vĩnh viễn mà không báo lỗi).

**2. Runtime không bao giờ dùng chủ bảng.** Flyway chạy bằng `crm_owner` (`DB_MIGRATION_USER`),
ứng dụng chạy bằng `crm_app` (`DB_USERNAME`). `crm_owner` là superuser nên bypass RLS kể cả khi
đã `FORCE`.

**3. Policy gọi `platform.current_tenant()`, không viết thẳng `current_setting(...)::uuid`.**
Viết thẳng thì khi quên `SET LOCAL app.tenant_id`, truy vấn nổ `invalid input syntax for type
uuid: ""` — an toàn nhưng không chỉ ra nguyên nhân. Hàm này báo đúng chỗ thiếu, mã lỗi `42501`.

**4. Vai trò hệ thống có `tenant_id NULL`.** Dùng khuôn policy chuẩn cho `platform.roles` là hỏng:
`NULL = <uuid>` trả về NULL nên không tenant nào đọc được vai trò nào, và đăng nhập mất phân
quyền. V112 tách `role_read` (mở) khỏi `role_write` (khoá theo tenant).

## Đường đăng nhập — vì sao có `SECURITY DEFINER`

Lúc đăng nhập, hệ thống chưa biết tenant: người dùng mới chỉ gõ email. Với RLS `FORCE` và
`app.tenant_id` chưa đặt thì không đọc được `users`, và không ai đăng nhập được.

V112 giải bằng ba hàm `SECURITY DEFINER` thuộc sở hữu `crm_owner`, mỗi hàm trả về đúng phần dữ
liệu tối thiểu cho một tình huống chưa có ngữ cảnh tenant:

| Hàm | Dùng cho |
|---|---|
| `platform.find_login_identity(email)` | Xác thực — trả thông tin đăng nhập, **không** trả dữ liệu nghiệp vụ |
| `platform.slug_is_taken(slug)` | Đăng ký doanh nghiệp, kiểm trùng mã |
| `engagement.resolve_widget_key(key)` | Web Widget gọi từ trình duyệt khách (bề mặt T2) |

Thêm hàm mới ở đây là **mở rộng bề mặt tấn công** — cân nhắc kỹ, và không bao giờ trả về dữ liệu
hội thoại hay danh bạ.
