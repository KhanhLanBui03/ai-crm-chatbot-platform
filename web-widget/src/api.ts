// [PRODUCTION] Lời gọi API công khai /api/v1/widget/** của java-core (qua gateway).
// Khớp WidgetDtos.java. Không bao giờ gửi tenant — máy chủ tự suy từ khoá và token đã ký.

export type TrangThaiPhien = 'ACTIVE' | 'SUSPENDED'
export type LoaiNguoiGui = 'CUSTOMER' | 'BOT' | 'AGENT' | 'SYSTEM'

export interface TrichDan {
  documentId: string | null
  title: string | null
  snippet: string | null
}

export interface TinNhan {
  id: string
  senderType: LoaiNguoiGui
  content: string
  citations: TrichDan[]
  sentAt: string
}

export interface GiaoDien {
  primaryColor: string | null
  position: 'BOTTOM_RIGHT' | 'BOTTOM_LEFT'
  greetingMessage: string | null
  avatarUrl: string | null
}

export interface KetQuaPhien {
  status: TrangThaiPhien
  token: string | null
  appearance: GiaoDien | null
  conversationStatus: string | null
  messages: TinNhan[]
}

export interface KetQuaLuot {
  conversationStatus: string | null
  messages: TinNhan[]
}

/** Lỗi có câu thông báo tiếng Việt từ máy chủ, kèm mã HTTP để widget xử lý riêng 401/429. */
export class LoiApi extends Error {
  readonly maHttp: number
  constructor(message: string, maHttp: number) {
    super(message)
    this.maHttp = maHttp
  }
}

export class WidgetApi {
  private readonly goc: string

  constructor(goc: string) {
    this.goc = goc.replace(/\/+$/, '')
  }

  moPhien(widgetKey: string, token: string | null): Promise<KetQuaPhien> {
    return this.goi('POST', '/api/v1/widget/session', null, { widgetKey, token })
  }

  guiTin(token: string, content: string): Promise<KetQuaLuot> {
    return this.goi('POST', '/api/v1/widget/messages', token, { content })
  }

  gapNhanVien(token: string): Promise<KetQuaLuot> {
    return this.goi('POST', '/api/v1/widget/handoff', token, undefined)
  }

  tinMoi(token: string, sau: string | null): Promise<KetQuaLuot> {
    const q = sau ? `?after=${encodeURIComponent(sau)}` : ''
    return this.goi('GET', `/api/v1/widget/messages${q}`, token, undefined)
  }

  private async goi<T>(method: string, duongDan: string, token: string | null, than: unknown): Promise<T> {
    const headers: Record<string, string> = {}
    if (than !== undefined) headers['Content-Type'] = 'application/json'
    if (token) headers['X-Widget-Token'] = token
    let res: Response
    try {
      res = await fetch(this.goc + duongDan, {
        method,
        headers,
        body: than === undefined ? undefined : JSON.stringify(than),
        credentials: 'omit',
      })
    } catch {
      throw new LoiApi('Không kết nối được máy chủ. Bạn kiểm tra mạng rồi thử lại nhé.', 0)
    }
    let json: { success?: boolean; data?: T; message?: string } = {}
    try {
      json = await res.json()
    } catch {
      /* phản hồi rỗng hoặc không phải JSON */
    }
    if (!res.ok || json.success === false) {
      throw new LoiApi(json.message || 'Có lỗi xảy ra, bạn thử lại sau nhé.', res.status)
    }
    return json.data as T
  }
}
