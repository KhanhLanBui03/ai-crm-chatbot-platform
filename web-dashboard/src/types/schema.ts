/**
 * Cầu nối duy nhất giữa mã nguồn và `docs/openapi/dashboard-api.yaml`.
 *
 * `api-schema.d.ts` sinh tự động (`npm run gen:api`) và **không được sửa tay**. File này chỉ đặt
 * tên ngắn cho những schema màn hình thật sự dùng — nhờ vậy component viết
 * `import type { HoiThoaiTomTat } from '@/types/schema'` thay vì
 * `components['schemas']['HoiThoaiTomTat']` ở khắp nơi, và khi giao ước đổi thì lỗi kiểu nổ ra ở
 * đây trước, không phải rải rác trong 58 màn hình.
 *
 * Không schema nào có `tenantId` — nó đến từ ngữ cảnh đã xác thực ở phía máy chủ.
 */
import type { components } from '@/types/api-schema'

export type Schemas = components['schemas']

// ── Enum ──────────────────────────────────────────────────────────────────────

export type MaVaiTro = Schemas['MaVaiTro']
export type TrangThaiNguoiDung = Schemas['TrangThaiNguoiDung']
export type MaGoi = Schemas['MaGoi']
export type GiongDieuAi = Schemas['GiongDieuAi']
export type TrangThaiDoanhNghiep = Schemas['TrangThaiDoanhNghiep']
export type TrangThaiThueBao = Schemas['TrangThaiThueBao']
export type LoaiKenh = Schemas['LoaiKenh']
export type KenhChinh = Schemas['KenhChinh']
export type TrangThaiKenh = Schemas['TrangThaiKenh']
export type TrangThaiHoiThoai = Schemas['TrangThaiHoiThoai']
export type LoaiNguoiGui = Schemas['LoaiNguoiGui']
export type LoaiNoiDung = Schemas['LoaiNoiDung']
export type TrangThaiGui = Schemas['TrangThaiGui']
export type LyDoChuyenGiao = Schemas['LyDoChuyenGiao']
export type TrangThaiKhachHang = Schemas['TrangThaiKhachHang']
export type TrangThaiTaiLieu = Schemas['TrangThaiTaiLieu']
export type LoaiNguonTaiLieu = Schemas['LoaiNguonTaiLieu']
export type TrangThaiCongViecNap = Schemas['TrangThaiCongViecNap']
export type LoaiKhoangTrong = Schemas['LoaiKhoangTrong']
export type MucRuiRo = Schemas['MucRuiRo']
export type KetQuaKiemDuyet = Schemas['KetQuaKiemDuyet']
export type LyDoChan = Schemas['LyDoChan']
export type TrangThaiPheDuyet = Schemas['TrangThaiPheDuyet']
export type NhanhXuLyAi = Schemas['NhanhXuLyAi']
export type LyDoTuChoi = Schemas['LyDoTuChoi']
export type MucNghiemTrong = Schemas['MucNghiemTrong']
export type KetQuaGoiCongCu = Schemas['KetQuaGoiCongCu']
export type LoaiSuKienAnToan = Schemas['LoaiSuKienAnToan']
export type LyDoDanhGia = Schemas['LyDoDanhGia']
/** T1–T8 của `docs/threat-model.md` — sự kiện an toàn quy chiếu thẳng về bề mặt đe doạ. */
export type BeMatDeDoa = Schemas['BeMatDeDoa']
export type TrangThaiLead = Schemas['TrangThaiLead']
export type NguonLead = Schemas['NguonLead']
export type MucDo = Schemas['MucDo']
export type TrangThaiDeal = Schemas['TrangThaiDeal']
export type LoaiHoatDong = Schemas['LoaiHoatDong']
export type KetQuaHoatDong = Schemas['KetQuaHoatDong']
export type TrangThaiNhacViec = Schemas['TrangThaiNhacViec']
export type LoaiBaoCao = Schemas['LoaiBaoCao']
export type TrangThaiTepBaoCao = Schemas['TrangThaiTepBaoCao']
export type MucNghiemTrongKiemToan = Schemas['MucNghiemTrongKiemToan']
export type TrangThaiYeuCauXoa = Schemas['TrangThaiYeuCauXoa']
export type LoaiChuThe = Schemas['LoaiChuThe']
export type ThaoTacXoa = Schemas['ThaoTacXoa']

// ── Xác thực, người dùng, doanh nghiệp ────────────────────────────────────────

export type NguoiDungHienTai = Schemas['NguoiDungHienTai']
export type KetQuaDangNhap = Schemas['KetQuaDangNhap']
export type DangKyResult = Schemas['DangKyResult']
export type PhienDangNhap = Schemas['PhienDangNhap']
export type NguoiDung = Schemas['NguoiDung']
export type VaiTro = Schemas['VaiTro']
export type DoanhNghiep = Schemas['DoanhNghiep']
export type GoiDichVu = Schemas['GoiDichVu']
export type ThueBao = Schemas['ThueBao']
export type HanMucSuDung = Schemas['HanMucSuDung']
export type MotHanMuc = Schemas['MotHanMuc']
export type DiemSuDungNgay = Schemas['DiemSuDungNgay']

// ── Kênh ──────────────────────────────────────────────────────────────────────

export type Kenh = Schemas['Kenh']
export type CauHinhWidget = Schemas['CauHinhWidget']

// ── Hộp thư ───────────────────────────────────────────────────────────────────

export type HoiThoaiTomTat = Schemas['HoiThoaiTomTat']
export type HoiThoaiChiTiet = Schemas['HoiThoaiChiTiet']
export type NguCanhHoiThoai = Schemas['NguCanhHoiThoai']
export type TomTatHoiThoai = Schemas['TomTatHoiThoai']
export type TinNhan = Schemas['TinNhan']
export type TepDinhKem = Schemas['TepDinhKem']
export type TrichDan = Schemas['TrichDan']
export type SuKienChuyenGiao = Schemas['SuKienChuyenGiao']
export type MauCauTraLoi = Schemas['MauCauTraLoi']
export type QuyTacPhanCong = Schemas['QuyTacPhanCong']

// ── Khách hàng ────────────────────────────────────────────────────────────────

export type KhachHang = Schemas['KhachHang']
export type KhachHangChiTiet = Schemas['KhachHangChiTiet']
export type DanhTinhKenh = Schemas['DanhTinhKenh']
export type GhiChu = Schemas['GhiChu']
export type The = Schemas['The']

// ── Tri thức ──────────────────────────────────────────────────────────────────

export type TaiLieu = Schemas['TaiLieu']
export type TaiLieuChiTiet = Schemas['TaiLieuChiTiet']
export type CongViecNap = Schemas['CongViecNap']
export type DoanTaiLieu = Schemas['DoanTaiLieu']
export type KetQuaTruyHoi = Schemas['KetQuaTruyHoi']
export type KhoangTrongTriThuc = Schemas['KhoangTrongTriThuc']

// ── Tác tử AI ─────────────────────────────────────────────────────────────────

export type MayChuMcp = Schemas['MayChuMcp']
export type CongCu = Schemas['CongCu']
export type NhatKyGoiCongCu = Schemas['NhatKyGoiCongCu']
export type LuotXuLyAi = Schemas['LuotXuLyAi']
export type DanhGiaAi = Schemas['DanhGiaAi']
export type SuKienAnToan = Schemas['SuKienAnToan']

// ── Bán hàng ──────────────────────────────────────────────────────────────────

export type Lead = Schemas['Lead']
export type LeadChiTiet = Schemas['LeadChiTiet']
export type DiemLead = Schemas['DiemLead']
export type YeuToDiem = Schemas['YeuToDiem']
export type Pheu = Schemas['Pheu']
export type GiaiDoanPheu = Schemas['GiaiDoanPheu']
export type Deal = Schemas['Deal']
export type DealChiTiet = Schemas['DealChiTiet']
export type LichSuGiaiDoan = Schemas['LichSuGiaiDoan']
export type HoatDong = Schemas['HoatDong']

// ── Phân tích và kiểm toán ────────────────────────────────────────────────────

export type TongQuan = Schemas['TongQuan']
export type DiemHoiThoaiNgay = Schemas['DiemHoiThoaiNgay']
export type BacPheu = Schemas['BacPheu']
export type ThongKeChuDe = Schemas['ThongKeChuDe']
export type HieuQuaAi = Schemas['HieuQuaAi']
export type TepBaoCao = Schemas['TepBaoCao']
export type BanGhiKiemToan = Schemas['BanGhiKiemToan']
export type YeuCauXoa = Schemas['YeuCauXoa']
export type YeuCauXoaChiTiet = Schemas['YeuCauXoaChiTiet']
export type MucXoa = Schemas['MucXoa']
