# Architecture Decision Records

Mỗi quyết định kiến trúc một file. Nguồn trực tiếp cho **chương 3** của báo cáo.

## Quy ước

- Tên file: `NNNN-mo-ta-ngan-khong-dau.md`, số tăng dần, không tái sử dụng số đã dùng.
- ADR đã ở trạng thái `Chấp nhận` thì **không sửa nội dung**. Muốn đổi quyết định thì viết
  ADR mới với trạng thái `Thay thế` và trỏ ngược về ADR cũ.
- Viết ADR **lúc đang thiết kế**, không phải sau khi code xong (mục 10 của kế hoạch:
  "trí nhớ sau ba tháng luôn hợp lý hóa những quyết định vốn được đưa ra vì hết thời gian").
- Phần **Đánh đổi** là phần hội đồng đọc kỹ nhất. Không được để trống.

## Danh sách

| # | Quyết định | Nguồn |
|---|---|---|
| 0001 | Cô lập dữ liệu đa khách thuê bằng Row-Level Security | KH mục 4.2 |
| 0002 | ai-service không truy cập trực tiếp bảng nghiệp vụ | KH mục 4.2 |
| 0003 | Xử lý bất đồng bộ bằng Outbox Pattern + Kafka | KH mục 4.2, 4.3 |
| 0004 | Khám phá dịch vụ bằng Eureka, gateway định tuyến qua `lb://` | KH mục 4.2, 4.4 |
| 0005 | Truy xuất hệ thống nghiệp vụ qua MCP thay vì adapter riêng | KH mục 4.2 |
| 0006 | Tìm kiếm lai vector + BM25, hợp nhất RRF, xếp hạng lại | KH mục 4.2, 7.1 |
| 0007 | pgvector trong cùng cụm PostgreSQL thay vì vector DB riêng | KH mục 4.2 |
| 0008 | web-dashboard dùng React + Vite thay vì Next.js 15 | Lệch so với KH |
| 0009 | Kafka chạy ở chế độ ZooKeeper thay vì KRaft | Lệch so với KH |

`KH` = tài liệu `Ke-hoach-do-an-Chatbot-AI-CRM-v2-nhom-2-nguoi.docx`.
