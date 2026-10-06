-- ═════════════════════════════════════════════════════════════════════════════
-- V129 — UC014 (chuyển giao AI → nhân viên) + UC015 (gán hội thoại)
-- ═════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. Trạng thái trực tuyến của người dùng (UC014 6.1, UC015 6.1)
--
-- Bảng RIÊNG chứ không thêm cột vào platform.users: users có trigger touch_updated_at, ghi mốc hoạt
-- động mỗi phút vào đó thì updated_at ("hồ sơ sửa lần cuối") mất nghĩa.
-- "Đang trực" = last_active_at trong 2 phút gần nhất — Hộp thư hỏi máy chủ định kỳ nên mốc này tự
-- cập nhật khi nhân viên còn mở màn hình (tối đa một lần ghi mỗi phút).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE platform.user_presence (
    user_id        uuid        PRIMARY KEY,
    tenant_id      uuid        NOT NULL REFERENCES platform.tenants (id),
    last_active_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT fk_presence_user FOREIGN KEY (user_id, tenant_id)
        REFERENCES platform.users (id, tenant_id) ON DELETE CASCADE
);

CREATE INDEX ix_presence_tenant ON platform.user_presence (tenant_id, last_active_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. Sự kiện chuyển giao (UC014 hậu điều kiện, b3, 1a–2a)
--
-- conversations chỉ giữ lý do chuyển giao CUỐI. Thống kê "tỉ lệ AI xử lý trọn vẹn" và "khách chờ bao
-- lâu mới có người nhận" cần MỌI lần chuyển — mỗi lần một dòng.
-- counts_against_ai_quality do máy chủ quyết: hết hạn mức / AI lỗi không phải lỗi chất lượng của AI.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE engagement.handoff_events (
    id                        uuid         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                 uuid         NOT NULL REFERENCES platform.tenants (id),
    conversation_id           uuid         NOT NULL,
    direction                 varchar(20)  NOT NULL CHECK (direction IN ('BOT_TO_AGENT','AGENT_TO_BOT')),
    reason                    varchar(30)  NOT NULL
                              CHECK (reason IN ('CUSTOMER_REQUEST','LOW_CONFIDENCE','NO_GROUNDING',
                                                'NEGATIVE_SENTIMENT','REPEATED_FAILURE',
                                                'WRITE_TOOL_APPROVAL','QUOTA_EXCEEDED','LLM_ERROR')),
    triggered_by              varchar(20)  NOT NULL CHECK (triggered_by IN ('AI_AGENT','AGENT','SYSTEM')),
    actor_user_id             uuid,
    to_user_id                uuid,
    counts_against_ai_quality boolean      NOT NULL DEFAULT false,
    queued_at                 timestamptz,
    accepted_at               timestamptz,
    occurred_at               timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT fk_handoff_conversation FOREIGN KEY (conversation_id, tenant_id)
        REFERENCES engagement.conversations (id, tenant_id) ON DELETE CASCADE,
    CONSTRAINT fk_handoff_actor FOREIGN KEY (actor_user_id, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    CONSTRAINT fk_handoff_to FOREIGN KEY (to_user_id, tenant_id)
        REFERENCES platform.users (id, tenant_id),
    -- Nhân viên bấm thì phải biết là ai
    CONSTRAINT ck_handoff_actor CHECK (triggered_by <> 'AGENT' OR actor_user_id IS NOT NULL),
    CONSTRAINT ck_handoff_accept CHECK (accepted_at IS NULL OR to_user_id IS NOT NULL)
);

CREATE INDEX ix_handoff_conversation ON engagement.handoff_events (tenant_id, conversation_id, occurred_at DESC);
CREATE INDEX ix_handoff_tenant_time  ON engagement.handoff_events (tenant_id, occurred_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Quyền + RLS — khuôn chuẩn của V112/V113 (V111 không với tới bảng tạo sau nó)
-- ─────────────────────────────────────────────────────────────────────────────
GRANT SELECT, INSERT, UPDATE, DELETE ON platform.user_presence, engagement.handoff_events TO crm_app;

DO $$
DECLARE
    full_name text;
    tbl       text[] := ARRAY['platform.user_presence', 'engagement.handoff_events'];
BEGIN
    FOREACH full_name IN ARRAY tbl LOOP
        EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', full_name);
        EXECUTE format('ALTER TABLE %s FORCE  ROW LEVEL SECURITY', full_name);
        EXECUTE format($f$
            CREATE POLICY tenant_isolation ON %s
                USING      (tenant_id = platform.current_tenant())
                WITH CHECK (tenant_id = platform.current_tenant())
        $f$, full_name);
    END LOOP;
END $$;

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. Hàm cho job quá hạn (UC014 7.1, UC015 6.2)
--
-- Job chạy nền KHÔNG có ngữ cảnh tenant nên RLS chặn mọi dòng. Hàm SECURITY DEFINER này chỉ trả về
-- ID DOANH NGHIỆP đang có việc quá hạn — không trả dữ liệu hội thoại; job đặt tenant rồi mới đọc chi
-- tiết qua RLS như mọi truy vấn khác (mẫu resolve_widget_key, V112).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE FUNCTION engagement.tenants_with_overdue_handoffs(p_minutes int)
RETURNS SETOF uuid
LANGUAGE sql SECURITY DEFINER SET search_path = engagement, pg_temp STABLE
AS $$
    SELECT DISTINCT c.tenant_id
      FROM engagement.conversations c
     WHERE (c.status = 'PENDING_AGENT' AND c.assigned_user_id IS NULL
            AND coalesce(c.handover_at, c.created_at) < now() - make_interval(mins => p_minutes))
        OR (c.status = 'AGENT_HANDLING' AND c.assigned_user_id IS NOT NULL
            AND c.assigned_at < now() - make_interval(mins => p_minutes));
$$;

REVOKE ALL ON FUNCTION engagement.tenants_with_overdue_handoffs(int) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION engagement.tenants_with_overdue_handoffs(int) TO crm_app;
