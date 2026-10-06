// [PRODUCTION] Điểm vào của widget nhúng (UC009 bước 9–11, UC010).
//
// Doanh nghiệp dán một thẻ:
//   <script src="https://<gateway>/widget.js" data-widget-key="wk_..." async></script>
// Tuỳ chọn data-api-url khi API nằm ở địa chỉ khác nơi phục vụ widget.js.

import { LoiApi, WidgetApi, type TinNhan } from './api'
import { docToken, luuToken, xoaToken } from './session'
import { GiaoDienChat } from './ui'

const CHU_KY_HOI_MS = 5000
const DANG_CO_NHAN_VIEN = new Set(['PENDING_AGENT', 'AGENT_HANDLING'])

function timThe(): HTMLScriptElement | null {
  // currentScript chỉ có khi chạy ĐỒNG BỘ lúc trang tải; bản dev chạy dạng module thì không có
  const s = document.currentScript
  if (s instanceof HTMLScriptElement && s.dataset.widgetKey) return s
  return document.querySelector<HTMLScriptElement>('script[data-widget-key]')
}

class WidgetApp {
  private token: string | null
  private trangThai: string | null = null
  private moc: string | null = null
  private hoi: number | undefined
  private daKhoiTao = false
  private readonly ui: GiaoDienChat
  private readonly api: WidgetApi
  private readonly key: string

  constructor(key: string, apiUrl: string) {
    this.key = key
    this.api = new WidgetApi(apiUrl)
    this.token = docToken(key)
    const chuNha = document.createElement('div')
    chuNha.id = 'crm-ai-widget'
    document.body.appendChild(chuNha)
    this.ui = new GiaoDienChat(chuNha, {
      onGui: (n) => void this.gui(n),
      onGapNhanVien: () => void this.gapNhanVien(),
      onMo: () => this.batDauHoi(),
    })
  }

  async khoiTao(): Promise<void> {
    try {
      const p = await this.api.moPhien(this.key, this.token)
      this.daKhoiTao = true
      if (p.status === 'SUSPENDED' || !p.token) {
        this.ui.hienTamNgung()
        return
      }
      this.token = p.token
      luuToken(this.key, p.token)
      this.ui.apDungGiaoDien(p.appearance)
      this.ui.hienLoiChao(p.appearance?.greetingMessage ?? null)
      this.capNhat(p.conversationStatus, p.messages)
    } catch (e) {
      // 403 = tên miền chưa được phép (UC009 10.2): KHÔNG hiện widget trên trang nhúng trái phép
      if (e instanceof LoiApi && (e.maHttp === 403 || e.maHttp === 404)) {
        document.getElementById('crm-ai-widget')?.remove()
        console.warn('[CRM AI widget]', e.message)
        return
      }
      this.ui.hienLoiChao(null)
      this.ui.baoLoi(e instanceof Error ? e.message : 'Không mở được khung chat.')
    }
  }

  private capNhat(trangThai: string | null, ds: TinNhan[]): void {
    if (trangThai) this.trangThai = trangThai
    if (ds.length > 0) {
      this.ui.themTin(ds)
      this.moc = ds[ds.length - 1].sentAt
    }
    // Chỉ cho bấm "Gặp nhân viên" khi đã có hội thoại và AI đang giữ
    this.ui.datCoTheGapNhanVien(this.trangThai === 'BOT_HANDLING')
    this.ui.datNguoiTraLoi(this.trangThai)
    this.batDauHoi()
  }

  private async gui(noiDung: string): Promise<void> {
    if (!this.token) {
      if (!this.daKhoiTao) await this.khoiTao()
      if (!this.token) return
    }
    this.ui.baoLoi(null)
    this.ui.datDangGo(true)
    try {
      const kq = await this.api.guiTin(this.token, noiDung)
      this.ui.datDangGo(false)
      this.capNhat(kq.conversationStatus, kq.messages)
    } catch (e) {
      this.ui.datDangGo(false)
      this.xuLyLoi(e)
    }
  }

  private async gapNhanVien(): Promise<void> {
    if (!this.token) return
    this.ui.baoLoi(null)
    try {
      const kq = await this.api.gapNhanVien(this.token)
      this.capNhat(kq.conversationStatus, kq.messages)
    } catch (e) {
      this.xuLyLoi(e)
    }
  }

  /** Hỏi tin nhân viên trả lời (UC013) — chỉ khi khung đang mở VÀ hội thoại đang ở phía nhân viên. */
  private batDauHoi(): void {
    const canHoi = this.ui.dangMo && this.trangThai !== null && DANG_CO_NHAN_VIEN.has(this.trangThai)
    if (canHoi && this.hoi === undefined) {
      this.hoi = window.setInterval(() => void this.hoiTinMoi(), CHU_KY_HOI_MS)
    } else if (!canHoi && this.hoi !== undefined) {
      window.clearInterval(this.hoi)
      this.hoi = undefined
    }
  }

  private async hoiTinMoi(): Promise<void> {
    if (!this.token || !this.ui.dangMo) {
      this.batDauHoi()
      return
    }
    try {
      const kq = await this.api.tinMoi(this.token, this.moc)
      this.capNhat(kq.conversationStatus, kq.messages)
    } catch {
      /* lỗi mạng tạm thời khi hỏi định kỳ — lần sau thử lại, không làm phiền khách */
    }
  }

  private xuLyLoi(e: unknown): void {
    if (e instanceof LoiApi && e.maHttp === 401) {
      // Token hết hạn / bị thu hồi: bỏ token cũ, mở phiên mới ở lần gửi sau
      xoaToken(this.key)
      this.token = null
      this.daKhoiTao = false
    }
    this.ui.baoLoi(e instanceof Error ? e.message : 'Có lỗi xảy ra, bạn thử lại sau nhé.')
  }
}

function khoiDong(): void {
  const the = timThe()
  const key = the?.dataset.widgetKey
  if (!the || !key) {
    console.warn('[CRM AI widget] Thiếu thuộc tính data-widget-key trên thẻ <script>.')
    return
  }
  if (document.getElementById('crm-ai-widget')) return // đã nhúng hai lần
  const apiUrl = the.dataset.apiUrl || (the.src ? new URL(the.src).origin : window.location.origin)
  void new WidgetApp(key, apiUrl).khoiTao()
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', khoiDong)
} else {
  khoiDong()
}
