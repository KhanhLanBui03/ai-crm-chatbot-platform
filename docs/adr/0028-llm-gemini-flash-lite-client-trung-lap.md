# ADR-0028 — LLM sinh câu trả lời: Gemini 3.5 Flash-Lite qua client trung lập chuẩn OpenAI

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-08
- **Làn sở hữu:** Track B (module AI)
- **Quan hệ:** lệch Master Plan (ghi Anthropic Claude) và `config.py` cũ (`anthropic_*`) · số liệu ở
  [`docs/report/uc023-thu-llm-2026-10-08.md`](../report/uc023-thu-llm-2026-10-08.md) · liên quan
  [ADR-0027](0027-luot-chat-pipeline-tuan-tu-khong-langgraph.md)

## Bối cảnh

UC023 cần một LLM sinh câu trả lời tiếng Việt có trích dẫn, trong ngân sách **2.500 ms** của tổng
p95 < 4.000 ms (§5.3). Master Plan và `config.py` giả định Anthropic (`ANTHROPIC_API_KEY`), nhưng
đến 08/10 nhóm chưa có khoá nào. Ràng buộc của nhóm 2 người, kinh phí 0:

- **Miễn phí** ở giai đoạn phát triển; **một** khoá duy nhất phải quản lý (người dùng chốt 08/10).
- **Hạn mức:** eval Ngày 13 cần ~142 lượt mỗi lần chạy, chạy ít nhất 2 lần (tái lập).
- **Dữ liệu:** bậc miễn phí của nhà cung cấp dùng nội dung để huấn luyện ⇒ không được đưa dữ liệu
  doanh nghiệp thật vào (Ngày 18, Nghị định 13/2023).

Ngày 07/10 tra cứu bảng xếp hạng bên thứ ba (LMArena, Artificial Analysis): model miễn phí mạnh nhất
là Gemini 3.8 Flash (LMArena #8), nhưng bậc miễn phí chỉ **20 lượt/ngày**. Người dùng chốt: chỉ dùng
khoá Google AI Studio, thử 10 câu rồi chọn model.

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Claude qua SDK `anthropic` (Master Plan) | Khớp tài liệu; chất lượng tiếng Việt tốt | Không có khoá; không có bậc miễn phí; thêm một gói vào image đã 776 MB |
| B. Gemini 3.8 Flash | Điểm xếp hạng cao nhất trong nhóm miễn phí | Đo được 3.636 ms cho 8 token ra (vượt ngân sách) rồi 503 *"high demand"*; 20 lượt/ngày không đủ một lần eval; không nhận `reasoning_effort=minimal` |
| C. **Gemini 3.5 Flash-Lite, `reasoning_effort=minimal`** | 10/10 câu trong ngân sách (trung vị 1.543 ms, lớn nhất 1.891 ms); 7/8 trích đúng căn cứ; **500 lượt/ngày** — eval Ngày 13 vừa bậc miễn phí | Model nhỏ hơn: lập luận nhiều bước kém hơn B; vẫn là bậc miễn phí (dữ liệu bị dùng huấn luyện) |
| D. Mistral / OpenRouter / Groq | Có bậc miễn phí rộng | Thêm khoá thứ hai — người dùng đã loại |

Về cách gọi: SDK riêng của từng nhà cung cấp, hay **một client theo chuẩn OpenAI chat completions**
gọi bằng `httpx` (đã có trong image).

## Quyết định

Sinh câu trả lời bằng **`gemini-3.5-flash-lite`, `reasoning_effort=minimal`, `temperature=0`**, gọi
qua client trung lập chuẩn OpenAI chat completions (`src/ai/integrations/llm/`), cấu hình hoàn toàn
bằng `.env`: `LLM_MODE`, `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_REASONING_EFFORT`.

## Lập luận

- **Độ trễ là ràng buộc cứng, chất lượng chênh không thấy được trên phép thử.** Trên cùng 10 câu, C
  trích đúng căn cứ 7/8, và câu trượt duy nhất trượt ở truy hồi chứ không ở LLM. B không đo xong
  được vì quá hạn rồi 503 — một model không phục vụ được trong ngân sách thì điểm xếp hạng không còn
  ý nghĩa với hệ thống này.
- **Mức suy luận quyết định đuôi độ trễ.** Cùng model C: `low` cho 3/10 câu quá 2.500 ms (đuôi
  8.464 ms), `minimal` cho 0/10. Chặng sinh của RAG chủ yếu là chép và tóm tắt từ đoạn — suy luận dài
  không cần thiết.
- **Hạn mức 500 lượt/ngày gỡ được nút thắt eval.** Với B, Ngày 13 buộc phải bật thanh toán hoặc chia
  một lần eval ra 8 ngày.
- **Client trung lập** vì Gemini, Mistral, OpenRouter, Groq đều phục vụ cùng hình dạng request. Đổi
  nhà cung cấp là đổi `.env`, không sửa code, không thêm gói vào image (ràng buộc < 400 MB).

## Đánh đổi

- **Lệch Master Plan.** Ba trường `anthropic_*` vẫn nằm trong `config.py` nhưng không còn được đọc
  (giữ để `.env` cũ không vỡ, có comment trỏ về ADR này).
- **Mất tính năng riêng của nhà cung cấp** qua lớp tương thích: bộ nhớ đệm lời nhắc, đầu ra JSON
  schema chặt, trích dẫn có cấu trúc. Hậu kiểm phải tự lọc `[n]` bằng regex.
- **Model nhỏ.** Câu hỏi cần ghép nhiều điều kiện từ nhiều đoạn có thể kém hơn model lớn. Chưa đo —
  10 câu không đủ; eval Ngày 13 phải tách số theo loại câu `lua_chon` / `tinh_huong`.
- **Bậc miễn phí dùng nội dung để huấn luyện.** Chấp nhận được với kho tổng hợp hiện tại; **trước khi
  nạp dữ liệu doanh nghiệp thật (Ngày 18) phải bật thanh toán** cho project — khi đó điền
  `LLM_GIA_*_VND_TRIEU_TOKEN` để `cost_vnd` nói thật (hiện = 0).
- **Phụ thuộc một nhà cung cấp ở bậc không có SLA.** Đã thấy 503 *"high demand"* ngay trong phép thử.
  Bù bằng circuit breaker + câu trả lời suy giảm (`degraded=true`), không bằng nhà cung cấp dự phòng —
  thêm nhà cung cấp thứ hai là thêm khoá thứ hai.
- `reasoning_effort` là chuỗi tự do trong `.env`: mỗi model nhận một tập giá trị khác nhau (3.8 Flash
  từ chối `minimal`, Flash-Lite từ chối `none`) và chỉ biết được bằng cách gọi thử. Đổi model là
  phải chạy lại `tests.eval.thu_llm`.

## Hệ quả

- `src/ai/integrations/llm/`: `client.py` (Protocol + `OpenAICompatLLMClient` + `MockLLMClient`),
  `circuit_breaker.py`, `chiu_loi.py` (thử lại trong hạn chót chung 2,5 s).
- **`LLM_MODE` tách khỏi `AI_MODE`**, mặc định `mock`: nhúng thật + LLM giả là chế độ phát triển
  thường ngày; CI và pytest không bao giờ đốt lượt.
- `requirements/base.txt` **không** thêm gói nào (kế hoạch cũ định thêm `anthropic`).
- Đổi model về sau: chạy `python -m tests.eval.thu_llm --model <tên>` (10 câu, tất định) trước khi
  đổi `.env`, ghi kết quả vào báo cáo cùng dạng.
- Báo cáo chương 3 (lựa chọn công nghệ) và chương 5 (độ trễ theo chặng) dẫn số từ báo cáo 08/10.
