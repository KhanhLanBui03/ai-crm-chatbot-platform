# Giao ước thời gian thực: web-dashboard ↔ java-core (WebSocket)

Bổ sung cho `dashboard-api.yaml`. Cùng cặp bên gọi/bên phục vụ, cùng nằm trong Track A —
nhưng **không mô tả được bằng OpenAPI**: OpenAPI 3.1 chỉ nói về cặp request/response, còn ở
đây máy chủ đẩy dữ liệu xuống mà trình duyệt không hỏi. Vì vậy giao ước nằm ở file này, viết
tay, và là nguồn duy nhất cho:

- `web-dashboard/src/api/realtime/sukien.ts` — kiểu TypeScript của **phong bì** khung tin
- `web-dashboard/src/mocks/ws.ts` — máy chủ giả bằng `ws.link()` của MSW
- (sẽ có) lớp `WebSocketHandler` phía java-core

**Phần thân (`message`, `conversation`) KHÔNG khai lại ở đây.** Chúng dùng thẳng `TinNhan` và
`HoiThoaiTomTat` của `dashboard-api.yaml`, tức là type sinh tự động. Chỉ phong bì là gõ tay —
đổi hình dạng `TinNhan` thì sửa YAML rồi `npm run gen:api`, không sửa file này.

## Điểm cuối

| | |
|---|---|
| URL | `VITE_WS_URL` — mặc định `ws://localhost:8080/ws` (qua **gateway**, không nối thẳng `:8081`) |
| Định dạng khung | JSON, một đối tượng mỗi khung, trường phân biệt là `type` |
| Kiểu tin | text (`WebSocket.send(string)`), không dùng khung nhị phân |

## Xác thực — bằng khung AUTH, không phải query string

Trình duyệt **không đặt được header** cho `new WebSocket(...)`, nên `Authorization: Bearer …`
không dùng được. Hai lối đi thường gặp, và lý do chọn lối thứ hai:

| Cách | Vấn đề |
|---|---|
| `?access_token=…` trên URL | Token vào **log truy cập** của gateway, vào `Referer`, vào lịch sử. Một dòng log là một token dùng lại được cho tới khi hết hạn. |
| **Khung `AUTH` đầu tiên** | Token nằm trong thân khung — không lọt vào access log. Đổi lại: máy chủ phải giữ socket ở trạng thái *chưa xác thực* một lúc. |

Luồng bắt tay:

```
client ──── (mở socket) ────▶ server        socket ở trạng thái CHƯA XÁC THỰC
client ──── {"type":"AUTH"} ─▶ server        server xác minh JWT, đọc tenant_id + user_id + permissions
client ◀─── {"type":"READY"} ── server        từ đây mới bắt đầu đẩy dữ liệu
```

Ràng buộc phía máy chủ:

1. **Không đẩy một khung dữ liệu nào trước `READY`.** Socket chưa xác thực chưa có tenant.
2. **Quá 10 giây không thấy `AUTH` thì đóng với mã `4408`.** Socket mở mà không xác thực là
   tài nguyên miễn phí cho kẻ dò — thuộc bề mặt **T7** (gateway) trong `docs/threat-model.md`.
3. **`tenant_id` lấy từ JWT, không bao giờ từ khung tin.** Giống hệt quy tắc bất biến số 1 của
   `dashboard-api.yaml`. Không có khung nào của giao ước này mang `tenantId`.
4. **Mọi khung đẩy xuống phải lọc theo `tenant_id` của chính socket đó.** Đây là điểm khác
   quan trọng so với HTTP: một request HTTP đi qua RLS vì nó chạy trong phiên `crm_app` có
   `SET LOCAL app.tenant_id`. Một khung đẩy thì do máy chủ tự sinh khi có sự kiện — nếu bộ
   phát sự kiện gửi cho mọi socket đang mở thì **RLS không nằm trên đường đi**, và rò rỉ chéo
   tenant xảy ra mà không có truy vấn nào sai. Bộ phát phải định tuyến theo `tenant_id`.
5. Token hết hạn giữa chừng thì đóng với `4401`. Client làm mới token qua
   `POST /api/v1/auth/refresh` rồi nối lại — **không** gia hạn token qua WebSocket.

## Khung client → server

| `type` | Trường | Ý nghĩa |
|---|---|---|
| `AUTH` | `accessToken` | Khung đầu tiên, bắt buộc |
| `SUBSCRIBE` | `conversationId` | Xin nhận `MESSAGE_CREATED` của **một** hội thoại (hội thoại đang mở) |
| `UNSUBSCRIBE` | `conversationId` | Thôi nhận |
| `PING` | — | Nhịp tim, 25 giây một lần |

Vì sao phải `SUBSCRIBE` chứ không đẩy hết: một doanh nghiệp bận có thể có hàng trăm hội thoại
mở cùng lúc; đẩy mọi tin nhắn của mọi hội thoại xuống mọi nhân viên là gửi thừa gần như toàn
bộ. Còn **danh sách** hộp thư thì đẩy toàn tenant, vì đó chính là thứ mọi nhân viên đang nhìn.

`SUBSCRIBE` chỉ nhận `conversationId`; máy chủ vẫn phải kiểm hội thoại đó có thuộc tenant của
socket không. Một `conversationId` đoán được là một request, không phải một chứng chỉ.

## Khung server → client

Mọi khung mang dữ liệu đều có `eventId` (UUID) và `occurredAt` (ISO-8601).
`eventId` là **khoá chống trùng** — client có thể nhận lại một khung sau khi nối lại, và
`MESSAGE_CREATED` xử lý hai lần là một tin nhắn hiện hai lần trên màn hình.

| `type` | Trường | Client làm gì |
|---|---|---|
| `READY` | `connectionId`, `serverTime` | Mở cờ đã xác thực, gửi lại các `SUBSCRIBE` đang treo |
| `PONG` | `serverTime` | Ghi nhận nhịp tim |
| `MESSAGE_CREATED` | `conversationId`, `message: TinNhan` | Nối vào cuối `messages` của cache `chiTietHoiThoai` |
| `CONVERSATION_UPDATED` | `conversation: HoiThoaiTomTat` | Thay nguyên dòng trong cache `danhSachHoiThoai`, sắp lại |
| `HANDOFF_REQUESTED` | `conversationId`, `reason`, `conversation` | Như trên, cộng thêm báo cho nhân viên (SCR021) |
| `AGENT_TYPING` | `conversationId`, `senderType`, `expiresAt` | Hiện chấm "đang gõ", **không** ghi vào cache |
| `ERROR` | `code`, `message` | Hiện lỗi; `code` là mã nghiệp vụ, không phải mã đóng |

### Vì sao một tin nhắn mới sinh ra **hai** khung

Tin nhắn mới của khách làm đổi cả hai chỗ: nội dung hội thoại **và** dòng của nó trong danh
sách (`lastMessagePreview`, `lastMessageAt`, `unreadCount`, có khi cả `status`). Máy chủ gửi
`MESSAGE_CREATED` **và** `CONVERSATION_UPDATED`.

Cách còn lại — gửi một khung rồi để client tự suy ra dòng danh sách — là bắt trình duyệt tính
lại những cột mà máy chủ đã tính sẵn khi ghi, và `unreadCount` thì client **không** tính đúng
được: nó phụ thuộc vào việc nhân viên nào đã đọc tới đâu, dữ liệu chỉ máy chủ có.

`AGENT_TYPING` cố ý **không** có `eventId`: nó là trạng thái phù du, mất một khung không sao,
và không được phép chạm vào cache.

## Mã đóng

| Mã | Nghĩa | Client phản ứng |
|---|---|---|
| `1000` | Đóng bình thường (đăng xuất, rời trang) | Không nối lại |
| `1006` | Rớt kết nối bất thường | Nối lại, lùi dần 1s → 2s → 4s → … tối đa 30s, có nhiễu ngẫu nhiên |
| `4401` | Chưa xác thực / token hết hạn | Làm mới token rồi nối lại |
| `4403` | Không đủ quyền cho hội thoại vừa `SUBSCRIBE` | Không nối lại, hiện lỗi |
| `4408` | Không gửi `AUTH` kịp trong 10 giây | Nối lại (thường là lỗi phía client) |
| `4429` | Vượt số kết nối cho phép của tenant | Nối lại với thời gian lùi dài hơn |

Nhiễu ngẫu nhiên trong thời gian lùi là bắt buộc, không phải trang trí: gateway khởi động lại
làm **mọi** trình duyệt đang mở rớt cùng một khoảnh khắc, và nếu tất cả cùng nối lại sau đúng
1 giây thì cú nối lại đó chính là đợt tấn công tiếp theo lên gateway vừa hồi phục.

## Trạng thái phía client

`src/app/store/realtimeSlice.ts` giữ đúng ba thứ: trạng thái đường truyền
(`dong` · `dang-noi` · `mo` · `dang-noi-lai` · `loi`), thời điểm nhận khung gần nhất, và mã
đóng cuối. Chỉ báo trên thanh trên đọc từ đây.

Không giữ dữ liệu nghiệp vụ trong slice này. Tin nhắn và hội thoại đi thẳng vào cache của RTK
Query qua `onCacheEntryAdded`, để một dòng dữ liệu chỉ có **một** chỗ chứa.

## Máy chủ giả

`src/mocks/ws.ts` cài đúng giao ước trên bằng `ws.link()` của MSW — kể cả bắt tay `AUTH`,
đóng `4408` khi không xác thực kịp, và gửi cặp `MESSAGE_CREATED` + `CONVERSATION_UPDATED`.

Nhờ vậy khi java-core có `WebSocketHandler` thật thì phía trình duyệt **không sửa gì**: đổi
`VITE_USE_MOCK=false` là các khung đến từ máy chủ thật.
