import { format } from 'date-fns'
import { ShieldCheck } from 'lucide-react'
import { useMemo, useState } from 'react'

import { useDanhSachSuKienAnToanQuery } from '@/api/ai-agent'
import { laLoiTruyVan } from '@/api/baseQuery'
import { ListPage } from '@/components/layout/ListPage'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type { CotBang } from '@/components/ui/data-table'
import { StatusChip } from '@/components/ui/status-chip'
import { NHAN_LOAI_SU_KIEN_AN_TOAN, NHAN_MUC_NGHIEM_TRONG } from '@/features/ai-agent/nhan'
import type { LoaiSuKienAnToan, MucNghiemTrong, SuKienAnToan } from '@/types/schema'

/** Bề mặt đe doạ — đúng tên trong docs/threat-model.md để người đọc tra được biện pháp phòng thủ. */
const NHAN_BE_MAT: Record<string, string> = {
  T1: 'T1 · Webhook kênh',
  T2: 'T2 · Ô nhập của widget',
  T3: 'T3 · Tài liệu được nạp',
  T4: 'T4 · Gọi công cụ (MCP)',
  T5: 'T5 · ai-service → dữ liệu',
  T6: 'T6 · Truy vấn vector',
  T7: 'T7 · Gateway / phạm vi doanh nghiệp',
  T8: 'T8 · Log và báo cáo',
}

const NHAN_XU_LY: Record<SuKienAnToan['actionTaken'], string> = {
  TREATED_AS_DATA: 'Coi là dữ liệu, không làm theo',
  BLOCKED: 'Đã chặn',
  REFUSED: 'Từ chối trả lời',
  ESCALATED: 'Chuyển cho nhân viên',
}

/**
 * UC040 bước 8 — cảnh báo an toàn HỢP NHẤT ba nguồn (cờ an toàn trên lượt AI, lời gọi công cụ bị chặn,
 * nhật ký kiểm toán mức nghiêm trọng) trên MỘT màn, không phải ba màn rời.
 *
 * Guardrails không chặn luồng: tin nhắn khả nghi vẫn được trả lời nhưng nội dung bị đối xử như DỮ LIỆU,
 * không như chỉ thị — nên cột "Xử lý" phần lớn là "Coi là dữ liệu", và đó là hành vi đúng.
 *
 * Bằng chứng chỉ là trích đoạn ngắn đã che dữ liệu cá nhân — màn này không lưu lại nguyên câu tấn công.
 */
export function SafetyEventsPage() {
  const [boLoc, datBoLoc] = useState<{ mucNghiemTrong?: MucNghiemTrong; loai?: LoaiSuKienAnToan; trang: number }>({
    trang: 0,
  })
  const truyVan = useDanhSachSuKienAnToanQuery({ ...boLoc, co: 20 })

  const cot = useMemo<CotBang<SuKienAnToan>[]>(
    () => [
      {
        id: 'occurredAt',
        accessorKey: 'occurredAt',
        header: 'Thời điểm',
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground tabular-nums">
            {format(new Date(row.original.occurredAt), 'HH:mm:ss dd/MM/yyyy')}
          </span>
        ),
      },
      {
        id: 'eventType',
        accessorKey: 'eventType',
        header: 'Loại cảnh báo',
        enableSorting: false,
        cell: ({ row }) => {
          const e = row.original
          return (
            <div className="flex min-w-0 flex-col">
              <span className="font-medium">{NHAN_LOAI_SU_KIEN_AN_TOAN[e.eventType] ?? e.eventType}</span>
              <span className="text-muted-foreground font-mono text-xs">{e.detector ?? '—'}</span>
            </div>
          )
        },
      },
      {
        id: 'severity',
        accessorKey: 'severity',
        header: 'Mức',
        enableSorting: false,
        cell: ({ row }) => {
          const m = NHAN_MUC_NGHIEM_TRONG[row.original.severity]
          return <StatusChip sacThai={m.sacThai}>{m.nhan}</StatusChip>
        },
      },
      {
        id: 'threatSurface',
        accessorKey: 'threatSurface',
        header: 'Bề mặt đe doạ',
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-[13px]">
            {row.original.threatSurface ? NHAN_BE_MAT[row.original.threatSurface] : '—'}
          </span>
        ),
      },
      {
        id: 'actionTaken',
        accessorKey: 'actionTaken',
        header: 'Xử lý',
        enableSorting: false,
        cell: ({ row }) => <span className="text-[13px]">{NHAN_XU_LY[row.original.actionTaken]}</span>,
      },
      {
        id: 'evidence',
        header: 'Bằng chứng (đã che)',
        enableSorting: false,
        cell: ({ row }) => {
          const ev = (row.original.evidence ?? {}) as Record<string, string>
          const chu = ev.excerpt ?? ev.detail ?? ev.action
          return chu ? (
            <span className="text-muted-foreground line-clamp-2 font-mono text-xs">{chu}</span>
          ) : (
            <span className="text-muted-foreground">—</span>
          )
        },
      },
    ],
    [],
  )

  const loi = truyVan.error && laLoiTruyVan(truyVan.error) ? truyVan.error : undefined

  return (
    <>
      {loi && (
        <div className="px-4 pt-4 md:px-6">
          {/* Không hiện bảng rỗng khi lỗi: "không có sự cố" và "không lấy được dữ liệu" là hai điều khác hẳn */}
          <Alert variant="destructive">
            <AlertDescription>{loi.message}</AlertDescription>
          </Alert>
        </div>
      )}
      <ListPage
        tieuDe="Cảnh báo an toàn"
        moTa="Tiêm chỉ thị, dò dữ liệu doanh nghiệp khác, lời gọi công cụ bị chặn — gộp từ tác tử AI và nhật ký kiểm toán. 30 ngày gần nhất."
        cot={cot}
        trang={loi ? undefined : truyVan.data}
        dangTai={truyVan.isLoading}
        boLoc={[
          {
            khoa: 'mucNghiemTrong',
            nhan: 'Mức',
            luaChon: Object.entries(NHAN_MUC_NGHIEM_TRONG).map(([giaTri, v]) => ({ giaTri, nhan: v.nhan })),
          },
          {
            khoa: 'loai',
            nhan: 'Loại',
            luaChon: Object.entries(NHAN_LOAI_SU_KIEN_AN_TOAN).map(([giaTri, nhan]) => ({ giaTri, nhan })),
          },
        ]}
        giaTriBoLoc={{ mucNghiemTrong: boLoc.mucNghiemTrong, loai: boLoc.loai }}
        onDoiBoLoc={(khoa, giaTri) =>
          datBoLoc((cu) => ({
            ...cu,
            trang: 0,
            ...(khoa === 'mucNghiemTrong'
              ? { mucNghiemTrong: giaTri as MucNghiemTrong | undefined }
              : { loai: giaTri as LoaiSuKienAnToan | undefined }),
          }))
        }
        onGoHetBoLoc={() => datBoLoc({ trang: 0 })}
        onDoiTrang={(t) => datBoLoc((cu) => ({ ...cu, trang: t }))}
        khiChuaCoDuLieu={{
          BieuTuong: ShieldCheck,
          tieuDe: 'Chưa có cảnh báo an toàn nào',
          moTa: 'Khi tác tử phát hiện tin nhắn khả nghi hoặc có nỗ lực vượt phạm vi doanh nghiệp, cảnh báo hiện ở đây.',
        }}
      />
    </>
  )
}
