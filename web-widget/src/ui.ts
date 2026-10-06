// [PRODUCTION] Dựng giao diện widget trong Shadow DOM.
// Nội dung tin nhắn LUÔN gán bằng textContent, không bao giờ innerHTML: câu trả lời của AI và tin
// nhân viên có thể chứa chuỗi do khách khác cố tình nhét vào (bề mặt T2) — innerHTML là XSS ngay
// trên website của doanh nghiệp.

import type { GiaoDien, TinNhan } from './api'
import { CSS } from './styles'

const MAU_MAC_DINH = '#4F46E5'
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
  private dangGo: HTMLDivElement | null = null
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
    phu.append(tao('span', undefined, 'Trả lời tự động bởi trợ lý AI'), this.nutGapNv)
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
    el.appendChild(document.createTextNode(t.content))
    const nguon = t.citations.filter((c) => c.title)
    if (nguon.length > 0) {
      const khoi = tao('div', 'nguon')
      khoi.appendChild(tao('b', undefined, 'Nguồn: '))
      khoi.appendChild(document.createTextNode([...new Set(nguon.map((c) => c.title))].join(', ')))
      el.appendChild(khoi)
    }
    return el
  }

  private cuonXuong(): void {
    this.than.scrollTop = this.than.scrollHeight
  }
}
