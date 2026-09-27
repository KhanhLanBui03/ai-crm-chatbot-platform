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
  scope: 'TENANT',
}

/** Tài khoản quản trị viên nền tảng — scope PLATFORM, không thuộc doanh nghiệp nào. */
export const ADMIN_NEN_TANG_MAU: NguoiDungHienTai = {
  id: 'a0000000-0000-4000-8000-000000000099',
  fullName: 'Quản trị viên Hệ thống',
  email: 'admin@platform.vn',
  roleCode: 'PLATFORM_ADMIN',
  permissions: [
    'platform.tenants.read',
    'platform.tenants.write',
    'platform.plans.read',
    'platform.plans.write',
    'platform.ai-usage.read',
    'platform.audit.read',
  ],
  tenantName: 'Nền tảng CRM AI',
  planName: 'Platform',
  scope: 'PLATFORM',
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
  http.post('/api/v1/auth/login', async ({ request }) => {
    await delay(400)
    const than = (await request.json()) as { email?: string; password?: string }
    const emailNhap = than.email?.trim() || 'an.pham@cattuong.vn'
    const laAdmin =
      emailNhap.toLowerCase().includes('admin@platform') ||
      emailNhap.toLowerCase() === 'admin@platform.local' ||
      emailNhap.toLowerCase() === 'admin@platform.vn'

    const matKhauLuu = typeof window !== 'undefined' ? localStorage.getItem(`mock_pwd_${emailNhap.toLowerCase()}`) : null
    if (matKhauLuu && than.password && than.password !== matKhauLuu) {
      return HttpResponse.json(loi('Email hoặc mật khẩu không chính xác.'), { status: 401 })
    }

    if (laAdmin) {
      return HttpResponse.json(
        ok({
          accessToken: 'mau-access-token-admin',
          nguoiDung: {
            ...ADMIN_NEN_TANG_MAU,
            email: emailNhap,
          },
        }),
      )
    }

    // Các email khác → trả tài khoản Tenant Admin mẫu với đúng email đã nhập
    return HttpResponse.json(
      ok({
        accessToken: 'mau-access-token',
        nguoiDung: {
          ...NGUOI_DUNG_MAU,
          email: emailNhap,
          fullName: emailNhap.split('@')[0] || NGUOI_DUNG_MAU.fullName,
        },
      }),
    )
  }),

  http.post('/api/v1/auth/refresh', async () => {
    await delay(200)
    return HttpResponse.json(ok({ accessToken: 'mau-access-token-moi' }))
  }),

  http.post('/api/v1/auth/logout', async () => {
    await delay(150)
    return HttpResponse.json(ok(null))
  }),

  http.post('/api/v1/auth/send-otp', async ({ request }) => {
    await delay(350)
    const than = (await request.json()) as { email?: string; companyName?: string; purpose?: string }
    if (than.email && THU_DA_DUNG.includes(than.email.toLowerCase()) && than.purpose === 'REGISTER') {
      return HttpResponse.json(
        loi('Địa chỉ thư này đã đăng ký một doanh nghiệp. Đăng nhập hoặc dùng thư khác.'),
        { status: 409 },
      )
    }
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

  // SCR005 — đặt lại mật khẩu bằng mã OTP hoặc token
  http.post('/api/v1/auth/reset-password', async ({ request }) => {
    await delay(700)
    const than = (await request.json()) as {
      email?: string
      otpCode?: string
      token?: string
      newPassword?: string
    }

    if (than.token === 'het-han') {
      return HttpResponse.json(
        loi('Mã đặt lại đã hết hạn. Yêu cầu một liên kết mới rồi thử lại.'),
        { status: 410 },
      )
    }

    if (than.otpCode && than.otpCode === '000000') {
      return HttpResponse.json(loi('Mã OTP không chính xác hoặc đã hết hạn.'), { status: 400 })
    }

    if (!than.token && !than.otpCode) {
      return HttpResponse.json(loi('Thiếu mã OTP hoặc mã đặt lại mật khẩu.'), { status: 400 })
    }

    // Lưu mật khẩu mới vào storage để phiên đăng nhập sau dùng được
    if (than.email && than.newPassword) {
      try {
        localStorage.setItem(`mock_pwd_${than.email.toLowerCase().trim()}`, than.newPassword)
      } catch {}
    }

    return HttpResponse.json(ok(null))
  }),

  http.get('/api/v1/me', async () => {
    await delay(150)
    return HttpResponse.json(ok(NGUOI_DUNG_MAU))
  }),
]
