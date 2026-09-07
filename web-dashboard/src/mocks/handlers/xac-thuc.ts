import { HttpResponse, delay, http } from 'msw'

import { boDau, loi, ok } from '@/mocks/tienIch'
import type { DangKyResult, NguoiDungHienTai } from '@/types/schema'

export const NGUOI_DUNG_MAU: NguoiDungHienTai = {
  id: 'u1000000-0000-4000-8000-000000000001',
  fullName: 'Phạm Hoài An',
  email: 'an.pham@cattuong.vn',
  roleCode: 'TENANT_ADMIN',
  permissions: [
    'conversations.read',
    'conversations.write',
    'contacts.read',
    'contacts.write',
    'settings.manage',
    'audit.read',
  ],
  tenantName: 'Công ty TNHH Cát Tường',
  planName: 'Growth',
}

/** Thư đã có doanh nghiệp đăng ký — dùng để thử nhánh 409 của SCR001. */
const THU_DA_DUNG = ['an.pham@cattuong.vn', 'admin@cattuong.vn']

/** Máy chủ sinh `slug` từ tên doanh nghiệp, không nhận từ phía gọi. */
function slugHoa(ten: string): string {
  return boDau(ten)
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 60)
}

export const xacThucHandlers = [
  http.post('/api/v1/auth/login', async () => {
    await delay(400)
    return HttpResponse.json(ok({ accessToken: 'mau-access-token', nguoiDung: NGUOI_DUNG_MAU }))
  }),

  http.post('/api/v1/auth/refresh', async () => {
    await delay(200)
    return HttpResponse.json(ok({ accessToken: 'mau-access-token-moi' }))
  }),

  http.post('/api/v1/auth/logout', async () => {
    await delay(150)
    return HttpResponse.json(ok(null))
  }),

  // SCR001 — đăng ký doanh nghiệp
  http.post('/api/v1/auth/register', async ({ request }) => {
    await delay(800)
    const than = (await request.json()) as {
      companyName: string
      fullName: string
      email: string
      password: string
      acceptedTerms?: boolean
    }
    if (THU_DA_DUNG.includes(than.email.toLowerCase())) {
      return HttpResponse.json(
        loi('Địa chỉ thư này đã đăng ký một doanh nghiệp. Đăng nhập hoặc dùng thư khác.'),
        { status: 409 },
      )
    }
    if (!than.acceptedTerms) {
      return HttpResponse.json(loi('Cần đồng ý điều khoản trước khi tạo tài khoản.'), {
        status: 422,
      })
    }
    const kq: DangKyResult = {
      tenantId: crypto.randomUUID(),
      slug: slugHoa(than.companyName),
      email: than.email,
      // Chưa xác thực thư thì chưa đăng nhập được — đăng ký **không** trả về access token
      verificationRequired: true,
    }
    return HttpResponse.json(ok(kq), { status: 201 })
  }),

  // SCR002 — xác thực địa chỉ thư
  http.post('/api/v1/auth/verify-email', async ({ request }) => {
    await delay(600)
    const than = (await request.json()) as { token?: string }
    // Mã "het-han" cho phép thử nhánh thất bại mà không phải chờ token thật hết hạn
    if (!than.token || than.token === 'het-han') {
      return HttpResponse.json(loi('Liên kết xác thực đã hết hạn hoặc đã được dùng.'), {
        status: 410,
      })
    }
    return HttpResponse.json(ok(null))
  }),

  http.post('/api/v1/auth/resend-verification', async () => {
    await delay(500)
    return HttpResponse.json(ok(null), { status: 202 })
  }),

  // SCR004 — yêu cầu đặt lại mật khẩu. Luôn trả thành công, kể cả khi thư không tồn tại:
  // trả khác nhau là biến endpoint này thành công cụ dò tài khoản (bề mặt T7).
  http.post('/api/v1/auth/forgot-password', async () => {
    await delay(600)
    return HttpResponse.json(ok(null), { status: 202 })
  }),

  // SCR005 — đặt lại mật khẩu bằng mã
  http.post('/api/v1/auth/reset-password', async ({ request }) => {
    await delay(700)
    const than = (await request.json()) as { token?: string; newPassword?: string }
    if (!than.token || than.token === 'het-han') {
      return HttpResponse.json(
        loi('Mã đặt lại đã hết hạn. Yêu cầu một liên kết mới rồi thử lại.'),
        { status: 410 },
      )
    }
    return HttpResponse.json(ok(null))
  }),

  http.get('/api/v1/me', async () => {
    await delay(150)
    return HttpResponse.json(ok(NGUOI_DUNG_MAU))
  }),
]
