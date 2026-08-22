import { HttpResponse, delay, http } from 'msw'

import {
  chiTietKhachHang,
  danhSachKhachHang,
  danhSachThe,
  ghiChuKhachHang,
} from '@/mocks/du-lieu-khach-hang'
import { NGUOI_DUNG_MAU } from '@/mocks/handlers/xac-thuc'
import { boDau, loi, ok, trangHoa } from '@/mocks/tienIch'
import type { GhiChu, KhachHang, KhachHangChiTiet } from '@/types/schema'

let khachHang: KhachHang[] = [...danhSachKhachHang]
const chiTiet: Record<string, KhachHangChiTiet> = { ...chiTietKhachHang }
const ghiChu: Record<string, GhiChu[]> = { ...ghiChuKhachHang }

/** Số điện thoại so sau khi bỏ hết khoảng trắng — khách gõ "0903118274" phải ra "0903 118 274". */
const chuanSo = (s: string) => s.replace(/[\s.-]/g, '')

export const khachHangHandlers = [
  http.get('/api/v1/tags', async () => {
    await delay(180)
    return HttpResponse.json(ok(danhSachThe))
  }),

  http.get('/api/v1/contacts/:id/notes', async ({ params }) => {
    await delay(260)
    return HttpResponse.json(ok(ghiChu[params.id as string] ?? []))
  }),

  http.post('/api/v1/contacts/:id/notes', async ({ params, request }) => {
    await delay(500)
    const id = params.id as string
    const than = (await request.json()) as { content: string; conversationId?: string | null }
    const moi: GhiChu = {
      id: crypto.randomUUID(),
      content: than.content,
      conversationId: than.conversationId ?? null,
      authorUserId: NGUOI_DUNG_MAU.id,
      authorName: NGUOI_DUNG_MAU.fullName ?? NGUOI_DUNG_MAU.email,
      // Máy chủ tự đánh dấu khi thấy dạng số giống CCCD hoặc thẻ — Nghị định 13. Việc này phải
      // làm ở máy chủ chứ không phải ở trình duyệt: người gõ có thể tắt JavaScript.
      flaggedSensitive: /\d{9,}/.test(than.content),
      canEdit: true,
      editedAt: null,
      createdAt: new Date().toISOString(),
    }
    ghiChu[id] = [moi, ...(ghiChu[id] ?? [])]
    return HttpResponse.json(ok(moi), { status: 201 })
  }),

  http.post('/api/v1/contacts/:id/merge', async ({ params, request }) => {
    await delay(1100)
    const giu = params.id as string
    const { mergedContactId } = (await request.json()) as { mergedContactId: string }
    if (giu === mergedContactId) {
      return HttpResponse.json(loi('Không hợp nhất một hồ sơ với chính nó.'), { status: 400 })
    }
    const a = chiTiet[giu]
    const b = chiTiet[mergedContactId]
    if (!a || !b) return HttpResponse.json(loi('Không tìm thấy hồ sơ.'), { status: 404 })

    // Bản bị hợp nhất KHÔNG bị xoá: nó chuyển sang MERGED và trỏ về bản giữ lại. Xoá thẳng là
    // làm gãy mọi hội thoại, cơ hội và hoạt động đang trỏ tới nó.
    b.status = 'MERGED'
    b.mergedIntoContactId = giu
    a.channelIdentities = [...(a.channelIdentities ?? []), ...(b.channelIdentities ?? [])]
    a.conversationCount = (a.conversationCount ?? 0) + (b.conversationCount ?? 0)
    a.tags = [...(a.tags ?? []), ...(b.tags ?? []).filter((t) => !(a.tags ?? []).some((x) => x.id === t.id))]
    khachHang = khachHang.map((k) =>
      k.id === mergedContactId ? { ...k, status: 'MERGED' as const } : k.id === giu ? { ...a } : k,
    )
    return HttpResponse.json(ok(a))
  }),

  http.get('/api/v1/contacts/:id', async ({ params }) => {
    await delay(320)
    const k = chiTiet[params.id as string]
    if (!k) return HttpResponse.json(loi('Không tìm thấy khách hàng.'), { status: 404 })
    return HttpResponse.json(ok(k))
  }),

  http.patch('/api/v1/contacts/:id', async ({ params, request }) => {
    await delay(600)
    const id = params.id as string
    const k = chiTiet[id]
    if (!k) return HttpResponse.json(loi('Không tìm thấy khách hàng.'), { status: 404 })
    Object.assign(k, await request.json())
    khachHang = khachHang.map((x) => (x.id === id ? { ...x, ...k } : x))
    return HttpResponse.json(ok(k))
  }),

  http.post('/api/v1/contacts', async ({ request }) => {
    await delay(700)
    const than = (await request.json()) as Partial<KhachHang>
    const moi: KhachHangChiTiet = {
      id: crypto.randomUUID(),
      fullName: than.fullName ?? null,
      phone: than.phone ?? null,
      email: than.email ?? null,
      primaryChannel: than.primaryChannel ?? 'PHONE',
      status: 'ACTIVE',
      consentGranted: than.consentGranted ?? false,
      consentAt: than.consentGranted ? new Date().toISOString() : null,
      tags: [],
      lastInteractionAt: null,
      createdAt: new Date().toISOString(),
      mergedIntoContactId: null,
      channelIdentities: [],
      conversationCount: 0,
      openLeadCount: 0,
      openDealCount: 0,
      totalDealValue: 0,
      anonymizedAt: null,
    }

    /**
     * Trùng thì **cảnh báo**, không chặn.
     *
     * Chặn cứng nghe có vẻ an toàn nhưng làm luồng hợp nhất (SCR025) không chạy được: hai hồ sơ
     * phải cùng tồn tại thì mới hợp nhất được. Nhân viên là người quyết định đây là người mới
     * hay người cũ đổi số.
     */
    const trung = khachHang.filter(
      (k) =>
        k.status === 'ACTIVE' &&
        ((moi.phone && k.phone && chuanSo(k.phone) === chuanSo(moi.phone)) ||
          (moi.email && k.email && k.email.toLowerCase() === moi.email.toLowerCase())),
    )

    chiTiet[moi.id] = moi
    khachHang = [moi, ...khachHang]
    return HttpResponse.json(ok({ contact: moi, duplicateCandidates: trung }), { status: 201 })
  }),

  http.get('/api/v1/contacts', async ({ request }) => {
    await delay(400)
    const url = new URL(request.url)
    const tuKhoa = boDau((url.searchParams.get('q') ?? '').trim())
    const trangThai = url.searchParams.get('status')
    const daDongY = url.searchParams.get('hasConsent')

    let ket = khachHang.filter((k) =>
      // Bản ghi đã hợp nhất và đã ẩn danh hoá không hiện trong danh bạ trừ khi lọc đích danh —
      // chúng còn tồn tại để giữ liên kết cũ, không phải để tra cứu
      trangThai ? k.status === trangThai : k.status === 'ACTIVE',
    )
    if (tuKhoa) {
      ket = ket.filter(
        (k) =>
          boDau(k.fullName ?? '').includes(tuKhoa) ||
          chuanSo(k.phone ?? '').includes(chuanSo(tuKhoa)) ||
          (k.email ?? '').toLowerCase().includes(tuKhoa),
      )
    }
    if (daDongY !== null) {
      ket = ket.filter((k) => k.consentGranted === (daDongY === 'true'))
    }

    // Tìm kiếm đã làm ở trên (số điện thoại cần bỏ khoảng trắng, khác luật chung), nên
    // `trangHoa` chỉ còn lo sắp xếp và cắt trang.
    return HttpResponse.json(ok(trangHoa(ket, { url, co: 10, sapMacDinh: '-lastInteractionAt' })))
  }),
]
