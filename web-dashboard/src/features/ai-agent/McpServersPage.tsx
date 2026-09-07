import { formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import { Plug, PlugZap, Server, Unplug } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import {
  useBatTayMcpMutation,
  useDanhSachMayChuMcpQuery,
  useNgatMayChuMcpMutation,
} from '@/api/ai-agent'
import { laLoiTruyVan } from '@/api/baseQuery'
import { ListPage } from '@/components/layout/ListPage'
import { Button } from '@/components/ui/button'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { AddMcpServerDialog } from '@/features/ai-agent/AddMcpServerDialog'
import { NHAN_NGAT_MACH, NHAN_TRANG_THAI_MCP } from '@/features/ai-agent/nhan'
import type { MayChuMcp } from '@/types/schema'
import type { Page } from '@/types/api'

/**
 * SCR037 — máy chủ MCP đã cấu hình. Mẫu M1.
 *
 * Endpoint trả về mảng chứ không phân trang: một doanh nghiệp vừa và nhỏ có vài máy chủ MCP, không
 * phải vài nghìn. Bọc vào hình dạng `Page` ở đây để dùng lại nguyên mẫu M1 thay vì dựng một bảng
 * thứ hai chỉ vì thiếu bốn trường đếm.
 *
 * Cột **bộ ngắt mạch** tách khỏi cột trạng thái là có chủ đích: một máy chủ `ACTIVE` mà mạch đang
 * `OPEN` thì cấu hình vẫn đúng nhưng mọi lời gọi đang bị chặn tại chỗ — hai chuyện khác nhau, và
 * gộp lại thì người trực không biết nên sửa cấu hình hay chờ máy chủ hồi.
 */
export function McpServersPage() {
  const dieuHuong = useNavigate()
  const [moThem, datMoThem] = useState(false)
  const [dangBatTay, datDangBatTay] = useState<string | null>(null)

  const truyVan = useDanhSachMayChuMcpQuery()
  const [batTay] = useBatTayMcpMutation()
  const [ngat] = useNgatMayChuMcpMutation()

  const cot = useMemo<CotBang<MayChuMcp>[]>(
    () => [
      {
        id: 'name',
        accessorKey: 'name',
        header: 'Máy chủ',
        cell: ({ row }) => {
          const m = row.original
          return (
            <div className="flex min-w-0 flex-col">
              <span className="truncate font-medium">{m.name}</span>
              <span className="text-muted-foreground truncate font-mono text-xs">
                {m.endpointUrl}
              </span>
            </div>
          )
        },
      },
      {
        id: 'status',
        accessorKey: 'status',
        header: 'Trạng thái',
        cell: ({ row }) => {
          const m = row.original
          const t = NHAN_TRANG_THAI_MCP[m.status] ?? NHAN_TRANG_THAI_MCP.PENDING
          return (
            <div className="flex min-w-0 flex-col gap-1">
              <StatusChip sacThai={t.sacThai}>{t.nhan}</StatusChip>
              {m.lastError && (
                <span className="text-destructive line-clamp-2 max-w-56 text-xs">
                  {m.lastError}
                </span>
              )}
            </div>
          )
        },
      },
      {
        id: 'circuitState',
        accessorKey: 'circuitState',
        header: 'Bộ ngắt mạch',
        cell: ({ row }) => {
          const c = row.original.circuitState ?? 'CLOSED'
          const t = NHAN_NGAT_MACH[c] ?? NHAN_NGAT_MACH.CLOSED
          return <StatusChip sacThai={t.sacThai}>{t.nhan}</StatusChip>
        },
      },
      {
        id: 'transport',
        accessorKey: 'transport',
        header: 'Giao thức',
        cell: ({ row }) => {
          const m = row.original
          return (
            <div className="flex flex-col">
              <span className="text-[13px]">
                {m.transport === 'STREAMABLE_HTTP' ? 'Streamable HTTP' : 'HTTP + SSE'}
              </span>
              <span className="text-muted-foreground font-mono text-xs">{m.specVersion}</span>
            </div>
          )
        },
      },
      {
        id: 'toolCount',
        accessorKey: 'toolCount',
        header: 'Công cụ',
        cell: ({ row }) => {
          const m = row.original
          return (
            <span className="tabular-nums">
              {m.enabledToolCount ?? 0}
              <span className="text-muted-foreground">/{m.toolCount ?? 0} đang bật</span>
            </span>
          )
        },
      },
      {
        id: 'maxCallsPerConversation',
        accessorKey: 'maxCallsPerConversation',
        header: 'Trần lời gọi',
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {row.original.maxCallsPerConversation ?? '—'}/hội thoại
          </span>
        ),
      },
      {
        id: 'lastHandshakeAt',
        accessorKey: 'lastHandshakeAt',
        header: 'Bắt tay gần nhất',
        cell: ({ row }) => {
          const l = row.original.lastHandshakeAt
          return (
            <span className="text-muted-foreground tabular-nums">
              {l
                ? formatDistanceToNowStrict(new Date(l), { locale: vi, addSuffix: true })
                : 'Chưa bao giờ'}
            </span>
          )
        },
      },
      {
        id: 'thaoTac',
        header: '',
        cell: ({ row }) => {
          const m = row.original
          return (
            <div className="flex items-center justify-end gap-1.5">
              <Button
                variant="outline"
                size="sm"
                disabled={dangBatTay === m.id}
                onClick={async () => {
                  datDangBatTay(m.id)
                  try {
                    const kq = await batTay(m.id).unwrap()
                    toast.success(`Bắt tay thành công — dò được ${kq.tools.length} công cụ.`)
                  } catch (loi) {
                    toast.error(
                      laLoiTruyVan(loi) ? loi.message : 'Bắt tay thất bại. Kiểm tra lại địa chỉ.',
                    )
                  } finally {
                    datDangBatTay(null)
                  }
                }}
              >
                <PlugZap />
                {dangBatTay === m.id ? 'Đang bắt tay…' : 'Bắt tay'}
              </Button>
              {m.status !== 'DISCONNECTED' && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={async () => {
                    await ngat(m.id).unwrap()
                    toast.success('Đã ngắt máy chủ. Mọi công cụ của nó cũng bị tắt theo.')
                  }}
                >
                  <Unplug />
                  Ngắt
                </Button>
              )}
            </div>
          )
        },
      },
    ],
    [batTay, ngat, dangBatTay],
  )

  // Mảng phẳng bọc thành `Page` — mẫu M1 nhận vào hình dạng này, và phân trang tự ẩn ở một trang
  const trang: Page<MayChuMcp> | undefined = truyVan.data
    ? {
        items: truyVan.data,
        page: 0,
        size: truyVan.data.length || 1,
        totalItems: truyVan.data.length,
        totalPages: 1,
      }
    : undefined

  return (
    <>
      <ListPage
        tieuDe="Máy chủ MCP"
        moTa="Nguồn cung cấp công cụ cho tác tử AI. Thêm máy chủ chưa mở quyền gì — công cụ phải được bật từng cái ở sổ đăng ký."
        cot={cot}
        trang={trang}
        dangTai={truyVan.isLoading}
        onDoiTrang={() => {}}
        thaoTacChinh={{ nhan: 'Thêm máy chủ MCP', BieuTuong: Plug, onClick: () => datMoThem(true) }}
        thaoTacPhu={[{ nhan: 'Sổ đăng ký công cụ', onClick: () => dieuHuong('/tac-tu-ai/cong-cu') }]}
        khiChuaCoDuLieu={{
          BieuTuong: Server,
          tieuDe: 'Chưa nối máy chủ MCP nào',
          moTa: 'Không có máy chủ thì tác tử AI chỉ trả lời từ kho tri thức, không tra được dữ liệu nghiệp vụ theo thời gian thực.',
        }}
      />

      <AddMcpServerDialog mo={moThem} onDoiMo={datMoThem} />
    </>
  )
}
