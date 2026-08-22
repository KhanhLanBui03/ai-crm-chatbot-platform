import type { ApiResponse, Page } from '@/types/api'

/**
 * Tiện ích dùng chung cho tầng mock.
 *
 * Mười bốn màn danh sách cùng cần một việc: lọc, tìm, sắp, cắt trang. Viết lại mười bốn lần thì
 * mỗi lần là một cơ hội để mock lệch khỏi hành vi máy chủ — và lệch ở mock thì lộ ra rất muộn,
 * lúc nối backend thật.
 */

/** Vỏ phản hồi của java-core. Handler nào cũng phải trả đúng hình dạng này. */
export function ok<T>(data: T): ApiResponse<T> {
  return { success: true, data, message: null, traceId: null, timestamp: new Date().toISOString() }
}

export function loi(message: string, traceId = crypto.randomUUID()) {
  return { success: false, data: null, message, traceId, timestamp: new Date().toISOString() }
}

/**
 * Bỏ dấu tiếng Việt để tìm "huong" ra "Hường".
 * Máy chủ thật làm việc này bằng `unaccent` của PostgreSQL — ở đây chỉ mô phỏng cho đúng cảm giác.
 */
export function boDau(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()
}

export interface ThamSoTrang<T> {
  /** Tham số truy vấn của chính request — đọc `page`, `size`, `sort` từ đây. */
  url: URL
  /** Các trường được tìm theo từ khoá `q`. Bỏ trống là tắt tìm kiếm. */
  timTrong?: (muc: T) => Array<string | null | undefined>
  /** Cỡ trang mặc định khi request không nói. */
  co?: number
  /** Khoá sắp xếp mặc định, ví dụ `-createdAt`. */
  sapMacDinh?: string
}

/**
 * Lọc theo `q`, sắp theo `sort`, cắt theo `page`/`size` — đúng thứ tự máy chủ làm.
 *
 * Thứ tự quan trọng: cắt trang **sau cùng**. Cắt trước rồi mới lọc là lọc trên 25 dòng của trang
 * hiện tại chứ không phải trên cả tập, và bug đó trông giống hệt "dữ liệu bị thiếu".
 */
export function trangHoa<T extends Record<string, unknown>>(
  nguon: T[],
  { url, timTrong, co = 25, sapMacDinh }: ThamSoTrang<T>,
): Page<T> {
  let ket = [...nguon]

  const tuKhoa = boDau((url.searchParams.get('q') ?? '').trim())
  if (tuKhoa && timTrong) {
    ket = ket.filter((m) =>
      timTrong(m).some((truong) => truong != null && boDau(String(truong)).includes(tuKhoa)),
    )
  }

  const sapXep = url.searchParams.get('sort') ?? sapMacDinh
  if (sapXep) {
    const giam = sapXep.startsWith('-')
    const truong = giam ? sapXep.slice(1) : sapXep
    ket.sort((a, b) => {
      const va = a[truong]
      const vb = b[truong]
      // Số so bằng số, còn lại so bằng chuỗi có nhận biết tiếng Việt
      if (typeof va === 'number' && typeof vb === 'number') return (giam ? -1 : 1) * (va - vb)
      return (giam ? -1 : 1) * String(va ?? '').localeCompare(String(vb ?? ''), 'vi')
    })
  }

  const trang = Number(url.searchParams.get('page') ?? 0)
  const coTrang = Number(url.searchParams.get('size') ?? co)
  const tong = ket.length

  return {
    items: ket.slice(trang * coTrang, (trang + 1) * coTrang),
    page: trang,
    size: coTrang,
    totalItems: tong,
    totalPages: Math.max(Math.ceil(tong / coTrang), 1),
  }
}

/** Lọc theo một tham số truy vấn tuỳ chọn — bỏ qua khi tham số không có mặt. */
export function locTheo<T>(ds: T[], giaTri: string | null, khop: (m: T, v: string) => boolean): T[] {
  return giaTri === null ? ds : ds.filter((m) => khop(m, giaTri))
}

/** Sinh một dãy ngày lùi về trước, dùng cho biểu đồ và bảng theo ngày. */
export function daySoNgay(soNgay: number, moc = new Date()): string[] {
  return Array.from({ length: soNgay }, (_, i) => {
    const d = new Date(moc)
    d.setDate(d.getDate() - (soNgay - 1 - i))
    return d.toISOString().slice(0, 10)
  })
}
