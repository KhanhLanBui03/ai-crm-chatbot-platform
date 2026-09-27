# Bộ tệp mẫu kho tri thức — UC018

Nguồn dữ liệu cho kiểm thử tải tài liệu (UC018, Ngày 3), nạp và chia đoạn (UC019, Ngày 4–5), và
là nguồn để soạn bộ vàng đánh giá truy hồi (Ngày 6).

## Ranh giới trung thực — ghi vào báo cáo

- **Doanh nghiệp hư cấu.** "Siêu Thị Điện Máy Ngân Hà" không tồn tại. Mã sản phẩm tiền tố `NH-`
  là mã hư cấu, không phải sản phẩm của hãng nào.
- **Nội dung tự soạn bằng mô hình ngôn ngữ** (27/09/2026), không lấy từ tài liệu của doanh nghiệp
  thật. Số liệu (giá, thời hạn, phí) được giữ nhất quán giữa các tệp nhưng không phản ánh thị
  trường thật.
- **Không chứa dữ liệu cá nhân:** không số điện thoại, email, CCCD, tên người, địa chỉ số nhà.
  Đã quét trên text trích từ cả PDF và DOCX trước khi commit.
- Tài liệu viết như doanh nghiệp tự soạn cho khách hàng — không nhắc tới hệ thống chatbot, không
  cài từ khoá nhằm giúp truy hồi dễ hơn.

## Danh sách

`manifest.csv` là nguồn sự thật: 25 dòng, gồm tên tệp, định dạng, tiêu đề, ngôn ngữ, mã HTTP
mong đợi. 20 tệp hợp lệ + 5 tệp lỗi (`tep-qua-lon.pdf` không nằm ở đây — fixture test tự sinh,
vì commit tệp 20 MiB là phình repo vĩnh viễn).

| Định dạng | Tệp |
|---|---|
| PDF (5) | bảng giá, chính sách bảo hành, hướng dẫn máy lọc nước, trả góp, vận chuyển và lắp đặt |
| DOCX (4) | đổi trả bản 1, khách hàng thân thiết, phí sửa chữa, xử lý khiếu nại |
| TXT (4) | câu hỏi thanh toán, câu hỏi giao hàng (không dấu), bảo quản nồi chiên (NFD), giờ mở cửa |
| MD (4) | đổi trả bản 2, đặt hàng online, bảo vệ dữ liệu cá nhân, so sánh máy lạnh |
| HTML (3) | khuyến mãi tháng 10 (trang web đầy đủ), hỏi đáp bảo hành, warranty policy (tiếng Anh) |

## Tệp "bẩn có chủ đích"

| Tệp | Đặc điểm | Để kiểm |
|---|---|---|
| `cau-hoi-giao-hang-khong-dau.txt` | toàn bộ viết không dấu, văn phong tin nhắn | truy hồi khi tài liệu và câu hỏi lệch dấu |
| `huong-dan-bao-quan-noi-chien.txt` | NFD, 8 ký tự U+200B, trộn `hoà`/`hòa`, `thuỷ`/`thủy`, `hoá`/`hóa` | `normalize_vi` (Ngày 4) |
| `khuyen-mai-thang-10.html` | có `<nav>`, `<aside>`, `<footer>`, `<script>`, banner cookie | bóc nội dung chính, bỏ phần rác |
| `chinh-sach-doi-tra.docx` + `chinh-sach-doi-tra-v2.md` | CÙNG tiêu đề, bản 2 đổi 7 → 10 ngày | trùng tiêu đề tăng `version`; truy hồi đúng bản đang hiệu lực |

## Lưu ý khi soạn bộ vàng (Ngày 6)

- **Một câu hỏi có thể có nhiều đoạn đúng.** Thông tin bảo hành xuất hiện ở
  `chinh-sach-bao-hanh.pdf`, được diễn đạt lại ở `faq-bao-hanh.html` và dịch ở
  `warranty-policy-en.html`. Ghi nhận đủ các đoạn đúng, nếu không Recall@5 bị tính thấp oan.
- **Có những cặp thông tin dễ nhầm nhưng không mâu thuẫn** — ví dụ bảo hành 12 tháng (đồ nhỏ) và
  24 tháng (đồ lớn) và 10 năm (máy nén inverter); đổi trả 3 ngày (tại cửa hàng) và 7 hoặc 10
  ngày (online, theo bản). Đây là chỗ làm bài truy hồi có ý nghĩa.
- **Câu hỏi của bộ vàng phải do người soạn**, không dùng cùng mô hình đã viết tài liệu: câu hỏi
  do mô hình sinh dễ lặp nguyên văn câu trong tài liệu và thổi phồng Recall@5.

## Sinh lại

```bash
ai-service/.venv/bin/python data/kb_samples/_tao_tep_mau.py
```

Chỉ PDF, DOCX, tệp TXT bẩn và 4 tệp lỗi được sinh lại từ `_nguon/`. Các tệp TXT/MD/HTML còn lại
tự là nguồn của chính mình — sửa trực tiếp. Script tất định: chạy lại ra đúng từng byte.
