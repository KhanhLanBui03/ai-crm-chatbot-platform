import { HttpResponse, delay, http } from 'msw'

import {
  danhSachGoi,
  danhSachNguoiDung,
  danhSachVaiTro,
  hanMucHienTai,
  hoSoDoanhNghiep,
  mucSuDungTheoNgay,
  thueBaoHienTai,
} from '@/mocks/du-lieu-nen-tang'
import { loi, locTheo, ok, trangHoa } from '@/mocks/tienIch'
import type { DoanhNghiep, MaGoi } from '@/types/schema'

/** Bản ghi sống của phiên chạy — sửa được, để thao tác ghi thấy được hiệu lực ngay. */
let doanhNghiep: DoanhNghiep = { ...hoSoDoanhNghiep }
let nguoiDung = [...danhSachNguoiDung]
let thueBao = { ...thueBaoHienTai }

export const nenTangHandlers = [
  // ── SCR008 · SCR009 người dùng ─────────────────────────────────────────────
  http.get('/api/v1/users', async ({ request }) => {
    await delay(320)
    const url = new URL(request.url)
    let ket = locTheo(nguoiDung, url.searchParams.get('status'), (u, v) => u.status === v)
    ket = locTheo(ket, url.searchParams.get('roleCode'), (u, v) => u.roleCode === v)
    return HttpResponse.json(
      ok(
        trangHoa(ket, {
          url,
          co: 10,
          sapMacDinh: 'fullName',
          timTrong: (u) => [u.fullName, u.email],
        }),
      ),
    )
  }),

  http.post('/api/v1/users', async ({ request }) => {
    await delay(600)
    const than = (await request.json()) as { email: string; fullName?: string | null; roleCode: 'TENANT_ADMIN' | 'AGENT' }
    if (nguoiDung.some((u) => u.email.toLowerCase() === than.email.toLowerCase())) {
      return HttpResponse.json(loi('Địa chỉ thư này đã có trong doanh nghiệp.'), { status: 409 })
    }
    const moi = {
      id: crypto.randomUUID(),
      fullName: than.fullName ?? null,
      email: than.email,
      roleCode: than.roleCode,
      roleName: than.roleCode === 'TENANT_ADMIN' ? 'Quản trị doanh nghiệp' : 'Nhân viên chăm sóc',
      // Người được mời luôn ở PENDING cho tới khi họ xác thực thư — không có đường tắt
      status: 'PENDING' as const,
      emailVerifiedAt: null,
      lastLoginAt: null,
      assignedConversationCount: 0,
      createdAt: new Date().toISOString(),
    }
    nguoiDung = [moi, ...nguoiDung]
    return HttpResponse.json(ok(moi), { status: 201 })
  }),

  http.post('/api/v1/users/:id/disable', async ({ params }) => {
    await delay(400)
    const u = nguoiDung.find((x) => x.id === params.id)
    if (!u) return HttpResponse.json(loi('Không tìm thấy người dùng.'), { status: 404 })
    u.status = 'DISABLED'
    nguoiDung = [...nguoiDung]
    return HttpResponse.json(ok(u))
  }),

  http.post('/api/v1/users/:id/resend-invitation', async () => {
    await delay(500)
    return HttpResponse.json(ok(null))
  }),

  // ── SCR010 vai trò ─────────────────────────────────────────────────────────
  http.get('/api/v1/roles', async () => {
    await delay(200)
    return HttpResponse.json(ok(danhSachVaiTro))
  }),

  // ── SCR007 hồ sơ doanh nghiệp ──────────────────────────────────────────────
  http.get('/api/v1/tenant', async () => {
    await delay(250)
    return HttpResponse.json(ok(doanhNghiep))
  }),

  http.patch('/api/v1/tenant', async ({ request }) => {
    await delay(700)
    const than = (await request.json()) as Partial<DoanhNghiep>
    doanhNghiep = { ...doanhNghiep, ...than }
    return HttpResponse.json(ok(doanhNghiep))
  }),

  // ── SCR012 · SCR013 thuê bao và gói ────────────────────────────────────────
  http.get('/api/v1/plans', async () => {
    await delay(220)
    return HttpResponse.json(
      ok(danhSachGoi.map((g) => ({ ...g, isCurrent: g.code === thueBao.plan.code }))),
    )
  }),

  http.get('/api/v1/subscription', async () => {
    await delay(260)
    return HttpResponse.json(ok(thueBao))
  }),

  http.post('/api/v1/subscription/change', async ({ request }) => {
    await delay(900)
    const { planCode } = (await request.json()) as { planCode: MaGoi }
    const goi = danhSachGoi.find((g) => g.code === planCode)
    if (!goi) return HttpResponse.json(loi('Không có gói dịch vụ này.'), { status: 400 })

    const hienTai = thueBao.plan
    if (goi.sortOrder! >= hienTai.sortOrder!) {
      // Nâng gói có hiệu lực ngay
      thueBao = { ...thueBao, plan: goi, scheduledPlan: null, scheduledEffectiveAt: null }
    } else {
      // Hạ gói chỉ có hiệu lực từ chu kỳ sau — hạ giữa chừng là cắt hạn mức của phần đã trả tiền
      thueBao = { ...thueBao, scheduledPlan: goi, scheduledEffectiveAt: thueBao.periodEnd }
    }
    return HttpResponse.json(ok(thueBao))
  }),

  // ── SCR014 · SCR015 hạn mức ────────────────────────────────────────────────
  http.get('/api/v1/usage/daily', async ({ request }) => {
    await delay(380)
    const url = new URL(request.url)
    const tuNgay = url.searchParams.get('from')
    const denNgay = url.searchParams.get('to')
    let ket = mucSuDungTheoNgay
    if (tuNgay) ket = ket.filter((d) => d.statDate >= tuNgay)
    if (denNgay) ket = ket.filter((d) => d.statDate <= denNgay)
    return HttpResponse.json(ok(trangHoa(ket, { url, co: 12, sapMacDinh: '-statDate' })))
  }),

  http.get('/api/v1/usage', async () => {
    await delay(300)
    return HttpResponse.json(ok(hanMucHienTai))
  }),

]
