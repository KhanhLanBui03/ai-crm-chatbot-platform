import type { SortingState } from '@tanstack/react-table'
import { Route, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import {
  useDanhSachQuyTacQuery,
  useSuaQuyTacMutation,
  useXoaQuyTacMutation,
} from '@/api/conversations'
import { ListPage } from '@/components/layout/ListPage'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { CreateRuleDialog } from '@/features/conversations/CreateRuleDialog'
import { NHAN_KENH } from '@/features/conversations/nhan'
import type { Page } from '@/types/api'
import type { QuyTacPhanCong } from '@/types/schema'

const NHAN_CHIEN_LUOC: Record<string, { nhan: string; moTa: string }> = {
  LEAST_BUSY: { nhan: 'Người ít việc nhất', moTa: 'Ai đang giữ ít hội thoại nhất thì nhận' },
  ROUND_ROBIN: { nhan: 'Chia lượt', moTa: 'Lần lượt từng người, không nhìn tải hiện tại' },
  FIXED_USER: { nhan: 'Người cố định', moTa: 'Luôn giao cho một người' },
}

/**
 * SCR022 — quy tắc phân công tự động. Mẫu M1, cộng hộp thoại tạo của SCR023.
 *
 * Bảng sắp theo `priority` **giảm dần** và cột đó là cột đầu tiên: đây chính là thứ tự máy chủ
 * duyệt quy tắc, và quy tắc khớp đầu tiên thắng. Sắp theo tên cho đẹp là mời người dùng hiểu sai
 * quy tắc nào đang có hiệu lực.
 */
export function AssignmentRulesPage() {
  const [sapXep, datSapXep] = useState<SortingState>([{ id: 'priority', desc: true }])
  const [moTao, datMoTao] = useState(false)
  const [apDungCho, datApDungCho] = useState<'CONVERSATION' | 'LEAD' | undefined>()

  const truyVan = useDanhSachQuyTacQuery({ apDungCho })
  const [sua] = useSuaQuyTacMutation()
  const [xoa] = useXoaQuyTacMutation()

  const trang: Page<QuyTacPhanCong> | undefined = useMemo(() => {
    if (!truyVan.data) return undefined
    const ds = [...truyVan.data]
    const khoa = sapXep[0]
    if (khoa) {
      ds.sort((a, b) => {
        const va = a[khoa.id as keyof QuyTacPhanCong]
        const vb = b[khoa.id as keyof QuyTacPhanCong]
        if (typeof va === 'number' && typeof vb === 'number') return (khoa.desc ? -1 : 1) * (va - vb)
        return (khoa.desc ? -1 : 1) * String(va ?? '').localeCompare(String(vb ?? ''), 'vi')
      })
    }
    return { items: ds, page: 0, size: ds.length, totalItems: ds.length, totalPages: 1 }
  }, [truyVan.data, sapXep])

  const cot = useMemo<CotBang<QuyTacPhanCong>[]>(
    () => [
      {
        id: 'priority',
        accessorKey: 'priority',
        header: 'Ưu tiên',
        enableSorting: true,
        cell: ({ row }) => (
          <span className="tabular-nums font-medium">{row.original.priority}</span>
        ),
      },
      {
        id: 'name',
        accessorKey: 'name',
        header: 'Quy tắc',
        enableSorting: true,
        cell: ({ row }) => (
          <span className={row.original.isActive ? 'font-medium' : 'text-muted-foreground'}>
            {row.original.name}
          </span>
        ),
      },
      {
        id: 'appliesTo',
        accessorKey: 'appliesTo',
        header: 'Áp dụng cho',
        cell: ({ row }) => (
          <StatusChip>
            {row.original.appliesTo === 'LEAD' ? 'Cơ hội tiềm năng' : 'Hội thoại'}
          </StatusChip>
        ),
      },
      {
        id: 'dieuKien',
        header: 'Điều kiện',
        cell: ({ row }) => {
          const q = row.original
          const dk: string[] = []
          if (q.channelType) dk.push(NHAN_KENH[q.channelType])
          if (q.tagId) dk.push('có thẻ')
          return (
            <span className="text-muted-foreground text-[13px]">
              {dk.length > 0 ? dk.join(' · ') : 'Mọi hội thoại'}
            </span>
          )
        },
      },
      {
        id: 'strategy',
        accessorKey: 'strategy',
        header: 'Cách chia',
        cell: ({ row }) => {
          const q = row.original
          const cl = NHAN_CHIEN_LUOC[q.strategy]
          return (
            <div className="flex flex-col">
              <span className="text-[13px]">{cl?.nhan ?? q.strategy}</span>
              <span className="text-muted-foreground text-xs">
                {q.targetUserName ?? cl?.moTa}
                {q.maxConcurrent != null && ` · tối đa ${q.maxConcurrent}`}
              </span>
            </div>
          )
        },
      },
      {
        id: 'isActive',
        accessorKey: 'isActive',
        header: 'Bật',
        cell: ({ row }) => {
          const q = row.original
          return (
            <Checkbox
              checked={q.isActive}
              aria-label={`Bật quy tắc ${q.name}`}
              onClick={(su) => su.stopPropagation()}
              onCheckedChange={async (v) => {
                await sua({ id: q.id, than: { isActive: v === true } }).unwrap()
                toast.success(v === true ? 'Đã bật quy tắc.' : 'Đã tắt quy tắc.')
              }}
            />
          )
        },
      },
      {
        id: 'thaoTac',
        header: '',
        cell: ({ row }) => (
          <Button
            variant="ghost"
            size="sm"
            onClick={async (su) => {
              su.stopPropagation()
              await xoa(row.original.id).unwrap()
              toast.success('Đã xoá quy tắc.')
            }}
          >
            <Trash2 />
            Xoá
          </Button>
        ),
      },
    ],
    [sua, xoa],
  )

  return (
    <>
      <ListPage
        tieuDe="Quy tắc phân công"
        moTa="Duyệt từ ưu tiên cao xuống thấp, quy tắc khớp đầu tiên thắng. Không quy tắc nào khớp thì hội thoại vào hàng chờ chung."
        cot={cot}
        trang={trang}
        dangTai={truyVan.isLoading}
        sapXep={{ trangThai: sapXep, onDoiSapXep: datSapXep }}
        onDoiTrang={() => {}}
        boLoc={[
          {
            khoa: 'apDungCho',
            nhan: 'Áp dụng cho',
            luaChon: [
              { giaTri: 'CONVERSATION', nhan: 'Hội thoại' },
              { giaTri: 'LEAD', nhan: 'Cơ hội tiềm năng' },
            ],
          },
        ]}
        giaTriBoLoc={{ apDungCho }}
        onDoiBoLoc={(_khoa, giaTri) => datApDungCho(giaTri as 'CONVERSATION' | 'LEAD' | undefined)}
        onGoHetBoLoc={() => datApDungCho(undefined)}
        thaoTacChinh={{ nhan: 'Tạo quy tắc', onClick: () => datMoTao(true) }}
        khiChuaCoDuLieu={{
          BieuTuong: Route,
          tieuDe: 'Chưa có quy tắc nào',
          moTa: 'Không có quy tắc thì mọi hội thoại vào hàng chờ chung và nhân viên tự nhận.',
        }}
      />

      <CreateRuleDialog mo={moTao} onDoiMo={datMoTao} />
    </>
  )
}
