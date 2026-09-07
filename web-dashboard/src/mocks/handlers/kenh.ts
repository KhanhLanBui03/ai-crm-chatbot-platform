import { HttpResponse, delay, http } from 'msw'

import { cauHinhWidget, danhSachKenh } from '@/mocks/du-lieu-kenh'
import { loi, ok } from '@/mocks/tienIch'
import type { CauHinhWidget, Kenh } from '@/types/schema'

let kenh: Kenh[] = [...danhSachKenh]
let widget: CauHinhWidget = { ...cauHinhWidget }

export const kenhHandlers = [
  // Đặt trước `/api/v1/channels` để không bị nuốt bởi handler có tham số
  http.get('/api/v1/widget-config/snippet', async () => {
    await delay(200)
    return HttpResponse.json(
      ok({
        snippet: `<script
  src="https://cdn.cattuong.vn/widget.js"
  data-public-key="${widget.publicKey}"
  data-color="${widget.primaryColor ?? '#2a78d6'}"
  data-position="${widget.position === 'BOTTOM_LEFT' ? 'bottom-left' : 'bottom-right'}"
  async
></script>`,
      }),
    )
  }),

  http.get('/api/v1/widget-config', async () => {
    await delay(240)
    return HttpResponse.json(ok(widget))
  }),

  http.put('/api/v1/widget-config', async ({ request }) => {
    await delay(650)
    widget = (await request.json()) as CauHinhWidget
    return HttpResponse.json(ok(widget))
  }),

  http.get('/api/v1/channels', async () => {
    await delay(280)
    return HttpResponse.json(ok(kenh))
  }),

  http.post('/api/v1/channels', async ({ request }) => {
    await delay(800)
    const than = (await request.json()) as {
      channelType: 'ZALO' | 'FACEBOOK'
      externalAccountId: string
      accountName?: string
    }
    if (kenh.some((k) => k.externalAccountId === than.externalAccountId)) {
      return HttpResponse.json(loi('Tài khoản này đã được kết nối.'), { status: 409 })
    }
    const moi: Kenh = {
      id: crypto.randomUUID(),
      channelType: than.channelType,
      externalAccountId: than.externalAccountId,
      accountName: than.accountName ?? null,
      // Kết nối xong vẫn phải xác minh webhook — chưa xác minh thì chưa nhận được tin nào
      status: 'PENDING_VERIFY',
      tokenExpiresAt: null,
      verifiedAt: null,
      lastError: null,
      sendWindowHours: than.channelType === 'ZALO' ? 48 : 24,
      rateLimitPerMinute: than.channelType === 'ZALO' ? 20 : 30,
      conversationCount: 0,
      disconnectedAt: null,
      createdAt: new Date().toISOString(),
    }
    kenh = [...kenh, moi]
    return HttpResponse.json(ok(moi), { status: 201 })
  }),

  http.post('/api/v1/channels/:id/verify', async ({ params }) => {
    await delay(1200)
    const k = kenh.find((x) => x.id === params.id)
    if (!k) return HttpResponse.json(loi('Không tìm thấy kênh.'), { status: 404 })
    k.status = 'ACTIVE'
    k.verifiedAt = new Date().toISOString()
    k.lastError = null
    kenh = [...kenh]
    return HttpResponse.json(ok(k))
  }),

  http.delete('/api/v1/channels/:id', async ({ params }) => {
    await delay(500)
    kenh = kenh.filter((x) => x.id !== params.id)
    return HttpResponse.json(ok(null))
  }),
]
