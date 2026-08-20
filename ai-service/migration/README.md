# Flyway — dải V2xx (Track B)

## Quy ước đánh số — BẤT BIẾN

| Dải | Chủ sở hữu | Schema được phép đụng |
|---|---|---|
| V1xx | Track A (`java-core/src/main/resources/db/migration/`) | `platform`, `engagement`, `sales`, `analytics` |
| **V2xx** | **Track B** (thư mục này) | `knowledge`, `ai`, `integration` |

Hai làn **không bao giờ** ghi vào dải của nhau. Đây là ranh giới sở hữu schema ở mục 1.1
của kế hoạch, và là cách tránh xung đột số hiệu khi hai người làm song song.

Bảng `sales.LEAD_SCORES` do Track B dùng nhưng nằm trong schema của Track A: Track A tạo bảng
bằng migration V1xx, Track B **ghi qua API** chứ không ghi thẳng (ADR-0002).

## Thứ tự dự kiến

| Số | Nội dung |
|---|---|
| V201 | Tạo schema `knowledge`, `ai`, `integration` |
| V202 | `knowledge`: DOCUMENTS, INGESTION_JOBS |
| V203 | `knowledge`: DOCUMENT_CHUNKS — `embedding vector(1024)`, `content_segmented tsvector`, `embedding_model`, `embedding_version`, `section_path` |
| V204 | `ai`: AI_INTERACTIONS ★, AI_FEEDBACK ★ |
| V205 | `ai`: CONVERSATION_TOPICS |
| V206 | `ai`: EVAL_RUNS, EVAL_RESULTS |
| V207 | `integration`: MCP_SERVERS, MCP_CREDENTIALS |
| V208 | `integration`: TOOL_REGISTRY, TOOL_CALL_LOGS |
| V209 | Index: **HNSW** (m=16, ef_construction=64) trên `embedding`, **GIN** trên `content_segmented` |
| V210 | Bật RLS + policy trên mọi bảng có `tenant_id` |

★ = ba bảng đắt giá nhất về điểm số (kế hoạch mục 9.1). Không có `AI_INTERACTIONS` thì không
tính được chi phí mỗi hội thoại, không phân tích được độ trễ theo nhánh, không truy vết được
vì sao bot trả lời như vậy. `AI_FEEDBACK` là thứ cho phép viết câu "trên N hội thoại thực tế,
tỉ lệ phản hồi tích cực là X%" — câu mà phần lớn đồ án không viết được.

## Bẫy cần nhớ

- **Tạo index HNSW sau khi đã nạp dữ liệu**, không phải trước (kế hoạch mục 7.1 chặng 6).
- Lưu `embedding_model` và `embedding_version` **trên từng dòng**, để xây lại chỉ mục được
  khi đổi mô hình (thí nghiệm E2 sẽ đổi mô hình nhiều lần).
- Mọi truy vấn vector **bắt buộc lọc `tenant_id`** — ADR-0007, bề mặt tấn công T6.
