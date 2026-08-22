import {
  MA_DONG,
  dungNoiLai,
  type Khung,
  type KhungGui,
  type KhungNhan,
  type LoaiKhungNhan,
} from '@/api/realtime/sukien'
import { datTrangThai, ghiNhanKhung } from '@/app/store/realtimeSlice'
import { layStore } from '@/app/store/truyCapStore'

/**
 * Một kết nối WebSocket duy nhất cho cả ứng dụng — giao ước ở
 * `docs/openapi/dashboard-realtime.md`.
 *
 * **Vì sao là singleton chứ không phải một kết nối mỗi nơi cần.** Mỗi mục cache của RTK Query
 * chạy `onCacheEntryAdded` riêng: hộp thư mở ba bộ lọc là ba mục, cộng một mục cho hội thoại
 * đang xem. Nếu mỗi mục tự mở socket thì bốn socket cùng nhận một luồng, và mỗi lần đổi bộ lọc
 * là một lần bắt tay lại. Ở đây `dangKy()` chỉ cộng vào danh sách người nghe; socket mở một lần
 * theo phiên đăng nhập.
 *
 * Lớp này **không biết gì về React và không biết gì về RTK Query**. Nó nhận khung, phát cho
 * người nghe, và báo trạng thái đường truyền vào store.
 */

const URL_WS = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8080/ws'

/** Nhịp tim. Ngắn hơn thời gian nghỉ mà proxy thường cắt (60s) một cách thoải mái. */
const NHIP_TIM_MS = 25_000
/** Không thấy PONG trong bấy lâu thì coi như đường đã đứt dù socket vẫn báo `OPEN`. */
const CHO_PONG_MS = 10_000
const LUI_DAU_MS = 1_000
const LUI_TOI_DA_MS = 30_000

type HamNghe<L extends LoaiKhungNhan> = (khung: Khung<L>) => void

class KetNoiThoiGianThuc {
  #socket: WebSocket | null = null
  #token: string | null = null
  #daXacThuc = false
  #dongCoChuY = false
  #soLanThu = 0

  #hangCho: KhungGui[] = []
  /**
   * Người nghe lưu dưới dạng đã bọc, nhận nguyên `KhungNhan`. Khoá của Map mới là thứ bảo đảm
   * khung đưa vào đúng nhánh union — một lần thu hẹp kiểu ở `dangKy` thay vì rải ép kiểu khắp nơi.
   */
  #nghe = new Map<LoaiKhungNhan, Set<(khung: KhungNhan) => void>>()
  /** Đếm số nơi đang xin nhận một hội thoại — bốn nơi cùng mở thì chỉ gửi `SUBSCRIBE` một lần. */
  #dangTheoDoi = new Map<string, number>()

  #hen: ReturnType<typeof setTimeout> | null = null
  #henNhipTim: ReturnType<typeof setInterval> | null = null
  #henPong: ReturnType<typeof setTimeout> | null = null

  /**
   * Chống trùng theo `eventId`. Nối lại có thể phát lại vài khung cuối, và
   * `MESSAGE_CREATED` xử lý hai lần là một tin nhắn hiện hai lần trên màn hình.
   *
   * Cùng ý với quy tắc `analytics.processed_events` của consumer Kafka (CLAUDE.md mục 7) —
   * giao nhận ít nhất một lần thì nhận trùng là chắc chắn, không phải rủi ro.
   */
  #daXuLy = new Set<string>()

  // ── Vòng đời ────────────────────────────────────────────────────────────────

  moKetNoi(accessToken: string) {
    // Cùng token, socket còn sống: không làm gì. Gọi lại là chuyện thường vì effect chạy hai
    // lần dưới StrictMode.
    if (this.#token === accessToken && this.#socket && this.#socket.readyState <= WebSocket.OPEN) {
      return
    }
    this.#token = accessToken
    this.#dongCoChuY = false
    this.#soLanThu = 0
    this.#noi()
  }

  dongKetNoi() {
    this.#dongCoChuY = true
    this.#token = null
    this.#huyHen()
    this.#daXuLy.clear()
    this.#hangCho = []
    this.#dangTheoDoi.clear()
    this.#socket?.close(MA_DONG.BINH_THUONG, 'Đăng xuất')
    this.#socket = null
    this.#daXacThuc = false
    this.#bao('dong')
  }

  #noi() {
    if (!this.#token) return
    this.#huyHen()
    this.#daXacThuc = false
    this.#bao(this.#soLanThu === 0 ? 'dang-noi' : 'dang-noi-lai')

    // Socket cũ còn sót (đổi token giữa chừng) thì bỏ đi trước khi mở cái mới
    this.#socket?.close(MA_DONG.BINH_THUONG, 'Mở kết nối mới')

    let socket: WebSocket
    try {
      socket = new WebSocket(URL_WS)
    } catch {
      // URL sai hình dạng — nối lại cũng sai y như vậy, đừng quay vòng
      this.#bao('loi')
      return
    }
    this.#socket = socket

    /**
     * Mọi hàm xử lý phải tự hỏi mình có còn là socket hiện hành không.
     *
     * StrictMode chạy effect hai lần (mở → đóng → mở), nên `onclose` của socket **đầu** hay
     * đến sau khi socket **thứ hai** đã mở. Không có lá chắn này thì cú đóng cũ hẹn một lần
     * nối lại nữa, và ứng dụng lặng lẽ chạy hai kết nối song song — mỗi tin nhắn đến hai lần.
     */
    const conHieuLuc = () => this.#socket === socket

    socket.onopen = () => {
      // Khung đầu tiên phải là AUTH. Token đi trong thân khung chứ không trên URL: query
      // string lọt vào access log của gateway, và một dòng log là một token dùng lại được.
      if (conHieuLuc() && this.#token) {
        socket.send(JSON.stringify({ type: 'AUTH', accessToken: this.#token }))
      }
    }

    socket.onmessage = (su) => {
      if (conHieuLuc()) this.#nhan(su.data)
    }

    socket.onclose = (su) => {
      if (!conHieuLuc()) return
      this.#huyHen()
      this.#daXacThuc = false
      this.#socket = null
      layStore()?.dispatch(datTrangThai({ trangThai: 'dong', maDongCuoi: su.code }))
      if (this.#dongCoChuY || dungNoiLai(su.code)) return
      this.#henNoiLai()
    }

    // `onerror` không cho biết lý do (bản đặc tả cố ý giấu, tránh dò cổng). Việc dọn dẹp để
    // `onclose` lo — trình duyệt luôn gọi `onclose` sau `onerror`.
    socket.onerror = () => {
      if (conHieuLuc()) this.#bao('loi')
    }
  }

  #henNoiLai() {
    this.#soLanThu += 1
    const co = Math.min(LUI_DAU_MS * 2 ** (this.#soLanThu - 1), LUI_TOI_DA_MS)
    // Nhiễu ngẫu nhiên là bắt buộc, không phải trang trí: gateway khởi động lại làm mọi trình
    // duyệt đang mở rớt cùng một khoảnh khắc. Cùng nối lại sau đúng 1 giây thì chính cú nối
    // lại đó là đợt tấn công tiếp theo lên gateway vừa hồi phục.
    const cho = co / 2 + Math.random() * (co / 2)
    this.#bao('dang-noi-lai')
    this.#hen = setTimeout(() => this.#noi(), cho)
  }

  #huyHen() {
    if (this.#hen) clearTimeout(this.#hen)
    if (this.#henNhipTim) clearInterval(this.#henNhipTim)
    if (this.#henPong) clearTimeout(this.#henPong)
    this.#hen = this.#henNhipTim = this.#henPong = null
  }

  // ── Nhận khung ──────────────────────────────────────────────────────────────

  #nhan(duLieu: unknown) {
    if (typeof duLieu !== 'string') return
    let khung: KhungNhan
    try {
      khung = JSON.parse(duLieu) as KhungNhan
    } catch {
      return
    }

    switch (khung.type) {
      case 'READY':
        this.#daXacThuc = true
        this.#soLanThu = 0
        this.#bao('mo')
        this.#xaHangCho()
        this.#batNhipTim()
        return
      case 'PONG':
        if (this.#henPong) clearTimeout(this.#henPong)
        this.#henPong = null
        return
      default:
        break
    }

    // Nhận lại một khung sau khi nối lại là chuyện bình thường — bỏ qua khung đã xử lý
    if ('eventId' in khung) {
      if (this.#daXuLy.has(khung.eventId)) return
      this.#daXuLy.add(khung.eventId)
      // Giữ cửa sổ chống trùng ở mức gọn: máy chủ chỉ phát lại vài khung cuối
      if (this.#daXuLy.size > 500) {
        this.#daXuLy = new Set([...this.#daXuLy].slice(-250))
      }
    }

    layStore()?.dispatch(ghiNhanKhung())
    // Sao chép trước khi duyệt: một hàm nghe có thể tự gỡ đăng ký ngay trong lúc chạy
    for (const ham of [...(this.#nghe.get(khung.type) ?? [])]) ham(khung)
  }

  #batNhipTim() {
    if (this.#henNhipTim) clearInterval(this.#henNhipTim)
    this.#henNhipTim = setInterval(() => {
      if (this.#socket?.readyState !== WebSocket.OPEN) return
      this.#gui({ type: 'PING' })
      // Một socket đã đứt đường vẫn báo `OPEN` cho tới khi TCP hết giờ — có thể vài phút.
      // Không thấy PONG thì tự đóng để chu trình nối lại chạy sớm.
      if (this.#henPong) clearTimeout(this.#henPong)
      this.#henPong = setTimeout(() => {
        this.#socket?.close(MA_DONG.CHUA_XAC_THUC, 'Không nhận được PONG')
      }, CHO_PONG_MS)
    }, NHIP_TIM_MS)
  }

  // ── Gửi khung ───────────────────────────────────────────────────────────────

  #gui(khung: KhungGui) {
    // Chưa `READY` thì xếp hàng: máy chủ bỏ qua mọi khung trước khi xác thực xong, nên gửi
    // sớm là mất luôn. Hàng chờ làm cho thứ tự gọi `theoDoi()` không còn quan trọng.
    if (!this.#daXacThuc || this.#socket?.readyState !== WebSocket.OPEN) {
      this.#hangCho.push(khung)
      return
    }
    this.#socket.send(JSON.stringify(khung))
  }

  #xaHangCho() {
    // Nối lại xong thì máy chủ đã quên mọi thứ đã xin nhận — gửi lại toàn bộ theo `#dangTheoDoi`,
    // rồi bỏ mọi khung SUBSCRIBE/UNSUBSCRIBE còn nằm trong hàng chờ. `#dangTheoDoi` là nguồn duy
    // nhất; phát lại cả hai đường là gửi trùng, và một cặp xin-rồi-thôi xếp sai thứ tự trong hàng
    // chờ còn có thể huỷ mất thứ đang cần.
    for (const id of this.#dangTheoDoi.keys()) {
      this.#socket?.send(JSON.stringify({ type: 'SUBSCRIBE', conversationId: id }))
    }
    const cho = this.#hangCho.filter((k) => k.type !== 'SUBSCRIBE' && k.type !== 'UNSUBSCRIBE')
    this.#hangCho = []
    for (const khung of cho) this.#socket?.send(JSON.stringify(khung))
  }

  // ── Đăng ký nghe ────────────────────────────────────────────────────────────

  /** Trả về hàm gỡ đăng ký. Gọi nó trong nhánh dọn dẹp của `onCacheEntryAdded`. */
  dangKy<L extends LoaiKhungNhan>(loai: L, ham: HamNghe<L>): () => void {
    let tap = this.#nghe.get(loai)
    if (!tap) {
      tap = new Set()
      this.#nghe.set(loai, tap)
    }
    // `#nhan` chỉ gọi tập này khi `khung.type === loai`, nên nhánh union luôn khớp
    const boc = (khung: KhungNhan) => ham(khung as Khung<L>)
    tap.add(boc)
    return () => {
      tap.delete(boc)
      if (tap.size === 0) this.#nghe.delete(loai)
    }
  }

  /**
   * Xin nhận tin nhắn của một hội thoại. Đếm số nơi đang xin: hai màn cùng mở một hội thoại thì
   * chỉ khi nơi cuối cùng đóng mới gửi `UNSUBSCRIBE`.
   */
  theoDoi(idHoiThoai: string): () => void {
    const truoc = this.#dangTheoDoi.get(idHoiThoai) ?? 0
    this.#dangTheoDoi.set(idHoiThoai, truoc + 1)
    if (truoc === 0) this.#gui({ type: 'SUBSCRIBE', conversationId: idHoiThoai })

    return () => {
      const con = (this.#dangTheoDoi.get(idHoiThoai) ?? 1) - 1
      if (con > 0) {
        this.#dangTheoDoi.set(idHoiThoai, con)
        return
      }
      this.#dangTheoDoi.delete(idHoiThoai)
      this.#gui({ type: 'UNSUBSCRIBE', conversationId: idHoiThoai })
    }
  }

  #bao(trangThai: Parameters<typeof datTrangThai>[0]['trangThai']) {
    layStore()?.dispatch(datTrangThai({ trangThai }))
  }
}

export const ketNoiThoiGianThuc = new KetNoiThoiGianThuc()
