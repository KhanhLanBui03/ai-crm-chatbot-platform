# Hợp đồng UC023 — `POST /v1/ai/chat` trả lời từ tri thức (nháp 08/10/2026)

⚠️ Nháp phía Track B. Nguồn sự thật vẫn là `docs/openapi/ai-service-to-java-core.yaml`
(`ChatResponse`, dòng ~1000) — **chưa sửa**, chờ Dev B xác nhận (mục 4).

Căn cứ: [ADR-0027](../adr/0027-luot-chat-pipeline-tuan-tu-khong-langgraph.md),
[ADR-0028](../adr/0028-llm-gemini-flash-lite-client-trung-lap.md).

## 1. Thay đổi: hai trường THÊM vào `ChatResponse`, không trường nào đổi hay bỏ

| Trường | Kiểu | Bắt buộc | Nghĩa |
|---|---|---|---|
| `degraded` | boolean | có, mặc định `false` | LLM không phục vụ được (circuit breaker mở, quá hạn 2,5 s, nhà cung cấp 429/5xx). `answer` khi đó là **trích nguyên văn** đoạn tài liệu gần câu hỏi nhất, kèm đúng một `citations`. HTTP vẫn **200** — suy giảm không phải lỗi của bên gọi |
| `latency_breakdown` | object `{string: integer}` (ms) | có, có thể rỗng | Thời gian từng chặng. Khoá có thể có: `guard_ms` `classify_ms` `embed_ms` `retrieve_ms` `rerank_ms` `generate_ms` `postguard_ms` `total_ms`. **Chặng không chạy thì không có khoá** (đường nhanh không có `embed_ms`…; rerank tắt thì không có `rerank_ms`) |

Bản YAML đề xuất vá vào `ChatResponse.properties`:

```yaml
        degraded: { type: boolean, default: false }
        latency_breakdown:
          type: object
          additionalProperties: { type: integer }
```

## 2. Ngữ nghĩa đã đổi, dù trường không đổi

| Trường | Trước 08/10 | Từ 08/10 |
|---|---|---|
| `answer` ở nhánh `route=RAG` | luôn là câu mẫu từ chối (`PendingKnowledgeAnswerer`) | câu trả lời do LLM sinh, đã hậu kiểm |
| `citations` | luôn rỗng | các đoạn được trích; `[k]` trong `answer` trỏ vào **phần tử thứ k** (1-based) của mảng — đã đánh số lại, không phải số đoạn trong lời nhắc |
| `citations[].score` | — | cosine câu hỏi ↔ đoạn (0–1). Thiếu vector thì là điểm RRF |
| `refused` + nhánh RAG | luôn `true` | `true` khi không đoạn nào đạt sàn liên quan (không gọi LLM) hoặc LLM kết luận không đủ căn cứ |
| `groundedness_score` | luôn `null` | 0–1, đo bằng luật (định nghĩa: `src/ai/rag/generate/hau_kiem.py`). `null` khi từ chối hoặc suy giảm |

## 3. Tương thích ngược — đã kiểm

`java-core/.../engagement/widget/AiChatClient.java` đọc phản hồi bằng `JsonNode` và chỉ lấy `answer`,
`route`, `refused`, `handoff`, `citations` ⇒ hai trường mới bị bỏ qua, **không có gì vỡ**. Widget
nhận được `citations` thật từ hôm nay.

## 4. Cần Dev B xác nhận

1. Đồng ý vá `ai-service-to-java-core.yaml` theo mục 1?
2. `AiChatClient` có muốn đọc `degraded` để widget hiện nhãn "trả lời tạm" không? (không bắt buộc)
3. `dashboard-api.yaml` (SCR hội thoại) có cần hiện `latency_breakdown` cho quản trị viên không, hay
   để UC039 telemetry lo?
