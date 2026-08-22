import { apiSlice } from '@/api/apiSlice'
import type { Page } from '@/types/api'
import type {
  CongCu,
  DanhGiaAi,
  HieuQuaAi,
  KetQuaKiemDuyet,
  LoaiSuKienAnToan,
  LuotXuLyAi,
  LyDoDanhGia,
  MayChuMcp,
  MucNghiemTrong,
  MucRuiRo,
  NhanhXuLyAi,
  NhatKyGoiCongCu,
  SuKienAnToan,
  TrangThaiPheDuyet,
} from '@/types/schema'

/** Tác tử AI, MCP và giám sát — SCR035–SCR040, SCR051. */

export interface LuuMayChuMcp {
  name: string
  endpointUrl: string
  transport: string
  specVersion: string
  authType: string
  secret?: string | null
  scopes?: string[]
  timeoutMs?: number
  maxCallsPerConversation?: number
}

export interface BoLocGoiCongCu {
  ketQuaKiemDuyet?: KetQuaKiemDuyet
  trangThaiDuyet?: TrangThaiPheDuyet
  hoiThoaiId?: string
  tuNgay?: string
  denNgay?: string
  trang?: number
}

export interface BoLocLuotXuLy {
  nhanh?: NhanhXuLyAi
  daTuChoi?: boolean
  hoiThoaiId?: string
  tuNgay?: string
  denNgay?: string
  trang?: number
}

const CA_TOOL_CALL = { type: 'ToolCall' as const, id: 'DANH-SACH' }

export const aiAgentApi = apiSlice.injectEndpoints({
  endpoints: (build) => ({
    // ── SCR037 · SCR038 — máy chủ MCP ─────────────────────────────────────────
    danhSachMayChuMcp: build.query<MayChuMcp[], void>({
      query: () => ({ url: '/api/v1/mcp-servers' }),
      providesTags: ['TacTuAI'],
    }),

    themMayChuMcp: build.mutation<MayChuMcp, LuuMayChuMcp>({
      query: (than) => ({ url: '/api/v1/mcp-servers', method: 'POST', body: than }),
      invalidatesTags: ['TacTuAI'],
    }),

    suaMayChuMcp: build.mutation<MayChuMcp, { id: string; than: LuuMayChuMcp }>({
      query: ({ id, than }) => ({ url: `/api/v1/mcp-servers/${id}`, method: 'PATCH', body: than }),
      invalidatesTags: ['TacTuAI'],
    }),

    ngatMayChuMcp: build.mutation<null, string>({
      query: (id) => ({ url: `/api/v1/mcp-servers/${id}`, method: 'DELETE' }),
      invalidatesTags: ['TacTuAI'],
    }),

    /**
     * Bắt tay và dò lại danh sách công cụ.
     *
     * Làm mới cả `TacTuAI` vì lần dò có thể phát hiện lược đồ công cụ đã đổi — lúc đó
     * `schemaHash` lệch khỏi `approvedSchemaHash` và sổ đăng ký phải hiện cảnh báo ngay,
     * không đợi tới lần tải trang sau.
     */
    batTayMcp: build.mutation<{ server: MayChuMcp; tools: CongCu[] }, string>({
      query: (id) => ({ url: `/api/v1/mcp-servers/${id}/handshake`, method: 'POST' }),
      invalidatesTags: ['TacTuAI'],
    }),

    // ── SCR039 — sổ đăng ký công cụ ───────────────────────────────────────────
    danhSachCongCu: build.query<
      CongCu[],
      { mayChuId?: string; daBat?: boolean; mucRuiRo?: MucRuiRo }
    >({
      query: (bo) => ({
        url: '/api/v1/tools',
        params: { serverId: bo.mayChuId, enabled: bo.daBat, riskLevel: bo.mucRuiRo },
      }),
      providesTags: ['TacTuAI'],
    }),

    capNhatCongCu: build.mutation<
      CongCu,
      {
        id: string
        enabled?: boolean
        requiresConfirmation?: boolean
        approveSchemaHash?: boolean
      }
    >({
      query: ({ id, ...than }) => ({ url: `/api/v1/tools/${id}`, method: 'PATCH', body: than }),
      invalidatesTags: ['TacTuAI'],
    }),

    // ── SCR035 · SCR040 — nhật ký và phê duyệt lời gọi công cụ ────────────────
    danhSachGoiCongCu: build.query<Page<NhatKyGoiCongCu>, BoLocGoiCongCu>({
      query: (bo) => ({
        url: '/api/v1/tool-calls',
        params: {
          guardResult: bo.ketQuaKiemDuyet,
          approvalStatus: bo.trangThaiDuyet,
          conversationId: bo.hoiThoaiId,
          from: bo.tuNgay,
          to: bo.denNgay,
          page: bo.trang ?? 0,
          size: 10,
        },
      }),
      providesTags: (kq) =>
        kq
          ? [...kq.items.map(({ id }) => ({ type: 'ToolCall' as const, id })), CA_TOOL_CALL]
          : [CA_TOOL_CALL],
    }),

    /**
     * SCR040 — duyệt hoặc từ chối một lời gọi công cụ. Bề mặt **T4**.
     *
     * Làm mới cả `TuongTacAI`: quyết định ở đây mở khoá (hoặc chặn hẳn) lượt xử lý đang treo, nên
     * màn giám sát phải đổi theo trong cùng một nhịp.
     */
    duyetGoiCongCu: build.mutation<
      NhatKyGoiCongCu,
      { id: number; decision: 'APPROVED' | 'REJECTED'; note?: string | null }
    >({
      query: ({ id, ...than }) => ({
        url: `/api/v1/tool-calls/${id}/approval`,
        method: 'POST',
        body: than,
      }),
      invalidatesTags: (_kq, _loi, { id }) => [
        { type: 'ToolCall', id },
        CA_TOOL_CALL,
        'TuongTacAI',
      ],
    }),

    // ── SCR036 — giám sát lượt xử lý ──────────────────────────────────────────
    danhSachLuotXuLy: build.query<Page<LuotXuLyAi>, BoLocLuotXuLy>({
      query: (bo) => ({
        url: '/api/v1/ai-interactions',
        params: {
          route: bo.nhanh,
          refused: bo.daTuChoi,
          conversationId: bo.hoiThoaiId,
          from: bo.tuNgay,
          to: bo.denNgay,
          page: bo.trang ?? 0,
          size: 10,
        },
      }),
      providesTags: ['TuongTacAI'],
    }),

    danhGiaLuotXuLy: build.mutation<
      DanhGiaAi,
      {
        id: string
        rating: 'POSITIVE' | 'NEGATIVE'
        reasonCode?: LyDoDanhGia | null
        comment?: string | null
      }
    >({
      query: ({ id, ...than }) => ({
        url: `/api/v1/ai-interactions/${id}/feedback`,
        method: 'POST',
        body: than,
      }),
      invalidatesTags: ['TuongTacAI', 'BaoCao'],
    }),

    danhSachSuKienAnToan: build.query<
      Page<SuKienAnToan>,
      { mucNghiemTrong?: MucNghiemTrong; loai?: LoaiSuKienAnToan; trang?: number; co?: number }
    >({
      query: (bo) => ({
        url: '/api/v1/safety-events',
        params: {
          severity: bo.mucNghiemTrong,
          eventType: bo.loai,
          page: bo.trang ?? 0,
          size: bo.co ?? 10,
        },
      }),
      providesTags: ['TuongTacAI'],
    }),

    // ── SCR051 — hiệu quả và chi phí ──────────────────────────────────────────
    hieuQuaAi: build.query<HieuQuaAi, { tuNgay?: string; denNgay?: string; phienBanMo?: string }>({
      query: (bo) => ({
        url: '/api/v1/analytics/ai-performance',
        params: { from: bo.tuNgay, to: bo.denNgay, modelVersion: bo.phienBanMo },
      }),
      providesTags: ['BaoCao'],
    }),
  }),
})

export const {
  useDanhSachMayChuMcpQuery,
  useThemMayChuMcpMutation,
  useSuaMayChuMcpMutation,
  useNgatMayChuMcpMutation,
  useBatTayMcpMutation,
  useDanhSachCongCuQuery,
  useCapNhatCongCuMutation,
  useDanhSachGoiCongCuQuery,
  useDuyetGoiCongCuMutation,
  useDanhSachLuotXuLyQuery,
  useDanhGiaLuotXuLyMutation,
  useDanhSachSuKienAnToanQuery,
  useHieuQuaAiQuery,
} = aiAgentApi
