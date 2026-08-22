# ADR-0013 — WebSocket cho hộp thư thời gian thực, xác thực bằng khung AUTH

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-08-22
- **Làn sở hữu:** Track A

## Bối cảnh

SCR019 + SCR020 (hộp thư hợp nhất) là màn hình nhân viên chăm sóc khách hàng mở suốt ca làm.
Dữ liệu của nó thay đổi vì **người khác**: khách nhắn tin, tác tử AI trả lời, đồng nghiệp nhận
xử lý một hội thoại. Trình duyệt không có cách nào biết được nếu không ai nói cho nó.

Một hộp thư đứng im vì mất kết nối trông y hệt một hộp thư đứng im vì không có khách nhắn. Khác
biệt chỉ lộ ra khi khách gọi điện hỏi vì sao không ai trả lời — nghĩa là chi phí của việc làm sai
chỗ này không nằm ở giao diện mà nằm ở chất lượng dịch vụ.

Ba ràng buộc riêng của dự án:

1. **Chỉ nói chuyện với gateway `:8080`.** Không mở một cổng riêng cho luồng đẩy.
2. **`tenant_id` luôn từ ngữ cảnh đã xác thực** (quy tắc bất biến của ADR-0001).
3. **java-core chưa có endpoint đẩy.** Phía trình duyệt phải dựng được và kiểm được **trước**,
   nếu không hai làn chặn nhau.

## Các phương án đã cân nhắc

### Cơ chế truyền

| Phương án | Ưu | Nhược |
|---|---|---|
| **A.** Hỏi lại theo chu kỳ (polling) | Đơn giản nhất, không thêm giao thức | 20 nhân viên × 5 giây = 240 request/phút cho một tenant *khi không có gì xảy ra*; độ trễ vẫn tới 5 giây; hạn mức và log đều gánh phần lớn là request rỗng |
| **B.** Server-Sent Events (SSE) | Một chiều, nhẹ, tự nối lại sẵn có | Không gửi ngược lên được, nên `SUBSCRIBE` phải đi bằng một request HTTP khác; giới hạn 6 kết nối mỗi origin trên HTTP/1.1 là cái bẫy nếu nhân viên mở nhiều tab |
| **C.** WebSocket | Hai chiều nên `SUBSCRIBE`/`PING` đi cùng đường; Spring có sẵn `WebSocketHandler`; gateway đã hỗ trợ nâng cấp giao thức | Phải tự viết nối lại, nhịp tim, xác thực |

### Cách xác thực

| Phương án | Nhược |
|---|---|
| **A.** `Authorization: Bearer` | **Không dùng được.** `new WebSocket(url)` của trình duyệt không đặt được header. |
| **B.** `?access_token=…` trên URL | Token vào access log của gateway, vào `Referer`, vào lịch sử trình duyệt. Một dòng log là một token dùng lại được cho tới khi hết hạn. |
| **C.** Cookie phiên | Kéo theo CSRF và `SameSite` cho một luồng vốn không cần cookie; dashboard đang dùng token trong bộ nhớ chứ không dùng cookie. |
| **D.** **Khung `AUTH` đầu tiên** | Máy chủ phải giữ socket ở trạng thái chưa xác thực một lúc, và phải tự đóng nếu chờ quá lâu. |

## Quyết định

Chọn **C + D**: WebSocket qua gateway tại `VITE_WS_URL` (`ws://localhost:8080/ws`), xác thực
bằng **khung `AUTH` đầu tiên** chứ không phải query string.

Giao ước đầy đủ: `docs/openapi/dashboard-realtime.md`. Nó không viết bằng OpenAPI vì OpenAPI 3.1
chỉ mô tả được cặp request/response. Nhưng chỉ **phong bì** khung tin là gõ tay — phần thân dùng
thẳng `TinNhan` và `HoiThoaiTomTat` sinh từ `dashboard-api.yaml`, nên đổi hình dạng dữ liệu vẫn
nổ lỗi lúc `tsc` như mọi chỗ khác.

Bốn điểm chốt kèm theo:

1. **Một tin nhắn mới sinh ra hai khung** — `MESSAGE_CREATED` cho nội dung hội thoại và
   `CONVERSATION_UPDATED` cho dòng của nó trong danh sách.
2. **Khung đi thẳng vào cache RTK Query** qua `onCacheEntryAdded`, không qua một slice trung gian.
3. **Một kết nối duy nhất cho cả ứng dụng**, mở theo vòng đời `AppShell`.
4. **Máy chủ giả bằng `ws.link()` của MSW** cài đúng giao ước, kể cả bắt tay và mã đóng.

## Lập luận

**Vì sao không polling.** Con số quyết định: một tenant 20 nhân viên, chu kỳ 5 giây, là 240
request mỗi phút *lúc không có gì xảy ra*. Với 5 tenant thử nghiệm thì gateway phục vụ 1.200
request/phút mà gần như toàn bộ trả về "không có gì mới". Đây không phải tối ưu sớm — nó là phần
lớn tải của hệ thống ở giai đoạn pilot, và nó làm nhiễu mọi số đo hiệu năng khác.

**Vì sao khung AUTH thay vì query string.** Đây là chỗ dễ chọn sai nhất vì query string là cách
mọi hướng dẫn trên mạng viết. Token trên URL đi vào access log của gateway — mà log thì được giữ
lâu, được sao lưu, và được đọc bởi nhiều người hơn cơ sở dữ liệu. Nó biến một access token ngắn
hạn thành một chứng chỉ nằm sẵn trong file văn bản. Giá phải trả cho cách làm đúng chỉ là một
trạng thái "chưa xác thực" và một bộ đếm giờ 10 giây.

**Vì sao hai khung cho một tin nhắn.** Cách còn lại — gửi một khung rồi để trình duyệt tự suy ra
dòng danh sách — không làm được: `unreadCount` phụ thuộc vào việc nhân viên nào đã đọc tới đâu,
dữ liệu chỉ máy chủ có. `lastMessagePreview` thì máy chủ đã tính sẵn lúc ghi. Bắt trình duyệt
tính lại là mời hai bên lệch nhau.

**Vì sao đẩy vào cache RTK Query chứ không vào một slice.** Nếu tin nhắn đến qua WebSocket nằm ở
slice còn tin nhắn lấy qua HTTP nằm ở cache, thì màn hình phải ghép hai nguồn, và mọi câu hỏi
kiểu "tin này đã có chưa" phải hỏi ở hai chỗ. `updateCachedData` vá thẳng vào cache nên danh sách
nhích lên mà không tốn một request nào, và chỉ có **một** chỗ chứa dữ liệu.

**Vì sao mock trước.** Việc dựng và kiểm được toàn bộ phía trình duyệt trước khi java-core có
endpoint là điều kiện để hai làn không chặn nhau. Quan trọng hơn: máy chủ giả cài **cả phần khó
chịu** — bắt tay `AUTH`, đóng `4408`, cặp hai khung. Nếu nó bỏ qua bắt tay thì lỗi bắt tay của
phía trình duyệt chỉ lộ ra lúc nối máy chủ thật, tức là muộn nhất có thể.

## Đánh đổi

1. **Phải tự viết nối lại, nhịp tim, chống trùng.** SSE cho không phần nối lại; WebSocket thì
   không. Đổi lại là `SUBSCRIBE` đi cùng đường thay vì cần một endpoint HTTP riêng. Khoảng 200
   dòng ở `src/api/realtime/ketNoi.ts`, và chúng là loại mã dễ sai lặng lẽ nên đã kiểm bằng 17
   bài kiểm end-to-end.

2. **Nhiễu ngẫu nhiên trong thời gian lùi là bắt buộc.** Gateway khởi động lại làm **mọi** trình
   duyệt đang mở rớt cùng một khoảnh khắc. Nếu tất cả cùng nối lại sau đúng 1 giây thì chính cú
   nối lại đó là đợt tấn công tiếp theo lên gateway vừa hồi phục.

3. **Socket đứt đường vẫn báo `OPEN`** cho tới khi TCP hết giờ — có thể vài phút. Đó là lý do có
   nhịp tim `PING`/`PONG` và bộ đếm giờ chờ `PONG`: không có nó thì "Trực tuyến" nói dối.

4. **Trạng thái phù du phải nằm ngoài cache.** `AGENT_TYPING` cố ý không có `eventId` và không
   được ghi vào cache — cho một dòng chữ tạm bợ vào cache là để nó sống lâu hơn cả hội thoại sinh
   ra nó.

5. **Một hội thoại đổi trạng thái mà chưa nằm trong danh sách vẫn phải hỏi lại máy chủ.** Chỉ máy
   chủ biết bộ lọc có khớp không. Trường hợp này hiếm nên chi phí chấp nhận được, nhưng nó có
   nghĩa là "không bao giờ tốn request" là mô tả gần đúng chứ không phải tuyệt đối.

6. **Máy chủ thật phải định tuyến khung theo `tenant_id`.** Đây là điểm khác quan trọng nhất so
   với HTTP: một request HTTP đi qua RLS vì nó chạy trong phiên `crm_app` có
   `SET LOCAL app.tenant_id`. Một khung đẩy thì do máy chủ tự sinh — nếu bộ phát gửi cho mọi
   socket đang mở thì **RLS không nằm trên đường đi**, và rò rỉ chéo tenant xảy ra mà không có
   truy vấn nào sai. Đây là nghĩa vụ của java-core khi cài `WebSocketHandler`, không phải thứ
   phía trình duyệt kiểm được.

## Hệ quả

- `docs/openapi/dashboard-realtime.md` là giao ước mà java-core phải cài theo.
- `VITE_WS_URL` đã có sẵn trong `.env.example`; đổi `VITE_USE_MOCK=false` là dùng máy chủ thật,
  **không sửa một dòng mã nghiệp vụ nào**.
- Nhánh `/ws` phải được gateway cho phép nâng cấp giao thức và **không** StripPrefix.
- Bộ phát sự kiện phía java-core sẽ dựng trên chính consumer Kafka đã có (`crm.conversation.v1`),
  nên khung WebSocket là bước cuối của cùng một luồng outbox → Kafka → consumer (ADR-0003).
