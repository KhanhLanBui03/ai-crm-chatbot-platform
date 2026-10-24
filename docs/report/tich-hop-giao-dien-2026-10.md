# Tích hợp giao diện 8 UC của Dev A — minh chứng đợt GD1–GD4

Kế hoạch và luật đợt: [`docs/plan/ke-hoach-tich-hop-giao-dien.md`](../plan/ke-hoach-tich-hop-giao-dien.md).
Thước đo: `docs/Dac-ta-UseCase-Module-AI.docx`. Hợp đồng đã đổi: [`docs/contracts/giao-dien-gd.md`](../contracts/giao-dien-gd.md).

Một UC chỉ tick khi đủ 4 điều: (a) luồng chính bấm được trên giao diện thật · (b) luồng phụ / mã lỗi
trong DoD đã thử · (c) compile / typecheck / test sạch · (d) có dòng minh chứng ở đây.

---

## GD1 — Kho tri thức: UC018 · UC019 · UC020 (24/10/2026)

**Nhánh** `feat/giao-dien-gd1-kho` (tách từ `e5cb8ff`). Kiểm bằng trình duyệt thật (Chrome không giao
diện, Playwright điều khiển — script ở scratchpad, không vào repo), `VITE_USE_MOCK=false`, mọi lời gọi
qua gateway `:8080`. Ảnh chụp: người dùng tự chụp lại — danh sách cảnh ở cuối mục.

| | UC018 | UC019 | UC020 |
|---|---|---|---|
| (a) luồng chính trên giao diện | ✅ | ✅ | ✅ |
| (b) luồng phụ, mã lỗi | ✅ 4.1 · 4.2 · 6.1 · 7.1 · 8.1 · 403 | ✅ 4.1 · hàng đợi chung · ngừng hỏi lại | ✅ 2.1 · 5.1 · 7 · 7.2 · 403 · 422 · 8 (*) |
| (c) kiểm máy | ✅ | ✅ | ✅ |
| (d) minh chứng | ✅ | ✅ | ✅ |

(*) UC020 bước 8 **ghi** kiểm toán — đạt, kiểm bằng CSDL. Màn **xem** Nhật ký kiểm toán là của UC040
(Dev B) và `GET /api/v1/audit-logs` chưa có controller (trả 500) — không mở được trên giao diện.

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

- WebSocket `/ws` 404: gateway không có route, java-core chưa có endpoint STOMP → thanh trên luôn "Mất kết nối".
- `GET /api/v1/tool-calls` (MCP, đã hoãn) và `GET /api/v1/audit-logs` (UC040) trả **500**: không có controller,
  route lạ rơi vào handler chung thành 500 thay vì 404.
- ai-service chưa tự đăng ký Eureka (`src/api/eureka.py` còn là khung).

### Dữ liệu sau khi kiểm

Kho tenant B về đúng 2 tài liệu nha khoa (mọi tài liệu thử đã gỡ bằng chính thao tác gỡ trên giao diện);
hạn mức `DOCUMENT` = 2, `STORAGE_MB` = 3 861 byte (= 1 886 + 1 975). Tài liệu thử còn ở `ARCHIVED`,
0 đoạn — không ảnh hưởng truy hồi. Thêm mới, để dùng tiếp ở GD2/GD3: tài khoản nhân viên B và tenant
"Phòng khám trống GD1".

### Cảnh cần chụp (người dùng tự chụp, đặt `docs/report/scr-gd1-*.png`)

1. Hộp thoại tải lên báo sai đuôi (4.1) · 2. 409 hạn mức trong hộp thoại (6.1) · 3. Màn tiến độ `FAILED`
ảnh quét (8.1) · 4. Màn tiến độ `DONE` đủ 6 bước · 5. `/tri-thuc/tien-do` khi đang nạp lại ·
6. Tìm "bao hanh" · 7. Chi tiết + bảng đoạn có mô hình nhúng · 8. 422 trùng tiêu đề · 9. Danh sách
trong lúc nạp lại (v3 "Chờ nạp" + v2 "Sẵn sàng") · 10. Toast 409 · 11. Hộp xác nhận gỡ · 12. Lọc
"Đã lưu trữ" · 13. Toast 502 khi ai-service tắt + danh sách "Không tải được dữ liệu" · 14. Toast 403 của
nhân viên · 15. Kho rỗng (tenant mới).

### Phải giải thích được

- **Vì sao dashboard không gọi thẳng ai-service:** java-core là chỗ có JWT đã xác thực, quyền
  `TENANT_ADMIN`, hạn mức gói và nhật ký kiểm toán — ba thứ ai-service không có và không được có
  (ADR-0002, ADR-0014). Đi thẳng thì tenant phải lấy từ trình duyệt.
- **Vì sao tài liệu của tenant khác trả 404 chứ không 403:** RLS làm dòng đó vô hình; 403 sẽ xác nhận id
  có tồn tại ở đâu đó — dò được. 404 cho cả hai trường hợp là đúng đặc tả UC020.
- **Vì sao nạp lại đổi `id` mà kho không trống giây nào:** bản bóng là dòng mới (version kế tiếp, cùng tệp);
  bản cũ vẫn `READY` và vẫn được truy hồi; lúc bản bóng `READY`, ai-service xoá đoạn cũ và `ARCHIVED`
  bản cũ **trong cùng transaction** — người đọc thấy hoặc trạng thái trước, hoặc trạng thái sau (ADR-0031).
