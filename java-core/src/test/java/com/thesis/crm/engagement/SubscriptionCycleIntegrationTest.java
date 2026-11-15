package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.thesis.crm.platform.scheduler.SubscriptionCycleScheduler;
import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;

/**
 * UC006 — vòng đời chu kỳ thuê bao: job nền mở chu kỳ mới khi hết hạn, và chọn gói sau khi hết hạn thì
 * mở chu kỳ mới thay vì kẹt.
 *
 * <p>Lỗi đã gặp thật (Dev A, 10/11/2026): dùng thử hết hạn → mọi lượt chat nhận 409 "Hãy gia hạn hoặc
 * chọn gói", mà nâng gói chỉ đặt {@code status = ACTIVE} còn {@code period_end} để nguyên nên không cứu
 * được; phải dời ngày bằng SQL tay.
 */
class SubscriptionCycleIntegrationTest extends EngagementIntegrationTestBase {

    @Autowired SubscriptionCycleScheduler scheduler;

    private UUID tenant;
    private UUID admin;

    @BeforeEach
    void doanhNghiepMoi() throws Exception {
        tenant = UUID.randomUUID();
        admin = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, "INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES (?, 'DN chu kỳ', ?, ?)",
                    tenant, "ck-" + tenant.toString().substring(0, 8), "ck@" + tenant.toString().substring(0, 8) + ".vn");
            exec(c, """
                    INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                    VALUES (?, ?, ?, 'x', 'Quản trị', 'ACTIVE')""",
                    admin, tenant, admin.toString().substring(0, 8) + "@ck.vn");
        }
    }

    @Test
    void dungThuHetHan_jobDongLai_khongTuLanThanhMienPhiMaiMai() throws Exception {
        UUID sub = thueBao("TRIAL", "TRIALING", -20, -6, true);
        dungHanMuc(sub, "CONVERSATION", 150);

        assertThat(scheduler.runOnce(Instant.now())).isEqualTo(1);

        assertThat(cot("SELECT status FROM platform.tenant_subscriptions WHERE id = ?", sub)).isEqualTo("EXPIRED");
        assertThat(cot("SELECT count(*) FROM platform.tenant_subscriptions WHERE tenant_id = ?", tenant))
                .isEqualTo("1");      // KHÔNG mở chu kỳ mới cho bản dùng thử
    }

    @Test
    void goiTraPhiHetHan_jobMoChuKyMoi_tieuThuVe0_tonKhoGiuNguyen() throws Exception {
        UUID cu = thueBao("STARTER", "ACTIVE", -40, -10, true);
        dungHanMuc(cu, "CONVERSATION", 1500);     // dòng chảy
        dungHanMuc(cu, "AI_TOKEN", 4_000_000);    // dòng chảy
        dungHanMuc(cu, "DOCUMENT", 7);            // tồn kho

        assertThat(scheduler.runOnce(Instant.now())).isEqualTo(1);

        assertThat(cot("SELECT status FROM platform.tenant_subscriptions WHERE id = ?", cu)).isEqualTo("EXPIRED");
        UUID moi = UUID.fromString(cot(
                "SELECT id::text FROM platform.tenant_subscriptions WHERE tenant_id = ? AND status = 'ACTIVE'", tenant));
        assertThat(dung(moi, "CONVERSATION")).isEqualTo(0);       // tiêu thụ về 0
        assertThat(dung(moi, "AI_TOKEN")).isEqualTo(0);
        assertThat(dung(moi, "DOCUMENT")).isEqualTo(7);           // tài liệu không biến mất khi sang tháng
        assertThat(tran(moi, "CONVERSATION")).isEqualTo(2000);    // hạn mức chụp lại từ gói STARTER
        // Chu kỳ mới chưa chạm gì — hai mốc của V128 phải trống
        assertThat(cot("SELECT warned_at FROM platform.usage_records WHERE subscription_id = ? AND metric = 'CONVERSATION'",
                moi)).isNull();
    }

    @Test
    void lanBuNhieuThang_chuKyHienHanhPhuHomNay() throws Exception {
        thueBao("STARTER", "ACTIVE", -200, -170, true);

        scheduler.runOnce(Instant.now());

        assertThat(cot("""
                SELECT count(*) FROM platform.tenant_subscriptions
                 WHERE tenant_id = ? AND status = 'ACTIVE' AND period_end > now()""", tenant)).isEqualTo("1");
    }

    @Test
    void lichHaGoiDuocApKhiSangChuKyMoi() throws Exception {
        UUID cu = thueBao("GROWTH", "ACTIVE", -40, -10, true);
        try (Connection c = owner()) {
            exec(c, """
                    UPDATE platform.tenant_subscriptions
                       SET scheduled_plan_id = (SELECT id FROM platform.subscription_plans WHERE code = 'STARTER'),
                           scheduled_effective_at = period_end
                     WHERE id = ?""", cu);
        }

        scheduler.runOnce(Instant.now());

        assertThat(cot("""
                SELECT p.code FROM platform.tenant_subscriptions s
                  JOIN platform.subscription_plans p ON p.id = s.plan_id
                 WHERE s.tenant_id = ? AND s.status = 'ACTIVE'""", tenant)).isEqualTo("STARTER");
    }

    @Test
    void tatTuGiaHan_khongMoChuKyMoi() throws Exception {
        UUID cu = thueBao("STARTER", "ACTIVE", -40, -10, false);

        scheduler.runOnce(Instant.now());

        assertThat(cot("SELECT status FROM platform.tenant_subscriptions WHERE id = ?", cu)).isEqualTo("EXPIRED");
        assertThat(cot("SELECT count(*) FROM platform.tenant_subscriptions WHERE tenant_id = ?", tenant)).isEqualTo("1");
    }

    @Test
    void chonGoiSauKhiHetHan_moChuKyMoi_dungDuocNgay() throws Exception {
        UUID cu = thueBao("TRIAL", "TRIALING", -20, -6, true);

        JsonNode d = doiGoi("STARTER");

        assertThat(d.get("plan").get("code").asText()).isEqualTo("STARTER");
        assertThat(d.get("status").asText()).isEqualTo("ACTIVE");
        assertThat(cot("SELECT status FROM platform.tenant_subscriptions WHERE id = ?", cu)).isEqualTo("EXPIRED");
        // Chu kỳ mới phủ hiện tại — đây là điều kiện để lockForConsumption thôi trả 409
        assertThat(cot("""
                SELECT count(*) FROM platform.tenant_subscriptions
                 WHERE tenant_id = ? AND status = 'ACTIVE' AND period_start <= now() AND period_end > now()""",
                tenant)).isEqualTo("1");
        JsonNode hm = hanMuc();
        assertThat(hm.get("conversations").get("quota").asLong()).isEqualTo(2000);
        assertThat(hm.get("conversations").get("used").asLong()).isZero();
    }

    @Test
    void chuKyConHan_doiGoiVanDiDuongCu_khongMoChuKyThua() throws Exception {
        thueBao("STARTER", "ACTIVE", -5, 25, true);

        doiGoi("GROWTH");

        assertThat(cot("SELECT count(*) FROM platform.tenant_subscriptions WHERE tenant_id = ?", tenant))
                .isEqualTo("1");
        assertThat(cot("""
                SELECT p.code FROM platform.tenant_subscriptions s
                  JOIN platform.subscription_plans p ON p.id = s.plan_id WHERE s.tenant_id = ?""", tenant))
                .isEqualTo("GROWTH");
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private JsonNode doiGoi(String ma) throws Exception {
        String body = mvc.perform(post("/api/v1/subscription/change").with(asUser(tenant, admin, "TENANT_ADMIN"))
                        .contentType(MediaType.APPLICATION_JSON).content("{\"planCode\":\"" + ma + "\"}"))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8);
        return data(body);
    }

    private JsonNode hanMuc() throws Exception {
        return data(mvc.perform(get("/api/v1/usage").with(asUser(tenant, admin, "TENANT_ADMIN")))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
    }

    /** Một chu kỳ với mốc bắt đầu/kết thúc lệch so với bây giờ, kèm bộ usage_records chụp từ gói. */
    private UUID thueBao(String maGoi, String trangThai, int batDauNgay, int ketThucNgay, boolean tuGiaHan)
            throws Exception {
        UUID id = UUID.randomUUID();
        try (Connection c = owner()) {
            exec(c, """
                    INSERT INTO platform.tenant_subscriptions (id, tenant_id, plan_id, status, period_start,
                                                               period_end, auto_renew)
                    SELECT ?, ?, id, ?, now() + make_interval(days => ?), now() + make_interval(days => ?), ?
                      FROM platform.subscription_plans WHERE code = ?""",
                    id, tenant, trangThai, batDauNgay, ketThucNgay, tuGiaHan, maGoi);
            exec(c, """
                    INSERT INTO platform.usage_records (tenant_id, subscription_id, metric, used_value, quota_value)
                    SELECT ?, ?, m.metric,
                           0,
                           CASE m.metric WHEN 'CONVERSATION' THEN p.conversation_quota
                                         WHEN 'AI_TOKEN'     THEN p.ai_token_quota
                                         WHEN 'DOCUMENT'     THEN p.max_documents
                                         WHEN 'USER'         THEN p.max_users
                                         ELSE p.storage_mb * 1024 * 1024 END
                      FROM platform.subscription_plans p,
                           (VALUES ('CONVERSATION'),('AI_TOKEN'),('DOCUMENT'),('USER'),('STORAGE_MB')) AS m(metric)
                     WHERE p.code = ?""", tenant, id, maGoi);
        }
        return id;
    }

    private void dungHanMuc(UUID sub, String chiSo, long luong) throws Exception {
        try (Connection c = owner()) {
            exec(c, "UPDATE platform.usage_records SET used_value = ? WHERE subscription_id = ? AND metric = ?",
                    luong, sub, chiSo);
        }
    }

    private long dung(UUID sub, String chiSo) throws Exception {
        return Long.parseLong(cot("SELECT used_value FROM platform.usage_records "
                + "WHERE subscription_id = ? AND metric = ?", sub, chiSo));
    }

    private long tran(UUID sub, String chiSo) throws Exception {
        return Long.parseLong(cot("SELECT quota_value FROM platform.usage_records "
                + "WHERE subscription_id = ? AND metric = ?", sub, chiSo));
    }

    private static String cot(String query, Object... args) throws Exception {
        try (Connection c = owner(); PreparedStatement ps = c.prepareStatement(query)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            try (ResultSet rs = ps.executeQuery()) {
                return rs.next() ? rs.getString(1) : null;
            }
        }
    }

    private static void exec(Connection c, String query, Object... args) throws SQLException {
        try (PreparedStatement ps = c.prepareStatement(query)) {
            for (int i = 0; i < args.length; i++) {
                ps.setObject(i + 1, args[i]);
            }
            ps.executeUpdate();
        }
    }
}
