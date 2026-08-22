import { HttpResponse, delay, http } from 'msw'

import {
  banGhiDayDu,
  danhSachKiemToan,
  danhSachYeuCauXoa,
  xemTruocPhamVi,
} from '@/mocks/du-lieu-kiem-toan'
import { NGUOI_DUNG_MAU } from '@/mocks/handlers/xac-thuc'
import { locTheo, loi, ok, trangHoa } from '@/mocks/tienIch'
import type { BanGhiKiemToan, YeuCauXoaChiTiet } from '@/types/schema'

let kiemToan: BanGhiKiemToan[] = [...danhSachKiemToan]
let yeuCauXoa: YeuCauXoaChiTiet[] = danhSachYeuCauXoa.map((y) => ({ ...y }))
let idKe = 41_209

/** Ghi một dòng nhật ký mới — dùng cho chính những thao tác phải ghi lại vết. */
function ghiNhatKy(
  than: Pick<BanGhiKiemToan, 'action' | 'severity' | 'containsPersonalData'> &
    Partial<BanGhiKiemToan>,
) {
  const moi: BanGhiKiemToan = {
    id: (idKe += 1),
    actorType: 'USER',
    actorId: NGUOI_DUNG_MAU.id,
    actorEmail: NGUOI_DUNG_MAU.email,
    entityType: null,
    entityId: null,
    before: null,
    after: null,
    reason: null,
    masked: false,
    ipAddress: '113.161.42.18',
    traceId: crypto.randomUUID(),
    occurredAt: new Date().toISOString(),
    ...than,
  }
  kiemToan = [moi, ...kiemToan]
  return moi
}

export const kiemToanHandlers = [
  // ── SCR054 — nhật ký kiểm toán ────────────────────────────────────────────
  http.get('/api/v1/audit-logs', async ({ request }) => {
    await delay(340)
    const url = new URL(request.url)
    let ket = locTheo(kiemToan, url.searchParams.get('severity'), (b, v) => b.severity === v)
    ket = locTheo(ket, url.searchParams.get('action'), (b, v) => b.action === v)
    ket = locTheo(ket, url.searchParams.get('entityType'), (b, v) => b.entityType === v)
    ket = locTheo(ket, url.searchParams.get('actorId'), (b, v) => b.actorId === v)
    const tu = url.searchParams.get('from')
    const den = url.searchParams.get('to')
    if (tu) ket = ket.filter((b) => b.occurredAt.slice(0, 10) >= tu)
    if (den) ket = ket.filter((b) => b.occurredAt.slice(0, 10) <= den)
    return HttpResponse.json(
      ok(
        trangHoa(ket, {
          url,
          co: 10,
          sapMacDinh: '-occurredAt',
          timTrong: (b) => [b.action, b.actorEmail, b.entityType, b.reason, b.traceId],
        }),
      ),
    )
  }),

  /**
   * Bỏ che một bản ghi.
   *
   * Bản thân lời gọi này **cũng được ghi vào nhật ký** — đó là điểm mấu chốt của cơ chế, không
   * phải chi tiết phụ: xem dữ liệu cá nhân của khách là một hành vi phải truy vết được.
   */
  http.post('/api/v1/audit-logs/:id/reveal', async ({ params, request }) => {
    await delay(600)
    const id = Number(params.id)
    const b = kiemToan.find((x) => x.id === id)
    if (!b) return HttpResponse.json(loi('Không tìm thấy bản ghi kiểm toán.'), { status: 404 })
    const { reason } = (await request.json()) as { reason?: string }
    if (!reason || reason.trim().length < 10) {
      return HttpResponse.json(loi('Lý do xem phải có ít nhất 10 ký tự.'), { status: 422 })
    }
    const day = banGhiDayDu[id]
    const boChe: BanGhiKiemToan = {
      ...b,
      masked: false,
      before: (day?.before ?? b.before) as BanGhiKiemToan['before'],
      after: (day?.after ?? b.after) as BanGhiKiemToan['after'],
    }
    kiemToan = kiemToan.map((x) => (x.id === id ? boChe : x))
    ghiNhatKy({
      action: 'AUDIT_LOG_REVEALED',
      severity: 'WARNING',
      containsPersonalData: true,
      entityType: 'audit_log',
      reason: reason.trim(),
      after: { revealedLogId: id },
    })
    return HttpResponse.json(ok(boChe))
  }),

  // ── SCR055 — xem trước phạm vi ảnh hưởng ──────────────────────────────────
  // ĐỨNG TRƯỚC `/:id`. MSW lấy handler khớp đầu tiên, nên đảo hai dòng này là `preview` bị hiểu
  // thành một mã yêu cầu và màn xem trước trả về 404.
  http.get('/api/v1/erasure-requests/preview', async ({ request }) => {
    await delay(700)
    const khachHangId = new URL(request.url).searchParams.get('contactId')
    if (!khachHangId) {
      return HttpResponse.json(loi('Thiếu mã khách hàng cần xem trước.'), { status: 422 })
    }
    return HttpResponse.json(ok(xemTruocPhamVi()))
  }),

  // ── SCR056 — danh sách yêu cầu xoá ────────────────────────────────────────
  http.get('/api/v1/erasure-requests', async ({ request }) => {
    await delay(320)
    const url = new URL(request.url)
    const ket = locTheo(yeuCauXoa, url.searchParams.get('status'), (y, v) => y.status === v)
    return HttpResponse.json(
      ok(
        trangHoa(ket, {
          url,
          co: 10,
          sapMacDinh: '-requestedAt',
          timTrong: (y) => [y.contactName, y.legalBasis],
        }),
      ),
    )
  }),

  // ── SCR057 — tiến độ theo từng bảng ───────────────────────────────────────
  http.get('/api/v1/erasure-requests/:id', async ({ params }) => {
    await delay(300)
    const y = yeuCauXoa.find((x) => x.id === params.id)
    if (!y) return HttpResponse.json(loi('Không tìm thấy yêu cầu xoá.'), { status: 404 })
    return HttpResponse.json(ok(y))
  }),

  // ── SCR058 — thực thi ─────────────────────────────────────────────────────
  http.post('/api/v1/erasure-requests/:id/execute', async ({ params }) => {
    await delay(1_400)
    const id = params.id as string
    const y = yeuCauXoa.find((x) => x.id === id)
    if (!y) return HttpResponse.json(loi('Không tìm thấy yêu cầu xoá.'), { status: 404 })
    if (y.status === 'COMPLETED') {
      return HttpResponse.json(loi('Yêu cầu này đã thực thi xong, không chạy lại được.'), {
        status: 409,
      })
    }

    const luc = new Date().toISOString()
    const capNhat: YeuCauXoaChiTiet = {
      ...y,
      status: 'COMPLETED',
      startedAt: y.startedAt ?? luc,
      completedAt: luc,
      // Chạy lại chỉ đụng vào những mục chưa xong — mục `DONE` giữ nguyên số dòng và mốc thời gian
      items: y.items.map((m) =>
        m.status === 'DONE'
          ? m
          : { ...m, status: 'DONE' as const, affectedRows: m.affectedRows ?? 0, errorMessage: null, executedAt: luc },
      ),
      certificateUri: `/api/v1/erasure-requests/${id}/certificate.pdf`,
    }
    yeuCauXoa = yeuCauXoa.map((x) => (x.id === id ? capNhat : x))
    ghiNhatKy({
      action: 'ERASURE_EXECUTED',
      severity: 'CRITICAL',
      containsPersonalData: true,
      entityType: 'contact',
      entityId: y.contactId,
      reason: y.legalBasis,
      masked: true,
      before: { fullName: '***', phone: '***', email: '***' },
      after: { fullName: 'Khách đã ẩn danh', phone: null, email: null },
    })
    return HttpResponse.json(ok(capNhat), { status: 202 })
  }),
]
