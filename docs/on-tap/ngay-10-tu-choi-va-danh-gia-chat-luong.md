# Ôn tập Ngày 10 — Từ chối khi không đủ căn cứ (UC025) và đánh giá chất lượng (UC027)

> Viết 08–09/10/2026 (lịch gốc 30/09). Quyết định: [ADR-0029](../adr/0029-tu-choi-bon-ly-do-va-nguong-tu-duong-cong.md),
> [ADR-0030](../adr/0030-ghi-luot-dong-bo-va-bo-cham-tu-dong-mau-5.md). Số liệu:
> [`docs/report/uc025-uc027-ngay10-2026-10-09.md`](../report/uc025-uc027-ngay10-2026-10-09.md).
> Hợp đồng nháp: [`uc025-uc027-tu-choi-danh-gia.md`](../contracts/uc025-uc027-tu-choi-danh-gia.md).

## 1. Hôm nay hệ thống có thêm gì, nằm đâu trong luồng

```
POST /v1/ai/chat ─► run_turn (Dev B) ─► guardrails ─► classify ─► nhánh RAG ─► RagAnswerer
                                                                                    │
  rag/tu_choi.py  kiem_truoc_truy_hoi ── dò dữ liệu? ──────────► SAFETY_PROBE      (luật, 0 ms, 0 LLM)
                                     └─ đơn/phiếu/tài khoản cụ thể? ► OUT_OF_SCOPE_DATA + handoff
                  nhúng ─► truy hồi lai ─► search_or_abstain
                                     └─ cosine cao nhất < sàn ──► NOT_COVERED       (0 LLM)
                  LLM ─► "KHONG_DU_CAN_CU" ──────────────────────► NOT_COVERED
                       ─► hậu kiểm ─► 0 trích dẫn ──────────────► NOT_COVERED       (HUỶ câu đã sinh)
                                    ├─ "không phải câu trả lời" ─► NOT_COVERED       (HUỶ câu đã sinh)
                                    └─ bám nguồn < ngưỡng ───────► LOW_CONFIDENCE    (ngưỡng ship = 0: TẮT)
                  từ chối lần 2 liên tiếp trong hội thoại ⇒ handoff = true (đọc ai_interactions)
                                                                                    │
finally ─► DbTurnRecorder ─► ai.ai_interactions (1 dòng/lượt, interaction_id trả cho java-core)
                                                                                    │
POST /v1/ai/feedback ─► ai.ai_feedback (UPSERT, INSERT…SELECT dưới RLS)             │
GET  /v1/knowledge-gaps ─► truy vấn gộp các lượt từ chối (không bảng riêng)          │
GET  /v1/ai/quality     ─► 7 tín hiệu, mỗi tỉ lệ kèm tử số + mẫu số                  │
worker: mỗi 15 phút ─► ai.tim_luot_can_cham (DEFINER, mẫu md5 5%) ─► LLM giám khảo ─► AUTO_EVAL
```

## 2. Đi theo dữ liệu qua các file

| Bước | File | Ghi nhớ |
|---|---|---|
| Luật trước truy hồi | [`rag/tu_choi.py`](../../ai-service/src/ai/rag/tu_choi.py) `kiem_truoc_truy_hoi` | dò tìm xét TRƯỚC dữ liệu nghiệp vụ; nhóm `DATA_PROBING` dùng lại của Dev B |
| Sàn cosine | `tu_choi.py` `search_or_abstain` | trả điểm cao nhất KỂ CẢ khi dưới sàn — số liệu gốc để hiệu chỉnh |
| Cổng sau sinh | [`rag/answerer.py`](../../ai-service/src/ai/rag/answerer.py) sau `hau_kiem` | 0 trích dẫn, hoặc "không phải câu trả lời" ⇒ NOT_COVERED; có trích dẫn mà bám nguồn thấp ⇒ LOW_CONFIDENCE (cổng tắt khi ship) |
| "Không phải câu trả lời" | [`rag/generate/hau_kiem.py`](../../ai-service/src/ai/rag/generate/hau_kiem.py) `khong_phai_tra_loi` | có câu "chưa có thông tin" VÀ (0 câu mang thông tin — câu có trích dẫn — HOẶC 0 câu bám nguồn) |
| Lời nhắc | [`rag/generate/loi_nhac.py`](../../ai-service/src/ai/rag/generate/loi_nhac.py) | câu chào/mời/"chưa có thông tin" không ghi số; không đoạn nào giúp được thì chỉ ghi mã |
| Mẫu câu + chuyển giao | `answerer.py` `_tu_choi` | câu an toàn không nói lý do; lặp lại ⇒ handoff |
| Ghi lượt | [`orchestrator/ghi_luot.py`](../../ai-service/src/ai/orchestrator/ghi_luot.py) | hỏng thì log + metric, không ném |
| Đánh giá | [`db/repositories/feedback_repository.py`](../../ai-service/src/ai/db/repositories/feedback_repository.py) | `INSERT … SELECT` vì khoá ngoại không chịu RLS |
| Khoảng trống, tín hiệu | [`db/repositories/interaction_repository.py`](../../ai-service/src/ai/db/repositories/interaction_repository.py) | gom theo câu bỏ dấu; sắp theo số hội thoại khác nhau |
| Bộ chấm | [`rag/danh_gia/cham_tu_dong.py`](../../ai-service/src/ai/rag/danh_gia/cham_tu_dong.py), `service.cham_tu_dong_lo`, `worker/main.py` | mẫu tất định, không chắc thì không ghi, mốc quét không bỏ rơi lượt |
| Lược đồ | [`migration/V212`](../../ai-service/migration/V212__co_luot_xu_ly_va_chon_mau_cham_tu_dong.sql) | 3 cột + hàm DEFINER thứ hai |

## 3. Quyết định hôm nay và vì sao

1. **Mỗi lý do sinh ở đúng một chỗ** (ADR-0029). Đặc tả UC025 bắt phân biệt lý do *tại chỗ sinh* vì
   mỗi lý do dẫn tới một việc khác cho doanh nghiệp: NOT_COVERED → thêm tài liệu; OUT_OF_SCOPE_DATA →
   nối công cụ; LOW_CONFIDENCE → xem tài liệu có mơ hồ; SAFETY_PROBE → xem cờ an toàn.
2. **Hai bộ luật regex nghiêng về bỏ sót.** Bắt nhầm = từ chối câu kho trả lời được. Bỏ sót = câu đi
   tiếp vào RAG, mà kho có sẵn chỉ dẫn ("xem tồn kho trên website") nên vẫn được trả lời đúng.
3. **Luật "0 trích dẫn ⇒ NOT_COVERED"** — thêm GIỮA phép đo, khi câu đầu tiên (G001) lộ lại lớp lỗi
   G004 của Ngày 9: mô hình viết "cửa hàng chưa có thông tin…" thay vì mã `KHONG_DU_CAN_CU`. Luật dựa
   trên cấu trúc (có trích dẫn hay không), không dò câu chữ.
4. **Chọn ngưỡng trên bộ vàng, nghiệm thu trên 30 câu khác** — tách tập chọn khỏi tập kiểm. Luật chọn
   (F1 cao nhất, hoà thì mất ít câu đúng nhất) viết vào script TRƯỚC khi chạy. Kết quả: **cả hai ngưỡng
   bằng 0** — sàn cosine không tách được hai lớp, cổng bám nguồn chỉ làm mất câu đúng.
5. **Lớp lỗi "chưa có thông tin + câu mời + trích dẫn" sửa TẠI GỐC (lời nhắc), không vá luật mãi.** Ba
   lần vá luật hậu kiểm vẫn lọt biến thể mới (N005, N012, N003, N002, N007) ⇒ dừng, thêm hai câu vào
   lời nhắc ⇒ 4/4 lượt 30/30. Luật "không phải câu trả lời" giữ lại làm lưới đỡ.
6. **Ghi `ai_interactions` đồng bộ** (ADR-0030) — đánh giá của khách tới ngay sau câu trả lời, dòng phải
   có trước. Lỗi ghi không đổi câu trả lời đúng thành 500.
7. **Hàm DEFINER thứ hai** cho bộ chấm — cùng bốn chốt với hàm của V211, có ADR, có test khoá.
8. **Mẫu 5% tất định theo md5(id)** — chạy lại ra cùng tập; `random()` làm tổng số lượt bị chấm trôi.

## 4. "Phải giải thích được"

**Vì sao huỷ câu trả lời đã sinh thay vì trả kèm cảnh báo?**
- Khách không đọc cảnh báo — họ đọc con số. "Bảo hành 36 tháng (độ tin cậy thấp)" vẫn là một lời hứa
  sai mà cửa hàng phải gánh khi khách mang máy tới.
- Cái giá của huỷ là MỘT lượt LLM đã trả tiền (vài trăm đồng ở bậc trả phí). Cái giá của trả lời sai là
  một khiếu nại, có khi mất khách. Bất đối xứng rất lớn.
- Huỷ xong thì khách vẫn được đề nghị chuyển nhân viên — không bị bỏ rơi.
- Điểm vẫn được ghi (`groundedness_score`, `retrieval_top_score`) ⇒ hiệu chỉnh lại ngưỡng được về sau.

**Vì sao mẫu số tỉ lệ tích cực là "số lượt có đánh giá"? Tính trên tổng lượt thì bóp méo theo hướng nào?**
- Đa số khách không bấm nút nào. Chia cho tổng lượt thì con số bị **kéo về 0** theo tỉ lệ người chịu
  bấm: 90/100 khen trên 1.000 lượt thành 9% — đo độ lười bấm, không đo chất lượng.
- Ngược lại, nếu ai đó lấy "không bấm = hài lòng" thì con số **phồng về 100%** — cũng vô nghĩa.
- Đúng: `tích cực / có đánh giá`, và báo kèm `có đánh giá / tổng lượt` (độ phủ của nhãn) để người đọc
  biết con số dựa trên bao nhiêu mẫu. API trả cả tử số và mẫu số. Test:
  `test_ty_le_tich_cuc_chia_cho_so_luot_co_danh_gia` (0,5 chứ không phải 0,1); kiểm ngược đỏ.

**4 lý do khác nhau ở đâu? (1) NOT_COVERED và (3) LOW_CONFIDENCE phân biệt thế nào?**
- (2) OUT_OF_SCOPE_DATA và (4) SAFETY_PROBE nhận ra từ **câu hỏi**, trước khi truy hồi.
- (1) và (3) đều là "đã truy hồi mà không trả lời được". Khác ở **bằng chứng**:
  - (1) là bằng chứng **vắng mặt** — không đoạn nào đủ gần; mô hình đọc đoạn rồi nói không đoạn nào
    liên quan; câu trả lời không trích đoạn nào; hoặc câu trả lời chỉ nói "chưa có thông tin".
  - (3) là **thất bại kiểm chứng** — mô hình CÓ trả lời, CÓ trích đoạn, nhưng hậu kiểm không thấy câu đó
    nằm trong đoạn.
- Ranh giới máy kiểm được: **có câu mang thông tin kèm trích dẫn hay không**.
- Ở cấu hình ship, (3) không phát sinh: cổng bám nguồn tắt vì đo cho thấy nó chỉ làm mất câu đúng.
- Đặc tả UC023 ghi "điểm dưới ngưỡng ⇒ độ tin cậy thấp", UC025 ghi "không đoạn nào vượt sàn ⇒ chưa có
  trong tài liệu" — theo UC025 (UC sở hữu quyết định), ghi ở ADR-0029.

## 5. Câu phản biện kiểu hội đồng

1. *"Regex thì người ta viết lại câu là lọt."* — Đúng, và đó là chủ ý: luật dùng để **dán nhãn đúng lý
   do và thoát sớm** (0 nhúng, 0 LLM), không phải lớp bảo vệ dữ liệu. Câu dò lọt luật đi vào RAG — kho
   không chứa dữ liệu khách nào, LLM không có gì để lộ. Lớp bảo vệ thật là RLS + ai-service không nối
   bảng nghiệp vụ (ADR-0002).
2. *"30 câu và luật do cùng một người viết — có thiên vị không?"* — Có rủi ro đó. Giảm bằng: khoá hash 30
   câu trước khi viết luật; đo báo nhầm trên hai tập KHÔNG do mình viết cho luật (100 câu bộ vàng, 200
   câu người thật của Dev B); báo trung thực một lần báo nhầm ở lần đo đầu và việc sửa luật sau đó.
3. *"Bộ vàng chỉ có 12 câu nên từ chối — chọn ngưỡng trên 12 câu có đáng tin?"* — Không đủ để báo một
   con số chính xác; đủ để thấy **hình dạng** đường cong và chọn vùng ngưỡng. Mở rộng bộ vàng ở Ngày 13.
4. *"Khoá ngoại thì sao lại rò tenant được?"* — Postgres kiểm khoá ngoại bằng quyền hệ thống, không qua
   RLS. Test `test_khoa_ngoai_khong_chiu_rls` chứng minh `INSERT … VALUES` từ tenant B trỏ vào lượt của A
   **lọt**. Vì vậy repository đi qua `SELECT` (chịu RLS).
5. *"LLM chấm LLM thì có đáng tin?"* — Chỉ là MỘT trong bảy tín hiệu, lấy mẫu 5%, tự khai độ chắc, dưới
   0,7 thì bỏ. Nhãn người (khách, nhân viên) và tín hiệu rẻ 100% lượt vẫn là chính.

6. *"Ngưỡng bằng 0 thì sao gọi là 'chọn từ đường cong'?"* — Đường cong CHÍNH là câu trả lời: sàn cosine
   0–0,42 cho cùng kết quả (câu có đáp án thấp nhất 0,421, câu ngoài kho cao nhất 0,650), mọi ngưỡng bám
   nguồn > 0 mất ≥ 4 câu đúng. Luật chọn viết trước khi chạy chọn 0. Cải thiện F1 0,455 → 0,615 và độ phủ
   từ chối 0,417 → 1,000 đến từ hai luật cấu trúc, không từ ngưỡng nào — và đó là phát hiện đáng báo.
7. *"30/30 có thật không?"* — Lượt đầu, độc lập: 29/30. Sau đó sửa (luật, rồi lời nhắc) vì thấy lỗi trên
   chính 30 câu ⇒ 4/4 lượt 30/30 nhưng không còn độc lập. Báo cả hai, kèm toàn bộ lịch sử 11 lượt.

## 6. Số đo và ý nghĩa

Chi tiết: [báo cáo Ngày 10](../report/uc025-uc027-ngay10-2026-10-09.md).

| Đo gì | Kết quả | Nghĩa |
|---|---|---|
| Luật trước truy hồi trên 30 câu | 18/18 đúng lý do, 0 LLM | câu dò/câu đơn hàng thoát ở 0 ms |
| Báo nhầm của luật | 0/100 bộ vàng · 0/200 người thật (sau 1 lần sửa) | không chặn câu khách hỏi bình thường |
| F1 hành vi từ chối (bộ vàng) | 0,455 (Ngày 9) → **0,615**; độ phủ 0,417 → **1,000**; mất câu đúng **0** | 12/12 câu nên từ chối đều bị từ chối |
| Cosine câu có đáp án / ngoài kho | min 0,421 / max 0,650 | sàn cosine vô dụng với bge-m3 trên kho này ⇒ ship 0 |
| Cổng bám nguồn 0,1 | mất 4 câu đúng, thêm 0 câu từ chối đúng | ship 0 (tắt) |
| "Từ chối nhầm" (FP) | 15/15 là truy hồi trượt | nút thắt là recall@5 (74/100), việc của Ngày 13 |
| **30 câu nghiệm thu** | lượt độc lập **29/30**; sau sửa **4/4 lượt 30/30** | cổng ra Ngày 10 đạt — có ghi chú độc lập |
| Lời nhắc mới, UC023 | trả lời đúng 74 → 73/100 (mất G112) | cái giá của lời nhắc khắt khe hơn |
| `generate_ms` | trung vị 1.148 ms · p95 1.515 ms | trong ngân sách 2.500 ms |

## 7. Phần AI làm — khai trung thực

- Toàn bộ code, test, ADR-0029/0030, nháp hợp đồng và ghi chú này do Claude viết (theo chốt 05/10).
- **30 câu ngoài phạm vi do AI viết**, khoá sha256 lúc 23:19 08/10 trước khi viết luật.
- Luật regex do AI viết sau khi đã thấy 30 câu — báo nhầm đo trên hai tập độc lập (mục 5, câu 2).
- Câu kiểm "cách làm" trong `test_tu_choi.py` viết SAU luật — là bộ hồi quy, không phải phép đo độc lập.
- Ba lần vá luật "không phải câu trả lời" và lần sửa lời nhắc đều do AI làm sau khi thấy lỗi trên tập 30
  câu; mỗi lần sửa luật đều kiểm trên bộ vàng trước khi chạy lại.

## 8. Ba câu tự kiểm

1. Một câu trả lời trích `[1]` mà groundedness 0,3 bị từ chối với lý do nào? Còn câu không có `[n]` nào?
2. Vì sao bộ chấm tự động không chấm lại lượt nó "không chắc" ở chu kỳ sau?
3. Tenant B gửi `POST /v1/ai/feedback` với `interaction_id` của tenant A — đi qua những dòng code nào, và
   phản hồi là gì?
