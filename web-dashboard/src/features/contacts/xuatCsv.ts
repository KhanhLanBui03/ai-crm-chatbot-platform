import { format } from 'date-fns'

import { axiosClient } from '@/api/axiosClient'
import type { BoLocKhachHang } from '@/api/contacts'
import { NHAN_KENH } from '@/features/conversations/nhan'
import type { Page } from '@/types/api'
import type { KenhChinh, KhachHang } from '@/types/schema'

const NHAN_KENH_CHINH: Record<KenhChinh, string> = { ...NHAN_KENH, PHONE: 'Nhập tay' }

/** Trần số dòng một lần xuất — 50 trang × 100 dòng; danh bạ SME hiếm khi vượt. */
const TOI_DA_TRANG = 50

/**
 * Chặn "CSV injection": ô bắt đầu bằng = + - @ bị Excel hiểu là CÔNG THỨC. Tên khách do chính khách gõ
 * qua widget, nên một cái tên như `=HYPERLINK(...)` sẽ chạy khi nhân viên mở file — thêm dấu ' để Excel
 * coi là chữ.
 */
function o(giaTri: unknown): string {
  let s = giaTri == null ? '' : String(giaTri)
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`
  return /[",\n\r;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

/**
 * SĐT dạng ="0938…" để Excel giữ số 0 đầu (mở CSV thẳng, Excel đổi 0938123456 thành 938123456). An toàn
 * vì chỉ áp cho chuỗi CHỈ gồm chữ số (đã chuẩn hoá ở máy chủ) — không phải dữ liệu tự do của khách.
 */
function soDienThoai(sdt: string | null | undefined): string {
  if (!sdt) return ''
  return /^\+?\d{6,15}$/.test(sdt) ? `"=""${sdt}"""` : o(sdt)
}

function dong(k: KhachHang): string {
  return [
    o(k.fullName ?? ''),
    soDienThoai(k.phone),
    o(k.email ?? ''),
    o(NHAN_KENH_CHINH[k.primaryChannel as KenhChinh] ?? k.primaryChannel),
    o((k.tags ?? []).map((t) => t.name).join(', ')),
    o(k.consentGranted ? 'Đã đồng ý' : 'Chưa đồng ý'),
    o(k.lastInteractionAt ? format(new Date(k.lastInteractionAt), 'dd/MM/yyyy HH:mm') : ''),
  ].join(',')
}

/** Tải file CSV về máy. Có BOM UTF-8 để Excel đọc đúng tiếng Việt. */
export function taiCsv(ds: KhachHang[], tenFile: string): void {
  const dau = ['Họ tên', 'Số điện thoại', 'Email', 'Kênh chính', 'Thẻ', 'Đồng ý dữ liệu', 'Tương tác gần nhất']
  const noiDung = '﻿' + [dau.map(o).join(','), ...ds.map(dong)].join('\r\n')
  const url = URL.createObjectURL(new Blob([noiDung], { type: 'text/csv;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = tenFile
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/** Lấy TOÀN BỘ khách khớp bộ lọc đang chọn (đi qua từng trang 100 dòng) — cho nút "Xuất CSV". */
export async function layTatCaKhach(bo: BoLocKhachHang): Promise<{ ds: KhachHang[]; biCat: boolean }> {
  const ds: KhachHang[] = []
  for (let trang = 0; trang < TOI_DA_TRANG; trang++) {
    const { data } = await axiosClient.get<Page<KhachHang>>('/api/v1/contacts', {
      params: {
        q: bo.tuKhoa || undefined,
        status: bo.trangThai,
        hasConsent: bo.daDongY,
        sort: bo.sapXep,
        page: trang,
        size: 100,
      },
    })
    ds.push(...data.items)
    if (trang + 1 >= data.totalPages) return { ds, biCat: false }
  }
  return { ds, biCat: true }
}

/** Khách theo danh sách id — lấy từ trang đang xem, thiếu thì hỏi máy chủ từng hồ sơ. */
export async function layKhachTheoId(ids: string[], trangHienTai: KhachHang[]): Promise<KhachHang[]> {
  const coSan = new Map(trangHienTai.map((k) => [k.id, k]))
  return Promise.all(
    ids.map(async (id) => coSan.get(id) ?? (await axiosClient.get<KhachHang>(`/api/v1/contacts/${id}`)).data),
  )
}
