import { skipToken } from '@reduxjs/toolkit/query'
import { Inbox } from 'lucide-react'
import { useEffect, useState } from 'react'

import { toast } from 'sonner'

import {
  useChiTietHoiThoaiQuery,
  useDanhSachHoiThoaiQuery,
  useDoiTrangThaiHoiThoaiMutation,
  useNguCanhHoiThoaiQuery,
  usePhanCongHoiThoaiMutation,
  type BoLocHoiThoai,
} from '@/api/conversations'
import { ContextPanel } from '@/features/conversations/ContextPanel'
import { ConversationList } from '@/features/conversations/ConversationList'
import { MessageThread } from '@/features/conversations/MessageThread'
import { HandoffDialog } from '@/features/conversations/HandoffDialog'
import { useDangGo } from '@/features/conversations/useDangGo'

/**
 * SCR019 + SCR020 — hộp thư hợp nhất, bố cục ba cột.
 * Bản chuyển từ artboard "Hộp thư hợp nhất" ở canvas Hộp thư và CRM.
 */
export function InboxPage() {
  const [boLoc, datBoLoc] = useState<BoLocHoiThoai>({ phamVi: 'all' })
  const [idDangChon, datIdDangChon] = useState<string | null>(null)

  const danhSach = useDanhSachHoiThoaiQuery(boLoc)
  const chiTiet = useChiTietHoiThoaiQuery(idDangChon ?? skipToken)
  const nguCanh = useNguCanhHoiThoaiQuery(idDangChon ?? skipToken)
  const dangGo = useDangGo(idDangChon)
  const [phanCong, ketQuaPhanCong] = usePhanCongHoiThoaiMutation()
  const [doiTrangThai, ketQuaTrangThai] = useDoiTrangThaiHoiThoaiMutation()
  const [huongChuyenGiao, datHuongChuyenGiao] = useState<
    'BOT_TO_AGENT' | 'AGENT_TO_BOT' | null
  >(null)

  // `data` giữ kết quả của bộ lọc trước cho tới khi kết quả mới về — danh sách không nháy trắng
  const muc = danhSach.data?.items
  const dangChon = muc?.find((c) => c.id === idDangChon) ?? null

  // Tự chọn hội thoại đầu tiên, và bỏ chọn khi bộ lọc làm nó biến mất khỏi danh sách
  useEffect(() => {
    if (!muc) return
    if (muc.length === 0) {
      datIdDangChon(null)
    } else if (!idDangChon || !muc.some((c) => c.id === idDangChon)) {
      datIdDangChon(muc[0].id)
    }
  }, [muc, idDangChon])

  return (
    <div className="flex min-h-0 flex-1">
      <ConversationList
        danhSach={muc}
        dangTai={danhSach.isLoading}
        idDangChon={idDangChon}
        onChon={datIdDangChon}
        boLoc={boLoc}
        onDoiBoLoc={datBoLoc}
      />

      {idDangChon && dangChon ? (
        <>
          {/*
            Dùng `currentData` chứ không phải `data`: `data` giữ kết quả của hội thoại vừa xem,
            nên trong lúc chuyển hội thoại nó sẽ hiện tin nhắn của khách A dưới tên khách B.
            Với danh sách thì giữ dữ liệu cũ là tốt; với nội dung hội thoại thì là sai lệch.
          */}
          <MessageThread
            chiTiet={chiTiet.currentData}
            tenKhachHang={dangChon.contactName}
            dangTai={chiTiet.isFetching}
            dangGo={dangGo}
            dangThaoTac={ketQuaPhanCong.isLoading || ketQuaTrangThai.isLoading}
            onNhanXuLy={async () => {
              // Bỏ trống `assigneeUserId` là tự nhận — máy chủ lấy người dùng từ JWT
              await phanCong({ id: idDangChon }).unwrap()
              toast.success('Bạn đang phụ trách hội thoại này.')
            }}
            onDanhDauXong={async () => {
              await doiTrangThai({ id: idDangChon, status: 'RESOLVED' }).unwrap()
              toast.success('Đã đánh dấu hội thoại đã xử lý xong.')
            }}
            onChuyenGiao={datHuongChuyenGiao}
          />
          <ContextPanel nguCanh={nguCanh.currentData} dangTai={nguCanh.isFetching} />
        </>
      ) : (
        <ChuaChonHoiThoai />
      )}

      {idDangChon && huongChuyenGiao && (
        <HandoffDialog
          mo
          onDoiMo={(m) => !m && datHuongChuyenGiao(null)}
          idHoiThoai={idDangChon}
          huong={huongChuyenGiao}
        />
      )}
    </div>
  )
}

function ChuaChonHoiThoai() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
      <div className="bg-muted text-muted-foreground flex size-11 items-center justify-center rounded-full">
        <Inbox className="size-5" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-base font-medium">Chọn một hội thoại để xem</span>
        <span className="text-muted-foreground max-w-xs text-[13px]">
          Danh sách bên trái sắp theo thời điểm tin nhắn gần nhất.
        </span>
      </div>
    </div>
  )
}
