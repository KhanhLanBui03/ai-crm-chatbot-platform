# Flyway — dải V2xx (Track B)

## Quy ước đánh số — BẤT BIẾN

| Dải | Chủ sở hữu | Schema được phép đụng |
|---|---|---|
| V1xx | Track A (`java-core/src/main/resources/db/migration/`) | `platform`, `engagement`, `sales`, `analytics` |
| **V2xx** | **Track B** (thư mục này) | `knowledge`, `ai`, `integration` |

Hai làn **không bao giờ** ghi vào dải của nhau.

**Không có khoá ngoại nào từ đây sang schema của Track A.** Đó không phải thiếu sót mà là
ADR-0002: `ai-service` không nối thẳng bảng nghiệp vụ. Nếu mô hình ngôn ngữ bị tiêm chỉ thị, nó
không có đường nào chạm tới dữ liệu khách hàng. Các cột `tenant_id`, `conversation_id`,
`message_id`, `uploaded_by` là tham chiếu **logic** — kiểu `uuid`, không `REFERENCES`.

## Cách chạy

java-core nhúng Flyway trong Spring Boot nên dải V1xx tự chạy lúc khởi động. `ai-service` là
FastAPI, không có Flyway nhúng — nên dải V2xx chạy bằng Flyway CLI trong container dùng một lần:

```bash
bash scripts/migrate-ai.sh            # migrate
bash scripts/migrate-ai.sh info       # xem trạng thái
bash scripts/migrate-ai.sh validate   # kiểm checksum
```

> ⚠️ **Bảng lịch sử phải riêng.** Hai Flyway trên cùng một CSDL mà dùng chung một bảng lịch sử
> thì mỗi lần chạy một làn, Flyway sẽ thấy migration của làn kia là *applied but missing* và từ
> chối chạy tiếp. Track A dùng `platform.flyway_schema_history`; Track B dùng
> `knowledge.flyway_schema_history_ai`. Tham số này nằm sẵn trong `scripts/migrate-ai.sh` —
> đừng chạy `flyway migrate` bằng tay mà bỏ nó.

`alembic` có trong `requirements.txt` nhưng **không dùng**: lược đồ do Flyway quản để hai làn
chung một quy ước đánh số.

## Đã có — 8 file, 6 bảng

Nguồn: `docs/erd-ai-crm.md`. Sửa lược đồ thì sửa ERD trước, migration sau.

| Số | Nội dung | Bảng |
|---|---|---|
| V201 | 3 schema · extension `vector` · `touch_updated_at()` · **`ai.current_tenant()`** | — |
| V202 | Tài liệu tri thức (trạng thái nạp gộp vào cột `status`) | `knowledge_documents` |
| V203 | Đoạn + vector + **index GIN** trên `content_segmented` | `knowledge_chunks` |
| V204 | Lượt xử lý của tác tử và đánh giá chất lượng | `ai_interactions` `ai_feedback` |
| V205 | Máy chủ MCP và nhật ký gọi công cụ | `mcp_servers` `ai_tool_calls` |
| V206 | `GRANT` cho `ai_app` | — |
| V207 | **RLS** trên cả 6 bảng | — |
| V208 | `ai_interactions.safety_flag` + cấu trúc bắt buộc cho `mcp_servers.tool_schema_cache` | — (chỉ `ALTER`) |

`ai_interactions` và `ai_feedback` là hai bảng đắt giá nhất về mặt điểm số. Không có
`ai_interactions` thì không tính được chi phí mỗi hội thoại, không phân tích được độ trễ theo
nhánh, và không trả lời được câu chắc chắn bị hỏi: *"làm sao chứng minh bot không bịa?"* —
`retrieved_chunk_ids` chính là câu trả lời. `ai_feedback` là thứ cho phép viết câu *"trên N hội
thoại thực tế, tỉ lệ phản hồi tích cực là X%"*.

## Bốn cái bẫy

**1. Chỉ mục HNSW KHÔNG nằm trong dải Flyway.** Nó ở `ai-service/scripts/create_hnsw_index.sql`:

```bash
docker compose exec -T postgres psql -U crm_owner -d thesis_crm \
    < ai-service/scripts/create_hnsw_index.sql
```

Chạy **sau khi** đã nạp dữ liệu. Flyway chạy lúc khởi động, tức luôn là lúc bảng còn rỗng; dựng
HNSW trên bảng rỗng rồi chèn từng dòng cho đồ thị kém hơn hẳn — chất lượng truy hồi giảm mà
không có dấu hiệu nào báo, chỉ thấy Recall@5 thấp bất thường ở chương thực nghiệm.

**2. Vẫn phải ghi `tenant_id` vào `WHERE` của truy vấn vector.** RLS chặn được dòng nhưng không
đổi được thứ tự quét: HNSW xếp hạng trên **toàn bộ** bảng rồi RLS mới lọc bỏ, nên với kho nhiều
tenant, tám kết quả đầu có thể bị lọc sạch và câu trả về rỗng dù tenant hiện tại có đoạn phù hợp.
Đây là chỗ **duy nhất** trong dự án mà lọc tenant ở tầng ứng dụng là bắt buộc — lý do là hiệu
năng, không phải bảo mật (ADR-0007, bề mặt T6).

**3. `embedding_model` và `embedding_version` lưu trên TỪNG DÒNG.** Thí nghiệm sẽ đổi mô hình
nhúng nhiều lần; không có hai cột này thì mỗi lần đổi phải nạp lại toàn bộ kho thay vì xây lại
từng phần.

**4. Policy gọi `ai.current_tenant()`, không viết thẳng `current_setting(...)::uuid`.** Viết
thẳng thì khi phiên SQLAlchemy quên đặt biến, truy vấn nổ `invalid input syntax for type uuid`
— an toàn nhưng không chỉ ra nguyên nhân. Hàm này là bản sao có chủ ý của
`platform.current_tenant()`: Track B không phụ thuộc vào bất cứ thứ gì trong schema của Track A,
kể cả một hàm, để chạy riêng dải V2xx trên CSDL trống vẫn thành công.
