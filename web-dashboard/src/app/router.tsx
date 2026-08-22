import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { useAppSelector } from '@/app/store/hooks'
import { AppShell } from '@/components/layout/AppShell'
import { ForgotPasswordPage } from '@/features/auth/ForgotPasswordPage'
import { LoginPage } from '@/features/auth/LoginPage'
import { RegisterPage } from '@/features/auth/RegisterPage'
import { ResetPasswordPage } from '@/features/auth/ResetPasswordPage'
import { VerifyEmailPage } from '@/features/auth/VerifyEmailPage'
import { AiInteractionsPage } from '@/features/ai-agent/AiInteractionsPage'
import { AiPerformancePage } from '@/features/ai-agent/AiPerformancePage'
import { McpServersPage } from '@/features/ai-agent/McpServersPage'
import { ToolCallLogPage } from '@/features/ai-agent/ToolCallLogPage'
import { ToolRegistryPage } from '@/features/ai-agent/ToolRegistryPage'
import { DocumentChunksPage } from '@/features/knowledge/DocumentChunksPage'
import { DocumentsPage } from '@/features/knowledge/DocumentsPage'
import { IngestionProgressPage } from '@/features/knowledge/IngestionProgressPage'
import { KnowledgeGapsPage } from '@/features/knowledge/KnowledgeGapsPage'
import { KnowledgeSearchPage } from '@/features/knowledge/KnowledgeSearchPage'
import { AuditLogPage } from '@/features/audit/AuditLogPage'
import { ErasurePreviewPage } from '@/features/audit/ErasurePreviewPage'
import { ErasureProgressPage } from '@/features/audit/ErasureProgressPage'
import { ErasureRequestsPage } from '@/features/audit/ErasureRequestsPage'
import { ConversationStatsPage } from '@/features/analytics/ConversationStatsPage'
import { FunnelPage } from '@/features/analytics/FunnelPage'
import { OverviewPage } from '@/features/analytics/OverviewPage'
import { ReportExportsPage } from '@/features/analytics/ReportExportsPage'
import { TopicsPage } from '@/features/analytics/TopicsPage'
import { ContactDetailPage } from '@/features/contacts/ContactDetailPage'
import { ContactsPage } from '@/features/contacts/ContactsPage'
import { AssignmentRulesPage } from '@/features/conversations/AssignmentRulesPage'
import { ActivitiesPage } from '@/features/deals/ActivitiesPage'
import { DealDetailPage } from '@/features/deals/DealDetailPage'
import { DealsBoardPage } from '@/features/deals/DealsBoardPage'
import { LeadDetailPage } from '@/features/leads/LeadDetailPage'
import { LeadsPage } from '@/features/leads/LeadsPage'
import { InboxPage } from '@/features/conversations/InboxPage'
import { ChannelsPage } from '@/features/settings/ChannelsPage'
import { RolesPage } from '@/features/settings/RolesPage'
import { SessionsPage } from '@/features/settings/SessionsPage'
import { SettingsIndexPage } from '@/features/settings/SettingsIndexPage'
import { SubscriptionPage } from '@/features/settings/SubscriptionPage'
import { TenantProfilePage } from '@/features/settings/TenantProfilePage'
import { UsageDailyPage } from '@/features/settings/UsageDailyPage'
import { UsagePage } from '@/features/settings/UsagePage'
import { UsersPage } from '@/features/settings/UsersPage'
import { WidgetConfigPage } from '@/features/settings/WidgetConfigPage'

/** Chặn route khi chưa đăng nhập, nhớ đường dẫn đích để quay lại sau khi đăng nhập xong. */
function CanDangNhap({ children }: { children: React.ReactNode }) {
  const daDangNhap = useAppSelector((s) => Boolean(s.auth.accessToken))
  const viTri = useLocation()

  if (!daDangNhap) {
    return <Navigate to="/dang-nhap" replace state={{ tu: viTri.pathname }} />
  }
  return <>{children}</>
}

export function Router() {
  return (
    <Routes>
      {/* C2 — vòng đời tài khoản, nằm NGOÀI `AppShell` vì chưa có phiên đăng nhập */}
      <Route path="/dang-nhap" element={<LoginPage />} />
      <Route path="/dang-ky" element={<RegisterPage />} />
      <Route path="/xac-thuc-thu" element={<VerifyEmailPage />} />
      <Route path="/quen-mat-khau" element={<ForgotPasswordPage />} />
      <Route path="/dat-lai-mat-khau" element={<ResetPasswordPage />} />

      <Route
        element={
          <CanDangNhap>
            <AppShell />
          </CanDangNhap>
        }
      >
        <Route path="/hop-thu" element={<InboxPage />} />
        {/* SCR048 và SCR006 — cùng component, khác người đọc nên khác thứ tự chỉ số */}
        <Route path="/tong-quan" element={<OverviewPage />} />
        <Route path="/quan-tri" element={<OverviewPage nguoiDoc="quan-tri" />} />
        <Route path="/khach-hang" element={<ContactsPage />} />
        <Route path="/khach-hang/:id" element={<ContactDetailPage />} />
        <Route path="/ban-hang/co-hoi-tiem-nang" element={<LeadsPage />} />
        <Route path="/ban-hang/co-hoi-tiem-nang/:id" element={<LeadDetailPage />} />
        <Route path="/ban-hang/pheu" element={<DealsBoardPage />} />
        <Route path="/ban-hang/pheu/:id" element={<DealDetailPage />} />
        <Route path="/ban-hang/hoat-dong" element={<ActivitiesPage />} />
        {/* C5 — kho tri thức. SCR029–SCR034 */}
        <Route path="/tri-thuc" element={<DocumentsPage />} />
        <Route path="/tri-thuc/tim-thu" element={<KnowledgeSearchPage />} />
        <Route path="/tri-thuc/tien-do" element={<IngestionProgressPage />} />
        <Route path="/tri-thuc/khoang-trong" element={<KnowledgeGapsPage />} />
        <Route path="/tri-thuc/tai-lieu/:id" element={<DocumentChunksPage />} />
        <Route path="/tri-thuc/tai-lieu/:id/tien-do" element={<IngestionProgressPage />} />

        {/* C5 — tác tử AI và MCP. SCR035–SCR040 */}
        <Route path="/tac-tu-ai" element={<Navigate to="/tac-tu-ai/luot-xu-ly" replace />} />
        <Route path="/tac-tu-ai/luot-xu-ly" element={<AiInteractionsPage />} />
        <Route path="/tac-tu-ai/goi-cong-cu" element={<ToolCallLogPage />} />
        <Route path="/tac-tu-ai/mcp" element={<McpServersPage />} />
        <Route path="/tac-tu-ai/cong-cu" element={<ToolRegistryPage />} />

        {/* Kiểm toán và quyền xoá dữ liệu cá nhân — SCR054–SCR058, Nghị định 13/2023/NĐ-CP */}
        <Route path="/kiem-toan" element={<Navigate to="/kiem-toan/nhat-ky" replace />} />
        <Route path="/kiem-toan/nhat-ky" element={<AuditLogPage />} />
        <Route path="/kiem-toan/yeu-cau-xoa" element={<ErasureRequestsPage />} />
        <Route path="/kiem-toan/yeu-cau-xoa/:id" element={<ErasureProgressPage />} />
        <Route path="/kiem-toan/xem-truoc-xoa" element={<ErasurePreviewPage />} />

        <Route path="/phan-tich" element={<Navigate to="/phan-tich/hoi-thoai" replace />} />
        <Route path="/phan-tich/hoi-thoai" element={<ConversationStatsPage />} />
        <Route path="/phan-tich/pheu" element={<FunnelPage />} />
        <Route path="/phan-tich/chu-de" element={<TopicsPage />} />
        <Route path="/phan-tich/hieu-qua-ai" element={<AiPerformancePage />} />
        <Route path="/phan-tich/bao-cao" element={<ReportExportsPage />} />

        {/* Cài đặt — mười mục gom sau một trang chủ thay vì rải ra thanh bên */}
        <Route path="/cai-dat" element={<SettingsIndexPage />} />
        <Route path="/cai-dat/doanh-nghiep" element={<TenantProfilePage />} />
        <Route path="/cai-dat/nguoi-dung" element={<UsersPage />} />
        <Route path="/cai-dat/phan-quyen" element={<RolesPage />} />
        <Route path="/cai-dat/thue-bao" element={<SubscriptionPage />} />
        <Route path="/cai-dat/han-muc" element={<UsagePage />} />
        <Route path="/cai-dat/muc-su-dung" element={<UsageDailyPage />} />
        <Route path="/cai-dat/quy-tac-phan-cong" element={<AssignmentRulesPage />} />
        <Route path="/cai-dat/kenh" element={<ChannelsPage />} />
        <Route path="/cai-dat/widget" element={<WidgetConfigPage />} />
        <Route path="/cai-dat/phien" element={<SessionsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/hop-thu" replace />} />
    </Routes>
  )
}
