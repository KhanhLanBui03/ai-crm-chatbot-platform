import type { MauCauTraLoi, QuyTacPhanCong } from '@/types/schema'

/** Dữ liệu giả cho SCR022, SCR023 và ô "mẫu câu trả lời" của hộp thư. */

const U = (n: number) => `u1000000-0000-4000-8000-00000000000${n}`

export const danhSachQuyTac: QuyTacPhanCong[] = [
  {
    id: 'qt-001',
    name: 'Khách mua sỉ → Tuấn',
    appliesTo: 'CONVERSATION',
    strategy: 'FIXED_USER',
    channelType: null,
    tagId: 't-03',
    targetUserId: U(2),
    targetUserName: 'Lê Minh Tuấn',
    maxConcurrent: null,
    // Ưu tiên cao nhất: quy tắc theo thẻ phải thắng quy tắc theo kênh, nếu không thì khách sỉ
    // rơi vào hàng chờ chung
    priority: 100,
    isActive: true,
  },
  {
    id: 'qt-002',
    name: 'Zalo → người ít việc nhất',
    appliesTo: 'CONVERSATION',
    strategy: 'LEAST_BUSY',
    channelType: 'ZALO',
    tagId: null,
    targetUserId: null,
    targetUserName: null,
    maxConcurrent: 8,
    priority: 50,
    isActive: true,
  },
  {
    id: 'qt-003',
    name: 'Facebook → chia lượt',
    appliesTo: 'CONVERSATION',
    strategy: 'ROUND_ROBIN',
    channelType: 'FACEBOOK',
    tagId: null,
    targetUserId: null,
    targetUserName: null,
    maxConcurrent: 6,
    priority: 50,
    isActive: true,
  },
  {
    id: 'qt-004',
    name: 'Cơ hội tiềm năng → Ngân',
    appliesTo: 'LEAD',
    strategy: 'FIXED_USER',
    channelType: null,
    tagId: null,
    targetUserId: U(3),
    targetUserName: 'Võ Thị Kim Ngân',
    maxConcurrent: null,
    priority: 10,
    isActive: true,
  },
  {
    id: 'qt-005',
    name: 'Widget ngoài giờ → hàng chờ chung',
    appliesTo: 'CONVERSATION',
    strategy: 'LEAST_BUSY',
    channelType: 'WEB_WIDGET',
    tagId: null,
    targetUserId: null,
    targetUserName: null,
    maxConcurrent: 12,
    priority: 0,
    // Đã tắt — quy tắc tắt vẫn giữ lại chứ không xoá, để bật lại mùa cao điểm
    isActive: false,
  },
]

export const mauCauTraLoi: MauCauTraLoi[] = [
  {
    id: 'mc-001',
    title: 'Chào mở đầu',
    content: 'Dạ em chào anh/chị, em là nhân viên chăm sóc của Cát Tường. Em hỗ trợ mình ạ.',
    shortcut: '/chao',
    category: 'Chung',
    usageCount: 412,
  },
  {
    id: 'mc-002',
    title: 'Chính sách bảo hành',
    content:
      'Dạ sản phẩm được bảo hành 24 tháng kể từ ngày mua, áp dụng cho lỗi kỹ thuật của nhà sản xuất ạ.',
    shortcut: '/baohanh',
    category: 'Bảo hành',
    usageCount: 287,
  },
  {
    id: 'mc-003',
    title: 'Xin thông tin đơn hàng',
    content: 'Anh/chị cho em xin số điện thoại đặt hàng hoặc mã đơn để em tra giúp mình ạ.',
    shortcut: '/tradon',
    category: 'Đơn hàng',
    usageCount: 356,
  },
  {
    id: 'mc-004',
    title: 'Hẹn gọi lại',
    content: 'Dạ phần này em cần xác nhận với bộ phận kỹ thuật, em xin phép phản hồi lại trong hôm nay ạ.',
    shortcut: '/hengoi',
    category: 'Chung',
    usageCount: 198,
  },
]
