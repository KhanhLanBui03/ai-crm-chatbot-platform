import { apiSlice } from '@/api/apiSlice'
import { axiosClient } from '@/api/axiosClient'
import type { Page } from '@/types/api'
import {
  DOANH_NGHIEP_MAU,
  GOI_DICH_VU_MAU,
  PHAN_TICH_NEN_TANG_MAU,
  TAI_NGUYEN_AI_MAU,
  THONG_KE_NEN_TANG,
  type DoanhNghiepAdmin,
  type DuLieuPhanTichNenTang,
  type GoiDichVuAdmin,
  type TaiNguyenAiTenant,
  type ThongKeNenTang,
} from '@/mocks/du-lieu-admin'

/**
 * RTK Query endpoints cho Cổng Quản trị Nền tảng (Platform Admin Portal).
 *
 * Gọi trực tiếp backend `/api/v1/admin/**` kết nối cơ sở dữ liệu thật, và tự động fallback
 * sang bộ dữ liệu mẫu chi tiết khi chưa đăng nhập hoặc backend chưa sẵn sàng.
 */

let dsDoanhNghiep = [...DOANH_NGHIEP_MAU]
let dsGoiDV = [...GOI_DICH_VU_MAU]

interface ThamSoDoanhNghiep {
  page?: number
  size?: number
  q?: string
  status?: string
  planCode?: string
}

export const adminApi = apiSlice.injectEndpoints({
  endpoints: (build) => ({
    // ── Tổng quan ─────────────────────────────────────────────────────────────
    thongKeNenTang: build.query<ThongKeNenTang, void>({
      queryFn: async () => {
        try {
          const res = await axiosClient.get<ThongKeNenTang>('/api/v1/admin/overview')
          return { data: res.data }
        } catch {
          return { data: THONG_KE_NEN_TANG }
        }
      },
      providesTags: ['AdminOverview'],
    }),

    // ── Doanh nghiệp ─────────────────────────────────────────────────────────
    danhSachDoanhNghiepAdmin: build.query<Page<DoanhNghiepAdmin>, ThamSoDoanhNghiep>({
      queryFn: async (params) => {
        try {
          const res = await axiosClient.get<Page<DoanhNghiepAdmin>>('/api/v1/admin/tenants', {
            params: {
              page: params.page ?? 0,
              size: params.size ?? 25,
              ...(params.q ? { q: params.q } : {}),
              ...(params.status ? { status: params.status } : {}),
              ...(params.planCode ? { planCode: params.planCode } : {}),
            },
          })
          if (res.data && Array.isArray(res.data.items)) {
            return { data: res.data }
          }
          throw new Error('Dữ liệu không đúng định dạng')
        } catch {
          let ket = [...dsDoanhNghiep]
          if (params.status && params.status.trim()) {
            ket = ket.filter((d) => d.status === params.status)
          }
          if (params.planCode && params.planCode.trim()) {
            ket = ket.filter((d) => d.planCode === params.planCode)
          }
          if (params.q && params.q.trim()) {
            const qLower = params.q.toLowerCase().trim()
            ket = ket.filter(
              (d) =>
                d.companyName.toLowerCase().includes(qLower) ||
                d.contactEmail.toLowerCase().includes(qLower) ||
                (d.industry && d.industry.toLowerCase().includes(qLower)) ||
                d.slug.toLowerCase().includes(qLower),
            )
          }
          const page = params.page ?? 0
          const size = params.size ?? 25
          const start = page * size
          const pagedItems = ket.slice(start, start + size)
          return {
            data: {
              items: pagedItems,
              totalItems: ket.length,
              page,
              size,
              totalPages: Math.ceil(ket.length / size) || 1,
            },
          }
        }
      },
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'AdminTenants' as const, id })),
              { type: 'AdminTenants', id: 'LIST' },
            ]
          : [{ type: 'AdminTenants', id: 'LIST' }],
    }),

    khoaDoanhNghiep: build.mutation<DoanhNghiepAdmin, { id: string; reason: string }>({
      queryFn: async ({ id, reason }) => {
        try {
          const res = await axiosClient.post<DoanhNghiepAdmin>(
            `/api/v1/admin/tenants/${id}/suspend`,
            { reason },
          )
          return { data: res.data }
        } catch {
          const idx = dsDoanhNghiep.findIndex((d) => d.id === id)
          if (idx !== -1) {
            dsDoanhNghiep[idx] = {
              ...dsDoanhNghiep[idx],
              status: 'SUSPENDED',
              suspendedReason: reason,
            }
            return { data: dsDoanhNghiep[idx] }
          }
          return {
            error: {
              status: 404,
              message: 'Không tìm thấy doanh nghiệp',
              traceId: null,
            },
          }
        }
      },
      invalidatesTags: (_r, _e, { id }) => [
        { type: 'AdminTenants', id },
        { type: 'AdminTenants', id: 'LIST' },
        'AdminOverview',
      ],
    }),

    kichHoatDoanhNghiep: build.mutation<DoanhNghiepAdmin, { id: string }>({
      queryFn: async ({ id }) => {
        try {
          const res = await axiosClient.post<DoanhNghiepAdmin>(
            `/api/v1/admin/tenants/${id}/activate`,
          )
          return { data: res.data }
        } catch {
          const idx = dsDoanhNghiep.findIndex((d) => d.id === id)
          if (idx !== -1) {
            dsDoanhNghiep[idx] = {
              ...dsDoanhNghiep[idx],
              status: 'ACTIVE',
              suspendedReason: null,
            }
            return { data: dsDoanhNghiep[idx] }
          }
          return {
            error: {
              status: 404,
              message: 'Không tìm thấy doanh nghiệp',
              traceId: null,
            },
          }
        }
      },
      invalidatesTags: (_r, _e, { id }) => [
        { type: 'AdminTenants', id },
        { type: 'AdminTenants', id: 'LIST' },
        'AdminOverview',
      ],
    }),

    // ── Gói dịch vụ ──────────────────────────────────────────────────────────
    danhSachGoiAdmin: build.query<GoiDichVuAdmin[], void>({
      queryFn: async () => {
        try {
          const res = await axiosClient.get<GoiDichVuAdmin[]>('/api/v1/admin/plans')
          return { data: res.data }
        } catch {
          return { data: dsGoiDV }
        }
      },
      providesTags: ['AdminPlans'],
    }),

    capNhatGoiAdmin: build.mutation<GoiDichVuAdmin, { code: string; data: Partial<GoiDichVuAdmin> }>({
      queryFn: async ({ code, data }) => {
        try {
          const res = await axiosClient.patch<GoiDichVuAdmin>(
            `/api/v1/admin/plans/${code}`,
            data,
          )
          return { data: res.data }
        } catch {
          const idx = dsGoiDV.findIndex((g) => g.code === code)
          if (idx !== -1) {
            dsGoiDV[idx] = { ...dsGoiDV[idx], ...data }
            return { data: dsGoiDV[idx] }
          }
          return {
            error: {
              status: 404,
              message: 'Không tìm thấy gói dịch vụ',
              traceId: null,
            },
          }
        }
      },
      invalidatesTags: ['AdminPlans'],
    }),

    // ── Tài nguyên AI ────────────────────────────────────────────────────────
    taiNguyenAiAdmin: build.query<TaiNguyenAiTenant[], void>({
      queryFn: async () => {
        try {
          const res = await axiosClient.get<TaiNguyenAiTenant[]>('/api/v1/admin/ai-usage')
          return { data: res.data }
        } catch {
          return { data: TAI_NGUYEN_AI_MAU }
        }
      },
    }),

    // ── Phân tích chuyên sâu nền tảng ─────────────────────────────────────────
    phanTichNenTang: build.query<DuLieuPhanTichNenTang, { khoang?: string } | void>({
      queryFn: async (arg) => {
        try {
          const khoang = arg && typeof arg === 'object' ? arg.khoang : undefined
          const res = await axiosClient.get<DuLieuPhanTichNenTang>('/api/v1/admin/analytics', {
            params: { khoang: khoang ?? '30d' },
          })
          return { data: res.data }
        } catch {
          return { data: PHAN_TICH_NEN_TANG_MAU }
        }
      },
      providesTags: ['AdminOverview'],
    }),
  }),
})

export const {
  useThongKeNenTangQuery,
  useDanhSachDoanhNghiepAdminQuery,
  useKhoaDoanhNghiepMutation,
  useKichHoatDoanhNghiepMutation,
  useDanhSachGoiAdminQuery,
  useCapNhatGoiAdminMutation,
  useTaiNguyenAiAdminQuery,
  usePhanTichNenTangQuery,
} = adminApi
