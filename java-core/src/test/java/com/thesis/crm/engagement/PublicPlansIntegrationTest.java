package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * Bảng giá trên trang chủ công khai đọc {@code GET /api/v1/plans} KHÔNG cần đăng nhập — giá luôn khớp
 * CSDL (trước đây trang chủ ghi tay, lệch hẳn gói thật). Đặt trong gói {@code engagement} để dùng chung
 * nền Postgres thật của {@link EngagementIntegrationTestBase}.
 */
class PublicPlansIntegrationTest extends EngagementIntegrationTestBase {

    @Test
    void khachChuaDangNhap_docDuocBangGia_dungCsdl_khongDanhDauGoiNao() throws Exception {
        JsonNode goi = data(mvc.perform(get("/api/v1/plans")).andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString(StandardCharsets.UTF_8));
        List<String> ma = new ArrayList<>();
        goi.forEach(g -> ma.add(g.get("code").asText()));
        assertThat(ma).containsExactly("TRIAL", "STARTER", "GROWTH", "PRO");
        assertThat(goi.get(1).get("monthlyPriceVnd").decimalValue()).isEqualByComparingTo("490000");
        assertThat(goi.get(3).get("conversationQuota").asInt()).isEqualTo(30000);
        goi.forEach(g -> assertThat(g.get("isCurrent").asBoolean()).isFalse());
    }

    @Test
    void chiMoDungDocBangGia_cacApiKhacVanBatDangNhap() throws Exception {
        mvc.perform(get("/api/v1/subscription")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/subscription/change")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/contacts")).andExpect(status().isUnauthorized());
    }

    @Test
    void daDangNhapVanDocDuoc() throws Exception {
        mvc.perform(get("/api/v1/plans").with(as(TENANT_A))).andExpect(status().isOk());
    }
}
