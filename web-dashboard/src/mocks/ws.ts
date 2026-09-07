import { ws } from 'msw'

import { MA_DONG, type KhungGui, type KhungNhan } from '@/api/realtime/sukien'
import { chiTietHoiThoai, danhSachHoiThoai } from '@/mocks/du-lieu'
import type { TinNhan } from '@/types/schema'

/**
 * Máy chủ WebSocket giả — cài đúng `docs/openapi/dashboard-realtime.md`, kể cả những phần dễ
 * bị bỏ qua: bắt tay `AUTH`, đóng `4408` khi không xác thực kịp, và **cặp hai khung**
 * `MESSAGE_CREATED` + `CONVERSATION_UPDATED` cho mỗi tin nhắn mới.
 *
 * Cài đủ phần khó chịu mới là điểm của việc mock: nếu máy chủ giả bỏ qua bắt tay thì lỗi bắt
 * tay của phía trình duyệt chỉ lộ ra khi nối java-core thật — tức là muộn nhất có thể.
 *
 * MSW chặn WebSocket bằng cách thay lớp `WebSocket` toàn cục, **không** qua Service Worker như
 * phần HTTP. Nên nó chặn được cả khi URL trỏ sang origin khác (`ws://localhost:8080`).
 */

const URL_WS = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8080/ws'

const kenh = ws.link(URL_WS)

/** Quá bấy lâu không thấy `AUTH` thì đóng — socket mở mà chưa xác thực là tài nguyên miễn phí. */
const HAN_AUTH_MS = 10_000
/** Sau khi mở một hội thoại, bao lâu thì khách "nhắn tiếp". Đủ để nhìn thấy, đủ ngắn để không chờ. */
const TRE_KICH_BAN_MS = 7_000

let demSuKien = 0
const idSuKien = () => `ev-${Date.now().toString(36)}-${(demSuKien += 1)}`

/** Chỉ cần đúng một khả năng của client, khai theo cấu trúc để khỏi phụ thuộc type nội bộ của MSW. */
function gui(client: { send: (data: string) => void }, khung: KhungNhan) {
  client.send(JSON.stringify(khung))
}

/**
 * Sinh một tin nhắn mới của khách và **ghi vào chính dữ liệu giả**.
 *
 * Ghi thật chứ không chỉ đẩy khung: nếu chỉ đẩy, một lần nạp lại qua HTTP sẽ xoá mất tin nhắn
 * vừa hiện, và cái bug "tin nhắn biến mất khi đổi bộ lọc" đó lại là bug của tầng mock chứ không
 * phải của mã nghiệp vụ — tốn hàng giờ để nhận ra.
 */
function themTinNhanKhach(idHoiThoai: string, noiDung: string) {
  const tomTat = danhSachHoiThoai.find((c) => c.id === idHoiThoai)
  const chiTiet = chiTietHoiThoai[idHoiThoai]
  if (!tomTat || !chiTiet) return null

  const luc = new Date().toISOString()
  const tinNhan: TinNhan = {
    id: `m-${Date.now().toString(36)}`,
    senderType: 'CUSTOMER',
    senderUserId: null,
    senderName: tomTat.contactName,
    content: noiDung,
    contentType: 'TEXT',
    deliveryStatus: 'DELIVERED',
    failureReason: null,
    attachments: [],
    aiInteractionId: null,
    citations: [],
    createdAt: luc,
    sentAt: luc,
  }

  chiTiet.messages.push(tinNhan)
  chiTiet.messageCount = (chiTiet.messageCount ?? 0) + 1
  chiTiet.lastMessageAt = luc
  chiTiet.lastMessagePreview = noiDung
  chiTiet.unreadCount += 1

  tomTat.messageCount = chiTiet.messageCount
  tomTat.lastMessageAt = luc
  tomTat.lastMessagePreview = noiDung
  tomTat.unreadCount = chiTiet.unreadCount

  return { tinNhan, tomTat }
}

/** Phát cho mọi client **đang mở** — đúng như máy chủ thật phát cho mọi nhân viên cùng tenant. */
function phat(khung: KhungNhan) {
  const chuoi = JSON.stringify(khung)
  for (const c of donDepClientChet()) c.send(chuoi)
}

function phatTinNhanMoi(idHoiThoai: string, noiDung: string) {
  const ket = themTinNhanKhach(idHoiThoai, noiDung)
  if (!ket) return false
  const luc = ket.tinNhan.createdAt

  // Hai khung cho một sự kiện: một cho nội dung hội thoại, một cho dòng của nó trong danh sách.
  phat({
    type: 'MESSAGE_CREATED',
    eventId: idSuKien(),
    occurredAt: luc,
    conversationId: idHoiThoai,
    message: ket.tinNhan,
  })
  phat({
    type: 'CONVERSATION_UPDATED',
    eventId: idSuKien(),
    occurredAt: luc,
    // Bản sao chứ không phải chính đối tượng: khung tin đi qua JSON nên nội dung được chốt tại
    // đây, giống hệt máy chủ thật.
    conversation: { ...ket.tomTat },
  })
  return true
}

/**
 * Danh sách kết nối **còn sống**, tự giữ lấy và tự dọn theo `readyState`.
 *
 * Hai chỗ của MSW không dùng thay được:
 *
 * 1. `kenh.clients` chỉ thêm chứ không bao giờ gỡ khi socket đóng (`WebSocketClientManager`
 *    chỉ dọn lúc worker dừng), lại lưu qua IndexedDB nên số đếm sống sót cả sau khi tải lại
 *    trang — đọc ra một con số chỉ tăng.
 * 2. Sự kiện `close` phía máy chủ giả **không** luôn được phát khi phía client đóng socket.
 *    Rõ nhất là lúc `StrictMode` dựng rồi tháo effect trong cùng một nhịp: socket còn đang
 *    `CONNECTING` thì bị đóng, và `clientDangMo` giữ lại một mục có `readyState === 3`.
 *
 * Hệ quả nếu bỏ qua: bài kiểm "chỉ có một kết nối" báo hỏng trong khi ứng dụng hoàn toàn đúng —
 * mất thời gian đi tìm lỗi rò kết nối không tồn tại. Nên chốt số đếm theo `readyState`, thứ duy
 * nhất nói thật.
 */
interface ClientGia {
  send: (data: string) => void
  close: (ma: number, ly?: string) => void
  socket?: { readyState: number }
}

const clientDangMo = new Set<ClientGia>()

/** 0 CONNECTING · 1 OPEN · 2 CLOSING · 3 CLOSED */
function donDepClientChet(): Set<ClientGia> {
  for (const c of clientDangMo) {
    if (c.socket && c.socket.readyState >= 2) clientDangMo.delete(c)
  }
  return clientDangMo
}

const CAU_KICH_BAN = [
  'Cho mình hỏi thêm là bên mình có hỗ trợ xuất hoá đơn VAT không ạ?',
  'Mình vừa chuyển khoản rồi nhé, nhờ bạn kiểm tra giúp.',
  'Alo bạn ơi, mình vẫn đang chờ phản hồi ạ.',
]

export const wsHandlers = [
  kenh.addEventListener('connection', ({ client }) => {
    let daXacThuc = false
    const daHenKichBan = new Set<string>()
    const henKichBan: Array<ReturnType<typeof setTimeout>> = []

    clientDangMo.add(client)

    const henAuth = setTimeout(() => {
      if (!daXacThuc) client.close(MA_DONG.AUTH_QUA_HAN, 'Không nhận được khung AUTH')
    }, HAN_AUTH_MS)

    client.addEventListener('close', () => {
      clientDangMo.delete(client)
      clearTimeout(henAuth)
      for (const h of henKichBan) clearTimeout(h)
    })

    client.addEventListener('message', (su) => {
      if (typeof su.data !== 'string') return
      let khung: KhungGui
      try {
        khung = JSON.parse(su.data) as KhungGui
      } catch {
        return
      }

      // Trước khi xác thực, khung duy nhất được nhận là AUTH. Máy chủ thật cũng vậy: chưa có
      // JWT thì chưa có tenant, mà chưa có tenant thì không được trả về một byte dữ liệu nào.
      if (!daXacThuc && khung.type !== 'AUTH') return

      switch (khung.type) {
        case 'AUTH': {
          if (!khung.accessToken) {
            client.close(MA_DONG.CHUA_XAC_THUC, 'Thiếu access token')
            return
          }
          daXacThuc = true
          clearTimeout(henAuth)
          gui(client, {
            type: 'READY',
            connectionId: crypto.randomUUID(),
            serverTime: new Date().toISOString(),
          })
          return
        }

        case 'PING':
          gui(client, { type: 'PONG', serverTime: new Date().toISOString() })
          return

        case 'SUBSCRIBE': {
          const id = khung.conversationId
          if (!chiTietHoiThoai[id]) {
            gui(client, {
              type: 'ERROR',
              code: 'CONVERSATION_NOT_FOUND',
              message: 'Không tìm thấy hội thoại.',
            })
            return
          }
          if (daHenKichBan.has(id)) return
          daHenKichBan.add(id)

          // Kịch bản demo: mở một hội thoại rồi để yên thì lát sau khách nhắn tiếp. Chạy đúng
          // một lần cho mỗi hội thoại mỗi kết nối, để việc bấm qua lại không thành mưa tin nhắn.
          henKichBan.push(
            setTimeout(() => {
              gui(client, {
                type: 'AGENT_TYPING',
                conversationId: id,
                senderType: 'CUSTOMER',
                expiresAt: new Date(Date.now() + 4000).toISOString(),
              })
              henKichBan.push(
                setTimeout(() => {
                  phatTinNhanMoi(id, CAU_KICH_BAN[daHenKichBan.size % CAU_KICH_BAN.length])
                }, 2_000),
              )
            }, TRE_KICH_BAN_MS),
          )
          return
        }

        case 'UNSUBSCRIBE':
          return
      }
    })
  }),
]

/**
 * Cần kích tin nhắn ngay chứ không chờ kịch bản — dùng khi kiểm thử và khi trình bày.
 *
 * Chỉ tồn tại trong bản mock; `import.meta.env.VITE_USE_MOCK` khác `true` thì file này không
 * được nạp, nên không có đường nào rò ra bản chạy thật.
 */
declare global {
  interface Window {
    mockThoiGianThuc?: {
      guiTinNhan: (idHoiThoai?: string, noiDung?: string) => boolean
      guiDangGo: (idHoiThoai?: string, giay?: number) => void
      ngatKetNoi: (ma?: number) => void
      soClient: () => number
      chuanDoan: () => number[]
    }
  }
}

/**
 * Bỏ trống `idHoiThoai` thì nhắm vào hội thoại **mới nhất** — đúng hội thoại hộp thư tự chọn
 * khi mở, vì cả hai cùng sắp theo `lastMessageAt` giảm dần. Nhờ vậy gõ một lệnh là thấy ngay
 * kết quả, không phải đi tra id.
 */
const hoiThoaiMoiNhat = () =>
  [...danhSachHoiThoai].sort((a, b) => b.lastMessageAt.localeCompare(a.lastMessageAt))[0].id

window.mockThoiGianThuc = {
  guiTinNhan: (idHoiThoai, noiDung) =>
    phatTinNhanMoi(
      idHoiThoai ?? hoiThoaiMoiNhat(),
      noiDung ?? 'Tin nhắn kích tay từ máy chủ giả.',
    ),
  guiDangGo: (idHoiThoai, giay = 4) => {
    phat({
      type: 'AGENT_TYPING',
      conversationId: idHoiThoai ?? hoiThoaiMoiNhat(),
      senderType: 'CUSTOMER',
      expiresAt: new Date(Date.now() + giay * 1000).toISOString(),
    })
  },
  // 4500 chứ không phải 1006: dải 1xxx do chính giao thức đặt, chỉ 1000 và 3000–4999 mới gửi
  // tường minh được. Với phía trình duyệt thì giống nhau — mã nào không nằm trong `dungNoiLai`
  // cũng kích hoạt chu trình nối lại.
  ngatKetNoi: (ma = 4500) => {
    for (const c of donDepClientChet()) c.close(ma, 'Máy chủ giả ngắt kết nối')
  },
  soClient: () => donDepClientChet().size,
  chuanDoan: () => [...clientDangMo].map((c) => c.socket?.readyState ?? -1),
}
