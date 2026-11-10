// [PRODUCTION] Dựng giao diện widget trong Shadow DOM.
// Nội dung tin nhắn LUÔN gán bằng textContent, không bao giờ innerHTML: câu trả lời của AI và tin
// nhân viên có thể chứa chuỗi do khách khác cố tình nhét vào (bề mặt T2) — innerHTML là XSS ngay
// trên website của doanh nghiệp.

import type { GiaoDien, LyDoChe, ThongTinLienHe, TinNhan, YeuCauDanhGia } from './api'
import { CSS } from './styles'

const MAU_MAC_DINH = '#4F46E5'

/** Bốn lý do chê của đặc tả UC027 — cùng bộ mã với hộp thư của nhân viên. */
const LY_DO_CHE: [LyDoChe, string][] = [
  ['WRONG_INFO', 'Thông tin sai'],
  ['IRRELEVANT', 'Lạc đề'],
  ['INCOMPLETE', 'Trả lời thiếu'],
  ['BAD_TONE', 'Giọng điệu chưa phù hợp'],
]
const HEX = /^#[0-9a-fA-F]{6}$/

const ICON_CHAT =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2z"/></svg>'

function tao<K extends keyof HTMLElementTagNameMap>(
  the: K,
  lop?: string,
  chu?: string,
): HTMLElementTagNameMap[K] {
  const el = document.createElement(the)
  if (lop) el.className = lop
  if (chu !== undefined) el.textContent = chu
  return el
}

export interface SuKienUi {
  onGui: (noiDung: string) => void
  onGapNhanVien: () => void
  onMo: () => void
  onDeLaiThongTin: (tt: ThongTinLienHe) => void
  /** UC027 — gửi đánh giá; promise lỗi mang câu thông báo để hiện ngay dưới tin. */
  onDanhGia: (messageId: string, yc: YeuCauDanhGia) => Promise<void>
}

export class GiaoDienChat {
  private readonly goc: HTMLDivElement
  private readonly khung: HTMLDivElement
  private readonly than: HTMLDivElement
  private readonly loi: HTMLDivElement
  private readonly oNhap: HTMLTextAreaElement
  private readonly nutGui: HTMLButtonElement
  private readonly nutGapNv: HTMLButtonElement
  private readonly tenEl: HTMLSpanElement
  private readonly anhEl: HTMLImageElement
  private readonly chan: HTMLDivElement
  private readonly chanTrang: HTMLSpanElement
  private dangGo: HTMLDivElement | null = null
  private readonly nutThongTin: HTMLButtonElement
  private form: HTMLFormElement | null = null
  private daDeLai = false
  private readonly daCo = new Set<string>()

  constructor(chuNha: HTMLElement, private readonly suKien: SuKienUi) {
    const shadow = chuNha.attachShadow({ mode: 'open' })
    const style = tao('style')
    style.textContent = CSS
    shadow.appendChild(style)

    this.goc = tao('div', 'goc phai')
    this.khung = tao('div', 'khung')
    this.khung.hidden = true
    this.khung.setAttribute('role', 'dialog')
    this.khung.setAttribute('aria-label', 'Trò chuyện với chúng tôi')

    const dau = tao('div', 'dau')
    this.anhEl = tao('img')
    this.anhEl.alt = ''
    this.anhEl.hidden = true
    this.tenEl = tao('span', 'ten', 'Hỗ trợ trực tuyến')
    const dong = tao('button', undefined, '×')
    dong.type = 'button'
    dong.setAttribute('aria-label', 'Thu nhỏ khung chat')
    dong.addEventListener('click', () => this.dong())
    dau.append(this.anhEl, this.tenEl, dong)

    this.than = tao('div', 'than')
    this.than.setAttribute('aria-live', 'polite')
    this.loi = tao('div', 'loi')
    this.loi.hidden = true
    this.loi.setAttribute('role', 'alert')

    this.chan = tao('div', 'chan')
    const hang = tao('div', 'hang')
    this.oNhap = tao('textarea')
    this.oNhap.rows = 1
    this.oNhap.maxLength = 1000
    this.oNhap.placeholder = 'Nhập tin nhắn…'
    this.oNhap.setAttribute('aria-label', 'Nội dung tin nhắn')
    this.oNhap.addEventListener('keydown', (e) => {
      // Enter gửi, Shift+Enter xuống dòng; bỏ qua khi đang gõ tiếng Việt bằng bộ gõ (isComposing)
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
        e.preventDefault()
        this.gui()
      }
    })
    this.nutGui = tao('button', 'gui', 'Gửi')
    this.nutGui.type = 'button'
    this.nutGui.addEventListener('click', () => this.gui())
    hang.append(this.oNhap, this.nutGui)

    const phu = tao('div', 'phu')
    this.nutGapNv = tao('button', 'gap-nv', 'Gặp nhân viên')
    this.nutGapNv.type = 'button'
    this.nutGapNv.hidden = true
    this.nutGapNv.addEventListener('click', () => this.suKien.onGapNhanVien())
    this.chanTrang = tao('span', undefined, 'Trả lời tự động bởi trợ lý AI')
    this.nutThongTin = tao('button', 'gap-nv', 'Để lại thông tin')
    this.nutThongTin.type = 'button'
    this.nutThongTin.addEventListener('click', () => this.hienFormThongTin())
    const nut = tao('span', 'nut')
    nut.append(this.nutThongTin, this.nutGapNv)
    phu.append(this.chanTrang, nut)
    this.chan.append(hang, phu)

    this.khung.append(dau, this.than, this.loi, this.chan)

    const bong = tao('button', 'bong')
    bong.type = 'button'
    bong.setAttribute('aria-label', 'Mở khung chat')
    bong.innerHTML = ICON_CHAT // biểu tượng cố định trong mã, không phải dữ liệu
    bong.addEventListener('click', () => (this.khung.hidden ? this.mo() : this.dong()))

    this.goc.append(this.khung, bong)
    shadow.appendChild(this.goc)
    this.apDungGiaoDien(null)
  }

  apDungGiaoDien(g: GiaoDien | null): void {
    const mau = g?.primaryColor && HEX.test(g.primaryColor) ? g.primaryColor : MAU_MAC_DINH
    this.goc.style.setProperty('--mau', mau)
    this.goc.className = g?.position === 'BOTTOM_LEFT' ? 'goc trai' : 'goc phai'
    if (g?.displayName) this.tenEl.textContent = g.displayName
    if (g?.avatarUrl && /^https:\/\//.test(g.avatarUrl)) {
      this.anhEl.src = g.avatarUrl
      this.anhEl.hidden = false
    }
  }

  mo(): void {
    this.khung.hidden = false
    this.suKien.onMo()
    this.cuonXuong()
    this.oNhap.focus()
  }

  dong(): void {
    this.khung.hidden = true
  }

  get dangMo(): boolean {
    return !this.khung.hidden
  }

  /** UC009 11.2 — thay khung chat bằng thông báo, không nhận tin mới. */
  hienTamNgung(): void {
    this.than.replaceChildren(
      tao('div', 'tam-ngung', 'Dịch vụ trò chuyện đang tạm ngừng. Bạn vui lòng liên hệ doanh nghiệp qua kênh khác nhé.'),
    )
    this.chan.hidden = true
  }

  hienLoiChao(loiChao: string | null): void {
    if (this.than.childElementCount > 0) return
    const el = tao('div', 'tin bot', loiChao || 'Xin chào! Mình có thể giúp gì cho bạn?')
    this.than.appendChild(el)
  }

  themTin(ds: TinNhan[]): void {
    for (const t of ds) {
      if (this.daCo.has(t.id)) continue
      this.daCo.add(t.id)
      this.than.appendChild(this.veTin(t))
    }
    if (this.dangGo) this.than.appendChild(this.dangGo) // luôn ở cuối
    this.cuonXuong()
  }

  datDangGo(bat: boolean): void {
    if (bat && !this.dangGo) {
      this.dangGo = tao('div', 'dang-go', 'Đang trả lời…')
      this.than.appendChild(this.dangGo)
      this.cuonXuong()
    } else if (!bat && this.dangGo) {
      this.dangGo.remove()
      this.dangGo = null
    }
    this.nutGui.disabled = bat
  }

  datCoTheGapNhanVien(co: boolean): void {
    this.nutGapNv.hidden = !co
  }

  /** Chân khung chat nói đúng ai đang trả lời — khách không nhầm nhân viên với AI. */
  datNguoiTraLoi(trangThai: string | null): void {
    this.chanTrang.textContent =
      trangThai === 'AGENT_HANDLING'
        ? 'Nhân viên đang hỗ trợ bạn'
        : trangThai === 'PENDING_AGENT'
          ? 'Đang chờ nhân viên tiếp nhận…'
          : 'Trả lời tự động bởi trợ lý AI'
  }

  /** Khách đã để lại thông tin → ẩn nút và ô nhập, không hỏi lại. */
  datDaDeLaiThongTin(da: boolean): void {
    this.daDeLai = da
    this.nutThongTin.hidden = da
    if (da) this.anFormThongTin()
  }

  get daDeLaiThongTin(): boolean {
    return this.daDeLai
  }

  /**
   * Ô "Để lại thông tin". Bắt buộc tích đồng ý mới gửi được (Nghị định 13). Phải có SĐT hoặc email —
   * máy chủ kiểm lại lần nữa; ở đây chỉ để khách khỏi bấm gửi vô ích.
   */
  hienFormThongTin(): void {
    if (this.daDeLai || this.form) return
    const f = tao('form', 'the-tt')
    f.noValidate = true
    f.appendChild(tao('div', 'tieu-de', 'Để lại thông tin để nhân viên liên hệ lại nhé'))
    const ten = this.oTt('Tên của bạn', 'text', 'name', 200)
    const sdt = this.oTt('Số điện thoại', 'tel', 'tel', 20)
    const email = this.oTt('Email (không bắt buộc)', 'email', 'email', 255)
    const dongY = tao('label', 'dong-y')
    const hop = tao('input')
    hop.type = 'checkbox'
    dongY.append(hop, document.createTextNode(' Tôi đồng ý cho cửa hàng lưu thông tin này để liên hệ lại.'))
    const loi = tao('div', 'loi-tt')
    loi.hidden = true
    const hang = tao('div', 'hang-nut')
    const gui = tao('button', 'gui', 'Gửi')
    gui.type = 'submit'
    gui.disabled = true
    const deSau = tao('button', 'de-sau', 'Để sau')
    deSau.type = 'button'
    deSau.addEventListener('click', () => this.anFormThongTin())
    hang.append(deSau, gui)
    hop.addEventListener('change', () => (gui.disabled = !hop.checked))
    f.append(ten, sdt, email, dongY, loi, hang)
    f.addEventListener('submit', (e) => {
      e.preventDefault()
      const giaTri = (o: HTMLInputElement) => o.value.trim() || null
      const s = giaTri(sdt), m = giaTri(email)
      if (!s && !m) {
        loi.textContent = 'Bạn để lại số điện thoại hoặc email nhé.'
        loi.hidden = false
        return
      }
      loi.hidden = true
      gui.disabled = true
      this.suKien.onDeLaiThongTin({ fullName: giaTri(ten), phone: s, email: m, consent: hop.checked })
    })
    this.form = f
    this.than.appendChild(f)
    this.cuonXuong()
    ten.focus()
  }

  /** Máy chủ từ chối (SĐT sai…) — hiện lỗi ngay trong ô, cho sửa và gửi lại. */
  baoLoiFormThongTin(chu: string): void {
    if (!this.form) return
    const loi = this.form.querySelector<HTMLDivElement>('.loi-tt')
    const gui = this.form.querySelector<HTMLButtonElement>('button[type=submit]')
    const hop = this.form.querySelector<HTMLInputElement>('input[type=checkbox]')
    if (loi) {
      loi.textContent = chu
      loi.hidden = false
    }
    if (gui && hop) gui.disabled = !hop.checked
  }

  anFormThongTin(): void {
    this.form?.remove()
    this.form = null
  }

  private oTt(nhan: string, kieu: string, tuDien: string, toiDa: number): HTMLInputElement {
    const o = tao('input')
    o.type = kieu
    o.placeholder = nhan
    o.setAttribute('autocomplete', tuDien)
    o.maxLength = toiDa
    o.setAttribute('aria-label', nhan)
    return o
  }

  baoLoi(chu: string | null): void {
    this.loi.textContent = chu ?? ''
    this.loi.hidden = !chu
  }

  private gui(): void {
    const noiDung = this.oNhap.value.trim()
    if (!noiDung || this.nutGui.disabled) return
    this.oNhap.value = ''
    this.suKien.onGui(noiDung)
  }

  private veTin(t: TinNhan): HTMLElement {
    const lop =
      t.senderType === 'CUSTOMER' ? 'khach' : t.senderType === 'SYSTEM' ? 'he-thong' : t.senderType === 'AGENT' ? 'nv' : 'bot'
    const el = tao('div', `tin ${lop}`)
    if (t.senderType === 'AGENT') el.appendChild(tao('div', 'nhan', 'Nhân viên'))
    // UC023 8.2 — nói thẳng đây là câu trích tạm, không phải câu trả lời đầy đủ
    if (t.senderType === 'BOT' && t.degraded) el.appendChild(tao('div', 'nhan tam', 'Trả lời tạm'))
    el.appendChild(document.createTextNode(t.content))
    const nguon = t.citations.filter((c) => c.title)
    if (nguon.length > 0) el.appendChild(this.veNguon(nguon))
    if (t.senderType === 'BOT' && t.rateable) el.appendChild(this.veDanhGia(t.id))
    return el
  }

  /**
   * UC023 — "Nguồn: <tiêu đề>"; bấm vào một nguồn thì mở đoạn trích đã dùng. Dùng <details> sẵn có
   * của trình duyệt: bàn phím và trình đọc màn hình dùng được, không cần thêm mã. Đoạn trích gán bằng
   * textContent như mọi nội dung khác.
   */
  private veNguon(nguon: TinNhan['citations']): HTMLElement {
    const khoi = tao('div', 'nguon')
    khoi.appendChild(tao('b', undefined, 'Nguồn:'))
    const daCo = new Set<string>()
    for (const c of nguon) {
      const khoa = `${c.title}|${c.snippet ?? ''}`
      if (daCo.has(khoa)) continue
      daCo.add(khoa)
      if (!c.snippet) {
        khoi.appendChild(tao('div', 'muc', c.title ?? ''))
        continue
      }
      const chiTiet = tao('details', 'muc')
      chiTiet.appendChild(tao('summary', undefined, c.title ?? ''))
      chiTiet.appendChild(tao('div', 'trich', c.snippet))
      khoi.appendChild(chiTiet)
    }
    return khoi
  }

  /**
   * UC027 bước 1–5 — 👍/👎 dưới câu trả lời của tác tử. 👍 gửi ngay, không hỏi lý do (3.1); 👎 mở
   * bốn lý do + ô nhận xét, chưa chọn lý do thì chưa gửi được (bước 3). Gửi xong thay bằng lời cảm ơn.
   */
  private veDanhGia(messageId: string): HTMLElement {
    const khoi = tao('div', 'danh-gia')
    const hang = tao('div', 'hang-dg')
    hang.appendChild(tao('span', 'hoi', 'Câu trả lời có hữu ích không?'))
    const khen = this.nutDg('👍', 'Hữu ích')
    const che = this.nutDg('👎', 'Chưa ổn')
    hang.append(khen, che)
    const loi = tao('div', 'loi-dg')
    loi.hidden = true
    khoi.append(hang, loi)

    const gui = async (yc: YeuCauDanhGia, nutKhoa: HTMLButtonElement[]): Promise<void> => {
      nutKhoa.forEach((n) => (n.disabled = true))
      loi.hidden = true
      try {
        await this.suKien.onDanhGia(messageId, yc)
        khoi.replaceChildren(tao('div', 'cam-on', 'Cảm ơn bạn đã đánh giá!'))
      } catch (e) {
        loi.textContent = e instanceof Error ? e.message : 'Chưa gửi được, bạn thử lại nhé.'
        loi.hidden = false
        nutKhoa.forEach((n) => (n.disabled = false))
      }
    }

    khen.addEventListener('click', () => void gui({ rating: 'POSITIVE' }, [khen, che]))
    che.addEventListener('click', () => {
      if (khoi.querySelector('.form-dg')) return
      che.setAttribute('aria-pressed', 'true')
      const f = tao('form', 'form-dg')
      f.noValidate = true
      const nhom = tao('div', 'ly-do')
      nhom.setAttribute('role', 'radiogroup')
      nhom.setAttribute('aria-label', 'Lý do chưa ổn')
      let chon: LyDoChe | null = null
      const nutGui = tao('button', 'gui', 'Gửi')
      nutGui.type = 'submit'
      nutGui.disabled = true
      for (const [ma, nhan] of LY_DO_CHE) {
        const n = tao('button', 'chon', nhan)
        n.type = 'button'
        n.setAttribute('role', 'radio')
        n.setAttribute('aria-checked', 'false')
        n.addEventListener('click', () => {
          chon = ma
          nhom.querySelectorAll('button').forEach((b) => b.setAttribute('aria-checked', String(b === n)))
          nutGui.disabled = false
        })
        nhom.appendChild(n)
      }
      const nhanXet = tao('textarea')
      nhanXet.rows = 2
      nhanXet.maxLength = 1000
      nhanXet.placeholder = 'Nhận xét thêm (không bắt buộc)'
      nhanXet.setAttribute('aria-label', 'Nhận xét thêm')
      f.append(tao('div', 'hoi', 'Câu trả lời chưa ổn ở đâu?'), nhom, nhanXet, nutGui)
      f.addEventListener('submit', (e) => {
        e.preventDefault()
        if (!chon) return
        void gui({ rating: 'NEGATIVE', reasonCode: chon, comment: nhanXet.value.trim() || undefined }, [nutGui, khen])
      })
      khoi.insertBefore(f, loi)
      this.cuonXuong()
    })
    return khoi
  }

  private nutDg(bieuTuong: string, nhan: string): HTMLButtonElement {
    const n = tao('button', 'nut-dg', bieuTuong)
    n.type = 'button'
    n.setAttribute('aria-label', nhan)
    n.title = nhan
    return n
  }

  private cuonXuong(): void {
    this.than.scrollTop = this.than.scrollHeight
  }
}
