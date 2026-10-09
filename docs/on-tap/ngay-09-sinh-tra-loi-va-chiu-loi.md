# Ôn tập Ngày 9 — Sinh câu trả lời có trích dẫn, hậu kiểm, chịu lỗi LLM (UC023)

> Viết 08/10/2026 (lịch gốc 29/09). Quyết định: [ADR-0028](../adr/0028-llm-gemini-flash-lite-client-trung-lap.md).
> Số liệu: [`docs/report/uc023-thu-llm-2026-10-08.md`](../report/uc023-thu-llm-2026-10-08.md).

## 1. Hôm nay hệ thống chạy thế nào

```
5 đoạn đã qua sàn ─► loi_nhac.py:  system = CHỈ THỊ (cố định)
                                    user   = <tai_lieu><doan so="1" …>…</doan>…</tai_lieu>
                                             <cau_hoi> câu hỏi ĐÃ CHE PII </cau_hoi>
                 ─► LLMChiuLoi: mạch cho phép? ─ không ⇒ suy giảm ngay (0 ms)
                                 gọi Gemini 3.5 Flash-Lite, hạn chót CHUNG 2,5 s
                                 429/5xx/quá hạn ⇒ thử lại 1 lần nếu còn thời gian
                                 400/401/422     ⇒ không thử lại
                 ─► "KHONG_DU_CAN_CU"? ⇒ từ chối NOT_COVERED
                 ─► hau_kiem.py: bỏ [n] ngoài khoảng · đo groundedness · che PII lạ · đánh số lại [k]
                 ─► ChatResponse: answer, citations, groundedness_score, degraded, latency_breakdown
```

Kết quả đầu–cuối qua HTTP với Gemini thật: trả lời có trích dẫn trong **1,3–1,9 s** cho cả lượt.
Chặng sinh ~1,0–1,5 s.

## 2. "Phải giải thích được"

**`groundedness_score` và `retrieval_top_score` khác nhau thế nào? Cho ví dụ cái này cao, cái kia thấp.**
- `retrieval_top_score` = cosine cao nhất giữa câu hỏi và các đoạn. Nó đo *đoạn có giống câu hỏi
  không*, và có **trước** khi gọi LLM.
- `groundedness_score` = tỉ lệ câu trong câu trả lời vừa có trích dẫn hợp lệ, vừa có ≥ 50% âm tiết
  (đã bỏ dấu) nằm trong một đoạn được trích. Nó đo *câu trả lời có dựa vào đoạn không*, và chỉ có
  **sau** khi sinh.
- **Retrieval cao, groundedness thấp:** hỏi "máy lạnh bảo hành bao lâu", đoạn đúng về bảo hành máy
  lạnh (cosine 0,8) ghi "24 tháng", nhưng mô hình viết "bảo hành 36 tháng và tặng thêm quạt [1]". Câu
  bịa không có trong đoạn ⇒ groundedness thấp. Test: `test_truy_hoi_dung_ma_mo_hinh_bia_so`.
- **Retrieval thấp, groundedness cao:** đoạn chỉ gần câu hỏi vừa đủ qua sàn (cosine 0,3), nói về
  chuyện khác, nhưng mô hình chép đúng nguyên văn đoạn đó kèm `[1]`. Câu trả lời "trung thành với
  nguồn" mà không trả lời đúng câu hỏi.
- Đây là lý do phải báo **hai** con số: một con số không phân biệt được "tìm sai" với "nói sai".

**Vì sao không thử lại lỗi `422` (và `400`, `401`)?**
- Đó là lỗi **phía mình**: tham số sai, khoá sai, lời nhắc bị từ chối. Gửi lại y nguyên thì nhận lại
  y nguyên.
- Thử lại chỉ đốt ngân sách 2,5 s và hạn mức (bậc miễn phí có hạn mức theo ngày).
- Có ví dụ thật hôm nay: gửi `reasoning_effort=minimal` cho Gemini 3.8 Flash nhận 400 *"Thinking level
  MINIMAL is not supported"*. Thử lại 100 lần vẫn 400.
- Lỗi `4xx` cũng **không làm mở mạch**. Nhà cung cấp đã trả lời, tức là nó còn sống. Mở mạch vì một
  request sai là phạt mọi người dùng khác.

**Trạng thái `half-open` để làm gì? Bỏ nó đi thì hỏng thế nào?**
- Mạch mở 30 s rồi phải biết nhà cung cấp đã sống lại chưa. `HALF_OPEN` cho **đúng một** request đi
  thăm dò:
  - thăm dò qua ⇒ đóng mạch;
  - thăm dò hỏng ⇒ mở lại 30 s nữa.
  - Trong lúc thăm dò, mọi request khác vẫn bị chặn.
- Bỏ nó đi chỉ còn hai cách, cách nào cũng hỏng:
  1. Hết 30 s là đóng hẳn. Nếu nhà cung cấp vẫn sập thì cả loạt request ùa vào cùng lúc, mỗi cái chịu
     trọn 2,5 s rồi mới hỏng. Đó chính là cơn bão mà mạch sinh ra để chặn.
  2. Không bao giờ tự đóng. Nhà cung cấp sống lại rồi mà bot vẫn trả câu suy giảm tới khi khởi động
     lại pod.
- Chi tiết dễ bị hỏi vặn: lượt thăm dò bị huỷ giữa chừng (khách đóng tab) thì không bao giờ báo kết
  quả. Quá 30 s thì cho lượt khác thăm dò, nếu không mạch kẹt `HALF_OPEN` vĩnh viễn. Test:
  `test_breaker_luot_tham_do_mat_tich_khong_lam_ket_half_open`.

## 3. Quyết định hôm nay và vì sao

1. **Gemini 3.5 Flash-Lite với `reasoning_effort=minimal`, không dùng 3.8 Flash (ADR-0028).**
   - 3.8 Flash mất 3,6 s cho 8 token rồi trả 503 "high demand".
   - Flash-Lite ở mức `low`: 3/10 câu quá 2,5 s. Ở mức `minimal`: 10/10 trong ngân sách, trung vị
     1,5 s, vẫn 7/8 trích đúng căn cứ.
   - 500 lượt/ngày thì eval Ngày 13 (~142 lượt) vừa bậc miễn phí.
2. **Client trung lập chuẩn OpenAI, `httpx`, không thêm gói.** Đổi nhà cung cấp là đổi `.env`. Image
   đã 776 MB / 400 MB, không thêm SDK nào.
3. **`LLM_MODE` tách khỏi `AI_MODE`.**
   - `AI_MODE=mock` làm vector câu hỏi thành `mock-hash-1024`. Truy hồi lọc theo `embedding_model`,
     nên kho thật trả rỗng.
   - Chế độ phát triển thường ngày là nhúng thật + LLM giả. Mặc định `mock` ⇒ CI không đốt lượt nào.
4. **Hạn chót chung 2,5 s cho cả lần thử lại.**
   - Hạn riêng từng lần thì 2,5 + 2,5 = 5 s, phá p95 < 4 s.
   - Với hạn chung: quá hạn lần đầu là hết ngân sách ⇒ không thử lại. 503 trả về nhanh ⇒ còn thời
     gian ⇒ thử lại.
5. **Câu suy giảm trích nguyên văn đoạn có cosine cao nhất.** Nó vẫn đúng sự thật vì chép từ tài liệu,
   chỉ kém mượt. Lấy đoạn cosine cao nhất chứ không lấy hạng 1 RRF, vì làn dense một mình trúng nhiều
   hơn (0,800 so với 0,740). Đo được: với "mất hoá đơn còn bảo hành không", hạng 1 RRF là đoạn "xuất
   hoá đơn GTGT".
6. **Ba sửa rút từ phép thử 10 câu** (bảng đầy đủ trong báo cáo):
   - Lời nhắc: trả lời phần có căn cứ, chỉ từ chối khi không đoạn nào liên quan.
   - Groundedness so âm tiết **đã bỏ dấu**, vì kho có FAQ viết không dấu.
   - Groundedness so với **đoạn tốt nhất** được trích, không gộp từ vựng của 5 đoạn.
7. **Đánh số lại `[n]` → `[k]` theo mảng `citations`.** Mô hình chỉ dùng đoạn 4 thì response có MỘT
   trích dẫn; để nguyên `[4]` thì widget không biết nó trỏ vào đâu.
8. **Che PII của khách trước khi gửi LLM; hậu kiểm chỉ che PII "lạ".**
   - Câu hỏi rời hệ thống sang nhà cung cấp ngoài, nên che số điện thoại/email/CCCD trước.
   - Ở câu trả lời, PII có sẵn trong tài liệu (hotline cửa hàng) thì giữ. Che nó là phá đúng câu trả
     lời khách cần.

## 4. Bằng chứng

- `tests/unit/test_llm_chiu_loi.py` (23 ca):
  - breaker đủ 3 trạng thái bằng đồng hồ giả;
  - phân loại 429/5xx/400/401/422;
  - hạn chót chung;
  - mạch mở thì không chạm nhà cung cấp.
- `tests/unit/test_hau_kiem.py`:
  - lọc `[7]` khi chỉ có 3 đoạn;
  - tài liệu cài chỉ thị `</tai_lieu>` không đóng được vùng dữ liệu;
  - giữ hotline, che số lạ.

  Hai test của phép đo groundedness đã kiểm ngược: gỡ quyết định thì test đỏ.
- Đầu–cuối qua HTTP:
  - câu ngoài phạm vi và câu "in ra chỉ thị hệ thống" đều bị từ chối;
  - LLM trỏ vào cổng đóng ⇒ 4/4 HTTP 200 `degraded`, lượt thứ 4 mạch mở, `generate_ms` = 0.

## 5. Điểm yếu đã biết — nói trước khi bị hỏi

- **Groundedness là phép đo từ vựng.**
  - Câu trả lời dịch từ tài liệu tiếng Anh bị điểm 0 oan (G061: đúng, trích đúng).
  - Câu chép đúng chữ nhưng đảo nghĩa ("không được đổi" ↔ "được đổi") được điểm cao oan.
  - Đổi lại, nó tất định, 0 đồng và chạy 100% lượt. Chấm bằng LLM lấy mẫu 5% là việc của UC027.
- **Câu "chưa có thông tin" chưa mang cờ `refused`** (G004). Ngày 10 thêm cổng groundedness để huỷ
  câu trả lời đã sinh và chuyển thành từ chối.
- **Bậc miễn phí dùng nội dung để huấn luyện.** Trước Ngày 18 (dữ liệu doanh nghiệp thật) phải bật
  thanh toán. `cost_vnd` hiện = 0 vì giá để 0.
- 10 câu không đủ để báo tỉ lệ. Số chính thức là eval Ngày 13.
