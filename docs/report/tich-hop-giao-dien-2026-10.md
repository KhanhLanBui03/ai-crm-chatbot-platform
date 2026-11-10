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
