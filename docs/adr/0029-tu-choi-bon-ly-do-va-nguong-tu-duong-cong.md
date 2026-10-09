# ADR-0029 — Từ chối UC025: bốn lý do sinh ở bốn chỗ cố định; ngưỡng chọn từ đường cong trên bộ vàng, nghiệm thu trên 30 câu riêng

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-09
- **Làn sở hữu:** Track B (module AI)
- **Quan hệ:** đặc tả UC025 (và UC023 mục ngoại lệ) · kế hoạch Ngày 10 · số liệu ở
  [`docs/report/uc025-uc027-ngay10-2026-10-09.md`](../report/uc025-uc027-ngay10-2026-10-09.md) ·
  liên quan [ADR-0028](0028-llm-gemini-flash-lite-client-trung-lap.md),
  [ADR-0030](0030-ghi-luot-dong-bo-va-bo-cham-tu-dong-mau-5.md)

## Bối cảnh

Đến Ngày 9, nhánh tri thức chỉ có hai lối từ chối, cả hai mang nhãn `NOT_COVERED`: sàn cosine 0,25
(lấy theo kế hoạch) và LLM tự trả mã `KHONG_DU_CAN_CU`. Ba vấn đề:

1. **Đặc tả UC025 có bốn lý do** (`NOT_COVERED`, `OUT_OF_SCOPE_DATA`, `LOW_CONFIDENCE`, `SAFETY_PROBE` —
   CHECK của V204) và bắt phân biệt chúng **tại chỗ sinh**, vì mỗi lý do dẫn tới một hành động khác
   phía doanh nghiệp. Dồn hết vào `NOT_COVERED` làm danh sách khoảng trống tri thức lẫn cả câu dò dữ
   liệu và câu hỏi về đơn hàng — thứ thêm tài liệu không bao giờ lấp được.
2. **Sàn 0,25 gần như không chặn gì:** câu ngoài phạm vi vẫn có cosine 0,35–0,46 với bge-m3 (đo 08/10);
   câu gần lĩnh vực như G004 "thu cũ đổi mới tủ lạnh" lên tới 0,63 — cao hơn nhiều câu có đáp án.
3. **Mô hình không phải lúc nào cũng ghi đúng mã:** G004 (08/10) và G001 (09/10, câu đầu của phép đo)
   — mô hình viết "Dạ cửa hàng chưa có thông tin về…" thay vì `KHONG_DU_CAN_CU`, không kèm trích dẫn nào,
   và lượt bị tính là "đã trả lời".

Kế hoạch Ngày 10 yêu cầu: ngưỡng chọn **từ đường cong hiệu chỉnh** có baseline "không ngưỡng" để so,
và **30/30** câu ngoài phạm vi trả rỗng đúng.

## Các phương án đã cân nhắc

**Ai quyết lý do:**

| Phương án | Ưu | Nhược |
|---|---|---|
| A. LLM tự phân loại lý do trong cùng lời nhắc | Một chỗ, hiểu diễn đạt tự do | Câu dò/câu đơn hàng vẫn tốn một lượt LLM; không tất định; mô hình đã không tuân mã `KHONG_DU_CAN_CU` (G001, G004) |
| B. Một lý do chung `NOT_COVERED` | Đơn giản | Trái đặc tả; khoảng trống tri thức bị nhiễu |
| C. **Mỗi lý do sinh ở đúng một chỗ trong đường ống** | Tất định, kiểm được bằng máy; hai lý do nhận ra từ câu hỏi thoát sớm (0 nhúng, 0 LLM) | Hai bộ luật regex phải bảo trì; diễn đạt lạ lọt luật |

**Nhận ra `OUT_OF_SCOPE_DATA` và `SAFETY_PROBE`:** router ML (ai-classify) — taxonomy 7 nhánh không có
lớp này, và ai-classify chưa chạy trên máy dev; LLM — tốn lượt; **luật regex** (Rule → ML → LLM).

**Chọn ngưỡng:** (i) giữ số của kế hoạch (0,25); (ii) chỉnh trên chính 30 câu nghiệm thu — quá khớp;
(iii) **chỉnh trên bộ vàng (112 câu, 12 câu nên từ chối), nghiệm thu trên 30 câu riêng**.

## Quyết định

Bốn lý do sinh ở bốn chỗ cố định của `RagAnswerer`:

| Lý do | Chỗ sinh | Gọi LLM |
|---|---|---|
| `SAFETY_PROBE` (+ cờ `CROSS_TENANT_PROBE` / `INTERNAL_DATA_PROBE`) | luật, trước truy hồi; nhóm `DATA_PROBING` dùng lại của guardrails | không |
| `OUT_OF_SCOPE_DATA` (+ `handoff`) | luật, trước truy hồi — chỉ câu về MỘT đơn/phiếu/tài khoản/lịch hẹn/mã tồn kho cụ thể | không |
| `NOT_COVERED` | (a) cosine cao nhất < sàn; (b) LLM trả `KHONG_DU_CAN_CU`; (c) câu trả lời **0 trích dẫn hợp lệ**; (d) câu trả lời **không phải câu trả lời** — có câu "chưa có thông tin" và 0 câu mang thông tin (câu có trích dẫn) hoặc 0 câu bám nguồn (`hau_kiem.khong_phai_tra_loi`) | (a) không · (b)(c)(d) có — **huỷ** câu đã sinh |
| `LOW_CONFIDENCE` | có trích dẫn nhưng `groundedness_score` < ngưỡng bám nguồn — **huỷ** câu đã sinh | có |

**Ngưỡng ship: sàn toàn tập 0, ngưỡng bám nguồn 0 (cổng tắt)** — chọn bằng luật định trước trên bộ vàng
(mục Lập luận). Cơ chế hai ngưỡng giữ trong code và cấu hình (`RAG_SAN_TOAN_TAP`, `RAG_NGUONG_BAM_NGUON`);
sàn từng đoạn 0,15 vẫn chặn đoạn quá xa. Với ngưỡng 0, `LOW_CONFIDENCE` không phát sinh ở cấu hình ship.

Lời nhắc (`rag/generate/loi_nhac.py`) thêm hai câu: câu chào / câu mời / câu "chưa có thông tin" KHÔNG
ghi số trích dẫn; không đoạn nào giúp được thì CHỈ ghi `KHONG_DU_CAN_CU`.

Lượt từ chối `NOT_COVERED`/`LOW_CONFIDENCE` thứ 2 liên tiếp trong cùng hội thoại ⇒ `handoff = true`
(UC025 luồng phụ 3.3); `SAFETY_PROBE` không bao giờ chuyển giao và không giải thích lý do.

## Lập luận

- **Ranh giới (1)/(3) là có trích dẫn hay không** — máy kiểm được, không cần hiểu nghĩa. `NOT_COVERED`
  là bằng chứng *vắng mặt*; `LOW_CONFIDENCE` là *thất bại kiểm chứng*. Luật (c) bắt đúng lớp lỗi
  G001/G004 mà không dò câu chữ "chưa có thông tin" — trích dẫn là bắt buộc (thí nghiệm E6), câu trả lời
  không trích gì thì theo định nghĩa không dựa vào tài liệu.
- **Đặc tả UC023 lệch UC025:** UC023 ghi "điểm dưới ngưỡng ⇒ độ tin cậy thấp", UC025 ghi "không đoạn
  nào vượt sàn ⇒ chưa có trong tài liệu". Theo UC025 — UC sở hữu quyết định từ chối, và khớp kế hoạch.
- **Luật nghiêng về bỏ sót:** bắt nhầm = từ chối một câu kho trả lời được; bỏ sót = câu đi tiếp vào RAG,
  mà kho có sẵn chỉ dẫn ("tình trạng còn hàng xem trên website", "theo dõi đơn ở mục Đơn hàng của tôi")
  nên vẫn nhận câu trả lời đúng. Vì vậy luật đòi dấu hiệu CỤ THỂ (mã số, "của em … giao tới đâu", "kiểm
  tra **giúp** em"), không bắt câu hỏi cách làm.
- **Luật chọn ngưỡng viết vào script TRƯỚC khi chạy** (`tests/eval/hieu_chinh_tu_choi.py`): F1 của hành
  vi từ chối cao nhất trên bộ vàng; hoà thì mất ít câu trả lời đúng nhất; vẫn hoà thì ngưỡng nhỏ hơn.
  Hai ngưỡng chỉ quyết "dừng trước LLM" và "huỷ sau LLM", không đổi những gì LLM sinh ⇒ quét lưới
  offline trên điểm thô của MỘT lượt chạy baseline là đúng, trừ độ ngẫu nhiên của LLM. 30 câu nghiệm
  thu khoá sha256 (`a1b6fd97…`, 23:19 08/10) trước khi viết dòng luật nào và không dùng để chọn ngưỡng.

**Số đo** ([báo cáo Ngày 10](../report/uc025-uc027-ngay10-2026-10-09.md)) — hành vi từ chối trên bộ vàng:

| Cấu hình | TP/FP/FN/TN | chính xác | độ phủ | F1 | mất câu đúng |
|---|---|---|---|---|---|
| không ngưỡng (Ngày 9) | 5/5/7/95 | 0,500 | 0,417 | 0,455 | 0 |
| + luật (c) "0 trích dẫn" | 11/13/1/87 | 0,458 | 0,917 | 0,611 | 0 |
| + luật (d) "không phải câu trả lời" — **ship** | 12/15/0/85 | 0,444 | **1,000** | **0,615** | **0** |
| + bám nguồn 0,1 (tốt nhất trong các ngưỡng > 0) | 12/19/0/81 | 0,387 | 1,000 | 0,558 | 4 |

- Sàn cosine: câu có đáp án thấp nhất 0,421, câu ngoài kho cao nhất 0,650 ⇒ mọi sàn 0–0,42 cho cùng kết
  quả, sàn cao hơn chỉ mất câu đúng. Luật chọn lấy số nhỏ nhất ⇒ 0.
- Cổng bám nguồn: mọi ngưỡng > 0 mất ≥ 4 câu đúng (groundedness từ vựng chấm oan câu diễn đạt lại) mà
  không thêm câu từ chối đúng nào ⇒ 0.
- 15/15 câu "từ chối nhầm" là truy hồi trượt (đoạn đúng không trong top-5) — nút thắt là recall@5.
- **30 câu nghiệm thu:** lượt độc lập đầu tiên **29/30** (N005). Ba lần vá luật (d) vẫn lọt biến thể mới
  của cùng lớp lỗi ⇒ sửa lời nhắc tại gốc ⇒ **4/4 lượt 30/30**, đúng cả lý do — sau sửa, không độc lập.

## Đánh đổi

- **Regex lọt khi diễn đạt lạ.** Chấp nhận vì luật là để *dán nhãn đúng và thoát sớm*, không phải lớp
  bảo vệ dữ liệu: câu dò lọt luật đi vào RAG, kho không chứa dữ liệu khách nào, LLM không có gì để lộ.
  Lớp bảo vệ thật là RLS và việc ai-service không nối bảng nghiệp vụ (ADR-0002).
- **30 câu và luật cùng một tác giả (AI).** Rủi ro thiên vị; giảm bằng khoá hash trước, đo báo nhầm trên
  hai tập không viết cho luật (100 câu bộ vàng có đáp án, 200 câu người thật của UC022). Lần đo đầu có
  1/200 báo nhầm ("cách import danh sách khách hàng…") — đã sửa luật; con số 0/200 sau sửa không còn
  độc lập.
- **Chỉ 12 câu nên-từ-chối trong bộ vàng** — đủ thấy hình dạng đường cong, chưa đủ một tỉ lệ có khoảng
  tin cậy hẹp. Mở rộng ở Ngày 13.
- **Huỷ câu đã sinh tốn một lượt LLM** (đã trả tiền). Đổi lại không trả một câu không xác nhận được.
- **Ship ngưỡng 0 nghĩa là KHÔNG có lớp chặn trước LLM theo độ liên quan** — mọi câu qua được luật đều tốn
  một lượt LLM; KPI "≥ 55% lượt không gọi LLM" không được sàn giúp gì trên kho này.
- **`LOW_CONFIDENCE` không phát sinh ở cấu hình ship** (cổng tắt). Lý do vẫn có trong code, CHECK của
  V204 và danh sách khoảng trống; bật lại khi có phép đo bám nguồn tốt hơn phép đo từ vựng.
- **Lời nhắc khắt khe hơn làm mất 1/100 câu trả lời đúng** (G112: trả mã từ chối dù đoạn đúng đã có).
  Đổi lại lớp lỗi "chưa có thông tin + câu mời + trích dẫn" biến mất ở 4/4 lượt.
- **Luật (d) dò cụm "chưa có / không có thông tin" trên đầu ra** — vẫn là regex; mô hình diễn đạt khác
  hẳn thì lọt. Lời nhắc là lớp chính, luật (d) là lưới đỡ.
- **30/30 sau sửa không độc lập**: mọi lần sửa đều do thấy lỗi trên chính 30 câu đó. Mỗi lần sửa luật đều
  kiểm trên bộ vàng trước (0 câu đúng bị bắt), nhưng con số nghiệm thu độc lập duy nhất là 29/30.
- **Groundedness là phép đo từ vựng:** câu đúng diễn đạt lại (rõ nhất: dịch từ tài liệu tiếng Anh, G061)
  bị điểm thấp oan ⇒ ngưỡng cao làm mất câu đúng. Đường cong cho thấy cái giá này bằng số.
- **"Từ chối lần 2 thì chuyển giao" cần đọc `ai_interactions`** — một truy vấn trên lối từ chối (không
  trên lối trả lời); đọc hỏng thì coi như chưa từ chối lần nào.

## Hệ quả

- **Cấu hình:** `RAG_SAN_TOAN_TAP=0`, `RAG_NGUONG_BAM_NGUON=0`, `RAG_TU_CHOI_LAP_LAI_CHUYEN_GIAO=2`.
- **UC023:** lời nhắc đổi hai câu — eval Ngày 13 đo lại trên bộ vàng mở rộng.
- **Giao ước:** `ChatResponse.refusal_reason`, và `handoff = true` ở nhánh `RAG` — nháp
  [`uc025-uc027-tu-choi-danh-gia.md`](../contracts/uc025-uc027-tu-choi-danh-gia.md). `WidgetService` đã
  xử lý tổ hợp `handoff + refused` (lý do `NO_GROUNDING`) — java-core không phải sửa.
- **Telemetry:** `ai_refusals_total{reason}`; mỗi lượt từ chối ghi lý do + điểm truy hồi cao nhất (kể cả
  dưới sàn) + groundedness vào `ai_interactions` — số liệu gốc để hiệu chỉnh lại sau.
- **Báo cáo:** chương 3 (bảng bốn lý do × chỗ sinh); chương 5 (đường cong, baseline, 30/30).
