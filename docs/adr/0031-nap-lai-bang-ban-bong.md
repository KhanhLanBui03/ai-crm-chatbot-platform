# ADR-0031 — Nạp lại tài liệu bằng bản ghi bóng: đổi bản trong một transaction, 0 giây kho trống

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-09
- **Làn sở hữu:** Track B (module AI)
- **Quan hệ:** đặc tả UC020 (nạp lại, gỡ, luồng phụ 5.1, 6.1, 7.1, 7.2) · kế hoạch Ngày 11 · V213 ·
  dựa trên [ADR-0024](0024-nap-tai-lieu-commit-theo-chang-chong-trung-va-quet-job-ket.md) (máy trạng
  thái nạp, bộ quét job kẹt)

## Bối cảnh

Kế hoạch Ngày 11: *"Reindex — GIỮ NGUYÊN bản cũ tới khi bản mới nạp xong mới chuyển đổi. **0 giây kho
tri thức trống.**"* Đường nạp của UC019 (ADR-0024) không làm được điều đó nếu chạy lại trên chính dòng
tài liệu:

- bước nhận việc (`nhan_xu_ly`) chuyển dòng sang `PROCESSING` **và xoá sạch đoạn cũ** để lượt thử lại
  bắt đầu từ trang trắng;
- truy hồi (`hybrid.py`) chỉ lấy đoạn của tài liệu `READY`.

Nạp lại tại chỗ ⇒ tài liệu biến mất khỏi kho suốt vài giây tới vài phút. Ràng buộc thêm:

- `uq_doc_title_version (tenant, title, version)`; `attempt_count` vừa là trần thử lại vừa là **thẻ sở
  hữu** của lượt nạp — không đặt lại về 0 được mà không mở đường cho lượt cũ ghi đè lượt mới.
- Bản tin `crm.kb.document.uploaded` là của java-core; ai-service không phát vào topic đó.
- Đổi mô hình nhúng ⇒ nạp lại TOÀN kho của tenant, chạy nền (UC020 luồng phụ 6.1).

## Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| A. Nạp lại tại chỗ, chấp nhận khoảng trống | Không đổi gì | Trái yêu cầu kế hoạch; khách hỏi đúng lúc nạp thì bị từ chối |
| B. **Lớp đoạn** — đoạn mang số lượt nạp, tài liệu giữ "lớp đang phục vụ", truy hồi lọc theo lớp | `id` tài liệu không đổi | Sửa câu SQL truy hồi lõi (đã đo E3); đổi `uq_chunk_index`; tách trần thử lại khỏi thẻ sở hữu; sửa cả ba đường xoá đoạn; tài liệu hiện `PROCESSING`/`FAILED` mà vẫn được truy hồi — khó giải thích trên giao diện |
| C. **Bản ghi bóng** — nạp lại tạo một DÒNG MỚI cùng tệp (`version + 1`, `replaces_document_id` = dòng cũ), đi qua đúng đường nạp có sẵn; khi bản bóng `READY` thì cùng transaction xoá đoạn bản cũ và chuyển nó `ARCHIVED` | Truy hồi, máy trạng thái nạp, trần thử lại, thẻ sở hữu **không đổi gì**; nạp lại hỏng thì bản cũ vẫn `READY` nguyên vẹn | `id` tài liệu đổi sau nạp lại; danh sách có hai dòng cùng tiêu đề trong lúc nạp; version tăng dù nội dung không đổi |

**Ai kích hoạt worker cho bản bóng:** (i) ai-service phát vào topic của java-core — sai chủ sở hữu topic;
(ii) java-core phát sau khi gọi ai-service — kéo thêm việc liên làn; (iii) **bộ quét job kẹt nhặt bản
bóng ngay** (`tim_job_ket` thêm một điều kiện).

## Quyết định

Phương án **C** với kích hoạt **(iii)**.

| Thao tác | Hành vi |
|---|---|
| Nạp lại một tài liệu | Chỉ khi `READY`. Khoá dòng, tạo bản bóng `PENDING` (`tao_ban_bong`). Bộ quét nhặt trong ≤ 1 chu kỳ (60 s), worker nạp như tài liệu mới |
| Đổi bản | `document_repository.hoan_tat`: bản bóng `READY` ⇒ CÙNG transaction xoá đoạn bản cũ, rồi `ARCHIVED` |
| Nạp lại toàn kho | Mọi tài liệu `READY` chưa có lượt nạp lại đang chạy ⇒ mỗi tài liệu một bản bóng, worker xử lý lần lượt (một job đồng thời, như UC019) |
| Gỡ khỏi chỉ mục | Khoá dòng; xoá đoạn TRƯỚC rồi `ARCHIVED`, cùng transaction (`xoa_khoi_chi_muc`). Hỏng ⇒ rollback, trạng thái giữ nguyên |
| Bận | `PENDING`/`PROCESSING`, hoặc đang có bản bóng chạy ⇒ 409 `DOCUMENT_BUSY` cho nạp lại, gỡ và sửa siêu dữ liệu |

`uq_doc_mot_luot_nap_lai` (chỉ mục duy nhất bộ phận trên `replaces_document_id` khi bản bóng còn
`PENDING`/`PROCESSING`) chặn hai lượt nạp lại chồng nhau ở tầng CSDL.

## Lập luận

- **Tính nguyên tử có sẵn từ MVCC:** truy hồi là MỘT câu SQL trên MỘT ảnh chụp. Đổi bản trong một
  transaction ⇒ câu truy hồi thấy trước-đổi (bản cũ + đoạn cũ) hoặc sau-đổi (bản mới + đoạn mới), không
  thấy trạng thái giữa. Không cần khoá đọc, không cần cờ "đang chuyển đổi".
- **C không chạm đường nóng.** Câu SQL truy hồi đã đo ở E3 (dense 0,800 · hybrid 0,740) và đã có 11 test
  kiểm ngược; B buộc sửa nó. Máy trạng thái nạp của ADR-0024 (thẻ sở hữu, trần thử lại, bộ quét) đã có
  test cho mọi đường hỏng; C dùng lại nguyên vẹn — bản bóng chỉ là "một tài liệu mới".
- **Hỏng an toàn:** bản bóng `FAILED` ⇒ bản cũ vẫn `READY` và vẫn phục vụ. Ở B, tài liệu hiện `FAILED`
  mà vẫn được truy hồi — trạng thái nói dối.
- **Version tăng khớp nghĩa đã có của cột:** V202 ghi "tải lại cùng tên thì tăng version, không đè bản
  cũ — câu trả lời đã sinh vẫn trích dẫn đúng bản cũ". Nạp lại là một bản chỉ mục mới; đặc tả UC020 luồng
  phụ 7.1 yêu cầu đúng điều đó: câu trả lời cũ giữ trích dẫn theo version đã dùng.
- **Không đếm hạn mức hai lần:** java-core đếm hạn mức bằng `usage_records` riêng lúc tải lên; bản bóng
  do ai-service tạo không chạm vào đó.
- **Bộ quét thay vì sự kiện:** bộ quét đã là lưới an toàn của mọi tài liệu `PENDING` (ADR-0024); thêm một
  điều kiện vào hàm DEFINER có sẵn rẻ hơn một topic mới hay một bước liên làn. Độ trễ ≤ 60 s chấp nhận
  được cho thao tác chạy nền.

## Đánh đổi

- **`id` tài liệu đổi sau mỗi lần nạp lại.** Giao diện đang mở SCR031 của bản cũ sẽ thấy nó `ARCHIVED`;
  phản hồi của nạp lại trả `document_id` mới (= `job_id` để xem tiến độ) và bản mới mang
  `replaces_document_id` để lần ngược.
- **Hai dòng cùng tiêu đề trong lúc nạp lại** (bản cũ `READY`, bản bóng `PENDING`/`PROCESSING`); bản cũ
  mang `reindex_document_id` để giao diện gộp.
- **Version tăng dù nội dung tệp không đổi** — "version" nghĩa là bản chỉ mục, không phải bản nội dung.
- **Bản bóng hỏng nằm lại `FAILED`** làm lịch sử; nạp lại lần nữa tạo bản bóng mới với version mới.
- **Chỉ nạp lại tài liệu `READY`.** Tài liệu `FAILED` lần đầu thì tải lên lại (UC018) — không có bản cũ nào
  cần giữ, và đặt lại `attempt_count` sẽ phá thẻ sở hữu.
- **≤ 60 s từ lúc yêu cầu tới lúc bắt đầu nạp** (chu kỳ bộ quét).
- **Đổi mô hình nhúng vẫn có khoảng trống ở phía TRUY VẤN:** truy hồi lọc đoạn theo mô hình của chính
  vector câu hỏi (rag-eval.md). Đổi `ai-embed` của API trước khi nạp lại xong là mọi đoạn cũ bị lọc khỏi
  kết quả. Quy trình đúng: worker nhúng bằng mô hình MỚI (`EMBED_URL` của worker trỏ bản mới), API giữ mô
  hình CŨ tới khi nạp lại toàn kho xong, rồi mới đổi `EMBED_URL` của API. Đây là quy trình vận hành,
  không phải code.

## Hệ quả

- **Lược đồ:** V213 — cột `replaces_document_id`, chỉ mục `uq_doc_mot_luot_nap_lai`, chỉ mục trigram
  `ix_doc_tim_kiem` (tìm không dấu SCR030), `tim_job_ket` thêm điều kiện bản bóng (giữ bốn chốt của V211).
- **Giao ước:** `POST /v1/documents/{id}/reindex` trả bản bóng (202); `POST /v1/ai/kb/reindex` trả số tài
  liệu đã xếp hàng; thêm `PATCH /v1/documents/{id}` — nháp `docs/contracts/uc020-quan-ly-kho.md`.
- **java-core (Track A):** proxy SCR030–SCR032 và ghi `platform.audit_logs` cho sửa / nạp lại / gỡ — chưa
  có, ai-service chỉ log có cấu trúc.
- **Chưa làm:** phát `ai.kb.document.indexed` — topic có trong `docs/events/README.md` nhưng chưa có lược đồ.
- **Báo cáo:** chương 3 (vì sao bản bóng thay vì lớp đoạn); chương 5 (phép thử "0 giây trống").
