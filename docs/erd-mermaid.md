# ERD Mermaid — đầy đủ thuộc tính, sinh từ 24 migration Flyway

Sơ đồ thực thể — quan hệ **đầy đủ cột, kiểu và khoá** của toàn hệ thống: **32 bảng** (30 nghiệp vụ
+ 2 hạ tầng) trên **7 schema** PostgreSQL 16 + pgvector.

> **Nguồn duy nhất của tài liệu này là mã DDL đang chạy**, không phải bản phác:
> `java-core/src/main/resources/db/migration/` (V101–V115) và `ai-service/migration/`
> (V201–V209). Mọi cột, kiểu, giá trị `CHECK` dưới đây đọc thẳng từ 24 file đó — kể cả các cột
> thêm bằng `ALTER TABLE ... ADD COLUMN` ở V113/V114/V115/V208/V209.
>
> Tài liệu diễn giải thiết kế (lập luận, bảng đã cân nhắc rồi bỏ, RLS, chỉ mục) nằm ở
> [`erd-ai-crm.md`](erd-ai-crm.md). File này chỉ là **hình vẽ**.

---

## Đối chiếu context ↔ schema ↔ migration

| § | Bounded context | Schema | Làn | Migration | Bảng |
|---|---|---|---|---|---|
| [0](#0-tổng-quan--32-bảng) | *Tổng quan* | — | — | — | cả 32 |
| [1](#1-identity--access) | Identity & Access | `platform` | A | V103 | 3 |
| [2](#2-tenant-management) | Tenant Management | `platform` | A | V102 · V113 | 1 |
| [3](#3-subscription) | Subscription | `platform` | A | V102 · V115 | 3 |
| [4](#4-messaging) | Messaging | `engagement` | A | V106 · V107 · V114 | 4 |
| [5](#5-contact-management) | Contact Management | `engagement` | A | V105 | 4 |
| [6](#6-knowledge-base) | Knowledge Base | `knowledge` | **B** | V202 · V203 · V209 | 2 |
| [7](#7-ai-processing) | AI Processing | `ai` · `integration` | **B** | V204 · V205 · V208 · V209 | 4 |
| [8](#8-crm) | CRM | `sales` | A | V108 · V113 | 6 |
| [9](#9-analytics--compliance) | Analytics & Compliance | `platform` · `analytics` | A | V104 · V109 · V110 · V113 | 5 |

## Quy ước đọc sơ đồ

- **Tên thực thể** viết hoa, **bỏ tiền tố schema** (Mermaid không cho dấu chấm trong tên) — tra
  schema ở bảng trên.
- **Kiểu** giữ nguyên kiểu SQL thật: `uuid` `varchar(200)` `vector(1024)` `uuid[]` `text[]`
  `tsvector` `jsonb` `bytea` `inet` `timestamptz`.
- **Kiểu có độ chính xác và thang số ghi ở chú thích, không ghi ở cột kiểu.** Bộ phân tích cú
  pháp của Mermaid không nhận **dấu phẩy** trong tên kiểu — `numeric(16,4)` làm hỏng cả sơ đồ với
  `Expecting 'ATTRIBUTE_WORD', got ','`. Chín cột `numeric` vì thế viết kiểu là `numeric`, còn
  `numeric(16,4)` nằm ở đầu chú thích. Dấu ngoặc **không** kèm phẩy (`varchar(200)`, `char(3)`,
  `vector(1024)`) và dấu ngoặc vuông (`uuid[]`, `text[]`) thì mọi phiên bản đều nhận.
- **Khoá**: `PK` khoá chính · `FK` khoá ngoại · `UK` nằm trong một ràng buộc `UNIQUE` ·
  ghép được, ví dụ `uuid lead_id FK,UK`.
- **Chú thích cột** là chuỗi trong nháy kép, chứa giá trị enum của ràng buộc `CHECK` (ngăn bằng
  dấu `/`) hoặc ghi chú ngữ nghĩa.
- **Khoá ngoại phức hợp.** Hầu hết FK trong Track A là `(cột_nghiệp_vụ, tenant_id)` →
  `(id, tenant_id)` — ép quan hệ cha-con phải **cùng một tenant** ngay ở tầng CSDL, không phó mặc
  tầng ứng dụng. Mermaid không diễn tả được khoá phức hợp, nên chỉ cột nghiệp vụ được đánh `FK`,
  còn tính chất kép ghi trong chú thích.
- **Nét vẽ quan hệ**:
  - `||--o{` liền → có `FOREIGN KEY` thật trong CSDL.
  - `||..o{` đứt → **tham chiếu logic, không có khoá ngoại** vì cắt qua ranh giới hai làn
    (ADR-0002). Toàn vẹn do tầng ứng dụng giữ, xem [mục 7 của `erd-ai-crm.md`](erd-ai-crm.md#7-tham-chiếu-liên-làn--không-có-khoá-ngoại).
- **Bảng nối vẽ thành thực thể riêng** (`USER_ROLES`, `CONTACT_TAGS`) chứ không dùng ký hiệu
  N–N gộp: chúng mang cột riêng (`granted_by`, `tagged_at`, `tenant_id`), gộp lại là giấu mất.
- Cột `created_at` / `updated_at` có ở **mọi** bảng, do trigger `platform.touch_updated_at()` giữ.

---

## 0. Tổng quan — 32 bảng

Chỉ quan hệ, không cột. Đường **đứt** là ba chỗ duy nhất bắc qua ranh giới Track A ↔ Track B.

```mermaid
erDiagram
    TENANTS               ||--o{ USERS                 : "có"
    TENANTS               ||--o{ ROLES                 : "định nghĩa"
    TENANTS               ||--o{ USER_ROLES            : "phạm vi"
    USERS                 ||--o{ USER_ROLES            : "được gán"
    ROLES                 ||--o{ USER_ROLES            : "gán cho"

    TENANTS               ||--o{ TENANT_SUBSCRIPTIONS  : "đăng ký"
    SUBSCRIPTION_PLANS    ||--o{ TENANT_SUBSCRIPTIONS  : "được chọn"
    TENANT_SUBSCRIPTIONS  ||--o{ USAGE_RECORDS         : "đo bằng"

    TENANTS               ||--o{ CHANNELS              : "kết nối"
    CHANNELS              ||--o{ CHANNEL_IDENTITIES    : "nhận diện"
    CONTACTS              ||--o{ CHANNEL_IDENTITIES    : "hợp nhất từ"
    CHANNEL_IDENTITIES    ||--o{ CONVERSATIONS         : "mở"
    CHANNELS              ||--o{ CONVERSATIONS         : "qua kênh"
    CONTACTS              ||--o{ CONVERSATIONS         : "phát sinh"
    USERS                 ||--o{ CONVERSATIONS         : "phụ trách"
    CONVERSATIONS         ||--o{ MESSAGES              : "chứa"
    USERS                 ||--o{ MESSAGES              : "gửi"

    TENANTS               ||--o{ CONTACTS              : "sở hữu"
    CONTACTS              ||--o{ CONTACTS              : "hợp nhất vào"
    CONTACTS              ||--o{ CONTACT_NOTES         : "được ghi chú"
    CONTACTS              ||--o{ CONTACT_TAGS          : "gắn"
    TAGS                  ||--o{ CONTACT_TAGS          : "được gắn"
    TENANTS               ||--o{ TAGS                  : "quản lý"

    CONTACTS              ||--o{ LEADS                 : "trở thành"
    CONVERSATIONS         ||--o{ LEADS                 : "sinh ra"
    LEADS                 ||--o| DEALS                 : "chuyển đổi 1-1"
    CONTACTS              ||--o{ DEALS                 : "gắn với"
    PIPELINES             ||--o{ DEAL_STAGES           : "gồm"
    PIPELINES             ||--o{ DEALS                 : "chứa"
    DEAL_STAGES           ||--o{ DEALS                 : "đang ở"
    CONTACTS              ||--o{ ACTIVITIES            : "chăm sóc"
    LEADS                 ||--o{ ACTIVITIES            : "chăm sóc"
    DEALS                 ||--o{ ACTIVITIES            : "chăm sóc"
    USERS                 ||--o{ ACTIVITIES            : "thực hiện"
    LEADS                 ||--o{ LEAD_SCORES           : "lịch sử điểm"
    CONTACTS              ||--o{ LEAD_SCORES           : "của danh bạ"

    TENANTS               ||--o{ AUDIT_LOGS            : "ghi nhận"
    USERS                 ||--o{ AUDIT_LOGS            : "gây ra"
    CONTACTS              ||--o{ DATA_ERASURE_REQUESTS : "yêu cầu xoá"
    CHANNELS              ||--o{ METRICS_DAILY         : "tổng hợp theo"
    TENANTS               ||--o{ OUTBOX_EVENTS         : "phát sinh"
    TENANTS               ||--o{ PROCESSED_EVENTS      : "đã xử lý"

    KNOWLEDGE_DOCUMENTS   ||--o{ KNOWLEDGE_CHUNKS      : "chia thành"
    AI_INTERACTIONS       ||--o{ AI_TOOL_CALLS         : "đề xuất gọi"
    AI_INTERACTIONS       ||--o{ AI_FEEDBACK           : "được đánh giá"
    MCP_SERVERS           ||--o{ AI_TOOL_CALLS         : "phục vụ"

    CONVERSATIONS         ||..o{ AI_INTERACTIONS       : "logic · không FK · ADR-0002"
    MESSAGES              ||..o| AI_INTERACTIONS       : "logic · ngược chiều · không FK"
    KNOWLEDGE_CHUNKS      }o..o{ AI_INTERACTIONS       : "trích dẫn qua mảng uuid[]"
```

---

## 1. Identity & Access

`platform` · V103 · **3 bảng**. `users.scope = PLATFORM` thì `tenant_id IS NULL` — quản trị viên
nền tảng không thuộc tenant nào; `roles.is_system` cũng buộc phải bằng `(tenant_id IS NULL)`.

```mermaid
erDiagram
    TENANTS {
        uuid id PK
    }
    USERS {
        uuid        id                 PK
        uuid        tenant_id          FK,UK "NULL khi scope=PLATFORM"
        varchar(255) email                   "UNIQUE bộ phận theo tenant, bỏ qua bản ghi đã xoá mềm"
        varchar(255) password_hash           "BCrypt"
        varchar(200) full_name
        varchar(20)  phone
        text         avatar_url
        varchar(20)  scope                   "TENANT/PLATFORM"
        varchar(30)  status                  "PENDING/ACTIVE/DISABLED"
        timestamptz  email_verified_at
        timestamptz  last_login_at
        smallint     failed_login_count      "khoá tài khoản tạm thời"
        timestamptz  locked_until
        timestamptz  deleted_at              "xoá mềm"
        timestamptz  created_at
        timestamptz  updated_at
    }
    ROLES {
        uuid         id          PK
        uuid         tenant_id   FK "NULL = vai trò hệ thống"
        varchar(30)  code           "OWNER/ADMIN/AGENT/ANALYST/PLATFORM_ADMIN"
        varchar(100) name
        text         description
        jsonb        permissions    "mảng mã quyền"
        boolean      is_system      "buộc bằng tenant_id IS NULL"
        timestamptz  created_at
        timestamptz  updated_at
    }
    USER_ROLES {
        uuid        user_id    PK,FK "FK kép với tenant_id"
        uuid        role_id    PK,FK
        uuid        tenant_id  FK
        uuid        granted_by FK    "người cấp quyền"
        timestamptz granted_at
        timestamptz created_at
        timestamptz updated_at
    }

    TENANTS ||--o{ USERS      : "có"
    TENANTS ||--o{ ROLES      : "định nghĩa"
    TENANTS ||--o{ USER_ROLES : "phạm vi"
    USERS   ||--o{ USER_ROLES : "được gán"
    ROLES   ||--o{ USER_ROLES : "gán cho"
    USERS   ||--o{ USER_ROLES : "là người cấp"
```

---

## 2. Tenant Management

`platform` · V102 + V113 · **1 bảng**. `tenants` là gốc của mọi thứ: nó *là* tenant nên không có
cột `tenant_id`, và policy RLS so trên chính `id`.

```mermaid
erDiagram
    TENANTS {
        uuid         id                   PK
        varchar(200) name
        varchar(64)  slug                 UK "định danh trên URL"
        varchar(100) industry
        varchar(255) contact_email
        varchar(20)  phone
        varchar(64)  timezone                "mặc định Asia/Ho_Chi_Minh"
        varchar(10)  locale                  "mặc định vi-VN"
        jsonb        business_hours          "giờ làm việc theo thứ"
        varchar(30)  ai_tone                 "PROFESSIONAL/FRIENDLY/CONCISE"
        smallint     lead_score_threshold    "0..100, ngưỡng tạo lead tự động"
        boolean      auto_lead_creation
        varchar(30)  status                  "TRIAL/ACTIVE/SUSPENDED/EXPIRED"
        text         suspended_reason        "bắt buộc khi status=SUSPENDED"
        timestamptz  suspended_at
        varchar(20)  assignment_mode         "V113 · ROUND_ROBIN/LEAST_BUSY/MANUAL"
        jsonb        assignment_config       "V113 · tham số phân công"
        timestamptz  created_at
        timestamptz  updated_at
    }
```

---

## 3. Subscription

`platform` · V102 + V115 · **3 bảng**. `subscription_plans` là **ngoại lệ không có `tenant_id`**:
danh mục gói do quản trị nền tảng định nghĩa, mọi tenant đọc chung, không bật RLS.

`usage_records` dùng FK kép `(subscription_id, tenant_id)` → `tenant_subscriptions (id, tenant_id)`
— không thể ghi mức dùng của tenant này vào thuê bao của tenant kia dù ứng dụng có sai.

```mermaid
erDiagram
    TENANTS {
        uuid id PK
    }
    SUBSCRIPTION_PLANS {
        uuid          id                 PK
        varchar(30)   code               UK "TRIAL/STARTER/GROWTH/PRO"
        varchar(100)  name
        numeric       monthly_price_vnd     "numeric(14,2)"
        int           conversation_quota
        bigint        ai_token_quota
        int           max_users
        int           max_documents
        smallint      max_channels
        int           storage_mb
        smallint      max_tags              "V115 · trần số thẻ danh bạ"
        boolean       is_active
        smallint      sort_order
        timestamptz   created_at
        timestamptz   updated_at
    }
    TENANT_SUBSCRIPTIONS {
        uuid        id                     PK,UK "UNIQUE (id, tenant_id) cho FK kép"
        uuid        tenant_id              FK,UK
        uuid        plan_id                FK
        varchar(30) status                       "TRIALING/ACTIVE/PAST_DUE/EXPIRED/CANCELED"
        timestamptz period_start           UK    "UNIQUE (tenant_id, period_start)"
        timestamptz period_end                   "CHECK period_end > period_start"
        boolean     auto_renew
        uuid        scheduled_plan_id      FK    "gói sẽ đổi sang ở kỳ tới"
        timestamptz scheduled_effective_at
        timestamptz canceled_at
        uuid        changed_by
        timestamptz created_at
        timestamptz updated_at
    }
    USAGE_RECORDS {
        uuid        id                 PK
        uuid        tenant_id          FK
        uuid        subscription_id    FK,UK "FK kép với tenant_id"
        varchar(30) metric             UK    "CONVERSATION/AI_TOKEN/DOCUMENT/STORAGE_MB/USER"
        bigint      used_value
        bigint      quota_value              "chụp lại hạn mức tại thời điểm tính"
        timestamptz last_calculated_at
        timestamptz created_at
        timestamptz updated_at
    }

    TENANTS              ||--o{ TENANT_SUBSCRIPTIONS : "đăng ký"
    SUBSCRIPTION_PLANS   ||--o{ TENANT_SUBSCRIPTIONS : "được chọn"
    SUBSCRIPTION_PLANS   ||--o{ TENANT_SUBSCRIPTIONS : "hẹn đổi sang"
    TENANT_SUBSCRIPTIONS ||--o{ USAGE_RECORDS        : "đo bằng"
    TENANTS              ||--o{ USAGE_RECORDS        : "thuộc về"
```

---

## 4. Messaging

`engagement` · V106 + V107 + V114 · **4 bảng**. Đây là chỗ tin nhắn từ ba kênh đổ về.

Ba điểm đáng chú ý: bí mật kênh lưu `bytea` **đã mã hoá** kèm `credential_key_id`, không bao giờ
văn bản thô (UC008 bước 7) · `messages.external_message_id` là chốt chống nhận trùng webhook ·
`messages.ai_interaction_id` trỏ **ngược** sang Track B mà không có khoá ngoại.

```mermaid
erDiagram
    CONTACTS {
        uuid id PK
    }
    USERS {
        uuid id PK
    }
    CHANNELS {
        uuid         id                       PK,UK
        uuid         tenant_id                FK,UK
        varchar(30)  type                           "WEB_WIDGET/ZALO/FACEBOOK"
        varchar(150) name
        varchar(255) external_id                    "OA id / page id"
        varchar(64)  widget_key               UK    "chỉ WEB_WIDGET mới có"
        varchar(30)  status                         "DISCONNECTED/PENDING_VERIFY/ACTIVE/ERROR"
        jsonb        config                         "cấu hình widget gộp ở đây"
        bytea        credential_encrypted           "token kênh đã mã hoá"
        varchar(64)  credential_key_id              "bắt buộc nếu có credential"
        timestamptz  token_expires_at
        bytea        webhook_secret_encrypted
        text         last_error
        timestamptz  last_synced_at
        uuid         created_by               FK
        timestamptz  created_at
        timestamptz  updated_at
    }
    CHANNEL_IDENTITIES {
        uuid         id               PK,UK
        uuid         tenant_id        FK,UK
        uuid         channel_id       FK,UK "FK kép với tenant_id"
        uuid         contact_id       FK    "NULL cho tới khi hợp nhất danh bạ"
        varchar(255) external_user_id UK    "UNIQUE (tenant_id, channel_id, external_user_id)"
        varchar(200) display_name
        text         avatar_url
        jsonb        raw_profile
        timestamptz  first_seen_at
        timestamptz  last_seen_at
        timestamptz  created_at
        timestamptz  updated_at
    }
    CONVERSATIONS {
        uuid         id                    PK,UK
        uuid         tenant_id             FK,UK
        uuid         channel_id            FK
        uuid         channel_identity_id   FK
        uuid         contact_id            FK
        varchar(200) subject
        varchar(30)  status                      "BOT_HANDLING/PENDING_AGENT/AGENT_HANDLING/RESOLVED/CLOSED"
        varchar(20)  priority                    "LOW/NORMAL/HIGH/URGENT"
        uuid         assigned_user_id      FK
        timestamptz  assigned_at                 "buộc cùng NULL với assigned_user_id"
        timestamptz  handover_at
        varchar(30)  handover_reason             "CUSTOMER_REQUEST/LOW_CONFIDENCE/NO_GROUNDING/NEGATIVE_SENTIMENT/REPEATED_FAILURE/WRITE_TOOL_APPROVAL/QUOTA_EXCEEDED/LLM_ERROR"
        varchar(50)  primary_intent
        varchar(100) topic
        varchar(20)  sentiment                   "POSITIVE/NEUTRAL/NEGATIVE"
        text         summary                     "tóm tắt dạng văn xuôi"
        timestamptz  summarized_at
        jsonb        summary_data                "V114 · tóm tắt có cấu trúc"
        varchar(20)  summary_trigger             "V114 · HANDOFF/CLOSING/TURN_THRESHOLD/MANUAL"
        varchar(50)  summary_model_version       "V114 · bốn cột tóm tắt buộc cùng NULL hoặc cùng có"
        int          message_count
        int          unread_count
        timestamptz  first_response_at
        timestamptz  last_message_at
        timestamptz  resolved_at
        varchar(50)  closed_reason
        smallint     csat_score                  "1..5"
        timestamptz  created_at
        timestamptz  updated_at
    }
    MESSAGES {
        uuid         id                  PK
        uuid         tenant_id           FK
        uuid         conversation_id     FK "FK kép, ON DELETE CASCADE"
        varchar(20)  sender_type            "CUSTOMER/BOT/AGENT/SYSTEM"
        uuid         sender_user_id      FK "chỉ khác NULL khi sender_type=AGENT"
        varchar(10)  direction              "INBOUND/OUTBOUND"
        text         content
        varchar(20)  content_type           "TEXT/IMAGE/FILE/STICKER/LOCATION/SYSTEM_NOTE"
        jsonb        attachments            "mảng, CHECK jsonb_typeof = array"
        varchar(255) external_message_id    "chống nhận trùng webhook"
        varchar(20)  delivery_status        "PENDING/SENT/DELIVERED/FAILED"
        uuid         ai_interaction_id      "liên làn · KHÔNG có FK"
        boolean      is_redacted            "đã che theo Nghị định 13"
        timestamptz  sent_at
        timestamptz  created_at
        timestamptz  updated_at
    }

    CHANNELS           ||--o{ CHANNEL_IDENTITIES : "nhận diện"
    CONTACTS           ||--o{ CHANNEL_IDENTITIES : "hợp nhất từ"
    USERS              ||--o{ CHANNELS           : "tạo"
    CHANNEL_IDENTITIES ||--o{ CONVERSATIONS      : "mở"
    CHANNELS           ||--o{ CONVERSATIONS      : "qua kênh"
    CONTACTS           ||--o{ CONVERSATIONS      : "phát sinh"
    USERS              ||--o{ CONVERSATIONS      : "phụ trách"
    CONVERSATIONS      ||--o{ MESSAGES           : "chứa"
    USERS              ||--o{ MESSAGES           : "gửi khi là nhân viên"
```

---

## 5. Contact Management

`engagement` · V105 · **4 bảng**. `contacts` **tự tham chiếu** qua `merged_into_contact_id` để giữ
vết hợp nhất trùng lặp; xoá là xoá mềm bằng `status` + `anonymized_at` / `deleted_at`, không bao
giờ xoá vật lý (UC016, UC040).

```mermaid
erDiagram
    TENANTS {
        uuid id PK
    }
    USERS {
        uuid id PK
    }
    CONTACTS {
        uuid         id                     PK,UK
        uuid         tenant_id              FK,UK
        varchar(200) full_name
        varchar(255) email
        varchar(20)  phone
        varchar(200) company
        varchar(30)  primary_channel              "WEB_WIDGET/ZALO/FACEBOOK/PHONE"
        uuid         owner_user_id          FK    "FK kép với tenant_id"
        varchar(30)  status                       "ACTIVE/MERGED/ANONYMIZED"
        uuid         merged_into_contact_id FK    "tự tham chiếu, buộc có khi status=MERGED"
        timestamptz  last_contacted_at
        boolean      consent_marketing            "Nghị định 13"
        timestamptz  anonymized_at                "buộc có khi status=ANONYMIZED"
        timestamptz  deleted_at
        timestamptz  created_at
        timestamptz  updated_at
    }
    TAGS {
        uuid        id          PK,UK
        uuid        tenant_id   FK,UK
        varchar(50) name
        varchar(7)  color             "CHECK khớp ^#[0-9A-Fa-f]{6}$"
        text        description
        int         usage_count       "chệch chuẩn có chủ ý, đếm sẵn"
        uuid        created_by  FK
        timestamptz created_at
        timestamptz updated_at
    }
    CONTACT_TAGS {
        uuid        contact_id PK,FK "FK kép, ON DELETE CASCADE"
        uuid        tag_id     PK,FK "FK kép, ON DELETE CASCADE"
        uuid        tenant_id  FK
        uuid        tagged_by  FK
        timestamptz tagged_at
        timestamptz created_at
        timestamptz updated_at
    }
    CONTACT_NOTES {
        uuid        id             PK
        uuid        tenant_id      FK
        uuid        contact_id     FK "FK kép, ON DELETE CASCADE"
        uuid        author_user_id FK
        text        content           "CHECK không rỗng sau khi cắt khoảng trắng"
        boolean     is_pinned
        timestamptz created_at
        timestamptz updated_at
    }

    TENANTS  ||--o{ CONTACTS      : "sở hữu"
    CONTACTS ||--o{ CONTACTS      : "hợp nhất vào"
    USERS    ||--o{ CONTACTS      : "phụ trách"
    TENANTS  ||--o{ TAGS          : "quản lý"
    USERS    ||--o{ TAGS          : "tạo"
    CONTACTS ||--o{ CONTACT_TAGS  : "gắn"
    TAGS     ||--o{ CONTACT_TAGS  : "được gắn"
    USERS    ||--o{ CONTACT_TAGS  : "gắn thẻ"
    CONTACTS ||--o{ CONTACT_NOTES : "được ghi chú"
    USERS    ||--o{ CONTACT_NOTES : "viết"
```

---

## 6. Knowledge Base

`knowledge` · V202 + V203 + V209 · **2 bảng**, làn **Track B**.

Không bảng nào ở đây có khoá ngoại sang Track A — `uploaded_by` là `uuid` trần, đối chiếu qua API
nội bộ. `tenant_id` vẫn `NOT NULL` và **phải lọc ngay trong truy vấn vector**: chỉ mục HNSW là
chỉ mục xấp xỉ, nó chọn ứng viên *trước* khi RLS lọc, nên bỏ điều kiện `tenant_id` ra khỏi câu
truy vấn là mất kết quả chứ không phải rò rỉ (ADR-0007, bề mặt T6).

```mermaid
erDiagram
    KNOWLEDGE_DOCUMENTS {
        uuid         id              PK
        uuid         tenant_id          "không FK · liên làn"
        varchar(255) title           UK "UNIQUE (tenant_id, title, version)"
        text         description        "V209 · mô tả cho tác tử chọn nguồn"
        varchar(30)  source_type        "PDF/DOCX/TXT/MD/HTML/URL"
        varchar(255) file_name
        text         file_path          "bắt buộc khi source_type khác URL"
        varchar(100) mime_type
        bigint       file_size_bytes
        text         source_url         "bắt buộc khi source_type=URL"
        varchar(10)  language           "mặc định vi"
        varchar(30)  status             "PENDING/PROCESSING/READY/FAILED/ARCHIVED"
        int          chunk_count
        text         error_message      "bắt buộc khi status=FAILED"
        int          version         UK "phiên bản tài liệu cùng tên"
        uuid         uploaded_by        "không FK · liên làn"
        timestamptz  indexed_at
        timestamptz  created_at
        timestamptz  updated_at
    }
    KNOWLEDGE_CHUNKS {
        uuid          id                PK
        uuid          tenant_id            "LỌC TRONG TRUY VẤN, không dựa vào RLS"
        uuid          document_id       FK "ON DELETE CASCADE"
        int           chunk_index       UK "UNIQUE (document_id, chunk_index)"
        text          content
        tsvector      content_segmented    "đã tách từ tiếng Việt · chỉ mục GIN"
        int           token_count
        vector(1024)  embedding            "pgvector · chỉ mục HNSW"
        varchar(100)  embedding_model
        varchar(30)   embedding_version    "đổi mô hình là phải nhúng lại"
        int           page_number
        varchar(255)  heading
        jsonb         metadata
        timestamptz   created_at
        timestamptz   updated_at
    }

    KNOWLEDGE_DOCUMENTS ||--o{ KNOWLEDGE_CHUNKS : "chia thành"
```

---

## 7. AI Processing

`ai` + `integration` · V204 + V205 + V208 + V209 · **4 bảng**, làn **Track B**.

`ai_tool_calls` là **sổ kiểm toán mọi lần tác tử chạm vào công cụ ngoài** — kể cả lần bị chặn:
`decision=BLOCKED` buộc phải có `block_reason`, `decision=NEEDS_APPROVAL` buộc phải có
`approval_status`, và chỉ `decision=ALLOWED` mới được có `outcome`. Đây là bằng chứng cho bề mặt
T4/T7 trong `threat-model.md`.

```mermaid
erDiagram
    AI_INTERACTIONS {
        uuid          id                  PK
        uuid          tenant_id              "không FK · liên làn"
        uuid          conversation_id        "không FK · liên làn"
        uuid          message_id             "không FK · liên làn"
        varchar(30)   branch                 "SMALL_TALK/RAG/TOOL_CALL/CLARIFY/HANDOFF/SUMMARY/EXTRACTION"
        varchar(50)   intent
        numeric       intent_confidence      "numeric(4,3) · 0..1"
        text          user_query
        text          response_text
        uuid[]        retrieved_chunk_ids    "trích dẫn N-N dạng mảng"
        numeric       retrieval_top_score    "numeric(5,4) · điểm RRF cao nhất"
        numeric       groundedness_score     "numeric(4,3) · V209 · 0..1, độ bám nguồn"
        boolean       is_answered
        varchar(50)   refusal_reason         "NOT_COVERED/OUT_OF_SCOPE_DATA/LOW_CONFIDENCE/SAFETY_PROBE"
        varchar(40)   safety_flag            "V208 · PROMPT_INJECTION_INPUT/_TOOL_RESULT/_DOCUMENT/CROSS_TENANT_PROBE/INTERNAL_DATA_PROBE"
        varchar(100)  model_name
        varchar(50)   model_version
        int           prompt_tokens
        int           completion_tokens
        int           total_tokens
        numeric       cost_vnd               "numeric(16,4) · một lượt gọi mô hình nhỏ hơn một đồng"
        int           latency_ms
        boolean       is_cached              "V209 · trả từ bộ nhớ đệm ngữ nghĩa"
        varchar(20)   status                 "SUCCESS/FAILED/TIMEOUT"
        text          error_message
        timestamptz   created_at
        timestamptz   updated_at
    }
    AI_FEEDBACK {
        uuid        id                PK
        uuid        tenant_id            "không FK · liên làn"
        uuid        ai_interaction_id FK "ON DELETE CASCADE"
        varchar(20) rater_type           "CUSTOMER/AGENT/AUTO_EVAL"
        uuid        rater_user_id        "chỉ khác NULL khi rater_type=AGENT"
        varchar(20) rating               "POSITIVE/NEGATIVE"
        varchar(30) reason_code          "WRONG_INFO/IRRELEVANT/INCOMPLETE/BAD_TONE · buộc có khi NEGATIVE"
        text        comment
        text        correction_text      "câu trả lời đúng do nhân viên soạn"
        timestamptz created_at
        timestamptz updated_at
    }
    MCP_SERVERS {
        uuid         id                   PK
        uuid         tenant_id               "không FK · liên làn"
        varchar(150) name                 UK "UNIQUE (tenant_id, name)"
        text         endpoint_url
        varchar(20)  transport               "HTTP/SSE/STDIO"
        varchar(20)  spec_version            "ghim phiên bản giao thức MCP"
        varchar(20)  auth_type               "NONE/API_KEY/OAUTH2"
        bytea        credential_encrypted    "buộc có khi auth_type khác NONE"
        varchar(64)  credential_key_id
        text[]       allowed_tools           "danh sách trắng công cụ"
        jsonb        tool_schema_cache       "V208 · sổ đăng ký công cụ, mặc định mảng rỗng"
        int          rate_limit_per_min
        int          timeout_ms
        varchar(30)  status                  "DRAFT/ACTIVE/ERROR/DISABLED"
        timestamptz  last_health_check_at
        text         last_error
        uuid         created_by              "không FK · liên làn"
        timestamptz  created_at
        timestamptz  updated_at
    }
    AI_TOOL_CALLS {
        bigint       id                PK "GENERATED ALWAYS AS IDENTITY"
        uuid         tenant_id            "không FK · liên làn"
        uuid         ai_interaction_id FK "ON DELETE CASCADE"
        uuid         mcp_server_id     FK
        varchar(100) tool_name
        varchar(20)  risk_level           "READ/WRITE/DESTRUCTIVE"
        jsonb        arguments
        jsonb        result_summary
        varchar(20)  decision             "ALLOWED/BLOCKED/NEEDS_APPROVAL"
        varchar(50)  block_reason         "NOT_ALLOWLISTED/TOOL_DISABLED/SCHEMA_HASH_MISMATCH/INVALID_ARGUMENTS/CROSS_TENANT_IDENTIFIER/RATE_LIMIT_EXCEEDED"
        varchar(20)  approval_status      "PENDING/APPROVED/REJECTED/EXPIRED"
        uuid         approved_by          "không FK · liên làn"
        timestamptz  approved_at
        varchar(20)  outcome              "SUCCESS/BUSINESS_ERROR/TIMEOUT/TRANSPORT_ERROR · chỉ khi ALLOWED"
        int          latency_ms
        int          guard_latency_ms     "V209 · thời gian riêng của lớp chặn"
        text         error_message
        timestamptz  created_at
        timestamptz  updated_at
    }

    AI_INTERACTIONS ||--o{ AI_FEEDBACK   : "được đánh giá"
    AI_INTERACTIONS ||--o{ AI_TOOL_CALLS : "đề xuất gọi"
    MCP_SERVERS     ||--o{ AI_TOOL_CALLS : "phục vụ"
```

---

## 8. CRM

`sales` · V108 + V113 · **6 bảng**.

Chỗ tinh tế nhất của lược đồ nằm ở đây: `deals` có **hai** khoá ngoại về phễu —
`(pipeline_id, tenant_id) → pipelines` và `(pipeline_id, stage_id) → deal_stages (pipeline_id, id)`.
Khoá thứ hai ép giai đoạn phải thuộc **đúng cái phễu** mà deal đang nằm, thứ mà một FK đơn
`stage_id → deal_stages(id)` không chặn được.

`leads.current_score` do Track B ghi **qua API**, không ghi thẳng — xem ngoại lệ duy nhất ở
[CLAUDE.md](../.claude/CLAUDE.md); `lead_scores` giữ lịch sử từng lần chấm.

```mermaid
erDiagram
    CONTACTS {
        uuid id PK
    }
    CONVERSATIONS {
        uuid id PK
    }
    USERS {
        uuid id PK
    }
    PIPELINES {
        uuid         id         PK,UK
        uuid         tenant_id  FK,UK
        varchar(150) name       UK "UNIQUE (tenant_id, name)"
        boolean      is_default
        boolean      is_active
        timestamptz  created_at
        timestamptz  updated_at
    }
    DEAL_STAGES {
        uuid         id              PK,UK "thêm UNIQUE (pipeline_id, id) cho FK kép của deals"
        uuid         tenant_id       FK,UK
        uuid         pipeline_id     FK,UK "ON DELETE CASCADE"
        varchar(100) name
        smallint     position        UK    "UNIQUE (pipeline_id, position)"
        smallint     probability           "0..100"
        boolean      is_won                "CHECK không đồng thời is_won và is_lost"
        boolean      is_lost
        text[]       required_fields       "trường bắt buộc để vào giai đoạn"
        timestamptz  created_at
        timestamptz  updated_at
    }
    LEADS {
        uuid          id                     PK,UK
        uuid          tenant_id              FK,UK
        uuid          contact_id             FK
        uuid          source_conversation_id FK    "ON DELETE SET NULL"
        varchar(30)   source                       "AI_AUTO/MANUAL"
        varchar(30)   status                       "NEW/CONTACTED/QUALIFIED/CONVERTED/DISQUALIFIED"
        varchar(200)  interested_product
        numeric       budget_min                   "numeric(18,2) · CHECK budget_max >= budget_min"
        numeric       budget_max                   "numeric(18,2)"
        varchar(10)   budget_confidence            "LOW/MEDIUM/HIGH"
        varchar(10)   urgency                      "LOW/MEDIUM/HIGH"
        text          interest_summary
        smallint      current_score                "0..100 · Track B ghi QUA API"
        jsonb         score_reason
        timestamptz   score_updated_at             "buộc cùng NULL với current_score"
        uuid          owner_user_id          FK
        timestamptz   converted_at
        varchar(200)  disqualified_reason
        timestamptz   created_at
        timestamptz   updated_at
    }
    DEALS {
        uuid          id                  PK,UK
        uuid          tenant_id           FK,UK
        uuid          lead_id             FK,UK "UNIQUE · quan hệ 1-1 với lead"
        uuid          contact_id          FK
        uuid          pipeline_id         FK
        uuid          stage_id            FK    "FK kép (pipeline_id, stage_id)"
        varchar(200)  title
        varchar(20)   status                    "OPEN/WON/LOST"
        varchar(20)   source                    "AI_LEAD/MANUAL"
        numeric       amount                    "numeric(18,2)"
        char(3)       currency                  "mặc định VND"
        date          expected_close_date
        timestamptz   stage_changed_at
        timestamptz   closed_at                 "buộc cùng NULL với status=OPEN"
        varchar(200)  close_reason
        uuid          owner_user_id       FK
        timestamptz   created_at
        timestamptz   updated_at
    }
    ACTIVITIES {
        uuid         id             PK
        uuid         tenant_id      FK
        uuid         contact_id     FK "ON DELETE CASCADE"
        uuid         lead_id        FK "ON DELETE SET NULL"
        uuid         deal_id        FK "ON DELETE SET NULL"
        varchar(30)  type              "CALL/MEETING/QUOTE/EMAIL/NOTE"
        varchar(200) subject
        text         content
        varchar(30)  outcome           "DONE/NO_ANSWER/REFUSED/NOT_INTERESTED/RESCHEDULED"
        varchar(20)  source            "MANUAL/AUTO"
        uuid         performed_by   FK
        timestamptz  performed_at
        timestamptz  remind_at         "buộc cùng NULL với remind_status=NONE"
        uuid         remind_user_id FK
        varchar(20)  remind_status     "NONE/PENDING/SENT/DONE/CANCELED"
        timestamptz  created_at
        timestamptz  updated_at
    }
    LEAD_SCORES {
        uuid        id            PK,UK
        uuid        tenant_id     FK,UK
        uuid        lead_id       FK "ON DELETE CASCADE"
        uuid        contact_id    FK "ON DELETE CASCADE"
        smallint    score            "0..100"
        varchar(50) model_version    "phiên bản mô hình chấm điểm"
        jsonb       features         "đặc trưng đầu vào"
        jsonb       top_factors      "mảng · yếu tố ảnh hưởng nhiều nhất"
        varchar(10) confidence       "LOW/MEDIUM/HIGH"
        timestamptz scored_at
        timestamptz created_at
        timestamptz updated_at
    }

    PIPELINES     ||--o{ DEAL_STAGES : "gồm"
    PIPELINES     ||--o{ DEALS       : "chứa"
    DEAL_STAGES   ||--o{ DEALS       : "đang ở · FK kép ép cùng phễu"
    CONTACTS      ||--o{ LEADS       : "trở thành"
    CONVERSATIONS ||--o{ LEADS       : "sinh ra"
    USERS         ||--o{ LEADS       : "phụ trách"
    LEADS         ||--o| DEALS       : "chuyển đổi 1-1"
    CONTACTS      ||--o{ DEALS       : "gắn với"
    USERS         ||--o{ DEALS       : "phụ trách"
    CONTACTS      ||--o{ ACTIVITIES  : "chăm sóc"
    LEADS         ||--o{ ACTIVITIES  : "chăm sóc"
    DEALS         ||--o{ ACTIVITIES  : "chăm sóc"
    USERS         ||--o{ ACTIVITIES  : "thực hiện"
    USERS         ||--o{ ACTIVITIES  : "được nhắc"
    LEADS         ||--o{ LEAD_SCORES : "lịch sử điểm"
    CONTACTS      ||--o{ LEAD_SCORES : "của danh bạ"
```

---

## 9. Analytics & Compliance

`platform` + `analytics` · V104 + V109 + V110 + V113 · **5 bảng** (3 nghiệp vụ + 2 hạ tầng).

- `audit_logs` **chỉ ghi thêm** — `UPDATE`/`DELETE` đã bị `REVOKE` khỏi `crm_app`.
- `outbox_events` và `processed_events` là **hạ tầng, không bật RLS**: outbox do tiến trình đẩy
  sự kiện đọc xuyên tenant, còn `processed_events` là chốt chống xử lý trùng khi Kafka giao nhận
  ít nhất một lần (ADR-0003).
- `metrics_daily` là read-model tổng hợp; `UNIQUE NULLS NOT DISTINCT` cho phép `channel_id`,
  `branch`, `model_name` cùng `NULL` mà vẫn coi là **một** hàng — nếu không, mỗi lần tổng hợp
  mức "toàn tenant" lại chèn thêm một dòng trùng.

```mermaid
erDiagram
    TENANTS {
        uuid id PK
    }
    USERS {
        uuid id PK
    }
    CONTACTS {
        uuid id PK
    }
    CHANNELS {
        uuid id PK
    }
    AUDIT_LOGS {
        bigint      id            PK "GENERATED ALWAYS AS IDENTITY"
        uuid        tenant_id     FK
        varchar(20) actor_type       "USER/AI_AGENT/SYSTEM/PLATFORM_ADMIN"
        uuid        actor_user_id FK "buộc có khi actor_type là USER/PLATFORM_ADMIN"
        varchar(60) action
        varchar(50) entity_type
        uuid        entity_id
        jsonb       before_data
        jsonb       after_data
        inet        ip_address
        text        user_agent
        varchar(64) request_id       "lần vết xuyên service"
        varchar(20) severity         "INFO/WARNING/CRITICAL"
        timestamptz created_at
        timestamptz updated_at
    }
    DATA_ERASURE_REQUESTS {
        uuid        id                    PK
        uuid        tenant_id             FK
        uuid        contact_id            FK
        varchar(20) requested_by             "CONTACT/STAFF"
        text        legal_basis              "căn cứ pháp lý, Nghị định 13"
        varchar(30) status                   "PENDING/IN_PROGRESS/COMPLETED/PARTIALLY_FAILED"
        jsonb       items                    "mảng · tiến độ xoá từng hạng mục"
        uuid        identity_verified_by  FK
        timestamptz identity_verified_at     "CHECK phải xác minh trước khi rời PENDING"
        text        external_systems_note
        text        certificate_uri          "chứng thư đã xoá"
        timestamptz requested_at
        timestamptz started_at
        timestamptz completed_at
        timestamptz created_at
        timestamptz updated_at
    }
    METRICS_DAILY {
        uuid          id                    PK
        uuid          tenant_id             FK,UK
        date          metric_date           UK
        uuid          channel_id            FK,UK "ON DELETE CASCADE · NULL = toàn tenant"
        varchar(30)   branch                UK    "SMALL_TALK/RAG/TOOL_CALL/CLARIFY/HANDOFF/SUMMARY/EXTRACTION"
        varchar(100)  model_name            UK    "UNIQUE NULLS NOT DISTINCT trên 5 cột"
        int           conversation_count
        int           ai_handled_count
        int           handover_count
        bigint        first_response_sum_ms       "tổng · chia cho count để ra trung bình"
        int           first_response_count
        int           interaction_count
        int           refusal_count
        int           positive_feedback
        int           negative_feedback
        bigint        prompt_tokens
        bigint        completion_tokens
        numeric       cost_vnd                    "numeric(16,4)"
        bigint        latency_sum_ms
        int           latency_p50_ms
        int           latency_p95_ms
        timestamptz   last_calculated_at
        timestamptz   created_at
        timestamptz   updated_at
    }
    OUTBOX_EVENTS {
        bigint      id             PK "GENERATED ALWAYS AS IDENTITY"
        uuid        tenant_id      FK
        varchar(50) aggregate_type
        uuid        aggregate_id
        varchar(60) event_type
        varchar(60) topic             "1 trong 5 topic ở docs/events/"
        jsonb       payload
        jsonb       headers
        timestamptz published_at      "NULL = chưa đẩy lên Kafka"
        smallint    attempt_count
        text        last_error
        timestamptz created_at
        timestamptz updated_at
    }
    PROCESSED_EVENTS {
        varchar(60) consumer_group PK
        bigint      event_id       PK "khoá chính kép chống xử lý trùng"
        uuid        tenant_id      FK
        timestamptz processed_at
        timestamptz created_at
        timestamptz updated_at
    }

    TENANTS  ||--o{ AUDIT_LOGS            : "ghi nhận"
    USERS    ||--o{ AUDIT_LOGS            : "gây ra"
    TENANTS  ||--o{ DATA_ERASURE_REQUESTS : "tiếp nhận"
    CONTACTS ||--o{ DATA_ERASURE_REQUESTS : "yêu cầu xoá"
    USERS    ||--o{ DATA_ERASURE_REQUESTS : "xác minh danh tính"
    TENANTS  ||--o{ METRICS_DAILY         : "tổng hợp cho"
    CHANNELS ||--o{ METRICS_DAILY         : "bóc tách theo"
    TENANTS  ||--o{ OUTBOX_EVENTS         : "phát sinh"
    TENANTS  ||--o{ PROCESSED_EVENTS      : "đã xử lý"
```

---

## Phụ lục — kiểm kê 32 bảng

| # | Bảng | Schema | Làn | Migration | Cột | Khoá chính |
|---|---|---|---|---|---|---|
| 1 | `tenants` | `platform` | A | V102, V113 | 19 | `uuid` |
| 2 | `subscription_plans` | `platform` | A | V102, V115 | 15 | `uuid` |
| 3 | `tenant_subscriptions` | `platform` | A | V102 | 13 | `uuid` |
| 4 | `usage_records` | `platform` | A | V102 | 9 | `uuid` |
| 5 | `users` | `platform` | A | V103 | 16 | `uuid` |
| 6 | `roles` | `platform` | A | V103 | 9 | `uuid` |
| 7 | `user_roles` | `platform` | A | V103 | 7 | kép `(user_id, role_id)` |
| 8 | `audit_logs` | `platform` | A | V104 | 15 | `bigint` identity |
| 9 | `contacts` | `engagement` | A | V105 | 16 | `uuid` |
| 10 | `tags` | `engagement` | A | V105 | 9 | `uuid` |
| 11 | `contact_tags` | `engagement` | A | V105 | 7 | kép `(contact_id, tag_id)` |
| 12 | `contact_notes` | `engagement` | A | V105 | 8 | `uuid` |
| 13 | `channels` | `engagement` | A | V106 | 17 | `uuid` |
| 14 | `channel_identities` | `engagement` | A | V106 | 12 | `uuid` |
| 15 | `conversations` | `engagement` | A | V107, V114 | 29 | `uuid` |
| 16 | `messages` | `engagement` | A | V107 | 16 | `uuid` |
| 17 | `pipelines` | `sales` | A | V108 | 7 | `uuid` |
| 18 | `deal_stages` | `sales` | A | V108 | 11 | `uuid` |
| 19 | `leads` | `sales` | A | V108 | 20 | `uuid` |
| 20 | `deals` | `sales` | A | V108 | 18 | `uuid` |
| 21 | `activities` | `sales` | A | V108 | 17 | `uuid` |
| 22 | `data_erasure_requests` | `platform` | A | V109 | 16 | `uuid` |
| 23 | `outbox_events` | `platform` | A | V110 | 13 | `bigint` identity |
| 24 | `processed_events` | `analytics` | A | V110 | 6 | kép `(consumer_group, event_id)` |
| 25 | `lead_scores` | `sales` | A | V113 | 12 | `uuid` |
| 26 | `metrics_daily` | `analytics` | A | V113 | 24 | `uuid` |
| 27 | `knowledge_documents` | `knowledge` | **B** | V202, V209 | 19 | `uuid` |
| 28 | `knowledge_chunks` | `knowledge` | **B** | V203 | 15 | `uuid` |
| 29 | `ai_interactions` | `ai` | **B** | V204, V208, V209 | 27 | `uuid` |
| 30 | `ai_feedback` | `ai` | **B** | V204 | 11 | `uuid` |
| 31 | `mcp_servers` | `integration` | **B** | V205, V208 | 19 | `uuid` |
| 32 | `ai_tool_calls` | `ai` | **B** | V205, V209 | 19 | `bigint` identity |

**Tổng: 32 bảng · 471 cột · 23 bảng Track A + 9 bảng Track B.**

### Ba ngoại lệ của quy tắc "mọi bảng nghiệp vụ có `tenant_id`"

1. `tenants` — chính nó *là* tenant, policy RLS so trên `id`.
2. `subscription_plans` — danh mục dùng chung, không bật RLS, `crm_app` chỉ có `SELECT`.
3. `processed_events` — có cột `tenant_id` nhưng **không bật RLS**: là hạ tầng chống xử lý trùng,
   consumer đọc xuyên tenant.

### Ba chỗ bắc qua ranh giới hai làn — không có khoá ngoại

| Từ | Tới | Cột | Vì sao không FK |
|---|---|---|---|
| `ai.ai_interactions` | `engagement.conversations` | `conversation_id` | ADR-0002 · `ai_app` không có cả quyền `USAGE` trên `engagement` |
| `ai.ai_interactions` | `engagement.messages` | `message_id` | như trên |
| `engagement.messages` | `ai.ai_interactions` | `ai_interaction_id` | tham chiếu **ngược chiều**, `crm_app` không đi vào schema `ai` |

Mất khoá ngoại là mất một lớp bảo đảm toàn vẹn — cái giá đã biết trước của ADR-0002, đổi lấy việc
mô hình ngôn ngữ không có bất kỳ đường nào chạm thẳng vào bảng nghiệp vụ.
