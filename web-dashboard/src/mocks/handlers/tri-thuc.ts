import { HttpResponse, delay, http } from 'msw'

import {
  chiTietTaiLieu,
  danhSachCongCu,
  danhSachCongViecNap,
  danhSachGoiCongCu,
  danhSachKhoangTrong,
  danhSachLuotXuLy,
  danhSachMayChuMcp,
  danhSachSuKienAnToan,
  danhSachTaiLieu,
  doanTheoTaiLieu,
  hieuQuaAi,
} from '@/mocks/du-lieu-tri-thuc'
import { NGUOI_DUNG_MAU } from '@/mocks/handlers/xac-thuc'
import { boDau, locTheo, loi, ok, trangHoa } from '@/mocks/tienIch'
import type {
  CongCu,
  CongViecNap,
  KetQuaTruyHoi,
  KhoangTrongTriThuc,
  MayChuMcp,
  NhatKyGoiCongCu,
  TaiLieu,
  TrangThaiCongViecNap,
} from '@/types/schema'

let taiLieu: TaiLieu[] = [...danhSachTaiLieu]
let congViecNap: CongViecNap[] = [...danhSachCongViecNap]
let khoangTrong: KhoangTrongTriThuc[] = [...danhSachKhoangTrong]
let mayChu: MayChuMcp[] = [...danhSachMayChuMcp]
let congCu: CongCu[] = [...danhSachCongCu]
let goiCongCu: NhatKyGoiCongCu[] = [...danhSachGoiCongCu]

// ── Truy hồi hai làn + hợp nhất RRF ──────────────────────────────────────────

/**
 * Điểm từ khoá — đếm lần xuất hiện của từng từ trong câu hỏi, chuẩn hoá theo độ dài đoạn.
 *
 * Chuẩn hoá độ dài là phần không được bỏ: không có nó thì đoạn dài luôn thắng chỉ vì dài hơn,
 * và làn từ khoá biến thành "sắp theo số ký tự".
 */
function diemTuKhoa(cauHoi: string, noiDung: string): number {
  const tu = boDau(cauHoi).split(/\s+/).filter((t) => t.length > 1)
  if (tu.length === 0) return 0
  const van = boDau(noiDung)
  const dem = tu.reduce((t, k) => t + (van.split(k).length - 1), 0)
  return dem === 0 ? 0 : dem / Math.sqrt(van.length)
}

/** Tập tam tự của một chuỗi — dùng làm biểu diễn thay cho vector nhúng ở tầng giả. */
function tamTu(s: string): Set<string> {
  const van = ` ${boDau(s).replace(/\s+/g, ' ')} `
  const tap = new Set<string>()
  for (let i = 0; i + 3 <= van.length; i += 1) tap.add(van.slice(i, i + 3))
  return tap
}

/**
 * Điểm "vector" — cosine trên tập tam tự ký tự.
 *
 * Không phải nhúng thật, nhưng có đúng tính chất khiến hai làn của ADR-0006 đáng tồn tại: nó bắt
 * được biến thể hình thái và lỗi gõ mà so khớp từ khoá bỏ sót, nên **thứ hạng hai làn lệch nhau**.
 * Nếu mock cho hai làn ra cùng một thứ tự thì SCR031 không chứng minh được điều gì.
 */
function diemVector(cauHoi: string, noiDung: string): number {
  const a = tamTu(cauHoi)
  const b = tamTu(noiDung)
  if (a.size === 0 || b.size === 0) return 0
  let chung = 0
  for (const t of a) if (b.has(t)) chung += 1
  return chung / Math.sqrt(a.size * b.size)
}

/** Hằng số RRF của ADR-0006. Giữ nguyên 60 để mock không lệch khỏi giao ước. */
const K_RRF = 60

/**
 * Mỗi làn chỉ trả về ngần này ứng viên.
 *
 * Có trần là phần **bắt buộc**, không phải tối ưu: bỏ trần đi thì với kho nhỏ cả hai làn cùng trả
 * về toàn bộ đoạn, thứ hạng hai làn phủ nhau hoàn toàn, và bước hợp nhất RRF trở thành một phép
 * cộng vô nghĩa. Máy chủ thật lấy top-20 trên kho hàng nghìn đoạn; ở đây 8 trên 20 đoạn đã là tỉ
 * lệ rộng rãi hơn nhiều.
 */
const SAU_MOI_LAN = 8

/**
 * Ngưỡng liên quan sau khi xếp hạng lại.
 *
 * `SAN_TOAN_BO` áp lên kết quả **đầu tiên**: không đoạn nào vượt được nghĩa là kho không có căn cứ
 * cho câu này, và đường ống thật sẽ để tác tử từ chối chứ không nhét năm đoạn lạc đề vào lời nhắc.
 * `SAN_TUNG_DOAN` cắt phần đuôi — đoạn dưới mức này chỉ làm loãng ngữ cảnh.
 */
const SAN_TOAN_BO = 0.25
const SAN_TUNG_DOAN = 0.15

function truyHoi(cauHoi: string, topK: number): KetQuaTruyHoi[] {
  const kho = taiLieu
    .filter((t) => t.status === 'READY')
    .flatMap((t) =>
      (doanTheoTaiLieu[t.id] ?? []).map((d) => ({
        chunk: d,
        documentId: t.id,
        documentTitle: t.title,
      })),
    )
  if (kho.length === 0) return []

  const noiDung = (m: (typeof kho)[number]) => `${m.chunk.sectionPath ?? ''} ${m.chunk.content}`

  const lanVector = [...kho]
    .map((m) => ({ m, diem: diemVector(cauHoi, noiDung(m)) }))
    .filter((x) => x.diem > 0)
    .sort((a, b) => b.diem - a.diem)
    .slice(0, SAU_MOI_LAN)

  const lanTuKhoa = [...kho]
    .map((m) => ({ m, diem: diemTuKhoa(cauHoi, noiDung(m)) }))
    .filter((x) => x.diem > 0)
    .sort((a, b) => b.diem - a.diem)
    .slice(0, SAU_MOI_LAN)

  const hangVector = new Map(lanVector.map((x, i) => [x.m.chunk.id, i + 1]))
  const hangTuKhoa = new Map(lanTuKhoa.map((x, i) => [x.m.chunk.id, i + 1]))

  const ungVien = new Map<string, (typeof kho)[number]>()
  for (const x of [...lanVector, ...lanTuKhoa]) ungVien.set(x.m.chunk.id, x.m)

  // Hợp nhất RRF: 1/(k + hạng) cộng dồn qua hai làn. Đoạn vắng mặt ở một làn thì làn đó góp 0.
  const hopNhat = [...ungVien.values()].map((m) => {
    const hv = hangVector.get(m.chunk.id)
    const ht = hangTuKhoa.get(m.chunk.id)
    return {
      m,
      rrf: (hv ? 1 / (K_RRF + hv) : 0) + (ht ? 1 / (K_RRF + ht) : 0),
      vectorRank: hv ?? null,
      keywordRank: ht ?? null,
    }
  })
  hopNhat.sort((a, b) => b.rrf - a.rrf)

  // Xếp hạng lại: chỉ 10 ứng viên đầu mới đi qua bước này, đúng như đường ống thật —
  // mô hình xếp hạng lại đắt hơn truy hồi vài bậc nên không bao giờ chạy trên cả kho.
  const daXep = hopNhat
    .slice(0, 10)
    .map((x) => ({
      chunk: x.m.chunk,
      documentId: x.m.documentId,
      documentTitle: x.m.documentTitle,
      score: 0.6 * diemVector(cauHoi, noiDung(x.m)) + 0.4 * Math.min(diemTuKhoa(cauHoi, noiDung(x.m)), 1),
      vectorRank: x.vectorRank,
      keywordRank: x.keywordRank,
    }))
    .sort((a, b) => b.score - a.score)

  if (daXep.length === 0 || daXep[0].score < SAN_TOAN_BO) return []
  return daXep.filter((x) => x.score >= SAN_TUNG_DOAN).slice(0, topK)
}

// ── Máy trạng thái của công việc nạp ─────────────────────────────────────────

const CHUOI_TRANG_THAI: TrangThaiCongViecNap[] = [
  'QUEUED',
  'EXTRACTING',
  'CHUNKING',
  'EMBEDDING',
  'INDEXING',
  'DONE',
]

/**
 * Đẩy các công việc đang chạy tiến một bước mỗi lần có ai hỏi tới.
 *
 * SCR033 là màn theo dõi tiến độ; một danh sách đứng yên không kiểm được rằng màn hình có nạp lại
 * và có chuyển sang trạng thái kết thúc đúng lúc hay không.
 */
function tienMotBuoc() {
  congViecNap = congViecNap.map((c) => {
    const i = CHUOI_TRANG_THAI.indexOf(c.state)
    if (i < 0 || i >= CHUOI_TRANG_THAI.length - 1) return c
    const moi = CHUOI_TRANG_THAI[i + 1]
    const xong = moi === 'DONE'
    const capNhat: CongViecNap = {
      ...c,
      state: moi,
      startedAt: c.startedAt ?? new Date().toISOString(),
      chunksCreated: xong ? (c.chunksCreated ?? 0) : (c.chunksCreated ?? 0) + 6,
      finishedAt: xong ? new Date().toISOString() : null,
      durationMs: xong ? 48_600 : null,
    }
    if (xong) {
      taiLieu = taiLieu.map((t) =>
        t.id === c.documentId
          ? {
              ...t,
              status: 'READY',
              chunkCount: capNhat.chunksCreated ?? 0,
              indexedAt: capNhat.finishedAt,
            }
          : t,
      )
      const ct = chiTietTaiLieu[c.documentId]
      if (ct) Object.assign(ct, { status: 'READY', chunkCount: capNhat.chunksCreated ?? 0 })
    }
    const ct = chiTietTaiLieu[c.documentId]
    if (ct) ct.latestJob = capNhat
    return capNhat
  })
}

export const triThucHandlers = [
  // ── SCR030 · SCR029 — tài liệu ────────────────────────────────────────────
  http.get('/api/v1/documents', async ({ request }) => {
    await delay(340)
    const url = new URL(request.url)
    let ket = locTheo(taiLieu, url.searchParams.get('status'), (t, v) => t.status === v)
    ket = locTheo(ket, url.searchParams.get('sourceType'), (t, v) => t.sourceType === v)
    return HttpResponse.json(
      ok(
        trangHoa(ket, {
          url,
          co: 10,
          sapMacDinh: '-createdAt',
          timTrong: (t) => [t.title, t.description, t.fileName],
        }),
      ),
    )
  }),

  http.post('/api/v1/documents', async ({ request }) => {
    await delay(900)
    // Giao ước khai `multipart/form-data` — đọc bằng `formData()`, không phải `json()`
    const than = await request.formData()
    const tep = than.get('file')
    const title = String(than.get('title') ?? '').trim()
    if (!(tep instanceof File)) {
      return HttpResponse.json(loi('Thiếu tệp tài liệu.'), { status: 400 })
    }
    if (!title) {
      return HttpResponse.json(loi('Tiêu đề không được để trống.'), { status: 422 })
    }
    if (tep.size > 20 * 1024 * 1024) {
      return HttpResponse.json(loi('Tệp vượt quá 20 MB. Tách nhỏ rồi tải lên từng phần.'), {
        status: 413,
      })
    }

    const duoi = tep.name.split('.').pop()?.toUpperCase() ?? ''
    const loaiNguon = (['PDF', 'DOCX', 'TXT', 'MD', 'HTML'] as const).find((x) => x === duoi)
    if (!loaiNguon) {
      return HttpResponse.json(
        loi('Định dạng không được hỗ trợ. Nhận PDF, DOCX, TXT, MD hoặc HTML.'),
        { status: 415 },
      )
    }

    const id = crypto.randomUUID()
    const moi: TaiLieu = {
      id,
      title,
      description: (than.get('description') as string | null) || null,
      sourceType: loaiNguon,
      fileName: tep.name,
      mimeType: tep.type || 'application/octet-stream',
      sizeBytes: tep.size,
      language: (than.get('language') as string | null) || 'vi',
      // Nạp là việc chạy nền — trả về PENDING chứ không trả về tài liệu đã lập chỉ mục
      status: 'PENDING',
      chunkCount: 0,
      version: 1,
      errorMessage: null,
      uploadedByName: NGUOI_DUNG_MAU.fullName ?? NGUOI_DUNG_MAU.email,
      indexedAt: null,
      createdAt: new Date().toISOString(),
    }
    const viec: CongViecNap = {
      id: crypto.randomUUID(),
      documentId: id,
      documentTitle: title,
      trigger: 'UPLOAD',
      state: 'QUEUED',
      attempt: 1,
      chunksCreated: 0,
      tokensUsed: 0,
      costVnd: 0,
      errorCode: null,
      errorMessage: null,
      durationMs: null,
      startedAt: null,
      finishedAt: null,
      createdAt: new Date().toISOString(),
    }
    taiLieu = [moi, ...taiLieu]
    congViecNap = [viec, ...congViecNap]
    chiTietTaiLieu[id] = { ...moi, replacesDocumentId: null, latestJob: viec, checksum: null }
    return HttpResponse.json(ok(moi), { status: 201 })
  }),

  http.get('/api/v1/documents/:id/chunks', async ({ params, request }) => {
    await delay(300)
    const id = params.id as string
    if (!chiTietTaiLieu[id]) {
      return HttpResponse.json(loi('Không tìm thấy tài liệu.'), { status: 404 })
    }
    return HttpResponse.json(
      ok(trangHoa(doanTheoTaiLieu[id] ?? [], { url: new URL(request.url), co: 10, sapMacDinh: 'ordinal' })),
    )
  }),

  http.post('/api/v1/documents/:id/reindex', async ({ params }) => {
    await delay(700)
    const id = params.id as string
    const t = chiTietTaiLieu[id]
    if (!t) return HttpResponse.json(loi('Không tìm thấy tài liệu.'), { status: 404 })
    const viec: CongViecNap = {
      id: crypto.randomUUID(),
      documentId: id,
      documentTitle: t.title,
      trigger: 'REINDEX',
      state: 'QUEUED',
      attempt: 1,
      chunksCreated: 0,
      tokensUsed: 0,
      costVnd: 0,
      errorCode: null,
      errorMessage: null,
      durationMs: null,
      startedAt: null,
      finishedAt: null,
      createdAt: new Date().toISOString(),
    }
    congViecNap = [viec, ...congViecNap]
    t.latestJob = viec
    t.status = 'PROCESSING'
    taiLieu = taiLieu.map((x) => (x.id === id ? { ...x, status: 'PROCESSING' as const } : x))
    return HttpResponse.json(ok(viec), { status: 202 })
  }),

  http.get('/api/v1/documents/:id', async ({ params }) => {
    await delay(260)
    // Cũng đẩy đường ống một bước: SCR033 vào theo đường `/tai-lieu/:id/tien-do` thì nó hỏi lại
    // **endpoint này**, không phải `/ingestion-jobs`. Chỉ đẩy ở một chỗ là màn kia đứng hình mãi.
    tienMotBuoc()
    const t = chiTietTaiLieu[params.id as string]
    if (!t) return HttpResponse.json(loi('Không tìm thấy tài liệu.'), { status: 404 })
    return HttpResponse.json(ok(t))
  }),

  http.delete('/api/v1/documents/:id', async ({ params }) => {
    await delay(500)
    const id = params.id as string
    if (!chiTietTaiLieu[id]) {
      return HttpResponse.json(loi('Không tìm thấy tài liệu.'), { status: 404 })
    }
    taiLieu = taiLieu.filter((t) => t.id !== id)
    delete chiTietTaiLieu[id]
    return HttpResponse.json(ok(null))
  }),

  // ── SCR031 — tìm thử trong kho tri thức ───────────────────────────────────
  http.get('/api/v1/knowledge/search', async ({ request }) => {
    await delay(620)
    const url = new URL(request.url)
    const cauHoi = (url.searchParams.get('q') ?? '').trim()
    if (cauHoi.length < 2) {
      return HttpResponse.json(loi('Câu hỏi phải có ít nhất 2 ký tự.'), { status: 422 })
    }
    const topK = Math.min(Number(url.searchParams.get('topK') ?? 5), 20)
    return HttpResponse.json(ok(truyHoi(cauHoi, topK)))
  }),

  // ── SCR033 — tiến độ nạp ──────────────────────────────────────────────────
  http.get('/api/v1/ingestion-jobs', async ({ request }) => {
    await delay(280)
    tienMotBuoc()
    const url = new URL(request.url)
    const ket = locTheo(congViecNap, url.searchParams.get('state'), (c, v) => c.state === v)
    return HttpResponse.json(ok(trangHoa(ket, { url, co: 10, sapMacDinh: '-createdAt' })))
  }),

  // ── SCR034 — khoảng trống tri thức ────────────────────────────────────────
  http.get('/api/v1/knowledge-gaps', async ({ request }) => {
    await delay(320)
    const url = new URL(request.url)
    const ket = locTheo(khoangTrong, url.searchParams.get('gapType'), (k, v) => k.gapType === v)
    return HttpResponse.json(
      ok(
        trangHoa(ket, {
          url,
          co: 10,
          sapMacDinh: '-distinctContactCount',
          timTrong: (k) => [k.questionText],
        }),
      ),
    )
  }),

  // ── SCR037 · SCR038 — máy chủ MCP ─────────────────────────────────────────
  http.get('/api/v1/mcp-servers', async () => {
    await delay(260)
    return HttpResponse.json(ok(mayChu))
  }),

  http.post('/api/v1/mcp-servers', async ({ request }) => {
    await delay(800)
    const than = (await request.json()) as {
      name: string
      endpointUrl: string
      transport: MayChuMcp['transport']
      specVersion: string
      authType: MayChuMcp['authType']
      secret?: string | null
      timeoutMs?: number
      maxCallsPerConversation?: number
    }
    if (mayChu.some((m) => m.endpointUrl === than.endpointUrl)) {
      return HttpResponse.json(loi('Địa chỉ này đã được cấu hình rồi.'), { status: 409 })
    }
    const moi: MayChuMcp = {
      id: crypto.randomUUID(),
      name: than.name,
      endpointUrl: than.endpointUrl,
      transport: than.transport,
      specVersion: than.specVersion,
      authType: than.authType,
      hasCredential: Boolean(than.secret),
      // Chưa bắt tay thì chưa biết máy chủ có sống không — PENDING chứ không phải ACTIVE
      status: 'PENDING',
      timeoutMs: than.timeoutMs ?? 5_000,
      circuitState: 'CLOSED',
      maxCallsPerConversation: than.maxCallsPerConversation ?? 10,
      toolCount: 0,
      enabledToolCount: 0,
      lastHandshakeAt: null,
      lastError: null,
    }
    mayChu = [...mayChu, moi]
    return HttpResponse.json(ok(moi), { status: 201 })
  }),

  http.post('/api/v1/mcp-servers/:id/handshake', async ({ params }) => {
    await delay(1_100)
    const id = params.id as string
    const m = mayChu.find((x) => x.id === id)
    if (!m) return HttpResponse.json(loi('Không tìm thấy máy chủ MCP.'), { status: 404 })
    if (m.specVersion !== '2025-06-18' && m.specVersion !== '2025-03-26') {
      return HttpResponse.json(
        loi(`Máy chủ không hỗ trợ phiên bản đặc tả đã ghim (${m.specVersion}).`),
        { status: 502 },
      )
    }
    const cua = congCu.filter((c) => c.mcpServerId === id)
    const capNhat: MayChuMcp = {
      ...m,
      status: 'ACTIVE',
      circuitState: 'CLOSED',
      lastHandshakeAt: new Date().toISOString(),
      lastError: null,
      toolCount: cua.length,
      enabledToolCount: cua.filter((c) => c.enabled).length,
    }
    mayChu = mayChu.map((x) => (x.id === id ? capNhat : x))
    return HttpResponse.json(ok({ server: capNhat, tools: cua }))
  }),

  http.patch('/api/v1/mcp-servers/:id', async ({ params, request }) => {
    await delay(520)
    const id = params.id as string
    const m = mayChu.find((x) => x.id === id)
    if (!m) return HttpResponse.json(loi('Không tìm thấy máy chủ MCP.'), { status: 404 })
    const than = (await request.json()) as Partial<MayChuMcp> & { secret?: string | null }
    const { secret, ...conLai } = than
    const capNhat: MayChuMcp = {
      ...m,
      ...conLai,
      hasCredential: secret ? true : m.hasCredential,
    }
    mayChu = mayChu.map((x) => (x.id === id ? capNhat : x))
    return HttpResponse.json(ok(capNhat))
  }),

  http.delete('/api/v1/mcp-servers/:id', async ({ params }) => {
    await delay(480)
    const id = params.id as string
    if (!mayChu.some((x) => x.id === id)) {
      return HttpResponse.json(loi('Không tìm thấy máy chủ MCP.'), { status: 404 })
    }
    // Ngắt kết nối, không xoá hẳn: nhật ký gọi công cụ vẫn phải tra ngược được về máy chủ nào
    mayChu = mayChu.map((x) =>
      x.id === id ? { ...x, status: 'DISCONNECTED' as const, enabledToolCount: 0 } : x,
    )
    congCu = congCu.map((c) =>
      c.mcpServerId === id
        ? { ...c, enabled: false, autoDisabledReason: 'SERVER_DISCONNECTED' as const }
        : c,
    )
    return HttpResponse.json(ok(null))
  }),

  // ── SCR039 — sổ đăng ký công cụ ───────────────────────────────────────────
  http.get('/api/v1/tools', async ({ request }) => {
    await delay(300)
    const url = new URL(request.url)
    let ket = locTheo(congCu, url.searchParams.get('serverId'), (c, v) => c.mcpServerId === v)
    ket = locTheo(ket, url.searchParams.get('riskLevel'), (c, v) => c.riskLevel === v)
    ket = locTheo(ket, url.searchParams.get('enabled'), (c, v) => String(c.enabled) === v)
    return HttpResponse.json(ok(ket))
  }),

  http.patch('/api/v1/tools/:id', async ({ params, request }) => {
    await delay(450)
    const id = params.id as string
    const c = congCu.find((x) => x.id === id)
    if (!c) return HttpResponse.json(loi('Không tìm thấy công cụ.'), { status: 404 })
    const than = (await request.json()) as {
      enabled?: boolean
      requiresConfirmation?: boolean
      approveSchemaHash?: boolean
    }

    // Ràng buộc của ERD, kiểm ở máy chủ chứ không chỉ ở giao diện: công cụ ghi hoặc phá huỷ
    // **luôn** phải hỏi ý người, không có ngoại lệ do ai đó tắt nhầm một công tắc.
    if (than.requiresConfirmation === false && c.riskLevel !== 'READ') {
      return HttpResponse.json(
        loi('Công cụ có mức rủi ro khác READ bắt buộc phải yêu cầu xác nhận.'),
        { status: 422 },
      )
    }
    // Bật lại một công cụ có lược đồ đã đổi mà chưa duyệt lại là mở đúng cánh cửa mà cơ chế
    // băm lược đồ sinh ra để đóng.
    const daDuyetLuocDo = than.approveSchemaHash || c.approvedSchemaHash === c.schemaHash
    if (than.enabled === true && !daDuyetLuocDo) {
      return HttpResponse.json(
        loi('Lược đồ công cụ đã thay đổi. Xem và duyệt lược đồ mới trước khi bật lại.'),
        { status: 409 },
      )
    }

    const capNhat: CongCu = {
      ...c,
      enabled: than.enabled ?? c.enabled,
      requiresConfirmation: than.requiresConfirmation ?? c.requiresConfirmation,
      approvedSchemaHash: than.approveSchemaHash ? c.schemaHash : c.approvedSchemaHash,
      approvedByName: than.approveSchemaHash
        ? (NGUOI_DUNG_MAU.fullName ?? NGUOI_DUNG_MAU.email)
        : c.approvedByName,
      approvedAt: than.approveSchemaHash ? new Date().toISOString() : c.approvedAt,
      autoDisabledReason: than.enabled === true ? null : c.autoDisabledReason,
    }
    congCu = congCu.map((x) => (x.id === id ? capNhat : x))
    mayChu = mayChu.map((m) =>
      m.id === capNhat.mcpServerId
        ? {
            ...m,
            enabledToolCount: congCu.filter((x) => x.mcpServerId === m.id && x.enabled).length,
          }
        : m,
    )
    return HttpResponse.json(ok(capNhat))
  }),

  // ── SCR035 · SCR040 — nhật ký và phê duyệt lời gọi công cụ ────────────────
  http.get('/api/v1/tool-calls', async ({ request }) => {
    await delay(340)
    const url = new URL(request.url)
    let ket = locTheo(goiCongCu, url.searchParams.get('guardResult'), (g, v) => g.guardResult === v)
    ket = locTheo(ket, url.searchParams.get('approvalStatus'), (g, v) => g.approvalStatus === v)
    ket = locTheo(ket, url.searchParams.get('conversationId'), (g, v) => g.conversationId === v)
    return HttpResponse.json(
      ok(
        trangHoa(ket, {
          url,
          co: 10,
          sapMacDinh: '-calledAt',
          timTrong: (g) => [g.toolName, g.contactName, g.resultSummary],
        }),
      ),
    )
  }),

  http.post('/api/v1/tool-calls/:id/approval', async ({ params, request }) => {
    await delay(700)
    const id = Number(params.id)
    const g = goiCongCu.find((x) => x.id === id)
    if (!g) return HttpResponse.json(loi('Không tìm thấy lời gọi công cụ.'), { status: 404 })
    if (g.approvalStatus !== 'PENDING') {
      return HttpResponse.json(loi('Lời gọi này đã được xử lý rồi.'), { status: 409 })
    }
    const { decision } = (await request.json()) as {
      decision: 'APPROVED' | 'REJECTED'
      note?: string | null
    }
    const duyet = decision === 'APPROVED'
    const capNhat: NhatKyGoiCongCu = {
      ...g,
      approvalStatus: decision,
      approvedByName: NGUOI_DUNG_MAU.fullName ?? NGUOI_DUNG_MAU.email,
      approvedAt: new Date().toISOString(),
      resultStatus: duyet ? 'SUCCESS' : null,
      resultSummary: duyet
        ? `Đã thực thi ${g.toolName} sau khi được duyệt.`
        : 'Người duyệt từ chối — công cụ không được gọi.',
      latencyMs: duyet ? 642 : null,
    }
    goiCongCu = goiCongCu.map((x) => (x.id === id ? capNhat : x))
    return HttpResponse.json(ok(capNhat))
  }),

  // ── SCR036 — giám sát lượt xử lý ──────────────────────────────────────────
  http.get('/api/v1/ai-interactions', async ({ request }) => {
    await delay(380)
    const url = new URL(request.url)
    let ket = locTheo(danhSachLuotXuLy, url.searchParams.get('route'), (l, v) => l.route === v)
    ket = locTheo(ket, url.searchParams.get('refused'), (l, v) => String(l.refused) === v)
    ket = locTheo(ket, url.searchParams.get('conversationId'), (l, v) => l.conversationId === v)
    return HttpResponse.json(
      ok(
        trangHoa(ket, {
          url,
          co: 10,
          sapMacDinh: '-createdAt',
          timTrong: (l) => [l.intentLabel, l.conversationId, l.modelName],
        }),
      ),
    )
  }),

  http.post('/api/v1/ai-interactions/:id/feedback', async ({ params, request }) => {
    await delay(500)
    const l = danhSachLuotXuLy.find((x) => x.id === params.id)
    if (!l) return HttpResponse.json(loi('Không tìm thấy lượt xử lý.'), { status: 404 })
    const than = (await request.json()) as {
      rating: 'POSITIVE' | 'NEGATIVE'
      reasonCode?: string | null
      comment?: string | null
    }
    l.feedback = {
      id: crypto.randomUUID(),
      rating: than.rating,
      reasonCode: (than.reasonCode as never) ?? null,
      comment: than.comment ?? null,
      ratedByType: 'AGENT',
      ratedByName: NGUOI_DUNG_MAU.fullName ?? NGUOI_DUNG_MAU.email,
      createdAt: new Date().toISOString(),
    }
    return HttpResponse.json(ok(l.feedback))
  }),

  http.get('/api/v1/safety-events', async ({ request }) => {
    await delay(300)
    const url = new URL(request.url)
    let ket = locTheo(danhSachSuKienAnToan, url.searchParams.get('severity'), (s, v) => s.severity === v)
    ket = locTheo(ket, url.searchParams.get('eventType'), (s, v) => s.eventType === v)
    return HttpResponse.json(ok(trangHoa(ket, { url, co: 10, sapMacDinh: '-occurredAt' })))
  }),

  // ── SCR051 — hiệu quả và chi phí ──────────────────────────────────────────
  http.get('/api/v1/analytics/ai-performance', async () => {
    await delay(420)
    return HttpResponse.json(ok(hieuQuaAi))
  }),
]
