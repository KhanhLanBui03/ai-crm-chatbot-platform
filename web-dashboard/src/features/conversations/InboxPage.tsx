import { skipToken } from '@reduxjs/toolkit/query'
import { Inbox } from 'lucide-react'
import { useEffect, useState } from 'react'

import { toast } from 'sonner'

import { laLoiTruyVan } from '@/api/baseQuery'
import {
  useChiTietHoiThoaiQuery,
  useDanhDauDaDocMutation,
  useDanhSachHoiThoaiQuery,
  useDoiTrangThaiHoiThoaiMutation,
  useGuiTinNhanMutation,
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
 *
 * Tin mới về bằng HỎI ĐỊNH KỲ 5 giây (UC012 bước 4 — đã chốt giảm độ sâu: java-core chưa có máy chủ
 * WebSocket). Khi có máy chủ thời gian thực thì bỏ `pollingInterval`, phần còn lại giữ nguyên.
 */
const CHU_KY_HOI_MS = 5000
export function InboxPage() {
  const [boLoc, datBoLoc] = useState<BoLocHoiThoai>({ phamVi: 'all' })
  const [idDangChon, datIdDangChon] = useState<string | null>(null)

  const danhSach = useDanhSachHoiThoaiQuery(boLoc, { pollingInterval: CHU_KY_HOI_MS })
  const chiTiet = useChiTietHoiThoaiQuery(idDangChon ?? skipToken, { pollingInterval: CHU_KY_HOI_MS })
  const nguCanh = useNguCanhHoiThoaiQuery(idDangChon ?? skipToken)
  const dangGo = useDangGo(idDangChon)
  const [phanCong, ketQuaPhanCong] = usePhanCongHoiThoaiMutation()
  const [doiTrangThai, ketQuaTrangThai] = useDoiTrangThaiHoiThoaiMutation()
  const [guiTin, ketQuaGui] = useGuiTinNhanMutation()
  const [danhDauDaDoc] = useDanhDauDaDocMutation()
  const [huongChuyenGiao, datHuongChuyenGiao] = useState<
    'BOT_TO_AGENT' | 'AGENT_TO_BOT' | null
  >(null)

  // `data` giữ kết quả của bộ lọc trước cho tới khi kết quả mới về — danh sách không nháy trắng
  const muc = danhSach.data?.items
  const dangChon = muc?.find((c) => c.id === idDangChon) ?? null

  // UC012 bước 10 — đang mở hội thoại mà có tin chưa đọc thì đánh dấu đã đọc
  const chuaDoc = dangChon?.unreadCount ?? 0
  useEffect(() => {
    if (idDangChon && chuaDoc > 0) void danhDauDaDoc(idDangChon)
  }, [idDangChon, chuaDoc, danhDauDaDoc])

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
            // Chỉ hiện xương khi CHƯA có dữ liệu của hội thoại này — lần hỏi định kỳ 5 giây
            // cũng làm `isFetching` bật, dùng nó thì khung chat nháy trắng mỗi 5 giây.
            dangTai={!chiTiet.currentData}
            dangGo={dangGo}
            dangThaoTac={ketQuaPhanCong.isLoading || ketQuaTrangThai.isLoading}
            dangGui={ketQuaGui.isLoading}
            onGui={async (noiDung) => {
              try {
                await guiTin({ id: idDangChon, content: noiDung }).unwrap()
                return true
              } catch (loi) {
                toast.error(laLoiTruyVan(loi) ? loi.message : 'Không gửi được tin nhắn.')
                return false
              }
            }}
            onNhanXuLy={async () => {
              try {
                // Bỏ trống `assigneeUserId` là tự nhận — máy chủ lấy người dùng từ JWT
                await phanCong({ id: idDangChon }).unwrap()
                toast.success('Bạn đang phụ trách hội thoại này.')
              } catch (loi) {
                toast.error(laLoiTruyVan(loi) ? loi.message : 'Không nhận được hội thoại.')
              }
            }}
            onDanhDauXong={async () => {
              try {
                await doiTrangThai({ id: idDangChon, status: 'RESOLVED' }).unwrap()
                toast.success('Đã đánh dấu hội thoại đã xử lý xong.')
              } catch (loi) {
                toast.error(laLoiTruyVan(loi) ? loi.message : 'Không đổi được trạng thái.')
              }
            }}
            onChuyenGiao={datHuongChuyenGiao}
            onQuayLai={() => datIdDangChon(null)}
          />
          <ContextPanel nguCanh={nguCanh.currentData} dangTai={nguCanh.isFetching} />
        </>
      ) : (
        <div className="hidden md:flex flex-1">
          <ChuaChonHoiThoai />
        </div>
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
