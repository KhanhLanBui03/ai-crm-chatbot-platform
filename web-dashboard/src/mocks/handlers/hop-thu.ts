import { HttpResponse, delay, http } from 'msw'

import { chiTietHoiThoai, danhSachHoiThoai, nguCanhHoiThoai } from '@/mocks/du-lieu'
import { danhSachNguoiDung } from '@/mocks/du-lieu-nen-tang'
import { NGUOI_DUNG_MAU } from '@/mocks/handlers/xac-thuc'
import { loi, ok } from '@/mocks/tienIch'
import type { Page } from '@/types/api'
import type {
  HoiThoaiTomTat,
  LyDoChuyenGiao,
  SuKienChuyenGiao,
  TrangThaiHoiThoai,
} from '@/types/schema'

export const hopThuHandlers = [
  // ── SCR021 phân công và chuyển giao ───────────────────────────────────────
  http.post('/api/v1/conversations/:id/assign', async ({ params, request }) => {
    await delay(550)
    const c = danhSachHoiThoai.find((x) => x.id === params.id)
    const ct = chiTietHoiThoai[params.id as string]
    if (!c || !ct) return HttpResponse.json(loi('Không tìm thấy hội thoại.'), { status: 404 })
    const than = (await request.json()) as { assigneeUserId?: string | null }
    // Bỏ trống là tự nhận về mình — đúng thao tác thường gặp nhất ở hộp thư
    const id = than.assigneeUserId ?? NGUOI_DUNG_MAU.id
    const nguoi = danhSachNguoiDung.find((u) => u.id === id)
    for (const o of [c, ct]) {
      o.assignedUserId = id
      o.assignedUserName = nguoi?.fullName ?? NGUOI_DUNG_MAU.fullName
      o.status = 'AGENT_HANDLING'
    }
    return HttpResponse.json(ok({ ...c }))
  }),

  http.post('/api/v1/conversations/:id/handoff', async ({ params, request }) => {
    await delay(650)
    const c = danhSachHoiThoai.find((x) => x.id === params.id)
    const ct = chiTietHoiThoai[params.id as string]
    if (!c || !ct) return HttpResponse.json(loi('Không tìm thấy hội thoại.'), { status: 404 })
    const than = (await request.json()) as {
      direction: 'BOT_TO_AGENT' | 'AGENT_TO_BOT'
      reason: LyDoChuyenGiao
    }
    const veNguoi = than.direction === 'BOT_TO_AGENT'
    for (const o of [c, ct]) {
      o.status = veNguoi ? 'PENDING_AGENT' : 'BOT_HANDLING'
    }
    ct.autoReplyEnabled = !veNguoi
    const su: SuKienChuyenGiao = {
      id: crypto.randomUUID(),
      direction: than.direction,
      reason: than.reason,
      triggeredBy: 'AGENT',
      /**
       * Chỉ những lý do do chính tác tử gây ra mới tính vào chất lượng AI. Khách chủ động đòi
       * gặp người (`CUSTOMER_REQUEST`) hay hết hạn mức (`QUOTA_EXCEEDED`) mà tính vào thì chỉ
       * số ở SCR051 nói dối theo hướng bi quan.
       */
      countsAgainstAiQuality: !['CUSTOMER_REQUEST', 'QUOTA_EXCEEDED'].includes(than.reason),
      toUserId: veNguoi ? null : NGUOI_DUNG_MAU.id,
      queuedAt: veNguoi ? new Date().toISOString() : null,
      acceptedAt: null,
      occurredAt: new Date().toISOString(),
    }
    return HttpResponse.json(ok(su))
  }),

  http.post('/api/v1/conversations/:id/status', async ({ params, request }) => {
    await delay(500)
    const c = danhSachHoiThoai.find((x) => x.id === params.id)
    const ct = chiTietHoiThoai[params.id as string]
    if (!c || !ct) return HttpResponse.json(loi('Không tìm thấy hội thoại.'), { status: 404 })
    const than = (await request.json()) as { status: TrangThaiHoiThoai; closedReason?: string }
    for (const o of [c, ct]) o.status = than.status
    if (than.status === 'RESOLVED') ct.resolvedAt = new Date().toISOString()
    if (than.closedReason) ct.closedReason = than.closedReason
    return HttpResponse.json(ok({ ...c }))
  }),

  http.get('/api/v1/conversations', async ({ request }) => {
    await delay(350)
    const url = new URL(request.url)
    const phamVi = url.searchParams.get('scope') ?? 'all'
    const trangThai = url.searchParams.get('status')?.split(',').filter(Boolean) as
      | TrangThaiHoiThoai[]
      | undefined
    const tuKhoa = (url.searchParams.get('q') ?? '').trim().toLowerCase()

    let ket = [...danhSachHoiThoai]
    if (phamVi === 'mine') {
      ket = ket.filter((c) => c.assignedUserId === NGUOI_DUNG_MAU.id)
    } else if (phamVi === 'unassigned') {
      ket = ket.filter((c) => c.assignedUserId === null && c.status === 'PENDING_AGENT')
    }
    if (trangThai?.length) {
      ket = ket.filter((c) => trangThai.includes(c.status))
    }
    if (tuKhoa) {
      ket = ket.filter(
        (c) =>
          c.contactName.toLowerCase().includes(tuKhoa) ||
          (c.lastMessagePreview ?? '').toLowerCase().includes(tuKhoa),
      )
    }
    // Khoá sắp xếp mặc định của hộp thư: last_message_at giảm dần
    ket.sort((a, b) => b.lastMessageAt.localeCompare(a.lastMessageAt))

    const trang: Page<HoiThoaiTomTat> = {
      items: ket,
      page: 0,
      size: 25,
      totalItems: ket.length,
      totalPages: 1,
    }
    return HttpResponse.json(ok(trang))
  }),

  http.get('/api/v1/conversations/:id/context', async ({ params }) => {
    await delay(300)
    const nguCanh = nguCanhHoiThoai[params.id as string]
    if (!nguCanh) return HttpResponse.json(loi('Không tìm thấy ngữ cảnh hội thoại.'), { status: 404 })
    return HttpResponse.json(ok(nguCanh))
  }),

  http.get('/api/v1/conversations/:id', async ({ params }) => {
    await delay(250)
    const chiTiet = chiTietHoiThoai[params.id as string]
    if (!chiTiet) return HttpResponse.json(loi('Không tìm thấy hội thoại.'), { status: 404 })
    return HttpResponse.json(ok(chiTiet))
  }),
]
