# Ôn tập Ngày 4 — UC019 (1/2): phân tích cú pháp, chuẩn hoá tiếng Việt, chia đoạn

> Viết bù 06/10/2026. Code: `ai-service/src/ai/rag/chuan_hoa.py`, `src/ai/rag/tsquery.py`,
> `src/ai/rag/ingest/`, `migration/V210__unaccent_va_lan_tu_khoa.sql`.

## "Phải giải thích được"

**Vì sao `normalize_vi` phải là MỘT hàm dùng chung hai đầu? Ví dụ hỏng thế nào.**
- Ví dụ thật trong `data/kb_samples/huong-dan-bao-quan-noi-chien.txt`: tài liệu viết "thuỷ tinh" ở
  dạng **NFD**, tức chữ `u` và dấu hỏi là hai code point rời. Khách gõ "thủy tinh" bằng Unikey thì ra
  **NFC**.
- Nếu phía nạp chuẩn hoá NFC mà phía hỏi quên, hai chuỗi khác nhau từng byte:
  - làn từ khoá không khớp;
  - vector nhúng lệch.
- **Không có exception nào, chỉ có recall tụt.** Hai hàm "gần giống nhau" sớm muộn sẽ lệch nhau ở
  một chi tiết như thế.
- Ghi nhớ thêm: `normalize_vi` **không** hạ chữ thường và **không** bỏ dấu, vì kết quả của nó còn
  được lưu làm `content`, hiển thị trong trích dẫn và đưa vào model nhúng. Bỏ dấu cho làn từ khoá
  làm ở SQL (`knowledge.f_unaccent`).

**Vì sao `unaccent` phải bọc trong hàm `IMMUTABLE` mới đánh chỉ mục được?**
- Cột GENERATED và chỉ mục biểu thức chỉ nhận hàm **IMMUTABLE**. Postgres tính giá trị một lần lúc
  ghi rồi lưu lại, nên cần lời hứa "cùng đầu vào, luôn cùng đầu ra".
- `unaccent(text)` gốc chỉ là **STABLE**: nó tìm từ điển theo `search_path` **lúc chạy**, đổi
  `search_path` là có thể ra kết quả khác. Postgres báo lỗi `generation expression is not immutable`.
- Hàm bọc `knowledge.f_unaccent` chốt cứng cả hai thứ phụ thuộc `search_path`: gọi `public.unaccent`
  và truyền từ điển `'public.unaccent'::regdictionary`.
- Cái giá: IMMUTABLE là **lời hứa**, Postgres không kiểm. Ai đó sửa `unaccent.rules` trên máy chủ thì
  các dòng đã lưu vẫn mang giá trị cũ cho tới khi được ghi lại. Với tiếng Việt, bảng quy tắc gần như
  bất biến, nên chấp nhận được.

**Vì sao phrase query dùng `OR` giữa các từ chứ không dùng `AND`?**
- Khách gõ "chính sách đổi trả laptop" trong khi kho không có chữ "laptop": `AND` trả **rỗng** chỉ
  vì một từ thừa. `OR` vẫn trả các đoạn về chính sách đổi trả; đoạn khớp nhiều từ hơn xếp cao hơn.
- Làn từ khoá là một trong hai nguồn của RRF, nên việc của nó là **không bỏ sót**. Lọc nhiễu đã có
  làn vector và RRF lo.
- **Bên trong một từ ghép** thì dùng `<->` (hai âm tiết liền nhau, đúng thứ tự). Nhờ vậy "chính sách"
  không khớp một đoạn có "sách" ở đầu trang và "chính" ở cuối trang.

## Liên hệ kết quả Ngày 6

Câu **không dấu** mất lợi thế của `<->` vì pyvi không nhận ra "chinh sach" là một từ. Ngày 6 đo
được: làn từ khoá chỉ đạt 0,53 recall@5, nhưng ở câu không dấu nó vẫn kéo hybrid lên trên dense
(0,43 so với 0,29).
