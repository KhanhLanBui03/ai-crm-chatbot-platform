import { format, formatDistanceToNowStrict } from 'date-fns'
import { vi } from 'date-fns/locale'
import {
  AlertTriangle,
  Calendar,
  GitMerge,
  Mail,
  MessagesSquare,
  Phone,
  ShieldCheck,
  ShieldOff,
  Sparkles,
} from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { useChiTietKhachHangQuery, useGhiChuKhachHangQuery } from '@/api/contacts'
import { DetailPage, HangThongTin } from '@/components/layout/DetailPage'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { EmptyState } from '@/components/ui/empty-state'
import { StatusChip } from '@/components/ui/status-chip'
import { NHAN_KENH } from '@/features/conversations/nhan'
import { AddNoteDialog } from '@/features/contacts/AddNoteDialog'
import { MergeContactDialog } from '@/features/contacts/MergeContactDialog'
import type { DanhTinhKenh, GhiChu, LoaiKenh } from '@/types/schema'
import { chuCaiDau } from '@/utils/ten'

const tien = (v: number) => new Intl.NumberFormat('vi-VN').format(v) + ' ₫'

/**
 * SCR024 — hồ sơ khách hàng. Màn chữ ký, dựng trên khung của mẫu M2.
 *
 * Điểm riêng của màn này là tab **Danh tính kênh**: một người nhắn từ widget hôm nay và từ Zalo
 * tuần sau là *hai* `channel_identities` trỏ về *một* `contact`. Không bày chúng ra thì nhân viên
 * không hiểu vì sao hai luồng tin nhắn lại nằm chung một hồ sơ — và cũng không biết khi nào cần
 * hợp nhất tay.
 */
export function ContactDetailPage() {
  const { id = '' } = useParams()
  const dieuHuong = useNavigate()
  const [tab, datTab] = useState('tong-quan')
  const [moGhiChu, datMoGhiChu] = useState(false)
  const [moHopNhat, datMoHopNhat] = useState(false)

  const truyVan = useChiTietKhachHangQuery(id)
  const ghiChu = useGhiChuKhachHangQuery(id)
  const k = truyVan.data

  return (
    <>
      <DetailPage
        quayLai={{ duongDan: '/khach-hang', nhan: 'Khách hàng' }}
        tieuDe={k?.fullName ?? 'Khách chưa có tên'}
        phuDe={k?.createdAt ? `Tạo ngày ${format(new Date(k.createdAt), 'dd/MM/yyyy')}` : undefined}
        dangTai={truyVan.isLoading}
        chip={
          k && (
            <>
              {k.consentGranted ? (
                <StatusChip sacThai="success" BieuTuong={ShieldCheck}>
                  Đã đồng ý dữ liệu
                </StatusChip>
              ) : (
                <StatusChip sacThai="warning" BieuTuong={ShieldOff}>
                  Chưa đồng ý dữ liệu
                </StatusChip>
              )}
              {k.status === 'MERGED' && <StatusChip sacThai="neutral">Đã hợp nhất</StatusChip>}
              {k.status === 'ANONYMIZED' && (
                <StatusChip sacThai="neutral">Đã ẩn danh hoá</StatusChip>
              )}
            </>
          )
        }
        thaoTacChinh={{
          nhan: 'Thêm ghi chú',
          onClick: () => datMoGhiChu(true),
        }}
        thaoTacPhu={[
          { nhan: 'Hợp nhất', BieuTuong: GitMerge, onClick: () => datMoHopNhat(true) },
        ]}
        tab={[
          {
            khoa: 'tong-quan',
            nhan: 'Tổng quan',
            noiDung: k && (
              <div className="flex flex-col gap-4">
                {k.status === 'MERGED' && k.mergedIntoContactId && (
                  <Alert>
                    <GitMerge />
                    <AlertDescription>
                      Hồ sơ này đã được hợp nhất vào một hồ sơ khác. Nó vẫn tồn tại để giữ liên kết
                      của các hội thoại cũ.{' '}
                      <button
                        type="button"
                        className="underline underline-offset-2"
                        onClick={() => dieuHuong(`/khach-hang/${k.mergedIntoContactId}`)}
                      >
                        Mở hồ sơ đang giữ
                      </button>
                    </AlertDescription>
                  </Alert>
                )}

                {!k.consentGranted && (
                  <Alert>
                    <AlertTriangle />
                    <AlertDescription>
                      Khách chưa đồng ý xử lý dữ liệu cá nhân. Theo Nghị định 13/2023/NĐ-CP, không
                      được dùng dữ liệu này cho mục đích tiếp thị — chăm sóc theo yêu cầu của chính
                      khách thì vẫn được.
                    </AlertDescription>
                  </Alert>
                )}

                <div className="grid gap-3 sm:grid-cols-3">
                  <TheSo nhan="Hội thoại" giaTri={k.conversationCount ?? 0} />
                  <TheSo nhan="Cơ hội đang mở" giaTri={k.openLeadCount ?? 0} />
                  <TheSo
                    nhan="Giá trị cơ hội"
                    giaTri={tien(k.totalDealValue ?? 0)}
                    nho
                  />
                </div>

                {(k.tags?.length ?? 0) > 0 && (
                  <div className="flex flex-col gap-1.5">
                    <span className="text-muted-foreground text-xs font-medium">Thẻ</span>
                    <div className="flex flex-wrap gap-1.5">
                      {k.tags?.map((t) => (
                        <StatusChip key={t.id}>{t.name}</StatusChip>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ),
          },
          {
            khoa: 'danh-tinh',
            nhan: 'Danh tính kênh',
            soLuong: k?.channelIdentities?.length,
            noiDung: k && (
              <div className="flex flex-col gap-2">
                <p className="text-muted-foreground text-[13px] leading-relaxed">
                  Mỗi dòng là một tài khoản trên một nền tảng. Hệ thống gộp chúng về một hồ sơ khi
                  trùng số điện thoại hoặc địa chỉ thư; những trường hợp còn lại phải hợp nhất tay.
                </p>
                {(k.channelIdentities?.length ?? 0) === 0 ? (
                  <EmptyState
                    BieuTuong={MessagesSquare}
                    tieuDe="Chưa có danh tính kênh nào"
                    moTa="Hồ sơ này được nhập tay, chưa gắn với tài khoản trên nền tảng nào."
                  />
                ) : (
                  k.channelIdentities?.map((d) => <DongDanhTinh key={d.id} danhTinh={d} />)
                )}
              </div>
            ),
          },
          {
            khoa: 'ghi-chu',
            nhan: 'Ghi chú',
            soLuong: ghiChu.data?.length,
            noiDung: (
              <div className="flex flex-col gap-2">
                {ghiChu.data?.length === 0 ? (
                  <EmptyState
                    BieuTuong={Sparkles}
                    tieuDe="Chưa có ghi chú nào"
                    moTa="Ghi chú chỉ nhân viên đọc được, khách hàng không thấy."
                    thaoTac={{ nhan: 'Thêm ghi chú', onClick: () => datMoGhiChu(true) }}
                  />
                ) : (
                  ghiChu.data?.map((g) => <TheGhiChu key={g.id} ghiChu={g} />)
                )}
              </div>
            ),
          },
        ]}
        tabHienTai={tab}
        onDoiTab={datTab}
        cotPhu={
          k && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2.5">
                <div className="bg-secondary text-secondary-foreground flex size-10 shrink-0 items-center justify-center rounded-full text-sm font-medium">
                  {chuCaiDau(k.fullName ?? '?')}
                </div>
                <div className="flex min-w-0 flex-col">
                  <span className="truncate text-sm font-medium">{k.fullName ?? 'Chưa có tên'}</span>
                  <span className="text-muted-foreground text-xs">
                    {k.primaryChannel === 'PHONE'
                      ? 'Nhập tay'
                      : NHAN_KENH[k.primaryChannel as LoaiKenh]}
                  </span>
                </div>
              </div>

              <HangThongTin BieuTuong={Phone} nhan="Điện thoại">
                {k.phone ?? '—'}
              </HangThongTin>
              <HangThongTin BieuTuong={Mail} nhan="Thư điện tử">
                {k.email ?? '—'}
              </HangThongTin>
              <HangThongTin BieuTuong={Calendar} nhan="Tương tác gần nhất">
                {k.lastInteractionAt
                  ? formatDistanceToNowStrict(new Date(k.lastInteractionAt), {
                      locale: vi,
                      addSuffix: true,
                    })
                  : 'Chưa có'}
              </HangThongTin>
              {k.consentAt && (
                <HangThongTin BieuTuong={ShieldCheck} nhan="Đồng ý lúc">
                  {format(new Date(k.consentAt), 'dd/MM/yyyy HH:mm')}
                </HangThongTin>
              )}
            </div>
          )
        }
      />

      <AddNoteDialog mo={moGhiChu} onDoiMo={datMoGhiChu} contactId={id} />
      {k && <MergeContactDialog mo={moHopNhat} onDoiMo={datMoHopNhat} giuLai={k} />}
    </>
  )
}

function TheSo({ nhan, giaTri, nho }: { nhan: string; giaTri: string | number; nho?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-lg border p-3">
      <span className="text-muted-foreground text-xs">{nhan}</span>
      <span className={nho ? 'text-base font-semibold tabular-nums' : 'text-xl font-semibold tabular-nums'}>
        {giaTri}
      </span>
    </div>
  )
}

function DongDanhTinh({ danhTinh }: { danhTinh: DanhTinhKenh }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border p-3">
      <StatusChip sacThai="info">{NHAN_KENH[danhTinh.channelType]}</StatusChip>
      <div className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-[13px] font-medium">
          {danhTinh.displayName ?? 'Không có tên hiển thị'}
        </span>
        <span className="text-muted-foreground truncate font-mono text-xs">
          {danhTinh.externalUserId}
          {danhTinh.originDomain && ` · ${danhTinh.originDomain}`}
        </span>
      </div>
      {danhTinh.lastSeenAt && (
        <span className="text-muted-foreground shrink-0 text-xs">
          {formatDistanceToNowStrict(new Date(danhTinh.lastSeenAt), { locale: vi, addSuffix: true })}
        </span>
      )}
    </div>
  )
}

function TheGhiChu({ ghiChu }: { ghiChu: GhiChu }) {
  return (
    <div className="flex flex-col gap-1.5 rounded-lg border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[13px] font-medium">{ghiChu.authorName}</span>
        <span className="text-muted-foreground text-xs">
          {formatDistanceToNowStrict(new Date(ghiChu.createdAt), { locale: vi, addSuffix: true })}
        </span>
        {/* Máy chủ tự đánh dấu ghi chú chứa dữ liệu cá nhân. Hiện ra chứ không giấu — nhân viên
            cần biết dòng nào sẽ bị che khi xuất dữ liệu và bị xoá khi khách yêu cầu (SCR056). */}
        {ghiChu.flaggedSensitive && (
          <StatusChip sacThai="warning" BieuTuong={AlertTriangle}>
            Có dữ liệu cá nhân
          </StatusChip>
        )}
      </div>
      <p className="text-[13px] leading-relaxed whitespace-pre-line">{ghiChu.content}</p>
    </div>
  )
}
