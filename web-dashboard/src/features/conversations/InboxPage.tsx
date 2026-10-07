import { skipToken } from '@reduxjs/toolkit/query'
import { AlertTriangle, Inbox } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

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
  useTinhTrangHangChoQuery,
  type BoLocHoiThoai,
} from '@/api/conversations'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { GiaoChoNguoi, TraVeHangCho } from '@/features/conversations/AssignControls'
import { useAppSelector } from '@/app/store/hooks'
import { ContextPanel } from '@/features/conversations/ContextPanel'
import { ConversationList } from '@/features/conversations/ConversationList'
import { MessageThread } from '@/features/conversations/MessageThread'
import { CreateLeadDialog } from '@/features/leads/CreateLeadDialog'
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
  // `?c=<id>` — mở thẳng một hội thoại (vd. "Hội thoại nguồn" ở trang Lead, UC032 bước 5)
  const [thamSo] = useSearchParams()
  const idTuLienKet = thamSo.get('c')
  const [idDangChon, datIdDangChon] = useState<string | null>(idTuLienKet)
  const [moTaoLead, datMoTaoLead] = useState(false)

  const danhSach = useDanhSachHoiThoaiQuery(boLoc, { pollingInterval: CHU_KY_HOI_MS })
  const chiTiet = useChiTietHoiThoaiQuery(idDangChon ?? skipToken, { pollingInterval: CHU_KY_HOI_MS })
  const nguCanh = useNguCanhHoiThoaiQuery(idDangChon ?? skipToken)
  const dangGo = useDangGo(idDangChon)
  const [phanCong, ketQuaPhanCong] = usePhanCongHoiThoaiMutation()
  const [doiTrangThai, ketQuaTrangThai] = useDoiTrangThaiHoiThoaiMutation()
  const [guiTin, ketQuaGui] = useGuiTinNhanMutation()
  const [danhDauDaDoc] = useDanhDauDaDocMutation()
  const toi = useAppSelector((s) => s.auth.nguoiDung)
  const laQuanTri = toi?.roleCode === 'TENANT_ADMIN'
  // UC014 6.2 / 7.2 — cảnh báo cho quản trị viên thay cho thông báo đẩy (chưa có kênh thông báo)
  const hangCho = useTinhTrangHangChoQuery(undefined, { skip: !laQuanTri, pollingInterval: 30_000 })
  const [huongChuyenGiao, datHuongChuyenGiao] = useState<
    'BOT_TO_AGENT' | 'AGENT_TO_BOT' | null
  >(null)

  // `data` giữ kết quả của bộ lọc trước cho tới khi kết quả mới về — danh sách không nháy trắng
  const muc = danhSach.data?.items
  // Hội thoại mở từ liên kết có thể không nằm trong trang danh sách hiện tại → lấy từ chi tiết
  const dangChon =
    muc?.find((c) => c.id === idDangChon) ??
    (idDangChon && chiTiet.currentData?.id === idDangChon ? chiTiet.currentData : null)

  // UC012 bước 10 — đang mở hội thoại mà có tin chưa đọc thì đánh dấu đã đọc
  const chuaDoc = dangChon?.unreadCount ?? 0
  useEffect(() => {
    if (idDangChon && chuaDoc > 0) void danhDauDaDoc(idDangChon)
  }, [idDangChon, chuaDoc, danhDauDaDoc])

  /**
   * Đang ở tab "Chờ tôi" mà nhận / trả lời thì hội thoại thành "của tôi" và RỜI khỏi danh sách đang
   * lọc — đoạn tự chọn bên dưới sẽ nhảy sang hội thoại khác ngay lúc nhân viên đang làm, dễ trả lời
   * nhầm khách. Chuyển theo sang tab "Của tôi" để hội thoại vừa nhận vẫn đang mở.
   */
  function theoHoiThoaiVuaNhan() {
    if (boLoc.phamVi === 'unassigned') datBoLoc({ ...boLoc, phamVi: 'mine', trang: 0 })
  }

  // Tự chọn hội thoại đầu tiên, và bỏ chọn khi bộ lọc làm nó biến mất khỏi danh sách
  useEffect(() => {
    if (!muc) return
    if (muc.length === 0) {
      if (idDangChon !== idTuLienKet) datIdDangChon(null)
    } else if (!idDangChon || (!muc.some((c) => c.id === idDangChon) && idDangChon !== idTuLienKet)) {
      datIdDangChon(muc[0].id)
    }
  }, [muc, idDangChon, idTuLienKet])

  const canhBao = hangCho.data
    ? [
        hangCho.data.waitingOverdue > 0 ? `${hangCho.data.waitingOverdue} hội thoại chờ quá 5 phút chưa ai nhận` : null,
        hangCho.data.waitingTotal > 0 && hangCho.data.onlineAgents === 0 ? 'không nhân viên nào đang trực' : null,
      ].filter(Boolean)
    : []

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {canhBao.length > 0 && (
        <Alert className="rounded-none border-x-0 border-t-0" role="status">
          <AlertTriangle />
          <AlertDescription>
            {canhBao.join(' · ')}. Mở tab "Chờ tôi" để nhận, hoặc giao cho người đang trực.
          </AlertDescription>
        </Alert>
      )}
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
                theoHoiThoaiVuaNhan()
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
                theoHoiThoaiVuaNhan()
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
            // Giống luật ở máy chủ (InboxService): hội thoại người khác đang giữ thì nhân viên chỉ xem
            nguoiKhacGiu={
              dangChon.assignedUserId &&
              dangChon.assignedUserId !== toi?.id &&
              toi?.roleCode !== 'TENANT_ADMIN'
                ? (dangChon.assignedUserName ?? 'một nhân viên khác')
                : null
            }
            thaoTacPhanCong={
              <>
                {laQuanTri && <GiaoChoNguoi idHoiThoai={idDangChon} nguoiDangGiu={dangChon.assignedUserId} />}
                {dangChon.assignedUserId && (laQuanTri || dangChon.assignedUserId === toi?.id) && (
                  <TraVeHangCho idHoiThoai={idDangChon} onXong={() => datBoLoc({ ...boLoc, phamVi: 'all', trang: 0 })} />
                )}
              </>
            }
            onChuyenGiao={datHuongChuyenGiao}
            onQuayLai={() => datIdDangChon(null)}
          />
          <ContextPanel
            nguCanh={nguCanh.currentData}
            dangTai={nguCanh.isFetching}
            onTaoLead={nguCanh.currentData?.contact ? () => datMoTaoLead(true) : undefined}
          />
          {nguCanh.currentData?.contact && (
            <CreateLeadDialog
              mo={moTaoLead}
              onDoiMo={datMoTaoLead}
              tuHoiThoai={{
                contactId: nguCanh.currentData.contact.id,
                contactName: nguCanh.currentData.contact.fullName ?? dangChon.contactName,
                conversationId: idDangChon,
              }}
            />
          )}
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
