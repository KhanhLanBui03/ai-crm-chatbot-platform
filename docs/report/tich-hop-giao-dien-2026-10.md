# Tích hợp giao diện 8 UC của Dev A — minh chứng đợt GD1–GD4

Kế hoạch và luật đợt: [`docs/plan/ke-hoach-tich-hop-giao-dien.md`](../plan/ke-hoach-tich-hop-giao-dien.md).
Thước đo: `docs/Dac-ta-UseCase-Module-AI.docx`. Hợp đồng đã đổi: [`docs/contracts/giao-dien-gd.md`](../contracts/giao-dien-gd.md).

Một UC chỉ tick khi đủ 4 điều: (a) luồng chính bấm được trên giao diện thật · (b) luồng phụ / mã lỗi
trong DoD đã thử · (c) compile / typecheck / test sạch · (d) có dòng minh chứng ở đây.

---

## GD1 — Kho tri thức: UC018 · UC019 · UC020 (24/10/2026 · chạy lại 10/11/2026)

**Nhánh** `feat/giao-dien-gd1-kho` (tách từ `e5cb8ff`). Kiểm bằng trình duyệt thật (Chrome không giao
diện, Playwright điều khiển — script ở scratchpad, không vào repo), `VITE_USE_MOCK=false`, mọi lời gọi
qua gateway `:8080`. Sau khi gộp `develop` đã đi lại đủ 16 cảnh — mục [Chạy lại sau khi gộp
`develop`](#chạy-lại-sau-khi-gộp-develop-10112026). Không chụp ảnh: người dùng chốt 10/11 lượt chạy lại
bằng trình duyệt tự động là đủ minh chứng.

| | UC018 | UC019 | UC020 |
|---|---|---|---|
| (a) luồng chính trên giao diện | ✅ | ✅ | ✅ |
| (b) luồng phụ, mã lỗi | ✅ 4.1 · 4.2 · 6.1 · 7.1 · 8.1 · 403 | ✅ 4.1 · hàng đợi chung · ngừng hỏi lại | ✅ 2.1 · 5.1 · 7 · 7.2 · 403 · 422 · 8 |
| (c) kiểm máy | ✅ | ✅ | ✅ |
| (d) minh chứng | ✅ | ✅ | ✅ |

UC020 bước 8: ngày 24/10 chỉ kiểm được phần **ghi** kiểm toán (bằng CSDL), vì màn xem thuộc UC040 (Dev B)
khi đó chưa có backend. Ngày 10/11, sau khi gộp `develop` có `AuditLogController`, đã kiểm cả màn **xem**
`/kiem-toan/nhat-ky` trên giao diện (cảnh 16).

### Môi trường

| Thành phần | Trạng thái |
|---|---|
| Hạ tầng | postgres · redis · kafka · zookeeper · rustfs — healthy; đủ 14 topic |
| Suy luận | ai-embed :8091 · ai-rerank :8082 · ai-classify :8083 — healthy |
| eureka :8761 · java-core :8081 (profile `local`) · gateway :8080 | lên; java-core tìm ai-service qua danh sách dự phòng `localhost:8000` (ai-service chưa tự đăng ký Eureka) |
| ai-service API + worker | `LLM_MODE=mock`, `AI_MODE=remote`, `EMBED_URL=:8091`, worker `CHAM_TU_DONG_BAT=false` |
| web-dashboard :5173 | `VITE_USE_MOCK=false` |
| Tài khoản | quản trị B `quantri@nha-khoa-b17.test` · **nhân viên B (mới, `AGENT`)** `nhanvien@nha-khoa-b17.test` / `NhanVienB17@2026` · **tenant kho rỗng (mới)** `quantri@kho-trong-gd1.test` / `KhoTrongGD1@2026` (đăng ký qua `/auth/register` thật) |

### UC018 — Tải lên tài liệu tri thức

| Bước đặc tả | Thao tác | Kết quả thấy được |
|---|---|---|
| 1–5 | Kho tri thức → "Tải lên tài liệu", chọn `quy-trinh-bao-hanh-thu.pdf` | tiêu đề tự gợi ý "quy trinh bao hanh thu"; chọn được ngôn ngữ |
| 6–10 | Bấm "Tải lên và nạp" | toast "Đã nhận tài liệu. Quá trình nạp đang chạy nền." → chuyển `/tri-thuc/tai-lieu/{id}/tien-do` |
| 7.1 | Tải lại cùng tiêu đề | danh sách có **v2** và **v1** cùng tiêu đề, cả hai "Sẵn sàng" |
| 4.1 | Chọn `bang-gia.xlsx` | "Định dạng .xlsx không được hỗ trợ. Nhận .pdf, .docx, .txt, .md, .html." — hộp thoại giữ nguyên |
| 4.2 | Chọn tệp 21 000 000 byte | báo vượt 20 MB ngay ở trình duyệt, không có request nào (sau sửa: "Tệp 20.03 MB vượt quá giới hạn 20 MB…") |
| 8.1 | Tải `ban-scan-thu.pdf` (PDF ảnh quét) | màn tiến độ "Nạp tài liệu thất bại" · "PDF không có lớp chữ — có thể là bản scan, cần OCR trước khi tải lên" · mã `PARSE_NO_TEXT_EXTRACTED` |
| 6.1 | Đặt tạm `DOCUMENT` = 20/20 bằng SQL, tải lên | 409 trong hộp thoại: "Đã có 20/20 tài liệu theo gói. Hãy gỡ bớt tài liệu cũ hoặc nâng gói dịch vụ." — hộp thoại giữ nguyên |
| 403 | Nhân viên `AGENT` tải lên | "Vai trò hiện tại không được thực hiện thao tác này" |

### UC019 — Nạp và lập chỉ mục

| Bước đặc tả | Thao tác | Kết quả thấy được |
|---|---|---|
| 1–11 | Ở lại màn tiến độ sau khi tải | chạy `QUEUED → … → DONE` (~6 s, 11 đoạn); khi xong cả 6 bước có dấu xong, không còn vòng xoay |
| — | Đếm request 6 s sau `DONE` | **0** — màn tự ngừng hỏi lại |
| 12 | Đọc dòng hoàn tất | "… đã có 11 đoạn trong chỉ mục" — khớp cột "Số đoạn" = 11 ở danh sách |
| — | Mở `/tri-thuc/tien-do` trong lúc nạp lại | hiện việc đang chạy (bản bóng, "Nạp lại thủ công", "Chờ trong hàng đợi") + "Việc khác trong hàng đợi" |
| 4.1 | Tệp ảnh quét (UC018 8.1) | `FAILED` + câu lỗi + mã lỗi |
| — | Token / chi phí nhúng | hiện "Chưa ghi nhận" (trước sửa: số 0 như thể đã đo) |

### UC020 — Quản lý kho tri thức

| Bước đặc tả | Thao tác | Kết quả thấy được |
|---|---|---|
| 2 | Gõ `bao hanh` | 3 tài liệu "… bảo hành …" (không dấu khớp có dấu) |
| 2 | Lọc "Nạp lỗi", rồi "Markdown" | đúng 1 / đúng 2 tài liệu; request gửi `status=FAILED`, `sourceType=MD`, `size=10` lên máy chủ |
| 2.1 | Đăng nhập tenant kho rỗng | "Kho tri thức đang trống" + nút "Tải lên tài liệu"; `/tri-thuc/tien-do` "Hàng đợi nạp đang trống" |
| 4 | Bấm một tài liệu | mô tả + "Sẵn sàng · PDF · 305 KB · 11 đoạn · Tiếng Việt · v1 · tải lên bởi Quản trị Nha khoa B17"; bảng đoạn đủ cột #, Mục, Nội dung, Token, Mô hình nhúng (`BAAI/bge-m3` · `int8-71e2aa91` từng đoạn); 10 đoạn/trang |
| 5 (sửa) | "Sửa thông tin" → đổi tiêu đề + mô tả | toast "Đã cập nhật thông tin tài liệu."; danh sách hiện tên mới, **số đoạn vẫn 11** |
| 422 | Đổi tiêu đề trùng tài liệu khác cùng v1 | trong hộp thoại: "Đã có tài liệu khác tên '…' ở version 1" |
| 6 | "Nạp lại tài liệu" ở v2 | sang màn tiến độ của **id mới** (bản bóng `60c0ff7f…` ≠ `2b299d7b…`), nguồn "Nạp lại thủ công" |
| 6 | Danh sách trong lúc nạp lại | bản bóng v3 "Chờ nạp" **và** bản cũ v2 vẫn "Sẵn sàng" — kho không trống giây nào |
| 5.1 | Nạp lại / gỡ bản cũ khi bản bóng đang chờ | 409 cả hai: "Tài liệu đang được xử lý (nạp hoặc nạp lại). Thử lại khi việc nạp xong." |
| 6 | Chờ bản bóng xong (≤ 60 s bộ quét + 4 s nạp) | v3 "Sẵn sàng" 11 đoạn; v2 biến khỏi danh sách (đã `ARCHIVED`) |
| 7 | Chọn dòng → "Gỡ khỏi kho" | hộp xác nhận nói rõ AI thôi trích dẫn, câu trả lời cũ giữ trích dẫn, chuyển "Đã lưu trữ"; xác nhận → biến khỏi danh sách; lọc "Đã lưu trữ" thấy lại |
| 7 · hạn mức | So `usage_records` trước/sau gỡ bản quét | `DOCUMENT` 5 → 4, `STORAGE_MB` −507 067 byte (đúng cỡ tệp) — ADR-0023 (f) |
| 7.2 | Mở trang tài liệu → tắt ai-service → Gỡ | toast "Dịch vụ AI tạm thời không phản hồi. Thao tác chưa được thực hiện, thử lại sau." (502); CSDL: vẫn `READY`, 11 đoạn |
| 7.2 | Danh sách khi ai-service tắt | "Không tải được dữ liệu" + câu 502 + "Thử lại" (trước sửa: "Kho tri thức đang trống") |
| 8 | Truy vấn `platform.audit_logs` | `DOCUMENT_UPDATED` · `DOCUMENT_REINDEXED` (kèm id bản bóng, v3) · `DOCUMENT_ARCHIVED` (kèm `quotaReleased`), đủ người làm "Quản trị Nha khoa B17" và giờ; **không** dòng nào cho các lượt 403/409/422/502 |
| 403 | Nhân viên `AGENT`: gỡ · nạp lại · sửa | cả ba "Vai trò hiện tại không được thực hiện thao tác này"; vẫn đọc được danh sách (5 dòng) |

### Cổng ra — kiểm máy

| Lệnh | Kết quả |
|---|---|
| `mvn -f java-core/pom.xml compile` | sạch |
| `KnowledgeRelayTest` (mới, `MockRestServiceServer`) | 3/3 — snake → camel, từ khoá mã hoá chặt, `description: null` có trong thân `PATCH`, bảng 404/409/422/502/mất nối/401 |
| `KnowledgeDocumentUploadIntegrationTest` (+3 ca GD1) | 26/26 — gỡ trả hạn mức đúng một lần + kiểm toán · 502/409 không ghi gì · 403 cho `AGENT` |
| `mvn -f java-core/pom.xml test` (cả bộ, cần Docker) | **239/239**, 18 lớp, 0 lỗi |
| `npm run typecheck` · `npm run build` (web-dashboard) | sạch |
| ai-service `ruff check src tests` · `compileall` | sạch |
| ai-service `pytest test_nap_tai_lieu.py -k "tien_do or hang_doi"` | 7/7 (2 ca mới: hàng đợi lọc/phân trang/RLS, bản bóng `REINDEX`) |
| ai-service `pytest test_kho_http.py test_quan_ly_kho.py` | 22/22 (1 ca mới: `quota_released`) |
| ai-service `pytest tests/unit tests/integration` (cả bộ) | 729 passed · 1 skipped · **1 failed không liên quan**: `test_router_data_pipeline::test_intent_train_dedup_integrity` — sổ `artifacts/DATA_HASHES.txt` lệch hash `intent_train_dedup.jsonl` (nợ Dev B đã ghi; tệp đóng băng, không sửa) |

### Sửa trong lúc chạy thật (không có trong kế hoạch)

| Hiện tượng | Nguyên nhân | Sửa |
|---|---|---|
| Gỡ tài liệu không trả hạn mức — "gỡ bớt tài liệu cũ" (UC018 6.1) vô tác dụng | ADR-0023 (f) chưa làm | ai-service trả `quota_released` + `file_size_bytes`; java-core `UsageQuotaService.release` cùng transaction với kiểm toán |
| ai-service tắt ⇒ danh sách báo "Kho tri thức đang trống", màn tiến độ báo "Hàng đợi trống" | `ListPage` không có trạng thái lỗi | prop `loi`/`onThuLai` cho `ListPage`; màn chi tiết và tiến độ hiện lỗi thật |
| Bước "Hoàn tất" vẫn quay khi đã `DONE` | `DONE` là phần tử cuối của chuỗi nên bị coi là "đang chạy" | `DONE` ⇒ mọi bước xong |
| "Tệp 20.0 MB vượt quá giới hạn 20 MB" | làm tròn 1 chữ số | 2 chữ số |
| Cột trạng thái hiện "PARSE_NO_TEXT_EXTRACTED: PDF không có…" bị cắt | ai-service lưu `"{MÃ}: {câu}"` | java-core bỏ tiền tố cho `TaiLieu.errorMessage` |
| Cột Token, Mô hình nhúng bị đẩy ra ngoài khung (phải cuộn ngang) | ô bảng không xuống dòng | nội dung đoạn xuống dòng, giữ 3 dòng |
| Bộ đếm hạn mức tenant B lệch +1 tài liệu | tài liệu "Hồ sơ ưu đãi riêng" gỡ thẳng ở ai-service hôm N17, không qua java-core | đối soát tay bằng SQL về đúng số tài liệu chưa gỡ (ADR-0023 Đánh đổi 1 — job đối soát vẫn chưa có) |

### Thấy khi chạy, ngoài GD1 — đã báo Dev B, chưa sửa

- WebSocket `/ws` 404: gateway không có route, java-core chưa có endpoint STOMP → thanh trên luôn "Mất kết nối"
  (10/11 vẫn vậy).
- `GET /api/v1/tool-calls` (MCP, đã hoãn) trả **500**: không có controller, route lạ rơi vào handler chung thành
  500 thay vì 404 (10/11 vẫn vậy). `GET /api/v1/audit-logs` (UC040) **đã có** controller sau khi gộp `develop` —
  10/11 trả 200.
- ai-service chưa tự đăng ký Eureka (`src/api/eureka.py` còn là khung).
- *(10/11)* **Thuê bao dùng thử hết hạn thì không có đường nào gia hạn.** `changePlan` đổi `status` sang `ACTIVE`
  nhưng không dời `period_end`; không job nào chuyển `TRIALING` sang `EXPIRED`. Tenant hết hạn nhận câu "Hãy gia
  hạn hoặc chọn gói" mà cả hai đường đều không cứu được — UC006 của Dev B.
- *(10/11)* `FormDialog` (mẫu M3) `await onGui()` trong `handleSubmit` mà không bắt lỗi → mỗi lượt máy chủ từ chối
  (409, 422…) để lại một promise bị từ chối không ai xử lý (`pageerror` trên trình duyệt). Giao diện vẫn hiện lỗi
  đúng qua `loi` — chỉ là tiếng ồn trên console, gặp ở mọi biểu mẫu.

### Dữ liệu sau khi kiểm

Kho tenant B về đúng 2 tài liệu nha khoa (mọi tài liệu thử đã gỡ bằng chính thao tác gỡ trên giao diện);
hạn mức `DOCUMENT` = 2, `STORAGE_MB` = 3 861 byte (= 1 886 + 1 975), `warned_at`/`blocked_at` trống — đúng
cả sau lượt 24/10 lẫn lượt 10/11. Tài liệu thử còn ở `ARCHIVED`, 0 đoạn — không ảnh hưởng truy hồi. Thêm mới,
để dùng tiếp ở GD2/GD3: tài khoản nhân viên B và tenant "Phòng khám trống GD1".

**Đổi tay 10/11:** `platform.tenant_subscriptions.period_end` của tenant B dời từ `2026-11-01 00:38:17+00` tới
**31/12/2026** (vẫn `TRIALING`, gói `TRIAL`) để tải lên được — xem mục dưới. Tenant "Phòng khám trống GD1" hết
hạn 07/11, giữ nguyên (chỉ dùng để đọc kho rỗng).

### Chạy lại sau khi gộp `develop` (10/11/2026)

Nhánh đã gộp `develop` (`4ae448d`, gồm PR #43–#45 của Dev B: nhật ký kiểm toán UC040, chủ đề UC038, hạn mức
theo ngày UC006). Đi lại đủ 16 cảnh trên giao diện thật, cùng cách kiểm như 24/10. CSDL: Track A V135 →
**V139** (java-core tự chạy lúc khởi động), Track B V214 → **V215** (`scripts/migrate-ai.sh`).

| Kiểm máy | Kết quả |
|---|---|
| `mvn -f java-core/pom.xml test` (cả bộ, cần Docker) | **283/283**, 24 lớp, 0 lỗi (24/10: 239 — thêm 44 ca của Dev B) |
| `npm run typecheck` · `npm run build` (web-dashboard, sau khi vá nhãn) | sạch |

| # | Thao tác | Kết quả |
|---|---|---|
| 1 | Chọn `bang-gia.xlsx` | "Định dạng .xlsx không được hỗ trợ. Nhận .pdf, .docx, .txt, .md, .html." — hộp thoại giữ nguyên, không có request tải lên |
| 2 | Đặt `DOCUMENT` = 20/20 bằng SQL, tải PDF | 409 trong hộp thoại "Đã có 20/20 tài liệu theo gói. Hãy gỡ bớt…"; không tạo tài liệu. Lượt bị chặn đóng **cả hai** mốc `warned_at`, `blocked_at` (ADR-0023 (e)) — trả lại `used_value` = 2 và cả hai mốc về `NULL` |
| 3 | Tải `ban-scan-thu.pdf` | `FAILED` · "PDF không có lớp chữ — có thể là bản scan, cần OCR trước khi tải lên" · mã `PARSE_NO_TEXT_EXTRACTED` |
| 4 | Tải PDF có chữ, tiêu đề "Quy trình bảo hành thử 10-11" | `DONE` sau ~9 s, 11 đoạn; đủ 6 bước có dấu xong, không còn vòng xoay; 0 request trong 6 s sau `DONE` |
| 5 | Nạp lại → mở ngay `/tri-thuc/tien-do` | việc "Nạp lại thủ công" của bản bóng — id mới `7e6d2d07…` ≠ `9336bc0c…` |
| 6 | Gõ `bao hanh` | request `q=bao+hanh`; 2 dòng, cả hai "bảo hành" (tài liệu thử + "Chính sách bảo hành, trả góp và lịch hẹn") |
| 7 | Bấm tài liệu | cột `# · Mục · Nội dung đoạn · Token · Mô hình nhúng`; `BAAI/bge-m3 int8-71e2aa91` từng đoạn; 10 đoạn/trang |
| 8 | Đổi tiêu đề thành "Bảng giá dịch vụ nha khoa 2026" | `422 PATCH`, trong hộp thoại "Đã có tài liệu khác tên '…' ở version 1"; sửa lại mô tả thì "Đã cập nhật thông tin tài liệu." |
| 9 | Về danh sách ngay lúc đó | v2 "Chờ nạp" 0 đoạn **và** v1 "Sẵn sàng" 11 đoạn cùng lúc |
| 10 | Nạp lại rồi gỡ v1 khi v2 chưa xong | `409 POST …/reindex` + `409 DELETE`, toast "Tài liệu đang được xử lý (nạp hoặc nạp lại)…" |
| 11 | v2 xong (~12 s) → chọn dòng → Gỡ khỏi kho | v1 đã biến khỏi danh sách; hộp xác nhận nói rõ AI thôi trích dẫn, câu trả lời cũ giữ trích dẫn, chuyển "Đã lưu trữ" |
| 12 | Xác nhận, lọc "Đã lưu trữ" | "Đã gỡ 1 tài liệu khỏi kho tri thức."; thấy lại v2 (và v1, lưu trữ lúc đổi bản) |
| 13 | Trang tài liệu quét → Ctrl+C ai-service → Gỡ; mở danh sách | `502 DELETE` + "Dịch vụ AI tạm thời không phản hồi. Thao tác chưa được thực hiện…"; danh sách "Không tải được dữ liệu" + "Thử lại". CSDL: vẫn `FAILED`, hạn mức không đổi |
| 14 | Nhân viên `AGENT` bấm Gỡ | `403 DELETE` + "Vai trò hiện tại không được thực hiện thao tác này"; vẫn đọc được danh sách |
| 15 | Tenant kho rỗng | "Kho tri thức đang trống" + nút "Tải lên tài liệu" |
| 16 | Menu Nhật ký kiểm toán | 3 dòng mới "Sửa thông tin tài liệu tri thức" · "Nạp lại tài liệu tri thức" · "Gỡ tài liệu khỏi kho tri thức", đủ email người làm, giờ, IP; lọc theo hành động gửi `action=DOCUMENT_ARCHIVED` lên máy chủ. CSDL: đúng 3 dòng, không dòng nào cho các lượt 403/409/422/502; `DOCUMENT_UPDATED` chỉ ghi tên trường |

**Hạn mức qua lượt chạy** (`DOCUMENT` · `STORAGE_MB` byte): 2 · 3 861 → tải 2 tệp: 4 · 823 205 → gỡ v2 sau nạp
lại: 3 · 510 928 (−312 277, đúng cỡ tệp; bản bóng không bị đếm thêm) → gỡ bản quét: **2 · 3 861**. Phần trả hạn
mức của GD1 vẫn đúng sau khi gộp thay đổi `UsageQuotaServiceImpl` của Dev B.

| Hiện tượng | Nguyên nhân | Xử lý |
|---|---|---|
| Mọi lượt tải lên của tenant B: 409 "Doanh nghiệp chưa có gói dịch vụ đang hiệu lực…" | thuê bao `TRIAL` 14 ngày (18/10 → 01/11) đã hết hạn — đúng UC006, không do gộp code | dời `period_end` bằng SQL trên CSDL dev; ứng dụng không có đường gia hạn — đã báo Dev B (mục trên) |
| Nhật ký kiểm toán hiện mã thô `DOCUMENT_*`; bộ lọc "Hành động" (29 lựa chọn) thiếu 3 mã của GD1 | `features/audit/nhan.ts` của Dev B rà mã lúc GD1 chưa vào `develop` | thêm 3 nhãn — chú thích trong tệp dặn "thêm hành động mới ở java-core thì thêm nhãn ở đây" |

### Phải giải thích được

- **Vì sao dashboard không gọi thẳng ai-service:** java-core là chỗ có JWT đã xác thực, quyền
  `TENANT_ADMIN`, hạn mức gói và nhật ký kiểm toán — ba thứ ai-service không có và không được có
  (ADR-0002, ADR-0014). Đi thẳng thì tenant phải lấy từ trình duyệt.
- **Vì sao tài liệu của tenant khác trả 404 chứ không 403:** RLS làm dòng đó vô hình; 403 sẽ xác nhận id
  có tồn tại ở đâu đó — dò được. 404 cho cả hai trường hợp là đúng đặc tả UC020.
- **Vì sao nạp lại đổi `id` mà kho không trống giây nào:** bản bóng là dòng mới (version kế tiếp, cùng tệp);
  bản cũ vẫn `READY` và vẫn được truy hồi; lúc bản bóng `READY`, ai-service xoá đoạn cũ và `ARCHIVED`
  bản cũ **trong cùng transaction** — người đọc thấy hoặc trạng thái trước, hoặc trạng thái sau (ADR-0031).

---

## GD2 — Chat trọn luồng + từ chối + đánh giá: UC023 · UC025 · UC027 (10/11/2026)

**Nhánh** `feat/giao-dien-gd2-chat` (tách từ `develop` = `7c9f867`). Cách kiểm như GD1: trình duyệt thật (Chrome
không giao diện, Playwright điều khiển — script ở scratchpad, không vào repo), `VITE_USE_MOCK=false`, mọi lời gọi
qua gateway `:8080`; widget chạy trang dev `localhost:5174`. Không chụp ảnh — người dùng chốt áp lại cách của GD1.

### Sáu câu demo — chốt TRƯỚC khi chạy

Router chỉ cho qua câu kiểu "… bao nhiêu tiền / chi phí / bảng giá" (N17), nên cả sáu câu bám kiểu đó. Đã kiểm trước
từng câu bằng cách gọi thẳng `POST /v1/ai/chat` của ai-service với ba hội thoại thử riêng (`d4351161…`,
`0a6d6ee6…`, `8accdfb2…` — còn trong `ai.ai_interactions` của tenant B, có mặt ở màn Giám sát và Khoảng trống).

| # | Vai | Câu hỏi | Kết quả mong đợi (đã kiểm trước) |
|---|---|---|---|
| C1 | có đáp án | Niềng răng mắc cài sứ bao nhiêu tiền? | `RAG`, 46.000.000 đồng `[1]`, nguồn "Bảng giá dịch vụ nha khoa 2026" |
| C2 | có đáp án | Chi phí tẩy trắng răng bằng laser là bao nhiêu? | `RAG`, 2.450.000 đồng cho hai hàm `[1]` |
| C3 | "chi phí" ngoài kho | Chi phí điều trị viêm nha chu bao nhiêu tiền? | từ chối `NOT_COVERED`, không nguồn, mời chuyển nhân viên |
| C4 | đơn hàng cụ thể | Đơn hàng DH20261108 của em bao nhiêu tiền? | từ chối `OUT_OF_SCOPE_DATA`, `handoff = true` — luật mã đơn, không gọi LLM |
| C5 | chào (đường nhanh) | Xin chào | `SMALL_TALK`, `FAST_PATH`, không gọi LLM, chi phí 0 |
| C6 | ngoài kho hỏi lặp (3.3) | Chi phí làm răng giả tháo lắp bao nhiêu tiền? → Vậy chi phí làm răng giả tháo lắp hàm trên là bao nhiêu? | lần 1 `NOT_COVERED`; lần 2 cùng hội thoại `NOT_COVERED` + `handoff = true` ("Em chuyển anh/chị sang nhân viên…") |

**Cấu hình lúc chạy (khác mặc định, chỉ trong buổi này):** `LLM_MODE=remote` (Gemini `gemini-3.5-flash-lite`),
`RERANK_ENABLED=false`, `LLM_TIMEOUT_S=6`, `CHAM_TU_DONG_BAT=false`. Lý do: lượt kiểm trước đầu tiên đo được
rerank khởi động nguội **20 335 ms**, rồi hai lượt liền Gemini quá hạn chót 2,5 s (`LLM_TIMEOUT`) nên rơi về câu
"trả lời tạm" — mà java-core chỉ chờ ai-service 10 s cho một lượt widget. Độ trễ chưa là cổng (11/10) nên nới hạn
chót cho buổi đi cảnh, ghi số thật; mặc định trong code giữ nguyên. Số đo trên đọc từ cột mới
`ai_interactions.latency_breakdown` (V216).

| | UC023 | UC025 | UC027 |
|---|---|---|---|
| (a) luồng chính trên giao diện | ✅ | ✅ | ✅ |
| (b) luồng phụ, mã lỗi | ✅ CRM · 10 · KPI · 8.2 | ✅ 3.1 · 3.3 · 4 · 8 · 8.1 · bổ sung tài liệu | ✅ 2.1 · 3 · 3.1 · 4 · 7 · 8 · 422 · 404 |
| (c) kiểm máy | ✅ | ✅ | ✅ |
| (d) minh chứng | ✅ | ✅ | ✅ |

`LOW_CONFIDENCE` (câu bị huỷ vì không bám nguồn) **chưa tái hiện trên giao diện**: cổng huỷ đang tắt
(`RAG_NGUONG_BAM_NGUON = 0`, ADR-0029) nên đường này không xảy ra ở cấu hình ship — khoá bằng test (mục Kiểm máy).

### Môi trường

| Thành phần | Trạng thái |
|---|---|
| Hạ tầng · suy luận | như GD1; đủ 14 topic; ai-embed · ai-rerank · ai-classify healthy |
| CSDL | Track A V139 · Track B **V216** (mới, `scripts/migrate-ai.sh`) |
| ai-service API + worker | `LLM_MODE=remote`, `RERANK_ENABLED=false`, `LLM_TIMEOUT_S=6`, `CHAM_TU_DONG_BAT=false` |
| web-dashboard :5173 · web-widget :5174 | `VITE_USE_MOCK=false`; widget mở bằng `localhost:5174/?key=…&api=http://localhost:8080` |
| Kênh widget tenant B (mới) | tạo trên SCR018 bằng "Sinh mã nhúng" → `wk_4d68…`, tên miền `localhost`; `404 → 201 POST → 200 PUT /api/v1/widget-config` |

### UC023 — Trả lời dựa trên tri thức doanh nghiệp

| Bước đặc tả | Thao tác | Kết quả thấy được |
|---|---|---|
| 1–12 | C1 ở widget | "… niềng răng mắc cài sứ có giá 46.000.000 đồng cho toàn bộ liệu trình … [1]" · "Nguồn: Bảng giá dịch vụ nha khoa 2026". Đoạn trích **ẩn** tới khi bấm nguồn; bấm thì mở "- Niềng răng mắc cài kim loại: 34.000.000 … mắc cài sứ: 46.000.000 đồng …" |
| 1–12 | C2 | "… 2.450.000 đồng cho hai hàm ạ [1]", cùng nguồn |
| CRM | Hộp thư → hội thoại đó | hai tin BOT đều có "Nguồn: Bảng giá dịch vụ nha khoa 2026" như widget; mỗi tin BOT có 👍/👎 |
| 10 | Giám sát lượt xử lý | thẻ C1: "Truy hồi tri thức · PRICING_POLICY (94%) · gemini-3.5-flash-lite · 1.261 token", câu hỏi + câu trả lời, "Độ trễ theo chặng 5.7 s — Truy hồi 961 ms · Sinh câu trả lời 4.7 s", "Điểm truy hồi cao nhất 0.78", "Căn cứ đã trích dẫn" kèm đoạn |
| KPI | C5 "Xin chào" | widget trả mẫu câu chào ngay; thẻ giám sát "Chào hỏi · GREETING (96%) · template · 0 token · 0 ₫" — không gọi LLM |
| 8.2 | Bật lại ai-service với `LLM_API_KEY` sai, hỏi "Chi phí bọc răng sứ zirconia bao nhiêu tiền?" | Gemini trả 400 `INVALID_ARGUMENT` → log "LLM không khả dụng (LLM_HTTP_400) — trả câu suy giảm"; widget vẫn có câu trả lời: nhãn **"Trả lời tạm"** + trích nguyên văn đoạn "Thẩm mỹ" + nguồn + 👍/👎 |
| — | CSDL `engagement.messages` | cả 7 tin BOT của lượt chạy có `ai_interaction_id`; `metadata.refusalReason` có ở 3 tin từ chối; `metadata.degraded` có ở mọi tin |

### UC025 — Từ chối khi không đủ căn cứ

| Bước đặc tả | Thao tác | Kết quả thấy được |
|---|---|---|
| 1–6 | C3 ở widget | "Dạ hiện em chưa tìm thấy thông tin phù hợp trong tài liệu của cửa hàng … Anh/chị có muốn em chuyển cho nhân viên tư vấn không ạ?" — không bịa giá, không có nguồn |
| 5 / 3.1 | C4 | "Dạ câu này cần tra cứu thông tin cụ thể (đơn hàng, tài khoản …) … Em chuyển anh/chị sang nhân viên hỗ trợ ngay ạ."; chân widget "Đang chờ nhân viên tiếp nhận…"; Hộp thư: hội thoại "Chờ nhân viên" (`PENDING_AGENT`) |
| 3.3 | C6 hai lần, cùng hội thoại | lần 1 từ chối như C3; lần 2 "Dạ em xin lỗi vì chưa giúp được anh/chị. Em chuyển anh/chị sang nhân viên tư vấn ngay ạ." → `PENDING_AGENT` |
| 4 | Giám sát, "Chỉ lượt từ chối" | request `refused=true`; thẻ C3: "Đã từ chối", "Từ chối trả lời: Kho tri thức không có nội dung phù hợp", "Điểm truy hồi cao nhất 0.61", độ trễ từng chặng |
| 8 · 8.1 | Khoảng trống tri thức | 4 dòng mới, mỗi dòng **2 khách · 2 lần** (hội thoại kiểm trước + widget): hai câu của C6, C4 "Cần dữ liệu thời gian thực", C3. Không còn ô tìm kiếm; cột "Số khách hỏi (≈)" |
| — | Tải "Bảng giá điều trị nha chu" (MD, 1 đoạn, qua gateway) → `READY` → hỏi lại C3 ở widget | "… viêm nha chu giai đoạn đầu là 1.800.000 đồng mỗi hàm [1] … nặng có phẫu thuật lật vạt là 4.500.000 đồng mỗi vùng [1]"; dòng C3 ở Khoảng trống đứng yên ở 2 — không tăng, rơi khỏi danh sách theo cửa sổ 30 ngày. Gỡ tài liệu thử: `200 DELETE`, kho về 2 tài liệu |

### UC027 — Đánh giá chất lượng câu trả lời

| Bước đặc tả | Thao tác | Kết quả thấy được |
|---|---|---|
| 1–5 (khách) | 👍 dưới câu C1 | không hỏi lý do (3.1), thay bằng "Cảm ơn bạn đã đánh giá!"; `200 POST /api/v1/widget/messages/{id}/feedback`; CSDL `CUSTOMER · POSITIVE` |
| 3 | 👎 dưới câu C2 | hiện 4 lý do; nút "Gửi" **khoá** tới khi chọn lý do; chọn "Lạc đề" + nhận xét → cảm ơn |
| 2.1 | Tải lại trang, 👍 lại câu C2 | CSDL vẫn **một** dòng `CUSTOMER` cho lượt đó, nay `POSITIVE`, `updated_at > created_at` |
| 4 (nhân viên) | Tài khoản `AGENT` ở Hộp thư: 👎 tin C2 | hộp thoại nhắc lại câu trả lời; bấm "Gửi đánh giá" khi chưa chọn → "Chọn một lý do."; chọn "Trả lời thiếu" + nhận xét + câu trả lời đúng → `201 POST /api/v1/ai-interactions/{id}/feedback`, toast; dưới tin hiện "Nhân viên Nha khoa B17 · Trả lời thiếu · “Thiếu thời gian một buổi” · Câu trả lời đúng: …" |
| 422 · 404 | Gọi thẳng API qua gateway | chê thiếu lý do → **422 `REASON_REQUIRED`** "Đánh giá chưa ổn cần chọn một lý do." (java-core chặn, không sang ai-service); lượt không tồn tại → 404 `INTERACTION_NOT_FOUND`; widget không token → 401 |
| 7 | Hiệu quả AI (30 ngày) | "Phản hồi tích cực **66.7%** — trên 3 lượt đánh giá của nhân viên và khách" = (khách 👍 C1 + khách 👍 C2) ÷ (2 của khách + 1 của nhân viên). Số lấy từ `/v1/ai/quality` (chốt Q2, hướng B) |
| 8 | Giám sát, "Bị chê" | request `rating=NEGATIVE`; đúng **1** thẻ (C2) kèm cả hai đánh giá: nhân viên (lý do, nhận xét, câu đúng) và khách; "Mở hội thoại" → Hộp thư đúng hội thoại |

### Cổng ra — kiểm máy

| Lệnh | Kết quả |
|---|---|
| `mvn -f java-core/pom.xml test` (cả bộ, cần Docker) | **296/296**, 25 lớp (283 + 13 ca GD2: `AiInteractionRelayIntegrationTest` 7 · `WidgetIntegrationTest` +4 · `AiPerformanceIntegrationTest` +2) |
| `npm run typecheck` · `npm run build` (web-dashboard, web-widget) | sạch; `widget.js` 20,9 kB |
| ai-service `compileall` | sạch |
| ai-service `ruff` | các tệp đã sửa không thêm lỗi nào; cả repo 102 lỗi **có sẵn trên `develop`** (E501, I001 — phần lớn UC038/UC040) |
| ai-service `pytest tests/unit tests/integration` | 753 passed · 1 skipped · **3 failed không liên quan**: `test_intent_train_dedup_integrity` (sổ hash, nợ cũ) và hai test đường dẫn UC040/UC038 vỡ vì venv đang có FastAPI 0.141.1 gói router thành `_IncludedRouter` (`fastapi>=0.121` không ghim trần) — đường thật vẫn trả 401, không 404 |
| ai-service test mới | `test_danh_sach_luot_loc_phan_trang_trich_dan_va_rls` · `test_danh_gia_lai_hien_ket_qua_moi_va_moc_moi` · `test_http_danh_sach_luot` · `test_luot_bi_huy_luu_cau_da_sinh_con_khach_nhan_cau_mau`; kiểm ngược: đổi điều kiện `discarded_answer` về công thức cũ thì test đỏ đúng chỗ |

### Sửa trong lúc chạy thật (không có trong kế hoạch)

| Hiện tượng | Nguyên nhân | Sửa |
|---|---|---|
| `discardedAnswer` sẽ hiện câu mẫu từ chối (khách ĐÃ nhận) thành "câu bị huỷ" | `response_text` của lượt từ chối là câu mẫu; công thức cũ `is_answered = false ? response_text : null` | lượt `LOW_CONFIDENCE` lưu câu ĐÃ SINH vào `response_text`; `discarded_answer` chỉ có ở lượt đó |
| Màn giám sát không có độ trễ từng chặng của từng lượt | số chặng chỉ đi theo sự kiện, cộng dồn theo ngày | **V216** `ai_interactions.latency_breakdown` |
| Link "Mở hội thoại" ở Giám sát lượt xử lý không mở hội thoại | link gửi `?hoiThoai=`, `InboxPage` đọc `?c=` | đổi link |
| Chip "Độ bám nguồn 0.50 · ngưỡng 0.7" tô đỏ như thể câu đã bị huỷ | hằng 0.7 viết cứng; cổng huỷ thật = 0 (ADR-0029) | chip theo dõi, ghi "cổng huỷ đang tắt" |
| Mô tả `POST …/feedback` trong hợp đồng ghi "đóng dòng cũ rồi chèn dòng mới" | lệch đặc tả 2.1 và lệch V204 | sửa mô tả theo đặc tả (cập nhật dòng cũ) |

### Thấy khi chạy, ngoài GD2 — báo Dev B, chưa sửa

- **Khoá Resend nằm trong gói JS của dashboard.** `RegisterPage.tsx`, `ForgotPasswordPage.tsx` đọc
  `import.meta.env.VITE_RESEND_API_KEY`; Vite nhúng giá trị vào `dist/assets/*.js` (đã thấy chuỗi khoá trong bản
  build). Ai mở trang đăng ký cũng đọc được khoá và gửi thư nhân danh doanh nghiệp. Cần chuyển việc gửi thư về
  java-core và thu hồi khoá đang dùng.
- Hai test đường dẫn UC040/UC038 vỡ với FastAPI 0.141 (mục trên).
- 102 lỗi `ruff` có sẵn ở ai-service.

### Dữ liệu sau khi kiểm

Kho tenant B về đúng **2 tài liệu** (tài liệu thử "Bảng giá điều trị nha chu" đã gỡ, `ARCHIVED`); `DOCUMENT` = 2,
`STORAGE_MB` = 3 861 byte — như trước buổi chạy. `AI_TOKEN` 13 194 / 500 000 (bộ đếm UC006 của Dev B ăn sự kiện
`ai.turn.completed` đúng), `CONVERSATION` 6. Thêm mới: kênh widget `wk_4d68…` (tên miền `localhost`), 18 lượt ở
`ai.ai_interactions` (3 hội thoại kiểm trước + 6 khách widget), 3 dòng `ai.ai_feedback`. **Gemini: 14 lượt gọi**
(3 hỏng: 2 quá hạn chót 2,5 s lúc kiểm trước, 1 cố ý dùng khoá sai), 13 194 token.

### Giảm độ sâu — ghi nhận ở GD2

- Ô "Phản hồi tích cực": bộ lọc phiên bản mô hình không áp; ai-service tắt thì riêng ô này trống, kèm
  `errorMessage`.
- "Số khách khác nhau" của khoảng trống xấp xỉ bằng số hội thoại khác nhau.
- `LuotXuLyAi.messageId` luôn `null`: ai-service không biết mã tin; chiều nối ngược là `messages.ai_interaction_id`.
- Hộp thư không có nhãn "trả lời tạm" (`TinNhan` không mang cờ) — chỉ widget và màn giám sát có.
- Trích dẫn của lượt cũ vắng ở màn giám sát khi tài liệu đã gỡ hoặc đã nạp lại (đoạn bị xoá); tin nhắn phía
  java-core vẫn giữ bản chép trích dẫn khách đã thấy.

### Phải giải thích được

- **`groundedness` khác `retrieval_top_score` ở đâu:** điểm truy hồi đo độ liên quan đoạn ↔ câu hỏi, **trước**
  khi sinh; bám nguồn đo câu trả lời có nằm trong đoạn không, **sau** khi sinh. Truy hồi 0.76 mà bám nguồn 0.50
  (lượt C2) là chuyện thường: đoạn đúng, câu diễn đạt lại. Vì groundedness là phép đo từ vựng nên cổng huỷ đang tắt
  (ADR-0029) — điểm chỉ để theo dõi.
- **Vì sao khoảng trống tri thức không có nút "đã xử lý":** nó là truy vấn gộp trên lượt từ chối, không phải bảng có
  trạng thái. Bổ sung tài liệu thì lượt từ chối thôi phát sinh và dòng tự rơi khỏi cửa sổ 30 ngày (cảnh "tải tài
  liệu bổ sung"); nút "đã xử lý" chỉ giấu dòng mà không sửa gì trong kho.
- **Vì sao tỉ lệ tích cực chia cho số lượt CÓ đánh giá:** phần lớn lượt không ai bấm. Chia cho tổng lượt (18) thì 2
  lượt khen thành 11% — đo mức sẵn lòng bấm nút chứ không đo chất lượng. Cộng tử với tử, mẫu với mẫu của hai phía
  (không lấy trung bình hai tỉ lệ), và lấy từ `ai.ai_feedback` thay vì `metrics_daily` vì đánh giá đến SAU sự kiện
  lượt — đánh giá lại (2.1) tự đúng vì mỗi phía chỉ có một dòng.

---

## GD3 — Tóm tắt hội thoại + xoá dữ liệu cá nhân: UC026 · UC041 (13/11/2026)

**Nhánh** `feat/giao-dien-gd3-tom-tat-xoa` (tách từ `develop` = `2840347`, sau khi PR #47 GD2 đã merge). Cách kiểm
như GD1/GD2 (người dùng chốt đầu GD3): Chrome không giao diện do Playwright điều khiển, `VITE_USE_MOCK=false`, mọi
lời gọi qua gateway `:8080`; không chụp ảnh. Ba điểm chốt đầu phiên: **Q1** `CLOSING` + `MANUAL`, **Q3** một
`INTERNAL_API_TOKEN` hai chiều, **Q4** biên bản bản gọn (`certificateUri = null`).

| | UC026 | UC041 |
|---|---|---|
| (a) luồng chính trên giao diện | ✅ 1–7 | ✅ 1–11 |
| (b) luồng phụ, mã lỗi | ✅ 1.1 · 1.2 (N12) · 3.1 (test) · 4.1 · 422/502 (test) | ✅ 2.1 · 3.1 (ứng dụng + CSDL) · 5.1 · 8.1 · 9.1 · gateway |
| (c) kiểm máy | ✅ | ✅ |
| (d) minh chứng | ✅ | ✅ |

### Môi trường

| Thành phần | Trạng thái |
|---|---|
| Hạ tầng · suy luận | postgres · redis · kafka · RustFS healthy; ai-embed · ai-classify (rerank tắt) |
| CSDL | Track A V139 · Track B V216 — GD3 **không thêm migration** |
| java-core · gateway | profile `local`; `INTERNAL_API_TOKEN` (32 byte ngẫu nhiên) đặt bằng biến môi trường lúc chạy, không ghi vào `.env` |
| ai-service API + worker | `JAVA_CORE_MODE=remote`, `LLM_MODE=remote` (Gemini `gemini-3.5-flash-lite`), cùng `INTERNAL_API_TOKEN`, `RERANK_ENABLED=false`, `LLM_TIMEOUT_S=6`, `CHAM_TU_DONG_BAT=false` |
| web-dashboard :5173 · widget | `VITE_USE_MOCK=false`; khách widget tạo bằng `POST /api/v1/widget/session` + `/messages` qua gateway, khoá `wk_4d68…` |

**Bề mặt nội bộ (kiểm trước, gọi thẳng :8081):** `GET /internal/conversations/{W1}/messages` không token → **401**;
có token → 200, 6 tin cũ trước (CUSTOMER "Xin chào" → BOT …). Qua gateway: `DELETE /ai/v1/ai/privacy/contacts/…` và
`POST /ai/v1/ai/summarize` kèm JWT quản trị → **403**; `/internal/**` → 401 (không có route).

### UC026 — Tóm tắt nội dung hội thoại

| Bước đặc tả | Thao tác | Kết quả thấy được |
|---|---|---|
| 1–6 | Hộp thư → W1 (chào + C1 + C2 của GD2) → "Đánh dấu xong" | toast "Đã đánh dấu hội thoại đã xử lý xong."; cột phải hiện **"Đang tóm tắt hội thoại vừa kết thúc…"**; outbox `crm.conversation.closed` đã phát; worker log `GET /internal/…/messages 200` → `PATCH /internal/…/summary 200` → "Tóm tắt 7055ed20…: gemini-3.5-flash-lite@tt2, 1 lượt LLM, 1 khối, sửa=False" |
| 7 | Chờ ở cột phải | **4,7 s** sau khi bấm: khối "Tóm tắt hội thoại" 4 phần — Nhu cầu chính "Khách muốn biết chi phí của dịch vụ niềng răng mắc cài sứ và dịch vụ tẩy trắng răng bằng laser." · Thông tin đã cung cấp "Không có" · Vấn đề chưa giải quyết "Không có" · Bước tiếp theo "Nhân viên chào khách và hỏi thêm …"; chân khối "Sinh khi kết thúc · 18:35 13/11/2026 · `gemini-3.5-flash-lite@tt2`" |
| 5 | CSDL | `ai.ai_interactions` một lượt `branch = SUMMARY`, 682 token, 1 304 ms |
| 4.1 | Bấm "Tóm tắt lại" | nút đổi "Đang tóm tắt…"; bản mới thay bản cũ, chân khối "Nhân viên bấm tóm tắt lại"; lượt `SUMMARY` thứ hai (678 token) — bản `CLOSING` vẫn truy được ở lượt cũ |
| 1.1 | Hội thoại chỉ có "Xin chào" (khách widget mới) → "Đánh dấu xong" | 25 s sau vẫn "Chưa có bản tóm tắt…"; worker log "bỏ qua — 3 tin, quá ngắn"; **không** có lượt `SUMMARY`, không gọi LLM |
| — | Cột phải sau khi có tóm tắt | "Lượt xử lý gần nhất của AI" vẫn là lượt trả lời khách (RAG · PRICING_POLICY · câu C2), không phải lượt tóm tắt (sửa trong lúc chạy, xem dưới) |

### UC041 — Xử lý yêu cầu xoá dữ liệu cá nhân

**Chuẩn bị:** khách X = "Khách web #B180" (`4bf2870a…`) chào qua widget; tải "Hợp đồng trả góp — Trần Thị Mai"
(MD, 357 byte, 1 đoạn) → `READY`; gắn `contact_id = X` bằng `PATCH /v1/documents/{id}` (gọi thẳng ai-service). X hỏi
"Chi phí trả góp niềng răng mỗi kỳ là bao nhiêu tiền?" → "… của khách hàng Trần Thị Mai là 7.700.000 đồng mỗi kỳ
[1]", nguồn "Hợp đồng trả góp — Trần Thị Mai". Hạn mức lúc này `DOCUMENT` 3, `STORAGE_MB` 4 218 byte.

| Bước đặc tả | Thao tác | Kết quả thấy được |
|---|---|---|
| 1–2 | Kiểm toán → Yêu cầu xoá → "Tạo yêu cầu": tìm "B180", nguồn "Khách hàng tự gửi yêu cầu", căn cứ "Điều 16 NĐ 13/2023 …" | `201`; mở thẳng trang yêu cầu, chip "Chờ thực thi", bảng phạm vi 14 dòng; ở danh sách: "Khách web #B180 · Khách hàng tự gửi yêu cầu · **Chưa xác minh** [Xác minh danh tính] · Chờ thực thi" |
| 2.1 | "Tạo yêu cầu" lần nữa cho X | hộp thoại báo "Khách này đã có một yêu cầu xoá đang xử lý — không tạo yêu cầu thứ hai." (`409 ERASURE_ALREADY_OPEN`) |
| 3.1 | "Thực thi xoá" → gõ `XOA VINH VIEN` khi chưa xác minh | hộp thoại báo "Chưa xác minh danh tính chủ thể dữ liệu — không thực thi được yêu cầu xoá." (`409 IDENTITY_NOT_VERIFIED`); không gọi ai-service. Lớp CSDL: `UPDATE … SET status = 'IN_PROGRESS'` khi chưa xác minh hỏng ở `ck_erasure_gate` (test) |
| 3–4 | "Xác minh danh tính" | toast; Hồ sơ pháp lý "Người xác minh danh tính: Quản trị Nha khoa B17", lúc 18:43 |
| 5–6 | Xem trước phạm vi → chọn X | "Xoá dữ liệu của Khách web #B180 sẽ đụng tới 14 bảng"; cảnh báo **"Phạm vi xoá dừng ở hệ thống này"** (MCP); từng bảng + thao tác (Xoá hẳn · Ẩn danh hoá · Giữ số tổng hợp) |
| 7–10 | "Thực thi xoá" → hộp thoại nhắc người xác minh + số bảng + ghi chú MCP → gõ `XOA VINH VIEN` | toast "Đã xoá xong. Biên bản xác nhận đã lưu …"; "Đã hoàn tất", **14/14 bảng**: `knowledge_documents` 1 · `knowledge_chunks` 1 · `ai_interactions` 2 · `s3.kb-tai-lieu` 1 · `contacts` 1 · `channel_identities` 1 · `messages` 4 · `conversations` 1 · `metrics_daily` giữ tổng hợp |
| 10 (biên bản) | "Xem biên bản xác nhận" | thẻ "Đã xoá dữ liệu của khách mã 4bf2870a trên 14 bảng … Danh tính do Quản trị Nha khoa B17 xác minh lúc 18:43; hoàn tất lúc 18:43. Lưu trong hồ sơ yêu cầu và nhật ký kiểm toán (`ERASURE_EXECUTED`)"; `audit_logs`: `ERASURE_REQUESTED` → `ERASURE_IDENTITY_VERIFIED` → `ERASURE_EXECUTED` (`after_data.status = COMPLETED`, 14 mục) |
| sau | Khách mới hỏi lại câu cũ ở widget | "Dạ hiện em chưa tìm thấy thông tin phù hợp …" — **không** còn trích hợp đồng của X |
| sau | CSDL / kho tệp | danh bạ X `ANONYMIZED`, "Khách đã ẩn danh", không số điện thoại; 4 tin không phải `SYSTEM` `is_redacted` = "[Nội dung đã xoá theo yêu cầu của chủ thể dữ liệu]"; tài liệu mất; tệp gốc mất khỏi RustFS; hạn mức về `DOCUMENT` **2**, `STORAGE_MB` **3 861** — trả đúng 1 tài liệu / 357 byte |
| 8.1 · 9.1 | Khách Y ("Khách web #A933"): tạo + xác minh, **tắt ai-service**, "Thực thi xoá" | toast "Xoá dừng lại ở một số bảng …"; "Hỏng giữa chừng", **7/14**; cảnh báo "Xoá dừng lại ở 7 bảng — dữ liệu đang ở trạng thái nửa vời · AI_SERVICE_UNAVAILABLE — Dịch vụ AI tạm thời không phản hồi …"; 7 mục CRM "Xong" |
| 8.1 | Bật lại ai-service → "Chạy lại phần còn lại" | "Đã hoàn tất", 14/14; 7 mục AI "Xong" (`ai_interactions` 1); 6 mục CRM giữ **nguyên** mốc `11:44:25.344881Z` — không chạy lại |
| gateway | `curl` `DELETE /ai/v1/ai/privacy/contacts/…` qua :8080 với JWT quản trị | **403** |

### Cổng ra — kiểm máy

| Lệnh | Kết quả |
|---|---|
| `mvn -f java-core/pom.xml test` (cả bộ, cần Docker) | **303/303** (296 + 7 ca `TomTatXoaDuLieuIntegrationTest`: `/internal` thiếu/sai token 401 · tenant khác 404 · outbox + ghi tóm tắt luỹ đẳng, không lùi · tóm tắt thiếu phần 422 · "Tóm tắt lại" giữ mã 422/502 · xoá `lead-scores` luỹ đẳng · luồng xoá đủ cổng 409 + `ck_erasure_gate` + chạy lại + trả hạn mức) |
| `mvn -f gateway/pom.xml compile` | sạch |
| `npm run typecheck` · `npm run build` (web-dashboard) | sạch; `dashboard-api.yaml` sửa + `npm run gen:api` |
| ai-service `compileall` · `ruff` (tệp đã sửa) | sạch; không thêm lỗi ruff nào (I001 ở `service.py` có sẵn) |
| ai-service `pytest tests/unit tests/integration` (Postgres + RustFS thật) | **756 passed · 1 skipped · 0 failed** — ba test đỏ ở GD2 đã được PR #48/#49 sửa; gồm `test_mang_x_internal_token_khi_co_cau_hinh` và kiểm hạn mức mới ở `test_xoa_ca_dong_doi_cung_tep` (3 dòng cùng tệp nhưng chỉ trả 1 tài liệu), `test_chay_lai_luy_dang` (lần hai trả 0) |

### Sửa trong lúc chạy thật (không có trong kế hoạch)

| Hiện tượng | Nguyên nhân | Sửa |
|---|---|---|
| Sau khi tóm tắt, ô "Lượt xử lý gần nhất của AI" hiện chính lượt tóm tắt (route `SUMMARY`) | lấy lượt mới nhất của hội thoại, mà UC026 cũng ghi một lượt | lấy lượt mới nhất **không phải** `SUMMARY` trong 5 lượt gần nhất |
| Màn xem trước ghi "0 dòng bị xoá hẳn" trong khi phía AI sẽ xoá tài liệu, lượt xử lý | phía AI `affectedRows = null` bị cộng như 0 | câu thêm "— chưa tính 6 bảng phía AI, số dòng biết sau khi thực thi" |
| Test MockMvc của mọi đường `hasRole(...)` trả 403 cho cả quản trị viên | post-processor `jwt()` không chạy `jwtAuthenticationConverter` của ứng dụng | `asUser` ở lớp nền test gắn `ROLE_<role>` như production |

### Thấy khi chạy, ngoài GD3 — báo Dev B, chưa sửa

- `FormDialog` vẫn để lại unhandled rejection sau mỗi lượt 409 (2 lần ở cảnh 2.1 + 3.1) — đã báo ở GD1.
- Sau khi khởi động lại java-core, gateway trả 503 khoảng 30–60 s tới khi Eureka cập nhật (đúng cảnh báo ADR-0004).

### Dữ liệu sau khi kiểm

Kho tenant B vẫn **2 tài liệu**, `DOCUMENT` 2, `STORAGE_MB` 3 861 byte (tài liệu thử của X đã bị chính UC041 xoá).
Thêm: 2 danh bạ `ANONYMIZED` (X, Y) cùng 2 yêu cầu xoá `COMPLETED`; W1 nay `RESOLVED` kèm bản tóm tắt `MANUAL`; một
hội thoại chỉ có câu chào `RESOLVED`, không tóm tắt; một khách widget hỏi lại câu của X (lượt từ chối). `AI_TOKEN`
16 767 / 500 000. **Gemini: 5 lượt gọi** (2 tóm tắt + 3 lượt trả lời; hai lượt trả lời của X, Y đã bị xoá đúng
theo UC041).

### Giảm độ sâu — ghi nhận ở GD3

- UC026: chỉ `CLOSING` + `MANUAL` (Q1); `HANDOFF`, `TURN_THRESHOLD` không có nguồn phát. `TOKEN_QUOTA_EXCEEDED` (3.2)
  chưa có. Cột phải chỉ tự hỏi lại trong 2 phút sau lúc đóng để chờ bản `CLOSING`.
- UC041: thực thi **đồng bộ**; biên bản bản gọn, không xuất tệp (Q4); phạm vi không vươn tới hệ thống ngoài (MCP đã
  hoãn) và nhà cung cấp LLM — nói rõ ở `externalSystemsNote`. Liên kết kênh ↔ khách (`external_user_id`) giữ nguyên
  để khách quay lại không tạo hồ sơ trùng; chỉ tên hiển thị, ảnh, hồ sơ thô bị xoá. Tối đa 500 hội thoại gửi sang
  ai-service một lượt. ai-service xoá xong mà java-core mất phản hồi giữa chừng thì phần hạn mức của lượt đó không
  được trả (lượt gọi lại báo 0) — cùng loại lệch bộ đếm ADR-0023 Đánh đổi 1.

### Phải giải thích được

- **Vì sao ai-service ghi tóm tắt qua API chứ không ghi thẳng:** `ai_app` không có quyền trên schema `engagement`
  (ADR-0002, V206). Đó là ranh giới quyền: mô hình bị tiêm chỉ thị cũng chỉ ghi được đúng năm cột tóm tắt của hội
  thoại thuộc tenant trong `X-Tenant-Id`, qua một endpoint có token — không phải mọi bảng nghiệp vụ.
- **Vì sao ẩn danh danh bạ thay vì xoá vật lý:** xoá dòng `contacts` kéo sập các tham chiếu lịch sử (deal, lead, hội
  thoại) mà nghĩa vụ kế toán và kiểm toán vẫn cần. Ẩn danh bỏ mọi trường quy về cá nhân nhưng giữ quan hệ nghiệp vụ;
  `ck_contacts_anonymized` bắt `status` và `anonymized_at` đi cùng nhau.
- **Vì sao gọi ai-service NGOÀI transaction của java-core:** giữa lượt xoá, ai-service gọi ngược
  `DELETE /internal/contacts/{id}/lead-scores` — giữ transaction (và khoá dòng) quanh lời gọi là tự khoá mình, cộng
  giữ kết nối pool suốt lượt gọi mạng. Lượt bấm thứ hai bị chặn bằng trạng thái `IN_PROGRESS` đã commit trước đó;
  hỏng giữa chừng thì tiến độ từng bảng cho biết chính xác phần nào cần chạy lại.

---

## GD4 — Diễn tập 8 UC một lèo + hoàn thiện (14/11/2026)

**Nhánh** `feat/giao-dien-gd4-dien-tap` (tách từ `develop` = `7e5b21c`, sau khi PR #52 GD3 đã merge). Cách kiểm như
GD1–GD3: Chrome không giao diện do Playwright điều khiển, `VITE_USE_MOCK=false`, mọi lời gọi qua gateway `:8080`.
Người dùng chốt đầu GD4: **không chụp ảnh** (kế hoạch ghi `scr-gd-*.png` — bỏ), diễn tập trên **tenant mới** thay vì
dọn tenant B, **có đo độ trễ** thao tác, lỗi thuộc phần Dev B **chỉ ghi + báo**.

Đi đúng thứ tự kế hoạch, trên một tenant trống, không chạm dữ liệu của GD1–GD3: đăng nhập → tải → tiến độ → quản lý
kho → chat (trích dẫn / từ chối / chuyển giao) → 👍/👎 → khoảng trống → đóng → tóm tắt → xoá. Gặp 3 chỗ vỡ: 2 chỗ
thuộc 8 UC đã sửa và đi lại, 1 chỗ của Dev B ghi vào tin báo.

| | UC018 | UC019 | UC020 | UC023 | UC025 | UC026 | UC027 | UC041 |
|---|---|---|---|---|---|---|---|---|
| (a) luồng chính một lèo | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| (b) luồng phụ đi lại | ✅ 4.1 · 7.1 | ✅ màn hàng đợi | ✅ 2 · 422 · 6 · 7 · 8 | ✅ KPI | ✅ 3.1 · 3.3 · 4 · 8 | ✅ 1.1 · 4.1 | ✅ 2 · 3 · 3.1 · 4 · 7 · 8 | ✅ 2.1 · 3.1 · 5–11 |
| (c) kiểm máy | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| (d) minh chứng | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Luồng phụ khó dựng lại (PDF ảnh quét, đầy hạn mức, tắt ai-service giữa lượt, nhân viên `AGENT`, `LLM_API_KEY` sai…)
đã đi ở GD1–GD3 và **không** lặp lại ở GD4. GD4 kiểm cả 8 UC nối nhau trên cùng một bộ dữ liệu.

### Môi trường

| Thành phần | Trạng thái |
|---|---|
| Hạ tầng · suy luận | postgres · redis · kafka · zookeeper · RustFS healthy; ai-embed · ai-rerank · ai-classify healthy (rerank **tắt** ở ai-service); đủ 14 topic |
| CSDL | Track A V139 · Track B V216 — GD4 **không thêm migration** |
| java-core · gateway · eureka | profile `local`; `INTERNAL_API_TOKEN` (24 byte ngẫu nhiên) bằng biến môi trường lúc chạy, không ghi `.env` |
| ai-service API + worker | `JAVA_CORE_MODE=remote`, `LLM_MODE=remote` (Gemini `gemini-3.5-flash-lite`), cùng token, `RERANK_ENABLED=false`, `LLM_TIMEOUT_S=6`, `CHAM_TU_DONG_BAT=false` |
| web-dashboard :5173 · web-widget :5174 | `VITE_USE_MOCK=false`; widget `localhost:5174/?key=wk_39ef…&api=http://localhost:8080` |
| Tenant diễn tập | **"Nha khoa Diễn tập GD4"** `df124522…` — tạo bằng `POST /api/v1/auth/register` (gói `TRIAL` 14 ngày, `DOCUMENT` 20). Không qua trang đăng ký: trang đó tự sinh OTP trong trình duyệt rồi **gửi thư thật qua Resend** — tránh gửi thư ra ngoài. Lần đăng nhập đầu kích hoạt tài khoản (`PENDING` → `ACTIVE`) |
| Tài liệu | 3 tệp Markdown hư cấu viết cho buổi này — "Bảng giá dịch vụ nha khoa 2026" (4 đoạn), "Lịch hẹn và trả góp" (3 đoạn), "Khuyến mãi tháng 10 (hết hạn)" (1 đoạn, để gỡ) — cộng `bang-gia.xlsx` (đuôi sai) |

### Bảng minh chứng cuối — 8 UC, theo thứ tự diễn tập

Cột "Độ trễ" là thời gian thấy được trên giao diện (Playwright đo từ lúc bấm tới lúc kết quả hiện), máy dev, một
người dùng. **Không phải cổng** (11/10), chỉ ghi số thật.

| UC | Bước đặc tả | Thao tác | Kết quả thấy được | Độ trễ |
|---|---|---|---|---|
| — | đăng nhập | `quantri@dien-tap-gd4.test` | vào `/hop-thu` | 3,2 s (gồm tải trang) |
| 020 | 2.1 | Kho tri thức (tenant mới) | "Kho tri thức đang trống" + nút "Tải lên tài liệu" | — |
| 018 | 4.1 | Chọn `bang-gia.xlsx` | "Định dạng .xlsx không được hỗ trợ. Nhận .pdf, .docx, .txt, .md, .html." — không request nào | tức thì |
| 018 | 1–10 | Tải `bang-gia-dich-vu-gd4.md`, tiêu đề gợi ý "bang gia dich vu gd4" → đặt "Bảng giá dịch vụ nha khoa 2026" | `202`; toast "Đã nhận tài liệu. Quá trình nạp đang chạy nền." → màn tiến độ | 1,4 s |
| 019 | 1–12 | Ở lại màn tiến độ | 6 bước đều có dấu xong; "… đã có 4 đoạn trong chỉ mục và sẵn sàng để tác tử AI truy hồi." | 4,9 s tới `DONE` |
| 018–019 | 1–12 | Tải thêm "Lịch hẹn và trả góp", "Khuyến mãi tháng 10 (hết hạn)" | `DONE` 3 đoạn · 1 đoạn | nhận 0,4 / 0,8 s · `DONE` 2,3 / 2,3 s |
| 018 | 7.1 (đối chứng) | Tải lại đúng tệp bảng giá dưới tiêu đề **khác** "Bảng giá bản sao" | nhận (`202`), nạp 4 đoạn — đúng đặc tả: luật trùng là cặp `(tenant_id, title)`, không phải nội dung | 0,2 s |
| 019 | — | `/tri-thuc/tien-do` | việc nạp gần nhất "Hoàn tất · Bước 6/6 · Tải lên mới · Lần thử 1 · 4 đoạn" | — |
| 020 | 2 | Gõ `tra gop` | đúng 1 dòng "Lịch hẹn và trả góp" (không dấu khớp có dấu) | trì hoãn 300 ms |
| 020 | 4 | Mở "Bảng giá dịch vụ nha khoa 2026" | 4 đoạn, cột # · Mục · Nội dung đoạn · Token · Mô hình nhúng | — |
| 020 | 422 · 5 | "Sửa thông tin" → tiêu đề "Lịch hẹn và trả góp" → rồi sửa mô tả | "Đã có tài liệu khác tên 'Lịch hẹn và trả góp' ở version 1" trong hộp thoại; sau đó toast "Đã cập nhật thông tin tài liệu." | `PATCH` 0,18 / 0,09 s |
| 020 | 6 | "Nạp lại tài liệu" | toast "… Bản hiện tại vẫn phục vụ tới khi bản mới xong."; sang tiến độ của **id mới** `86859680…` ≠ `9d6e36f3…`; danh sách về đúng một dòng **v2** "Sẵn sàng" | 30,9 s tới v2 (bộ quét ≤ 60 s) |
| 020 | 7 | Chọn "Bảng giá bản sao" → "Gỡ khỏi kho"; rồi "Khuyến mãi tháng 10" | hộp xác nhận nói rõ AI thôi trích dẫn, câu cũ giữ trích dẫn, chuyển "Đã lưu trữ"; kho còn 2 tài liệu; lọc "Đã lưu trữ" thấy lại cả hai (và v1 của bảng giá) | `DELETE` 0,13–0,25 s |
| 020 | 7 · hạn mức | `usage_records` | `DOCUMENT` **2**, `STORAGE_MB` **1 827** byte = 1 026 + 801 — chỉ hai tài liệu đang phục vụ | — |
| 020 | 8 | Kiểm toán → Nhật ký | `DOCUMENT_UPDATED` · `DOCUMENT_REINDEXED` · `DOCUMENT_ARCHIVED`, người làm `quantri@dien-tap-gd4.test`, có giờ | — |
| — | widget | Cài đặt → Widget → "Sinh mã nhúng", tên miền `localhost` | `wk_39ef…`; `404 → 201 POST → 200 PUT /api/v1/widget-config` | — |
| 023 | KPI | Khách A: "Xin chào" | câu chào mẫu; giám sát "Chào hỏi · GREETING (96%) · template · 0 token · 0 ₫" | 1,0 s |
| 023 | 1–12 | "Niềng răng mắc cài sứ bao nhiêu tiền?" | "… 45.000.000 đồng cho toàn bộ liệu trình và đã bao gồm hàm duy trì ạ [1]" · "Nguồn: Bảng giá dịch vụ nha khoa 2026"; đoạn trích **ẩn** tới khi bấm nguồn | 1,7 s |
| 027 | 3.1 | 👍 dưới câu đó | "Cảm ơn bạn đã đánh giá!" ngay, không hỏi lý do | 0,19 s |
| 023 | 1–12 | "Chi phí tẩy trắng răng bằng laser là bao nhiêu?" | "… 2.500.000 đồng cho hai hàm [1]", cùng nguồn | 1,6 s |
| 027 | 3 | 👎 dưới câu đó | 4 lý do; nút "Gửi" khoá tới khi chọn; chọn "Trả lời thiếu" + nhận xét → cảm ơn | 0,07 s |
| 023 | 1–12 | "Chi phí trả góp 12 tháng qua công ty tài chính là bao nhiêu?" | "… phí hồ sơ là 500.000 đồng và … trả trước tối thiểu 30% ạ [1]" · "Nguồn: Lịch hẹn và trả góp" — trích đúng tài liệu thứ hai | 1,4 s |
| 025 | 1–6 | "Chi phí điều trị tủy răng bao nhiêu tiền?" | "Dạ hiện em chưa tìm thấy thông tin phù hợp … Anh/chị có muốn em chuyển cho nhân viên tư vấn không ạ?" — không bịa giá, không nguồn | 1,3 s |
| 025 | 3.3 | "Vậy chi phí lấy tủy răng hàm là bao nhiêu?" (cùng hội thoại) | "Dạ em xin lỗi vì chưa giúp được anh/chị. Em chuyển anh/chị sang nhân viên tư vấn ngay ạ."; chân widget "Đang chờ nhân viên tiếp nhận…" | 1,2 s |
| 025 | 5 / 3.1 | Khách B: "Đơn hàng DH20261114 của em bao nhiêu tiền?" | "Dạ câu này cần tra cứu thông tin cụ thể (đơn hàng, …) … Em chuyển anh/chị sang nhân viên hỗ trợ ngay ạ." — luật mã đơn, **không gọi LLM**; `PENDING_AGENT` | 0,21 s |
| 023 | CRM | Hộp thư → hội thoại khách A | "Chờ nhân viên"; ba tin BOT có "Nguồn: …" như widget; 5 tin BOT có 👍/👎 | mở 1,2 s |
| 027 | 4 | Nhân viên 👎 câu trả góp: bấm Gửi khi chưa chọn → chọn "Trả lời thiếu" + nhận xét + câu đúng | "Chọn một lý do." → `201`; dưới tin "Quản trị Diễn tập · Trả lời thiếu · “Thiếu lựa chọn 0% qua thẻ tín dụng” · Câu trả lời đúng: …" | 0,17 s |
| 025 | 3.1 | "Nhận xử lý" → trả lời khách | `200 …/assign`; "Đang xử lý"; tin nhân viên vào luồng | 0,13 s |
| 023 · 025 · 027 | 10 · 4 · 8 | Tác tử AI → Giám sát lượt xử lý | 10 thẻ; thẻ C1 "Truy hồi tri thức · PRICING_POLICY (94%) · 1.148 token · Độ trễ theo chặng 1.4 s — Truy hồi 397 ms"; lọc "Chỉ lượt từ chối" 3 thẻ (2 câu tủy răng + đơn hàng); lọc "Bị chê" đúng **2** thẻ (khách chê C2, nhân viên chê C3) | 0,03–0,1 s mỗi lọc |
| 027 | 7 | Phân tích → Hiệu quả AI | "Phản hồi tích cực **33.3%** — trên 3 lượt đánh giá của nhân viên và khách" = 1 👍 ÷ (2 của khách + 1 của nhân viên) | 0,19 s |
| 025 | 8 | Tri thức → Khoảng trống | 3 dòng: đơn hàng "Cần dữ liệu thời gian thực", hai câu tủy răng "Chưa có tài liệu"; mỗi dòng 1 khách · 1 lần | 0,22 s |
| 026 | 1–7 | Hội thoại khách A → "Đánh dấu xong" | "Đang tóm tắt hội thoại vừa kết thúc…" → khối 4 phần, chân "Sinh khi kết thúc" | **6,0 s** |
| 026 | 4.1 | "Tóm tắt lại" | nút "Đang tóm tắt…" → "Nhu cầu chính: Khách hỏi chi phí niềng răng mắc cài sứ, tẩy trắng răng bằng laser, trả góp 12 tháng và chi phí điều trị lấy tủy răng hàm · Thông tin khách đã cung cấp: Không có · Vấn đề chưa giải quyết: Nhân viên đề nghị đặt lịch khám nhưng chưa nhận được phản hồi … · Bước tiếp theo: Hỏi lại khách có muốn chốt lịch hẹn khám …" · "Nhân viên bấm tóm tắt lại · `gemini-3.5-flash-lite@tt2`" | 4,1 s (`POST …/summary` 3,4 s) |
| 026 | 1.1 | Hội thoại chỉ có "Xin chào" → "Đánh dấu xong" | trong 2 phút: "Đang tóm tắt hội thoại vừa kết thúc…"; sau 2 phút: "Chưa có bản tóm tắt."; worker "bỏ qua — 3 tin, quá ngắn", không gọi LLM | — |
| 041 | 1–2 | Kiểm toán → Yêu cầu xoá → "Tạo yêu cầu" cho "Khách web #17F7" (khách A), căn cứ Điều 16 NĐ 13/2023 | `201`; trang yêu cầu "Chờ thực thi", bảng phạm vi 14 dòng; danh sách "Chưa xác minh" | 0,13 s |
| 041 | 2.1 | Tạo yêu cầu thứ hai | "Khách này đã có một yêu cầu xoá đang xử lý — không tạo yêu cầu thứ hai." (`409`) | 0,02 s |
| 041 | 3.1 | "Thực thi xoá" khi chưa xác minh | "Chưa xác minh danh tính chủ thể dữ liệu …" (`409`), không gọi ai-service | 0,03 s |
| 041 | 3–4 | "Xác minh danh tính" | toast; "Người xác minh danh tính: Quản trị Diễn tập" | 0,04 s |
| 041 | 5–6 | Xem trước phạm vi | "… sẽ đụng tới 14 bảng"; "0 dòng bị xoá hẳn, 14 dòng được ẩn danh hoá, 1 bảng số liệu tổng hợp giữ nguyên — chưa tính 6 bảng phía AI …"; cảnh báo "Phạm vi xoá dừng ở hệ thống này" | 0,05 s |
| 041 | 7–10 | "Thực thi xoá" → gõ `XOA VINH VIEN` | "Đã hoàn tất", **14/14**: `ai_interactions` 7 (5 lượt chat + 2 lượt tóm tắt) · `ai_feedback` 3 · `contacts` 1 · `channel_identities` 1 · `messages` 11 · `conversations` 1 · `metrics_daily` giữ tổng hợp | 0,31 s |
| 041 | 10–11 | Biên bản · nhật ký · hộp thư | "Đã xoá dữ liệu của khách mã c7ed6ace trên 14 bảng … Danh tính do Quản trị Diễn tập xác minh …"; `ERASURE_REQUESTED` → `ERASURE_IDENTITY_VERIFIED` → `ERASURE_EXECUTED`; hộp thư "Khách đã ẩn danh", cột phải "Chưa có bản tóm tắt", hết "Lượt xử lý gần nhất của AI"; CSDL 11 tin khách/bot/nhân viên = "[Nội dung đã xoá theo yêu cầu của chủ thể dữ liệu]", tin `SYSTEM` giữ nguyên | — |

### Chỗ vỡ gặp khi diễn tập

| # | Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|---|
| 1 | Gỡ "Bảng giá bản sao" rồi gỡ "Khuyến mãi" → mạng có **ba** `DELETE`, id bản sao **hai lần** (cả hai 200); nhật ký hai dòng `DOCUMENT_ARCHIVED` cho cùng một tài liệu. Hạn mức vẫn đúng (gỡ lần hai luỹ đẳng, không trả thêm) | `ListPage` giữ vùng chọn theo id; dòng vừa gỡ rời danh sách nhưng id vẫn ở `daChon`, lần chọn kế tiếp gửi cả id cũ | **Đã sửa** `components/layout/ListPage.tsx`: chỉ tính id còn trên trang đang hiện. Đi lại: tải "Tạm A", "Tạm B", gỡ lần lượt → đúng **2** `DELETE`, mỗi id một lần. Áp cho cả `ContactsPage` (cùng mẫu) |
| 2 | Mở hộp thư hội thoại khách A lần đầu → `500 GET /api/v1/ai-interactions?conversationId=…`; 👍/👎 của khách không hiện ở hộp thư. Sau khi nhân viên đánh giá thì hết | `AiInteractionMapper.luot` tra tên người đánh giá bằng `tenNhanVien.get(raterUserId)`; trang không có nhân viên nào đánh giá thì bảng tên là `Map.of()`, và `Map.of().get(null)` (khách không có `raterUserId`) ném NPE. GD2 không gặp vì hội thoại W1 đã có nhân viên chê trước khi mở | **Đã sửa** — chỉ tra khi `raterUserId != null`; thêm ca `danhSachLuot_chiCoKhachDanhGia_200`. Đi lại trên giao diện: khách C 👍 câu "bọc răng sứ zirconia" → hộp thư `200`, hiện đánh giá "Khách hàng" |
| 3 | Khách A gửi 6 câu nhưng CRM thấy **hai danh bạ**: "Xin chào" ở `Khách web #F198`, 5 câu sau ở `Khách web #17F7`. Mạng có hai `POST /widget/session` | **Widget (UC009, Dev B)**: `khoiTao()` chạy lúc nạp trang; khách gửi tin trước khi phiên trả về thì `gui()` thấy chưa có token, gọi `khoiTao()` lần nữa → hai phiên song song, phiên về sau ghi đè token. Tái hiện chắc chắn khi làm chậm `/widget/session` 1,5 s: gửi ngay → 2 phiên; chờ phiên rồi gửi → 1 phiên | **Không sửa** (phần Dev B) — ghi vào tin báo mục 0.3. Hệ quả lên UC041: xoá khách A bỏ sót câu "Xin chào" ở danh bạ kia. Gợi ý: giữ một promise khởi tạo dùng chung (`this.dangKhoiTao ??= …`) |

Hai lần ❌ trong script (bước nạp 2 và 3 "không đủ 6 bước") là lỗi **của script**: bộ chọn `ol li` bắt cả danh sách
toast của sonner (cũng là `ol`). Các bước đều có dấu xong, không phải chỗ vỡ.

### Cổng ra — kiểm máy

| Lệnh | Kết quả |
|---|---|
| `mvn -f java-core/pom.xml test -Dtest=AiInteractionRelayIntegrationTest` | 8/8 (7 + ca mới) |
| `mvn -f java-core/pom.xml test` (cả bộ, cần Docker) | **304/304**, 26 lớp (303 + ca mới) |
| `npm run typecheck` · `npm run build` (web-dashboard) | sạch |
| ai-service · gateway · web-widget | không đổi ở GD4 |

### Thấy khi chạy, ngoài 8 UC — báo Dev B, chưa sửa

- Lỗi đua phiên widget (chỗ vỡ 3).
- `FormDialog` vẫn để lại unhandled rejection sau mỗi lượt 4xx (1 lần ở 422 sửa tiêu đề, 2 lần ở 409 của UC041) — đã báo GD1.
- Thanh trên luôn "Mất kết nối, đang thử lại…" (gateway không route `/ws`) — đã báo GD1.
- `GET /api/v1/tool-calls` vẫn 500 (`NoResourceFoundException` rơi vào handler chung) — đã báo GD1.
- Trang đăng ký gửi OTP **thật** qua Resend bằng khoá nằm trong gói JS — nhắc lại việc thu hồi khoá (báo GD2).

### Dữ liệu sau khi kiểm

Tenant B **không bị đụng**. Tenant diễn tập `df124522…`: kho **2 tài liệu** (bảng giá v2, lịch hẹn và trả góp) + 4 bản
`ARCHIVED` (bảng giá v1, bản sao, khuyến mãi, "Tạm A/B" của lượt kiểm lại chỗ vỡ 1); `DOCUMENT` 2, `STORAGE_MB` 1 827
byte, `AI_TOKEN` 6 803 / 500 000, `CONVERSATION` 8. Kênh widget `wk_39ef…`. Danh bạ: khách A `ANONYMIZED` (yêu cầu xoá
`05c76ccc…` `COMPLETED`); `#F198` (câu chào của A, `RESOLVED`, không tóm tắt); khách B `PENDING_AGENT`; khách C (một lượt
RAG + 👍); 4 khách chỉ chào (lượt tái hiện chỗ vỡ 3). **Gemini: 8 lượt gọi** (6 trả lời + 2 tóm tắt), 0 lỗi.

### Giảm độ sâu — ghi nhận ở GD4

- Câu mẫu từ chối nói "tài liệu của cửa hàng" kể cả với phòng khám — câu mẫu dùng chung mọi ngành, chưa theo
  `industry` của tenant.
- Thẻ giám sát của lượt từ chối theo luật mã đơn vẫn mang nhãn "Truy hồi tri thức · PRICING_POLICY" (nhãn theo ý định
  router đã phân), dù lượt đó không truy hồi và không gọi LLM — phân biệt được bằng "template · 0 token".
- `POST /api/v1/documents` trả `uploadedByName = null` (danh sách và chi tiết thì có tên) — hộp thoại không dùng trường này.
- Chi phí mọi lượt hiện "0 ₫" — nợ `cost_vnd = 0` từ N13–N15.

### Phải giải thích được

- **Vì sao diễn tập trên tenant mới thay vì dọn tenant B:** dọn là xoá dữ liệu làm minh chứng GD1–GD3, và "kho trống →
  đầy đủ" mới là kịch bản demo thật. Tenant mới cũng kiểm thêm một đường chưa ai đi: tenant vừa đăng ký có hạn mức,
  thuê bao dùng thử, kênh widget từ con số 0.
- **Vì sao chỗ vỡ 2 không lộ ở GD2:** lỗi chỉ xảy ra khi một trang lượt có đánh giá của khách mà **không** có đánh giá
  nào của nhân viên. Cảnh GD2 mở W1 sau khi đã có nhân viên chê. Diễn tập theo đúng thứ tự người dùng thật (khách bấm
  trước, nhân viên mở hộp thư sau) mới lộ — đó là giá trị của một lượt "một lèo".
- **Vì sao lỗi đua phiên widget ảnh hưởng UC041:** quyền xoá đi theo danh bạ. Một người bị tách thành hai danh bạ thì
  một yêu cầu xoá chỉ phủ một nửa. Đây là lý do nối danh tính khách phải đúng **trước** mọi thứ khác trong chuỗi
  chăm sóc khách hàng.
