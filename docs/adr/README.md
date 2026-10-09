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
| 0010 | ~~ai-service dùng `app/` src-layout~~ — **thay bởi 0015** | Lệch so với KH |
| 0011 | shadcn/ui trên Tailwind v4; 21 màn vẽ chi tiết + 37 màn từ 6 mẫu lặp | Lệch so với KH |
| 0012 | Redux Toolkit + RTK Query quản lý toàn bộ state của web-dashboard | Lệch so với KH |
| 0013 | WebSocket cho hộp thư thời gian thực, xác thực bằng khung `AUTH` | KH mục 4.3 |
| 0014 | java-core là mặt tiền duy nhất của dashboard, kể cả với dữ liệu Track B | Rà soát truy vết |
| 0015 | Cấu trúc `src/` + tách tầng suy luận `inference/` theo Master Plan v8.0 | Thay ADR-0010 |
| 0016 | Role runtime tên `ai_app`; nhãn kết quả Lead vào `sales.lead_scores` | Lệch Master Plan |
| 0017 | Chốt 4 mâu thuẫn hợp đồng (endpoint, topic, golden set, tập test) + siết CI | Rà soát Tuần 1 |
| 0018 | Bỏ nhánh A (TF-IDF + LinearSVC), ưu tiên nhánh C (ai-embed) và nhánh B (XLM-R) | Quyết định phạm vi Ngày 4-5 |
| 0019 | Chốt nhánh ship Intent Router (Nhánh C qua ONNX INT8) và thiết lập ngưỡng Abstention | Quyết định ship Ngày 6 (UC022 3/4) |
| 0020 | Chốt hợp đồng liên làn đợt 1: endpoint `/v1/ai/**`, ranh giới UC018, `title` ≤ 255 (phần topic, bộ vàng, cỡ tập test do 0017 chốt) | Mâu thuẫn tài liệu |
| 0021 | Cổng parity INT8 trượt: hoãn phán quyết, phân xử bằng Recall@5 ở Ngày 7 — **06/10: ship INT8, bỏ phân xử fp32** | Đo thực nghiệm |
| 0022 | Tệp tài liệu gốc lưu ở object storage S3 (RustFS ở dev, AWS S3 trên cloud) | Thiết kế UC018 |
| 0023 | Hạn mức tài liệu tính theo lượng đang có (số lượng + dung lượng), không theo lượt tải | Chốt của nhóm 27/09 |
| 0024 | Nạp tài liệu commit theo chặng; chống trùng ở `ai.processed_events`; bộ quét job kẹt qua hàm `SECURITY DEFINER`; DLQ chỉ cho sự kiện chưa thành trạng thái | Thiết kế UC019 Ngày 5 |
| 0025 | _(để dành — chưa viết)_ Làn từ khoá theo âm tiết | Thiết kế UC019 Ngày 4 |
| 0026 | Bỏ fine-tune embedding — ship bge-m3 pretrained INT8 | Quyết định phạm vi 27/09 |
| 0027 | Lượt chat chạy bằng pipeline tuần tự `run_turn`, không dùng LangGraph 8 node | Thiết kế UC023 Ngày 8 |
| 0028 | LLM sinh câu trả lời: Gemini 3.5 Flash-Lite (`minimal`) qua client trung lập chuẩn OpenAI | Phép thử 10 câu 08/10 |
| 0029 | Từ chối UC025: bốn lý do sinh ở bốn chỗ cố định, luật "0 trích dẫn ⇒ NOT_COVERED", ngưỡng chọn từ đường cong trên bộ vàng | Thiết kế UC025 Ngày 10 |
| 0030 | Ghi `ai_interactions` đồng bộ mỗi lượt; bộ chấm tự động mẫu 5% qua hàm `SECURITY DEFINER` thứ hai | Thiết kế UC027 Ngày 10 |
| 0031 | Nạp lại tài liệu bằng bản ghi bóng — đổi bản trong một transaction, 0 giây kho trống | Thiết kế UC020 Ngày 11 |
| 0032 | Tóm tắt hội thoại: nhiệt độ 0 ghim cứng, phiên bản model là ảnh chụp, PATCH rồi mới đánh dấu xong | Thiết kế UC026 Ngày 12 |
| 0033 | Xoá dữ liệu cá nhân phía AI: `contact_id` trên tài liệu, hội thoại do java-core gửi, chốt token nội bộ | Thiết kế UC041 Ngày 12 |

`KH` = tài liệu `Ke-hoach-do-an-Chatbot-AI-CRM-v2-nhom-2-nguoi.docx`.
