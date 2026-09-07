import { apiSlice } from '@/api/apiSlice'
import type { CauHinhWidget, Kenh, LoaiKenh } from '@/types/schema'

/** Kênh và Web Widget — SCR016–SCR018. */
export const channelsApi = apiSlice.injectEndpoints({
  endpoints: (build) => ({
    danhSachKenh: build.query<Kenh[], void>({
      query: () => ({ url: '/api/v1/channels' }),
      providesTags: ['Kenh'],
    }),

    themKenh: build.mutation<
      Kenh,
      { channelType: LoaiKenh; externalAccountId: string; accountName?: string; accessToken?: string }
    >({
      query: (than) => ({ url: '/api/v1/channels', method: 'POST', body: than }),
      invalidatesTags: ['Kenh'],
    }),

    /**
     * Xác minh webhook. Tách khỏi lúc tạo vì nó gọi ra hệ thống bên ngoài và có thể hỏng vì lý do
     * ngoài tầm kiểm soát — gộp vào bước tạo là bắt người dùng nhập lại token chỉ vì Zalo lag.
     */
    xacMinhKenh: build.mutation<Kenh, string>({
      query: (id) => ({ url: `/api/v1/channels/${id}/verify`, method: 'POST' }),
      invalidatesTags: ['Kenh'],
    }),

    ngatKenh: build.mutation<void, string>({
      query: (id) => ({ url: `/api/v1/channels/${id}`, method: 'DELETE' }),
      invalidatesTags: ['Kenh'],
    }),

    cauHinhWidget: build.query<CauHinhWidget, void>({
      query: () => ({ url: '/api/v1/widget-config' }),
      providesTags: [{ type: 'Kenh', id: 'WIDGET' }],
    }),

    luuCauHinhWidget: build.mutation<CauHinhWidget, CauHinhWidget>({
      query: (than) => ({ url: '/api/v1/widget-config', method: 'PUT', body: than }),
      invalidatesTags: [{ type: 'Kenh', id: 'WIDGET' }],
    }),

    maNhungWidget: build.query<{ snippet: string }, void>({
      query: () => ({ url: '/api/v1/widget-config/snippet' }),
      providesTags: [{ type: 'Kenh', id: 'WIDGET' }],
    }),
  }),
})

export const {
  useDanhSachKenhQuery,
  useThemKenhMutation,
  useXacMinhKenhMutation,
  useNgatKenhMutation,
  useCauHinhWidgetQuery,
  useLuuCauHinhWidgetMutation,
  useMaNhungWidgetQuery,
} = channelsApi
