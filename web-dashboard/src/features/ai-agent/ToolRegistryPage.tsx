import { format } from 'date-fns'
import { Braces, Power, PowerOff, ShieldCheck, TriangleAlert, Wrench } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { useCapNhatCongCuMutation, useDanhSachCongCuQuery } from '@/api/ai-agent'
import { laLoiTruyVan } from '@/api/baseQuery'
import { ListPage } from '@/components/layout/ListPage'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import type { CotBang } from '@/components/ui/data-table'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { StatusChip } from '@/components/ui/status-chip'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { NHAN_MUC_RUI_RO, NHAN_TU_TAT } from '@/features/ai-agent/nhan'
import type { CongCu, MucRuiRo } from '@/types/schema'
import type { Page } from '@/types/api'

/**
 * SCR039 — sổ đăng ký công cụ. Mẫu M1, cộng một ngăn kéo xem lược đồ.
 *
 * Ba quy tắc của bề mặt T4 hiện thẳng trên bảng thay vì nằm trong tài liệu:
 *
 * 1. **Mặc định tắt.** Công cụ dò được từ máy chủ MCP không tự khả dụng.
 * 2. **Lược đồ đổi thì tự tắt.** `schemaHash` lệch khỏi `approvedSchemaHash` nghĩa là máy chủ vừa
 *    đổi hình dạng tham số — bật lại phải đọc lược đồ mới rồi duyệt, không phải bấm một nút.
 * 3. **Ghi và phá huỷ luôn cần người xác nhận.** Ràng buộc ở tầng cơ sở dữ liệu, giao diện chỉ
 *    phản ánh lại chứ không phải nơi duy nhất giữ nó.
 *
 * `description` do máy chủ MCP cung cấp — **dữ liệu không đáng tin**. Nó hiện dưới dạng văn bản
 * thuần, không diễn giải đánh dấu, vì chính chuỗi này đi vào lời nhắc gửi mô hình.
 */
export function ToolRegistryPage() {
  const dieuHuong = useNavigate()
  const [boLoc, datBoLoc] = useState<{ mucRuiRo?: MucRuiRo; daBat?: boolean }>({})
  const [xemLuocDo, datXemLuocDo] = useState<CongCu | null>(null)

  const truyVan = useDanhSachCongCuQuery(boLoc)
  const [capNhat, ketQuaCapNhat] = useCapNhatCongCuMutation()

  async function doiBat(c: CongCu, bat: boolean) {
    try {
      await capNhat({ id: c.id, enabled: bat }).unwrap()
      toast.success(bat ? `Đã bật ${c.toolName}.` : `Đã tắt ${c.toolName}.`)
    } catch (loi) {
      const thongDiep = laLoiTruyVan(loi) ? loi.message : 'Không đổi được trạng thái công cụ.'
      toast.error(thongDiep)
      // 409 luôn là lược đồ đã đổi — mở thẳng ngăn kéo để người dùng đọc rồi quyết định
      if (laLoiTruyVan(loi) && loi.status === 409) datXemLuocDo(c)
    }
  }

  const cot = useMemo<CotBang<CongCu>[]>(
    () => [
      {
        id: 'toolName',
        accessorKey: 'toolName',
        header: 'Công cụ',
        cell: ({ row }) => {
          const c = row.original
          return (
            <div className="flex min-w-0 flex-col">
              <span className="truncate font-mono text-[13px] font-medium">{c.toolName}</span>
              <span className="text-muted-foreground truncate text-xs">{c.mcpServerName}</span>
            </div>
          )
        },
      },
      {
        id: 'description',
        accessorKey: 'description',
        header: 'Mô tả do máy chủ khai',
        cell: ({ row }) => (
          <p className="text-muted-foreground max-w-sm text-[13px]">
            {row.original.description ?? '—'}
          </p>
        ),
      },
      {
        id: 'riskLevel',
        accessorKey: 'riskLevel',
        header: 'Mức rủi ro',
        cell: ({ row }) => {
          const r = NHAN_MUC_RUI_RO[row.original.riskLevel]
          return (
            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <StatusChip sacThai={r.sacThai}>{r.nhan}</StatusChip>
                </span>
              </TooltipTrigger>
              <TooltipContent className="max-w-64">{r.moTa}</TooltipContent>
            </Tooltip>
          )
        },
      },
      {
        id: 'schemaHash',
        accessorKey: 'schemaHash',
        header: 'Lược đồ',
        cell: ({ row }) => {
          const c = row.original
          const lech = c.approvedSchemaHash !== c.schemaHash
          return (
            <button
              type="button"
              onClick={(su) => {
                su.stopPropagation()
                datXemLuocDo(c)
              }}
              className="flex min-w-0 flex-col items-start gap-1 text-left"
            >
              {lech ? (
                <StatusChip sacThai="destructive" BieuTuong={TriangleAlert}>
                  Đã đổi, chưa duyệt
                </StatusChip>
              ) : (
                <StatusChip sacThai="success" BieuTuong={ShieldCheck}>
                  Đã duyệt
                </StatusChip>
              )}
              <span className="text-muted-foreground font-mono text-xs">{c.schemaHash}</span>
            </button>
          )
        },
      },
      {
        id: 'requiresConfirmation',
        accessorKey: 'requiresConfirmation',
        header: 'Cần duyệt',
        cell: ({ row }) =>
          row.original.requiresConfirmation ? (
            <StatusChip sacThai="warning">Có</StatusChip>
          ) : (
            <span className="text-muted-foreground text-[13px]">Không</span>
          ),
      },
      {
        id: 'enabled',
        accessorKey: 'enabled',
        header: 'Trạng thái',
        cell: ({ row }) => {
          const c = row.original
          return (
            <div className="flex min-w-0 flex-col gap-1">
              {c.enabled ? (
                <StatusChip sacThai="success">Đang bật</StatusChip>
              ) : (
                <StatusChip>Đang tắt</StatusChip>
              )}
              {!c.enabled && c.autoDisabledReason && (
                <span className="text-muted-foreground max-w-48 text-xs">
                  {NHAN_TU_TAT[c.autoDisabledReason] ?? c.autoDisabledReason}
                </span>
              )}
            </div>
          )
        },
      },
      {
        id: 'approvedByName',
        accessorKey: 'approvedByName',
        header: 'Người duyệt',
        cell: ({ row }) => {
          const c = row.original
          return c.approvedByName ? (
            <div className="flex flex-col">
              <span className="text-[13px]">{c.approvedByName}</span>
              <span className="text-muted-foreground text-xs tabular-nums">
                {c.approvedAt ? format(new Date(c.approvedAt), 'dd/MM/yyyy') : ''}
              </span>
            </div>
          ) : (
            <span className="text-muted-foreground text-[13px]">Chưa ai duyệt</span>
          )
        },
      },
      {
        id: 'thaoTac',
        header: '',
        cell: ({ row }) => {
          const c = row.original
          return (
            <div className="flex items-center justify-end gap-1.5">
              <Button
                variant="outline"
                size="sm"
                disabled={ketQuaCapNhat.isLoading}
                onClick={(su) => {
                  su.stopPropagation()
                  void doiBat(c, !c.enabled)
                }}
              >
                {c.enabled ? <PowerOff /> : <Power />}
                {c.enabled ? 'Tắt' : 'Bật'}
              </Button>
            </div>
          )
        },
      },
    ],
    // `doiBat` dựng lại ở mỗi lần render nhưng chỉ đọc `capNhat`, vốn ổn định qua các lần render
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [ketQuaCapNhat.isLoading],
  )

  const trang: Page<CongCu> | undefined = truyVan.data
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
        tieuDe="Sổ đăng ký công cụ"
        moTa="Mọi công cụ tác tử AI có thể gọi. Mặc định tắt; công cụ ghi và phá huỷ luôn phải có người duyệt từng lời gọi."
        cot={cot}
        trang={trang}
        dangTai={truyVan.isLoading}
        onChonDong={(c) => datXemLuocDo(c)}
        boLoc={[
          {
            khoa: 'mucRuiRo',
            nhan: 'Mức rủi ro',
            luaChon: Object.entries(NHAN_MUC_RUI_RO).map(([giaTri, v]) => ({
              giaTri,
              nhan: v.nhan,
            })),
          },
          {
            khoa: 'daBat',
            nhan: 'Trạng thái',
            luaChon: [
              { giaTri: 'true', nhan: 'Đang bật' },
              { giaTri: 'false', nhan: 'Đang tắt' },
            ],
          },
        ]}
        giaTriBoLoc={{
          mucRuiRo: boLoc.mucRuiRo,
          daBat: boLoc.daBat === undefined ? undefined : String(boLoc.daBat),
        }}
        onDoiBoLoc={(khoa, giaTri) =>
          datBoLoc((cu) => ({
            ...cu,
            ...(khoa === 'mucRuiRo'
              ? { mucRuiRo: giaTri as MucRuiRo }
              : { daBat: giaTri === undefined ? undefined : giaTri === 'true' }),
          }))
        }
        onGoHetBoLoc={() => datBoLoc({})}
        onDoiTrang={() => {}}
        thaoTacPhu={[{ nhan: 'Máy chủ MCP', onClick: () => dieuHuong('/tac-tu-ai/mcp') }]}
        khiChuaCoDuLieu={{
          BieuTuong: Wrench,
          tieuDe: 'Chưa dò được công cụ nào',
          moTa: 'Thêm máy chủ MCP rồi bấm Bắt tay để dò danh sách công cụ máy chủ đó cung cấp.',
        }}
      />

      <NganKeoLuocDo
        congCu={xemLuocDo}
        onDong={() => datXemLuocDo(null)}
        dangLuu={ketQuaCapNhat.isLoading}
        onDuyet={async (c, batLuon) => {
          await capNhat({ id: c.id, approveSchemaHash: true, enabled: batLuon || undefined }).unwrap()
          toast.success(
            batLuon
              ? `Đã duyệt lược đồ và bật ${c.toolName}.`
              : `Đã duyệt lược đồ hiện tại của ${c.toolName}.`,
          )
          datXemLuocDo(null)
        }}
      />
    </>
  )
}

/**
 * Ngăn kéo xem lược đồ tham số.
 *
 * Phải hiện **toàn bộ** lược đồ chứ không phải một dòng tóm tắt: người duyệt đang xác nhận rằng
 * hình dạng tham số mới không mở thêm đường nào ngoài ý muốn, và việc đó không làm được nếu chỉ
 * nhìn thấy tên công cụ với một mã băm.
 */
function NganKeoLuocDo({
  congCu,
  onDong,
  onDuyet,
  dangLuu,
}: {
  congCu: CongCu | null
  onDong: () => void
  onDuyet: (c: CongCu, batLuon: boolean) => Promise<void>
  dangLuu: boolean
}) {
  if (!congCu) return null
  const lech = congCu.approvedSchemaHash !== congCu.schemaHash
  const r = NHAN_MUC_RUI_RO[congCu.riskLevel]

  return (
    <Sheet open onOpenChange={(m) => !m && onDong()}>
      <SheetContent className="flex w-full flex-col gap-4 sm:max-w-xl">
        <SheetHeader>
          <SheetTitle className="font-mono">{congCu.toolName}</SheetTitle>
          <SheetDescription>
            {congCu.mcpServerName} · <StatusChip sacThai={r.sacThai}>{r.nhan}</StatusChip>
          </SheetDescription>
        </SheetHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-4">
          {lech && (
            <Alert variant="destructive">
              <TriangleAlert />
              <AlertTitle>Lược đồ đã thay đổi kể từ lần duyệt trước</AlertTitle>
              <AlertDescription>
                Mã băm đã duyệt là{' '}
                <code className="font-mono">{congCu.approvedSchemaHash ?? 'chưa có'}</code>, mã băm
                máy chủ đang khai là <code className="font-mono">{congCu.schemaHash}</code>. Đọc kỹ
                lược đồ dưới đây trước khi duyệt — trường mới có thể mở ra đường ghi mà lần duyệt
                trước không có.
              </AlertDescription>
            </Alert>
          )}

          <div className="flex flex-col gap-1.5">
            <span className="text-muted-foreground text-xs">Mô tả do máy chủ MCP khai</span>
            <p className="text-[13px] leading-relaxed">{congCu.description ?? '—'}</p>
            <p className="text-muted-foreground text-xs">
              Chuỗi này đi vào lời nhắc gửi mô hình nên được coi là dữ liệu không đáng tin — hiển
              thị nguyên văn, không diễn giải.
            </p>
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="text-muted-foreground flex items-center gap-1.5 text-xs">
              <Braces className="size-3.5" />
              Lược đồ tham số đầu vào
            </span>
            <pre className="bg-muted max-h-96 overflow-auto rounded-lg p-3 font-mono text-xs leading-relaxed">
              {JSON.stringify(congCu.inputSchema ?? {}, null, 2)}
            </pre>
          </div>
        </div>

        <SheetFooter>
          <Button variant="outline" onClick={onDong} disabled={dangLuu}>
            Đóng
          </Button>
          {lech && (
            <>
              <Button variant="outline" onClick={() => onDuyet(congCu, false)} disabled={dangLuu}>
                Chỉ duyệt lược đồ
              </Button>
              <Button onClick={() => onDuyet(congCu, true)} disabled={dangLuu}>
                Duyệt và bật lại
              </Button>
            </>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
