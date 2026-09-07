# Mô hình mối đe dọa

Trạng thái: **khung — TODO điền chi tiết**. Chốt cùng thí nghiệm E9 (phòng thủ tiêm chỉ thị).
Nguồn: kế hoạch mục 4.2, 9.2, và bảng thí nghiệm mục 8.

## 1. Tài sản cần bảo vệ

| Tài sản | Nơi lưu | Vì sao đáng giá |
|---|---|---|
| Dữ liệu cá nhân khách hàng | `engagement.CONTACTS`, `engagement.MESSAGES` | Thuộc phạm vi Nghị định 13/2023/NĐ-CP |
| Tài liệu tri thức doanh nghiệp | `knowledge.DOCUMENTS`, `DOCUMENT_CHUNKS` | Tài sản của khách thuê, rò rỉ chéo là lỗi nghiêm trọng nhất |
| Thông tin xác thực MCP | `integration.MCP_CREDENTIALS` | Cho phép gọi vào hệ thống nghiệp vụ thật |
| Thông tin xác thực kênh | `engagement.CHANNEL_INTEGRATIONS` | Chiếm được là mạo danh được Fanpage/OA |
| Ranh giới tenant | RLS + `tenant_id` | Vi phạm một lần là mất toàn bộ niềm tin |

## 2. Tác nhân đe dọa

- **Khách hàng cuối có ý đồ xấu** — nói chuyện với bot qua widget/kênh, không cần tài khoản.
- **Người dùng của một tenant khác** — có tài khoản hợp lệ, cố đọc dữ liệu tenant khác.
- **Người dùng nội bộ tenant vượt quyền** — nhân viên đọc dữ liệu ngoài phạm vi được giao.
- **Hệ thống MCP bị chiếm quyền** — trả về nội dung độc hại vào ngữ cảnh của mô hình.

## 3. Bề mặt tấn công

| # | Bề mặt | Mối đe dọa | Biện pháp |
|---|---|---|---|
| T1 | Webhook kênh (Zalo/FB) | Giả mạo bản tin đến | Xác minh chữ ký bằng `webhook_secret`, chống phát lại theo dấu thời gian |
| T2 | Ô nhập của widget | Tiêm chỉ thị trực tiếp (prompt injection) | Tách chỉ thị hệ thống khỏi nội dung người dùng, lọc đầu vào, đo bằng E9 |
| T3 | Tài liệu được nạp | Tiêm chỉ thị gián tiếp qua nội dung tài liệu | Làm sạch khi nạp, đánh dấu nội dung truy hồi là dữ liệu không đáng tin |
| T4 | Tool Calling qua MCP | AI bị dụ gọi tool phá hoại hoặc vượt tenant | Danh sách cho phép, `risk_level`, `requires_confirmation`, kiểm toán `TOOL_CALL_LOGS` |
| T5 | `ai-service` → dữ liệu | Mô hình trở thành đường vòng qua RLS | ADR-0002: chỉ đi qua API nội bộ, không nối thẳng DB |
| T6 | Truy vấn vector | Trả về chunk của tenant khác | Bắt buộc lọc `tenant_id` **trong** truy vấn vector (ADR-0007) |
| T7 | Gateway | Lạm dụng, dò tài khoản | JWT RS256, rate limit, giới hạn kích thước body ở Nginx |
| T8 | Log và báo cáo đánh giá | Rò rỉ dữ liệu cá nhân ra file | Ẩn danh hóa trước khi đưa vào `eval/`, tách khỏi dữ liệu vận hành |

## 4. Nghị định 13/2023/NĐ-CP — điểm cần có trong thiết kế

Xem kế hoạch mục 9.2.

- [ ] Ghi nhận sự đồng ý của khách trước khi lưu thông tin cá nhân, có dấu thời gian.
- [ ] Chỉ thu thập dữ liệu tối thiểu cần thiết cho mục đích chăm sóc khách hàng.
- [ ] Ẩn danh hóa dữ liệu dùng cho huấn luyện và đánh giá, tách khỏi dữ liệu vận hành.
- [ ] Cơ chế xóa dữ liệu theo yêu cầu, xóa lan truyền tới các bảng dẫn xuất.
- [ ] `platform.AUDIT_LOGS` ghi ai đã truy cập dữ liệu cá nhân nào, vào lúc nào.
- [ ] Chính sách lưu trữ có thời hạn cho nội dung hội thoại.

## 5. Liên hệ với thí nghiệm E9

E9 đo **Attack Success Rate** theo từng nhóm tấn công, bật lần lượt từng lớp phòng thủ.
Bộ kịch bản: `ai-service/eval/adversarial.jsonl` (60–80 kịch bản).
**Chạy trên môi trường cô lập với dữ liệu giả** (kế hoạch mục 8.1).
