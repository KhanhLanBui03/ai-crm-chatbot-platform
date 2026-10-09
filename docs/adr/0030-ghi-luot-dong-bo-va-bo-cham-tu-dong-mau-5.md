# ADR-0030 — Ghi `ai_interactions` đồng bộ mỗi lượt; bộ chấm tự động lấy mẫu 5% qua hàm `SECURITY DEFINER` thứ hai

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-08
- **Làn sở hữu:** Track B (module AI)
- **Quan hệ:** mở rộng [ADR-0024](0024-nap-tai-lieu-commit-theo-chang-chong-trung-va-quet-job-ket.md)
  (hàm DEFINER thứ nhất, `knowledge.tim_job_ket`) · V212 · đặc tả UC022 bước 9, UC027 bước 6–7 ·
  liên quan [ADR-0029](0029-tu-choi-bon-ly-do-va-nguong-tu-duong-cong.md)

## Bối cảnh

Đến Ngày 9, `run_turn` gọi `LogTurnRecorder` — lượt chat chỉ ra **log**, `ai.ai_interactions` chưa có
dòng nào (TODO UC022 bước 9–10). Ngày 10 cần bảng đó cho ba việc:

1. **UC027 — gắn đánh giá:** `ai_feedback.ai_interaction_id` là khoá ngoại; không có dòng thì không có
   gì để đánh giá, và java-core không có id nào để gửi lại.
2. **UC025 — khoảng trống tri thức:** đặc tả chốt là *truy vấn gộp* trên các lượt từ chối, không bảng
   riêng; luồng phụ 3.3 (từ chối lặp lại ⇒ chuyển giao) cần lịch sử của hội thoại.
3. **UC027 — tín hiệu rẻ 100% lượt:** tỉ lệ từ chối, suy giảm, chuyển giao, độ phủ trích dẫn.

Bộ chấm tự động (UC027 bước 6, "LLM chấm điểm lấy mẫu 5%") chạy nền trong worker, phải thấy lượt của
**mọi** tenant — mà `ai_app` chịu RLS FORCE và ai-service không biết danh sách tenant (`platform.tenants`
của Track A). Đúng bài toán của bộ quét job kẹt (ADR-0024). `.claude/rules/database.md`: thêm hàm
DEFINER thứ hai là quyết định kiến trúc, phải có ADR.

## Các phương án đã cân nhắc

**Ghi lượt:**

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Bất đồng bộ — task nền, hoặc qua Kafka `ai.turn.completed` rồi consumer ghi | Không cộng độ trễ vào lượt chat | Đánh giá có thể tới TRƯỚC dòng lượt ⇒ 404 giả; UC039 chưa có consumer nào |
| B. Đồng bộ, lỗi ghi ⇒ ném lên thành 500 | Không bao giờ mất dòng mà không biết | Đổi một câu trả lời ĐÚNG thành lỗi chỉ vì telemetry hỏng |
| C. **Đồng bộ trong `finally`, lỗi ghi ⇒ log ERROR + `ai_turn_record_failures_total`** | Dòng có ngay khi java-core nhận phản hồi; lượt hỏng vẫn được ghi | Mất dòng là có thể (thấy được trên metric) |

**Bộ chấm nhìn xuyên tenant:**

| Phương án | Ưu | Nhược |
|---|---|---|
| D. Hỏi java-core danh sách tenant rồi quét từng tenant | Không thêm lỗ RLS | Thêm endpoint liên làn; N tenant = N truy vấn mỗi chu kỳ |
| E. Role riêng có `BYPASSRLS` cho worker | Một truy vấn | Cả worker nhìn xuyên tenant — lỗ rộng nhất có thể |
| F. **Hàm `SECURITY DEFINER` chỉ trả định danh** — như `knowledge.tim_job_ket` | Lỗ hẹp, đã có mẫu và test; một truy vấn | Lỗ thứ hai trong RLS; cùng giới hạn RDS |

**Chọn mẫu 5%:** `random()` mỗi lần quét, hay **tất định theo `md5(id)`**.

## Quyết định

Ghi `ai.ai_interactions` **đồng bộ** trong `finally` của `run_turn` (`DbTurnRecorder`), lỗi ghi không
làm hỏng lượt chat; thêm ba cột `llm_called`, `is_degraded`, `is_handoff` (V212); bộ chấm tự động lấy
mẫu **tất định 5%** qua hàm `SECURITY DEFINER` thứ hai `ai.tim_luot_can_cham`, chỉ trả
`(tenant_id, interaction_id, created_at)`.

## Lập luận

- **C thắng A** vì đánh giá của khách tới ngay sau câu trả lời — dòng lượt phải có trước. **C thắng B**
  vì câu trả lời đã sinh, đã hậu kiểm là thứ khách cần; telemetry hỏng không được đổi nó thành lỗi.
  Chi phí của C: một `INSERT` vài ms trong ngân sách 4.000 ms.
- `interaction_id` sinh ở `run_turn` (UUID phía ứng dụng) để trả được trong `ChatResponse` mà không đợi
  `RETURNING` từ một `finally`.
- **Ba cột không suy ra được:** lượt suy giảm vì mạch mở mang `model_name` của LLM mà không gọi; lượt
  quá hạn có gọi mà 0 token (`llm_called`). Lượt suy giảm vẫn `is_answered = true` (`is_degraded`). Từ
  Ngày 10 nhánh `RAG` cũng chuyển giao (`is_handoff`, ADR-0029) — `branch` không còn đủ.
- **F thắng D và E** vì giữ đúng bốn chốt đã kiểm của hàm thứ nhất: chỉ trả định danh; không SQL động
  (một mốc, một tỉ lệ, một trần kẹp 1..200); `search_path = pg_catalog, pg_temp`; `REVOKE ALL FROM
  PUBLIC` + `GRANT EXECUTE` cho `ai_app`. Đọc nội dung lượt, các đoạn được trích, rồi ghi `ai_feedback`
  (`AUTO_EVAL`) đều chạy trong phiên đã gắn đúng tenant, dưới RLS. Test
  `test_ham_cham_chi_ai_app_goi_duoc_va_ghim_search_path` khoá cả bốn chốt.
- **Mẫu tất định** `('x' || substr(md5(id::text),1,8))::bit(32)::bigint % 10000 < tỉ_lệ × 10000`: cùng
  một lượt luôn thuộc hoặc không thuộc mẫu ⇒ đếm được "đã chấm bao nhiêu %", chạy lại không chọn tập
  khác. `random()` mỗi lần quét chọn một tập khác, tổng số lượt bị chấm trôi dần lên quá 5%. Bản Python
  `mau_cham()` cùng công thức — test tích hợp kiểm hai bên ra đúng một tập.
- Chỉ chấm lượt `RAG` đã trả lời, có gọi LLM, không suy giảm: lượt từ chối / mẫu câu / suy giảm không có
  câu sinh nào để giám khảo đánh giá — chúng đã có tín hiệu rẻ.
- **Mốc quét** giữ giữa các chu kỳ để mỗi lượt chỉ được XÉT một lần (lượt giám khảo không chắc — không
  ghi gì, UC027 luồng phụ 6.1 — không bị chấm lại mỗi 15 phút và đốt hạn mức). Lô đầy ⇒ mốc =
  `created_at` của lượt cuối trong lô; lô chưa đầy ⇒ mốc = giờ **CSDL** lúc quét (cùng đồng hồ với
  `created_at`). Bản đầu dời mốc thẳng tới lúc quét — test
  `test_lo_day_thi_moc_tiep_khong_nhay_qua_ung_vien_con_lai` bắt được: trần 50/lô mà có 60 ứng viên
  thì 10 lượt bị bỏ rơi vĩnh viễn.
- Giám khảo có **mạch và hạn chót riêng** (`service.tao_giam_khao`, 15 s): giám khảo làm mở mạch thì
  khách không phải nhận câu suy giảm vì nó. Chỉ chạy khi `LLM_MODE=remote` — giám khảo giả cho nhãn
  giả, làm bẩn đúng tỉ lệ cần đo.

## Đánh đổi

- **Hai lỗ có chủ đích trong RLS** thay vì một. Giữ hẹp như nhau, cùng test, nhưng mỗi hàm DEFINER là
  một chỗ phải soát lại khi sửa lược đồ `ai_interactions`.
- **Cùng giới hạn RDS với V211:** hàm chỉ vượt RLS khi chủ hàm có `BYPASSRLS` — `[CẦN XÁC NHẬN]` Ngày
  18. Không có thì hàm ném 42501 (hỏng ồn ào), bộ chấm ngừng, lượt chat không ảnh hưởng.
- **Mất dòng lượt là có thể** (phương án C): khi đó `interaction_id` trong phản hồi trỏ vào hư không và
  đánh giá của lượt đó nhận 404. Đổi lại lượt chat không bao giờ hỏng vì telemetry.
- **Lượt cuối của lô đầy được xét lại một lần** (mốc dùng `>=`): nếu giám khảo không chắc ở lần đầu, nó
  tốn thêm một lượt LLM. Chấp nhận — đổi lấy không lượt nào bị bỏ.
- **Khởi động lại worker nhìn lại 1 ngày**: vài lượt không chắc được chấm lại sau mỗi lần khởi động.
- **5% của lưu lượng đồ án là ít:** với vài trăm lượt/ngày, mẫu chỉ vài chục nhãn máy/ngày — đủ minh
  hoạ, chưa đủ một khoảng tin cậy hẹp. Tỉ lệ là cấu hình (`CHAM_TU_DONG_TY_LE`).
- **Đụng file chung của Dev B** (`orchestrator/turn.py`: thêm `interaction_id`, `safety_flag`, `handoff`
  vào `KnowledgeAnswer`/`TurnRecord`) — chờ Dev B duyệt khi review PR.

## Hệ quả

- **Lược đồ:** V212 — ba cột + một hàm, không bảng mới; `docs/erd-mermaid.md` cập nhật.
- **Giao ước:** `ChatResponse` thêm `interaction_id`, `refusal_reason`; `FeedbackRequest` thêm ba trường;
  `GET /v1/ai/quality` mới — nháp [`uc025-uc027-tu-choi-danh-gia.md`](../contracts/uc025-uc027-tu-choi-danh-gia.md),
  chưa vá `docs/openapi/` (luật 6: báo Dev B trước).
- **Vận hành:** worker thêm vòng nền thứ hai (`cham-tu-dong`) cạnh bộ quét job kẹt; metric mới
  `ai_turn_record_failures_total`, `ai_refusals_total{reason}`, `ai_auto_eval_total{outcome}`.
- **UC039 (Dev B):** KPI "≥ 55% lượt không gọi LLM" đo được bằng SQL; `ai.turn.completed` khi làm chỉ
  cần chép cột đã có.
- **Báo cáo:** chương 3 (thiết kế ghi lượt, hai lỗ RLS có chủ đích); chương 5 (bảng 7 tín hiệu × tần suất).
