import { HttpResponse, delay, http } from 'msw'

import {
  chiTietDeal,
  chiTietLead,
  danhSachDeal,
  danhSachHoatDong,
  danhSachLead,
  danhSachPheu,
  hoiThoaiTheoNgay,
  pheuChuyenDoi,
  thongKeChuDe,
  tongQuan,
} from '@/mocks/du-lieu-ban-hang'
import { chiTietKhachHang } from '@/mocks/du-lieu-khach-hang'
import { danhSachNguoiDung } from '@/mocks/du-lieu-nen-tang'
import { NGUOI_DUNG_MAU } from '@/mocks/handlers/xac-thuc'
import { locTheo, loi, ok, trangHoa } from '@/mocks/tienIch'
import type { Deal, HoatDong, Lead, Pheu } from '@/types/schema'

let lead: Lead[] = [...danhSachLead]
let deal: Deal[] = [...danhSachDeal]
let hoatDong: HoatDong[] = [...danhSachHoatDong]

/** Tính lại số đếm và tổng tiền của từng giai đoạn từ danh sách deal hiện tại. */
function pheuTuoi(): Pheu[] {
  return danhSachPheu.map((p) => ({
    ...p,
    stages: p.stages.map((g) => {
      const cua = deal.filter((d) => d.stageId === g.id)
      return { ...g, dealCount: cua.length, dealValueTotal: cua.reduce((t, d) => t + (d.amount ?? 0), 0) }
    }),
  }))
}

export const banHangHandlers = [
  // ── Phân tích ─────────────────────────────────────────────────────────────
  http.get('/api/v1/analytics/overview', async () => {
    await delay(340)
    return HttpResponse.json(ok(tongQuan))
  }),

  http.get('/api/v1/analytics/conversations', async ({ request }) => {
    await delay(420)
    const url = new URL(request.url)
    const tu = url.searchParams.get('from')
    const den = url.searchParams.get('to')
    let ket = hoiThoaiTheoNgay
    if (tu) ket = ket.filter((d) => d.statDate >= tu)
    if (den) ket = ket.filter((d) => d.statDate <= den)
    return HttpResponse.json(ok(ket))
  }),

  http.get('/api/v1/analytics/funnel', async ({ request }) => {
    await delay(400)
    const url = new URL(request.url)
    const ket = locTheo(pheuChuyenDoi, url.searchParams.get('leadSource'), (b, v) => b.leadSource === v)
    return HttpResponse.json(ok(ket))
  }),

  http.get('/api/v1/analytics/topics', async () => {
    await delay(380)
    return HttpResponse.json(ok(thongKeChuDe))
  }),

  // UC042 nhánh 4.2 — máy chủ sinh tệp đồng bộ và trả thẳng nội dung. Không có
  // danh sách tệp đã xuất vì không có tệp nào được lưu lại; hậu điều kiện "ghi vào
  // nhật ký kiểm toán" do handler audit-logs đảm nhiệm.
  http.post('/api/v1/reports/exports', async ({ request }) => {
    await delay(700)
    const than = (await request.json()) as {
      reportType: string
      format: 'CSV' | 'XLSX'
      confirmPersonalData?: boolean
    }
    if (than.reportType === 'AUDIT_LOG' && !than.confirmPersonalData) {
      return HttpResponse.json(
        loi('Báo cáo có chứa dữ liệu cá nhân. Cần xác nhận trước khi xuất.'),
        { status: 422 },
      )
    }
    const noiDung = `bao_cao;${than.reportType};${new Date().toISOString()}\n`
    return new HttpResponse(noiDung, {
      status: 200,
      headers: {
        'Content-Type': than.format === 'CSV' ? 'text/csv' : 'application/octet-stream',
        'Content-Disposition': `attachment; filename="${than.reportType.toLowerCase()}.${than.format.toLowerCase()}"`,
      },
    })
  }),

  // ── SCR041–SCR043 cơ hội tiềm năng ────────────────────────────────────────
  http.get('/api/v1/leads', async ({ request }) => {
    await delay(380)
    const url = new URL(request.url)
    let ket = locTheo(lead, url.searchParams.get('status'), (l, v) => l.status === v)
    ket = locTheo(ket, url.searchParams.get('source'), (l, v) => l.source === v)
    ket = locTheo(ket, url.searchParams.get('ownerUserId'), (l, v) => l.ownerUserId === v)
    const diemToiThieu = url.searchParams.get('minScore')
    if (diemToiThieu) ket = ket.filter((l) => (l.currentScore ?? 0) >= Number(diemToiThieu))
    return HttpResponse.json(
      ok(
        trangHoa(ket, {
          url,
          co: 10,
          sapMacDinh: '-currentScore',
          timTrong: (l) => [l.contactName, l.interestedProduct, l.contactPhone],
        }),
      ),
    )
  }),

  http.post('/api/v1/leads', async ({ request }) => {
    await delay(650)
    const than = (await request.json()) as {
      contactId: string
      interestedProduct?: string | null
      budgetMin?: number | null
      budgetMax?: number | null
      urgency?: Lead['urgency']
      ownerUserId?: string | null
    }
    const k = chiTietKhachHang[than.contactId]
    if (!k) return HttpResponse.json(loi('Không tìm thấy khách hàng.'), { status: 404 })
    const nguoi = danhSachNguoiDung.find((u) => u.id === than.ownerUserId)
    const moi: Lead = {
      id: crypto.randomUUID(),
      contactId: k.id,
      contactName: k.fullName ?? 'Khách chưa có tên',
      contactPhone: k.phone ?? null,
      sourceConversationId: null,
      // Tạo tay thì nguồn là MANUAL và **chưa có điểm**: mô hình chấm điểm chạy trên tín hiệu
      // hội thoại, mà lead nhập tay thì chưa có hội thoại nào.
      source: 'MANUAL',
      status: 'NEW',
      interestedProduct: than.interestedProduct ?? null,
      budgetMin: than.budgetMin ?? null,
      budgetMax: than.budgetMax ?? null,
      budgetConfidence: than.budgetMin ? 'MEDIUM' : null,
      urgency: than.urgency ?? null,
      currentScore: null,
      scoreUpdatedAt: null,
      ownerUserId: than.ownerUserId ?? null,
      ownerName: nguoi?.fullName ?? null,
      createdAt: new Date().toISOString(),
    }
    lead = [moi, ...lead]
    chiTietLead[moi.id] = {
      ...moi,
      latestScore: null,
      disqualifyReason: null,
      convertedDealId: null,
      convertedAt: null,
      activityCount: 0,
      closedAt: null,
    }
    return HttpResponse.json(ok(moi), { status: 201 })
  }),

  http.get('/api/v1/leads/:id', async ({ params }) => {
    await delay(300)
    const l = chiTietLead[params.id as string]
    if (!l) return HttpResponse.json(loi('Không tìm thấy cơ hội tiềm năng.'), { status: 404 })
    return HttpResponse.json(ok(l))
  }),

  http.patch('/api/v1/leads/:id', async ({ params, request }) => {
    await delay(500)
    const id = params.id as string
    const l = chiTietLead[id]
    if (!l) return HttpResponse.json(loi('Không tìm thấy cơ hội tiềm năng.'), { status: 404 })
    Object.assign(l, await request.json())
    lead = lead.map((x) => (x.id === id ? { ...x, ...l } : x))
    return HttpResponse.json(ok(l))
  }),

  http.post('/api/v1/leads/:id/convert', async ({ params, request }) => {
    await delay(900)
    const id = params.id as string
    const l = chiTietLead[id]
    if (!l) return HttpResponse.json(loi('Không tìm thấy cơ hội tiềm năng.'), { status: 404 })
    if (l.status === 'CONVERTED') {
      return HttpResponse.json(loi('Cơ hội này đã được chuyển đổi rồi.'), { status: 409 })
    }
    const { pipelineId, stageId } = (await request.json()) as { pipelineId: string; stageId: string }
    const gd = danhSachPheu[0].stages.find((g) => g.id === stageId)
    const moi: Deal = {
      id: crypto.randomUUID(),
      contactId: l.contactId,
      contactName: l.contactName,
      leadId: l.id,
      pipelineId,
      stageId,
      stageName: gd?.name ?? '',
      title: l.interestedProduct ?? `Cơ hội của ${l.contactName}`,
      amount: l.budgetMax ?? l.budgetMin ?? null,
      currency: 'VND',
      expectedCloseDate: null,
      isOverdue: false,
      status: 'OPEN',
      source: 'AI_LEAD',
      ownerUserId: l.ownerUserId ?? null,
      ownerName: l.ownerName ?? null,
      stageChangedAt: new Date().toISOString(),
      createdAt: new Date().toISOString(),
    }
    deal = [moi, ...deal]
    chiTietDeal[moi.id] = { ...moi, closeReason: null, closedAt: null, stageHistory: [], activities: [] }
    l.status = 'CONVERTED'
    l.convertedDealId = moi.id
    l.convertedAt = new Date().toISOString()
    lead = lead.map((x) => (x.id === id ? { ...x, status: 'CONVERTED' as const } : x))
    return HttpResponse.json(ok(moi), { status: 201 })
  }),

  // ── SCR044–SCR046 cơ hội bán hàng ─────────────────────────────────────────
  http.get('/api/v1/pipelines', async () => {
    await delay(260)
    return HttpResponse.json(ok(pheuTuoi()))
  }),

  http.get('/api/v1/deals', async ({ request }) => {
    await delay(420)
    const url = new URL(request.url)
    let ket = locTheo(deal, url.searchParams.get('pipelineId'), (d, v) => d.pipelineId === v)
    ket = locTheo(ket, url.searchParams.get('stageId'), (d, v) => d.stageId === v)
    ket = locTheo(ket, url.searchParams.get('status'), (d, v) => d.status === v)
    ket = locTheo(ket, url.searchParams.get('ownerUserId'), (d, v) => d.ownerUserId === v)
    return HttpResponse.json(ok(trangHoa(ket, { url, co: 200, sapMacDinh: '-createdAt' })))
  }),

  http.post('/api/v1/deals', async ({ request }) => {
    await delay(700)
    const than = (await request.json()) as {
      contactId: string
      pipelineId: string
      stageId: string
      title: string
      amount?: number | null
      expectedCloseDate?: string | null
      ownerUserId?: string | null
    }
    const k = chiTietKhachHang[than.contactId]
    if (!k) return HttpResponse.json(loi('Không tìm thấy khách hàng.'), { status: 404 })
    const gd = danhSachPheu[0].stages.find((g) => g.id === than.stageId)
    if (!gd) return HttpResponse.json(loi('Giai đoạn không thuộc phễu này.'), { status: 400 })
    const nguoi = danhSachNguoiDung.find((u) => u.id === than.ownerUserId)
    const moi: Deal = {
      id: crypto.randomUUID(),
      contactId: k.id,
      contactName: k.fullName ?? 'Khách chưa có tên',
      leadId: null,
      pipelineId: than.pipelineId,
      stageId: than.stageId,
      stageName: gd.name,
      title: than.title,
      amount: than.amount ?? null,
      currency: 'VND',
      expectedCloseDate: than.expectedCloseDate ?? null,
      isOverdue: false,
      status: 'OPEN',
      source: 'MANUAL',
      ownerUserId: than.ownerUserId ?? null,
      ownerName: nguoi?.fullName ?? null,
      stageChangedAt: new Date().toISOString(),
      createdAt: new Date().toISOString(),
    }
    deal = [moi, ...deal]
    chiTietDeal[moi.id] = { ...moi, closeReason: null, closedAt: null, stageHistory: [], activities: [] }
    return HttpResponse.json(ok(moi), { status: 201 })
  }),

  http.post('/api/v1/deals/:id/stage', async ({ params, request }) => {
    await delay(450)
    const id = params.id as string
    const d = chiTietDeal[id]
    if (!d) return HttpResponse.json(loi('Không tìm thấy cơ hội bán hàng.'), { status: 404 })
    const { stageId, closeReason } = (await request.json()) as {
      stageId: string
      closeReason?: string | null
    }
    const gd = danhSachPheu[0].stages.find((g) => g.id === stageId)
    if (!gd) return HttpResponse.json(loi('Giai đoạn không thuộc phễu này.'), { status: 400 })

    // Giai đoạn từ "Đã báo giá" trở đi bắt buộc có số tiền. Kiểm ở máy chủ chứ không chỉ ở giao
    // diện: kéo thả là thao tác dễ làm nhanh, và một cơ hội không có số tiền thì mọi báo cáo
    // doanh thu đều sai.
    if ((gd.requiredFields ?? []).includes('amount') && d.amount == null) {
      return HttpResponse.json(
        loi(`Giai đoạn "${gd.name}" cần có giá trị cơ hội. Nhập số tiền trước khi chuyển.`),
        { status: 422 },
      )
    }

    const truoc = danhSachPheu[0].stages.find((g) => g.id === d.stageId)
    d.stageHistory = [
      ...(d.stageHistory ?? []),
      {
        fromStageId: truoc?.id ?? null,
        fromStageName: truoc?.name ?? null,
        toStageId: gd.id,
        toStageName: gd.name,
        durationSeconds: 3_600,
        changedByName: NGUOI_DUNG_MAU.fullName,
        changedAt: new Date().toISOString(),
      },
    ]
    d.stageId = gd.id
    d.stageName = gd.name
    d.stageChangedAt = new Date().toISOString()
    d.status = gd.isWon ? 'WON' : gd.isLost ? 'LOST' : 'OPEN'
    if (closeReason) d.closeReason = closeReason
    if (d.status !== 'OPEN') d.closedAt = new Date().toISOString()
    deal = deal.map((x) => (x.id === id ? { ...x, ...d } : x))
    return HttpResponse.json(ok(d))
  }),

  http.get('/api/v1/deals/:id', async ({ params }) => {
    await delay(320)
    const d = chiTietDeal[params.id as string]
    if (!d) return HttpResponse.json(loi('Không tìm thấy cơ hội bán hàng.'), { status: 404 })
    return HttpResponse.json(ok({ ...d, activities: hoatDong.filter((h) => h.dealId === d.id) }))
  }),

  // ── SCR047 hoạt động ──────────────────────────────────────────────────────
  http.get('/api/v1/activities', async ({ request }) => {
    await delay(360)
    const url = new URL(request.url)
    let ket = locTheo(hoatDong, url.searchParams.get('contactId'), (h, v) => h.contactId === v)
    ket = locTheo(ket, url.searchParams.get('leadId'), (h, v) => h.leadId === v)
    ket = locTheo(ket, url.searchParams.get('dealId'), (h, v) => h.dealId === v)
    ket = locTheo(ket, url.searchParams.get('type'), (h, v) => h.type === v)
    ket = locTheo(ket, url.searchParams.get('remindStatus'), (h, v) => h.remindStatus === v)
    return HttpResponse.json(
      ok(
        trangHoa(ket, {
          url,
          co: 10,
          sapMacDinh: '-performedAt',
          timTrong: (h) => [h.contactName, h.subject],
        }),
      ),
    )
  }),

  http.post('/api/v1/activities', async ({ request }) => {
    await delay(600)
    const than = (await request.json()) as {
      contactId: string
      leadId?: string | null
      dealId?: string | null
      type: HoatDong['type']
      subject?: string | null
      content?: string | null
    }
    // Ràng buộc của ERD: `num_nonnulls(lead_id, deal_id) = 1`. Gửi cả hai hoặc không gửi cái nào
    // đều bị từ chối — kiểm ở đây để lỗi lộ ra ngay, không đợi tới lúc nối cơ sở dữ liệu thật.
    const soGan = [than.leadId, than.dealId].filter(Boolean).length
    if (soGan !== 1) {
      return HttpResponse.json(
        loi('Hoạt động phải gắn với đúng một trong hai: cơ hội tiềm năng hoặc cơ hội bán hàng.'),
        { status: 422 },
      )
    }
    const k = chiTietKhachHang[than.contactId]
    const moi: HoatDong = {
      id: crypto.randomUUID(),
      contactId: than.contactId,
      contactName: k?.fullName ?? 'Khách chưa có tên',
      leadId: than.leadId ?? null,
      dealId: than.dealId ?? null,
      type: than.type,
      subject: than.subject ?? null,
      content: than.content ?? null,
      outcome: null,
      source: 'MANUAL',
      performedBy: NGUOI_DUNG_MAU.id,
      performedByName: NGUOI_DUNG_MAU.fullName ?? NGUOI_DUNG_MAU.email,
      performedAt: new Date().toISOString(),
      remindAt: null,
      remindUserId: null,
      remindStatus: 'NONE',
      createdAt: new Date().toISOString(),
    }
    hoatDong = [moi, ...hoatDong]
    return HttpResponse.json(ok(moi), { status: 201 })
  }),
]
