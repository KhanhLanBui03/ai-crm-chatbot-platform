import { HttpResponse, delay, http } from 'msw'

import {
  DOANH_NGHIEP_MAU,
  GOI_DICH_VU_MAU,
  TAI_NGUYEN_AI_MAU,
  THONG_KE_NEN_TANG,
} from '@/mocks/du-lieu-admin'
import { locTheo, ok, trangHoa } from '@/mocks/tienIch'

/** Bản sao có thể thay đổi — mutation handlers sẽ sửa trực tiếp để demo UI tức thì. */
let dsDoanhNghiep = [...DOANH_NGHIEP_MAU]
const dsGoiDV = [...GOI_DICH_VU_MAU]

export const adminHandlers = [
  // ── Tổng quan nền tảng ────────────────────────────────────────────────────
  http.get('/api/v1/admin/overview', async () => {
    await delay(300)
    return HttpResponse.json(ok(THONG_KE_NEN_TANG))
  }),

  // ── Danh sách doanh nghiệp ───────────────────────────────────────────────
  http.get('/api/v1/admin/tenants', async ({ request }) => {
    await delay(350)
    const url = new URL(request.url)
    const trangThai = url.searchParams.get('status')
    const goi = url.searchParams.get('planCode')

    let ket = [...dsDoanhNghiep]
    ket = locTheo(ket, trangThai, (m, v) => m.status === v)
    ket = locTheo(ket, goi, (m, v) => m.planCode === v)

    return HttpResponse.json(
      ok(
        trangHoa(ket as unknown as Record<string, unknown>[], {
          url,
          timTrong: (m) => [m.companyName as string, m.contactEmail as string, m.slug as string, (m.industry as string) || ''],
          sapMacDinh: '-createdAt',
        }),
      ),
    )
  }),

  // ── Chi tiết doanh nghiệp ────────────────────────────────────────────────
  http.get('/api/v1/admin/tenants/:id', async ({ params }) => {
    await delay(200)
    const dn = dsDoanhNghiep.find((d) => d.id === params.id)
    if (!dn) return HttpResponse.json(ok(null), { status: 404 })
    return HttpResponse.json(ok(dn))
  }),

  // ── Khóa doanh nghiệp ────────────────────────────────────────────────────
  http.post('/api/v1/admin/tenants/:id/suspend', async ({ params, request }) => {
    await delay(400)
    const than = (await request.json()) as { reason: string }
    const viTri = dsDoanhNghiep.findIndex((d) => d.id === params.id)
    if (viTri === -1) return HttpResponse.json(ok(null), { status: 404 })
    dsDoanhNghiep[viTri] = {
      ...dsDoanhNghiep[viTri],
      status: 'SUSPENDED',
      suspendedReason: than.reason,
    }
    return HttpResponse.json(ok(dsDoanhNghiep[viTri]))
  }),

  // ── Mở khóa doanh nghiệp ─────────────────────────────────────────────────
  http.post('/api/v1/admin/tenants/:id/activate', async ({ params }) => {
    await delay(300)
    const viTri = dsDoanhNghiep.findIndex((d) => d.id === params.id)
    if (viTri === -1) return HttpResponse.json(ok(null), { status: 404 })
    dsDoanhNghiep[viTri] = {
      ...dsDoanhNghiep[viTri],
      status: 'ACTIVE',
      suspendedReason: null,
    }
    return HttpResponse.json(ok(dsDoanhNghiep[viTri]))
  }),

  // ── Danh sách gói dịch vụ ─────────────────────────────────────────────────
  http.get('/api/v1/admin/plans', async () => {
    await delay(250)
    return HttpResponse.json(ok(dsGoiDV))
  }),

  // ── Cập nhật gói dịch vụ ──────────────────────────────────────────────────
  http.patch('/api/v1/admin/plans/:code', async ({ params, request }) => {
    await delay(400)
    const than = (await request.json()) as Partial<(typeof dsGoiDV)[0]>
    const viTri = dsGoiDV.findIndex((g) => g.code === params.code)
    if (viTri === -1) return HttpResponse.json(ok(null), { status: 404 })
    dsGoiDV[viTri] = { ...dsGoiDV[viTri], ...than }
    return HttpResponse.json(ok(dsGoiDV[viTri]))
  }),

  // ── Tài nguyên & Chi phí AI ───────────────────────────────────────────────
  http.get('/api/v1/admin/ai-usage', async () => {
    await delay(300)
    return HttpResponse.json(ok(TAI_NGUYEN_AI_MAU))
  }),
]
