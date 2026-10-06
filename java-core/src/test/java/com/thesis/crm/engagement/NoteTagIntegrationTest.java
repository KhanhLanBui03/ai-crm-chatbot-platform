package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.thesis.crm.engagement.util.TagColors;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.JwtRequestPostProcessor;
import org.springframework.test.web.servlet.ResultActions;

/** UC017 — ghi chú và gắn thẻ, trên Postgres thật (xem {@link EngagementIntegrationTestBase}). */
class NoteTagIntegrationTest extends EngagementIntegrationTestBase {

    // ══ GHI CHÚ ═══════════════════════════════════════════════════════════════

    @Test
    void themGhiChuTraVeTacGiaVaQuyen() throws Exception {
        String c = contact("ghi.chu.co.ban");
        JsonNode n = noteCreated(c, as(TENANT_A), "Khách hẹn gọi lại thứ Hai");
        assertThat(n.get("authorName").asText()).isEqualTo("Quản trị A");
        assertThat(n.get("authorUserId").asText()).isEqualTo(USER_A.toString());
        assertThat(n.get("canEdit").asBoolean()).isTrue();
        assertThat(n.get("isPinned").asBoolean()).isFalse();
        assertThat(n.get("editedAt").isNull()).isTrue();
        assertThat(n.get("flaggedSensitive").asBoolean()).isFalse();
    }

    @Test
    void nhacDuLieuNhayCamNhungKhongChan() throws Exception {
        String c = contact("nhay.cam");
        for (String content : new String[] {
                "Khách cho số 0912 345 678 để gọi", "CCCD của khách 001200001234",
                "Gửi hợp đồng qua an.nguyen@khach.vn", "Thẻ 4111 1111 1111 1111", "STK Vietcombank 0123456789"}) {
            assertThat(noteCreated(c, as(TENANT_A), content).get("flaggedSensitive").asBoolean()).as(content).isTrue();
        }
        for (String content : new String[] {"Mã đơn 123456789, giá 150000000 đồng", "Khách thích gói Pro"}) {
            assertThat(noteCreated(c, as(TENANT_A), content).get("flaggedSensitive").asBoolean()).as(content).isFalse();
        }
    }

    @Test
    void ghiChuRongHoacQuaDaiBiTuChoi() throws Exception {
        String c = contact("rong.dai");
        addNote(c, as(TENANT_A), "{\"content\":\"   \"}").andExpect(status().isUnprocessableEntity());
        addNote(c, as(TENANT_A), "{\"content\":\"" + "a".repeat(4001) + "\"}").andExpect(status().isUnprocessableEntity());
    }

    @Test
    void ghimLenDauVaGhimKhongTinhLaDaSua() throws Exception {
        String c = contact("thu.tu.ghim");
        String cu = noteCreated(c, as(TENANT_A), "Ghi chú cũ").get("id").asText();
        noteCreated(c, as(TENANT_A), "Ghi chú mới");

        JsonNode pinned = data(patchNote(c, cu, as(TENANT_A), "{\"isPinned\":true}")
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8));
        assertThat(pinned.get("isPinned").asBoolean()).isTrue();
        assertThat(pinned.get("editedAt").isNull()).as("ghim KHÔNG phải sửa nội dung").isTrue();

        JsonNode list = notes(c, as(TENANT_A));
        assertThat(list.findValuesAsText("content")).containsExactly("Ghi chú cũ", "Ghi chú mới");

        JsonNode edited = data(patchNote(c, cu, as(TENANT_A), "{\"content\":\"Ghi chú cũ (bổ sung)\"}")
                .andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8));
        assertThat(edited.get("content").asText()).isEqualTo("Ghi chú cũ (bổ sung)");
        assertThat(edited.get("editedAt").isNull()).isFalse();
    }

    @Test
    void chiTacGiaHoacQuanTriSuaXoaDuoc() throws Exception {
        String c = contact("quyen.sua");
        JwtRequestPostProcessor agent = asUser(TENANT_A, AGENT_A, "AGENT");
        String ofAdmin = noteCreated(c, as(TENANT_A), "Của quản trị").get("id").asText();
        String ofAgent = noteCreated(c, agent, "Của nhân viên").get("id").asText();

        // Nhân viên không sửa/xoá được ghi chú của người khác, và giao diện không hiện nút
        JsonNode seenByAgent = notes(c, agent);
        assertThat(canEditOf(seenByAgent, ofAdmin)).isFalse();
        assertThat(canEditOf(seenByAgent, ofAgent)).isTrue();
        patchNote(c, ofAdmin, agent, "{\"content\":\"sửa trộm\"}").andExpect(status().isForbidden());
        mvc.perform(delete(notePath(c, ofAdmin)).with(agent)).andExpect(status().isForbidden());

        // Quản trị viên sửa được ghi chú của nhân viên
        patchNote(c, ofAgent, as(TENANT_A), "{\"isPinned\":true}").andExpect(status().isOk());
    }

    @Test
    void xoaMemKhongHienNhungVanConTrongCsdl() throws Exception {
        String c = contact("xoa.mem");
        String id = noteCreated(c, as(TENANT_A), "Sẽ bị xoá").get("id").asText();
        mvc.perform(delete(notePath(c, id)).with(as(TENANT_A))).andExpect(status().isOk());

        assertThat(notes(c, as(TENANT_A)).findValuesAsText("id")).doesNotContain(id);
        try (Connection db = owner(); PreparedStatement ps = db.prepareStatement(
                "SELECT deleted_at IS NOT NULL FROM engagement.contact_notes WHERE id = ?")) {
            ps.setObject(1, UUID.fromString(id));
            try (ResultSet rs = ps.executeQuery()) {
                assertThat(rs.next() && rs.getBoolean(1)).as("dòng còn, có deleted_at").isTrue();
            }
        }
        mvc.perform(delete(notePath(c, id)).with(as(TENANT_A))).andExpect(status().isNotFound());
    }

    @Test
    void hoiThoaiKhongThuocKhachThiBaoLoi() throws Exception {
        String c = contact("hoi.thoai.la");
        addNote(c, as(TENANT_A), "{\"content\":\"x\",\"conversationId\":\"" + UUID.randomUUID() + "\"}")
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.message").value("Hội thoại không thuộc khách hàng này."));
    }

    @Test
    void suaXoaGhiNhatKyKhongChepNoiDung() throws Exception {
        String c = contact("kiem.toan.ghi.chu");
        String id = noteCreated(c, as(TENANT_A), "Nội dung bí mật 0912345678").get("id").asText();
        patchNote(c, id, as(TENANT_A), "{\"content\":\"Nội dung mới bí mật\"}").andExpect(status().isOk());
        mvc.perform(delete(notePath(c, id)).with(as(TENANT_A))).andExpect(status().isOk());

        try (Connection db = owner(); PreparedStatement ps = db.prepareStatement("""
                SELECT action, after_data::text FROM platform.audit_logs
                WHERE entity_type = 'CONTACT_NOTE' AND entity_id = ? ORDER BY id""")) {
            ps.setObject(1, UUID.fromString(id));
            try (ResultSet rs = ps.executeQuery()) {
                assertThat(rs.next()).isTrue();
                assertThat(rs.getString(1)).isEqualTo("NOTE_UPDATED");
                assertThat(rs.getString(2)).doesNotContain("bí mật").doesNotContain("0912345678");
                assertThat(rs.next()).isTrue();
                assertThat(rs.getString(1)).isEqualTo("NOTE_DELETED");
            }
        }
    }

    // ══ THẺ ═══════════════════════════════════════════════════════════════════

    @Test
    void taoTheTrungTenKhacDauTraTheCu() throws Exception {
        JsonNode created = data(createTag(as(TENANT_A), "{\"name\":\"Khách quen\"}")
                .andExpect(status().isCreated()).andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8));
        assertThat(created.get("color").asText()).isEqualTo(TagColors.forName("Khách quen"));

        for (String same : new String[] {"khach quen", "KHÁCH QUEN", "  Khách Quen  "}) {
            JsonNode again = data(createTag(as(TENANT_A), "{\"name\":\"" + same + "\"}")
                    .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8));
            assertThat(again.get("id").asText()).as(same).isEqualTo(created.get("id").asText());
        }
    }

    @Test
    void theSaiDinhDangBiTuChoi() throws Exception {
        createTag(as(TENANT_A), "{\"name\":\"" + "x".repeat(51) + "\"}").andExpect(status().isUnprocessableEntity());
        createTag(as(TENANT_A), "{\"name\":\"Màu sai\",\"color\":\"#12345678\"}").andExpect(status().isUnprocessableEntity());
        createTag(as(TENANT_A), "{\"name\":\"   \"}").andExpect(status().isUnprocessableEntity());
    }

    @Test
    void ganGoTheVaDemSoLanDung() throws Exception {
        String c = contact("gan.the");
        String tag = tagId(TENANT_A, "Đếm lượt");

        mvc.perform(put(tagPath(c, tag)).with(as(TENANT_A))).andExpect(status().isOk());
        mvc.perform(put(tagPath(c, tag)).with(as(TENANT_A))).andExpect(status().isOk()); // gắn lại: không lỗi
        assertThat(usage(TENANT_A, tag)).isEqualTo(1);
        assertThat(contactTags(c)).contains("Đếm lượt");

        mvc.perform(delete(tagPath(c, tag)).with(as(TENANT_A))).andExpect(status().isOk());
        mvc.perform(delete(tagPath(c, tag)).with(as(TENANT_A))).andExpect(status().isOk()); // gỡ lại: không lỗi
        assertThat(usage(TENANT_A, tag)).isZero();
        assertThat(contactTags(c)).doesNotContain("Đếm lượt");
    }

    @Test
    void ganTheVaoKhachDaGopBiChan() throws Exception {
        String keep = contact("gop.giu");
        String merged = contact("gop.mat");
        try (Connection db = owner(); PreparedStatement ps = db.prepareStatement(
                "UPDATE engagement.contacts SET status='MERGED', merged_into_contact_id=? WHERE id=?")) {
            ps.setObject(1, UUID.fromString(keep));
            ps.setObject(2, UUID.fromString(merged));
            ps.executeUpdate();
        }
        mvc.perform(put(tagPath(merged, tagId(TENANT_A, "Gộp"))).with(as(TENANT_A))).andExpect(status().isConflict());
        addNote(merged, as(TENANT_A), "{\"content\":\"x\"}").andExpect(status().isConflict());
        notesRaw(merged, as(TENANT_A)).andExpect(status().isOk()); // xem vẫn được
    }

    @Test
    void hanMucTheTheoGoi() throws Exception {
        // Doanh nghiệp riêng, KHÔNG có thuê bao → tính như gói TRIAL (20 thẻ theo V115)
        UUID tenant = UUID.randomUUID();
        UUID admin = UUID.randomUUID();
        try (Connection db = owner()) {
            try (PreparedStatement ps = db.prepareStatement(
                    "INSERT INTO platform.tenants (id, name, slug, contact_email) VALUES (?, 'DN hạn mức', ?, 'hm@dn.vn')")) {
                ps.setObject(1, tenant);
                ps.setString(2, "hm-" + tenant.toString().substring(0, 8));
                ps.executeUpdate();
            }
            try (PreparedStatement ps = db.prepareStatement("""
                    INSERT INTO platform.users (id, tenant_id, email, password_hash, full_name, status)
                    VALUES (?, ?, ?, 'x', 'QT hạn mức', 'ACTIVE')""")) {
                ps.setObject(1, admin);
                ps.setObject(2, tenant);
                ps.setString(3, "hm-" + admin.toString().substring(0, 8) + "@dn.vn");
                ps.executeUpdate();
            }
        }
        JwtRequestPostProcessor who = asUser(tenant, admin, "TENANT_ADMIN");
        for (int i = 1; i <= 20; i++) {
            createTag(who, "{\"name\":\"Thẻ số " + i + "\"}").andExpect(status().isCreated());
        }
        createTag(who, "{\"name\":\"Thẻ thứ 21\"}").andExpect(status().isConflict());
        createTag(who, "{\"name\":\"thẻ số 1\"}").andExpect(status().isOk()); // trùng thẻ cũ: vẫn trả về được
    }

    @Test
    void doanhNghiepKhacKhongThayKhongDungDuocThe() throws Exception {
        String tagOfA = tagId(TENANT_A, "Riêng của A");
        String contactOfB = createdContactId(TENANT_B, "{\"fullName\":\"Khách B\",\"email\":\"the.b@khach.vn\"}");

        String res = mvc.perform(get("/api/v1/tags").with(as(TENANT_B)))
                .andExpect(status().isOk()).andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8);
        assertThat(data(res).findValuesAsText("id")).doesNotContain(tagOfA);
        mvc.perform(put(tagPath(contactOfB, tagOfA)).with(as(TENANT_B))).andExpect(status().isNotFound());
        notesRaw(contact("rieng.cua.a"), as(TENANT_B)).andExpect(status().isNotFound());
    }

    @Test
    void taoVaGanTheGhiNhatKy() throws Exception {
        String c = contact("kiem.toan.the");
        String tag = tagId(TENANT_A, "Kiểm toán thẻ");
        mvc.perform(put(tagPath(c, tag)).with(as(TENANT_A))).andExpect(status().isOk());
        try (Connection db = owner(); PreparedStatement ps = db.prepareStatement("""
                SELECT count(*) FILTER (WHERE action = 'TAG_CREATED' AND entity_id = ?),
                       count(*) FILTER (WHERE action = 'CONTACT_TAGGED' AND entity_id = ?)
                FROM platform.audit_logs""")) {
            ps.setObject(1, UUID.fromString(tag));
            ps.setObject(2, UUID.fromString(c));
            try (ResultSet rs = ps.executeQuery()) {
                rs.next();
                assertThat(rs.getInt(1)).isEqualTo(1);
                assertThat(rs.getInt(2)).isEqualTo(1);
            }
        }
    }

    // ── tiện ích ────────────────────────────────────────────────────────────────

    private String contact(String key) throws Exception {
        return createdContactId(TENANT_A, "{\"fullName\":\"Khách " + key + "\",\"email\":\"" + key + "@uc17.vn\"}");
    }

    private static String notePath(String contactId, String noteId) {
        return "/api/v1/contacts/" + contactId + "/notes/" + noteId;
    }

    private static String tagPath(String contactId, String tagId) {
        return "/api/v1/contacts/" + contactId + "/tags/" + tagId;
    }

    private ResultActions addNote(String contactId, JwtRequestPostProcessor who, String body) throws Exception {
        return mvc.perform(post("/api/v1/contacts/" + contactId + "/notes").with(who)
                .contentType(MediaType.APPLICATION_JSON).content(body));
    }

    private JsonNode noteCreated(String contactId, JwtRequestPostProcessor who, String content) throws Exception {
        String body = json.writeValueAsString(java.util.Map.of("content", content));
        return data(addNote(contactId, who, body).andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8));
    }

    private ResultActions patchNote(String c, String id, JwtRequestPostProcessor who, String body) throws Exception {
        return mvc.perform(patch(notePath(c, id)).with(who).contentType(MediaType.APPLICATION_JSON).content(body));
    }

    private ResultActions notesRaw(String contactId, JwtRequestPostProcessor who) throws Exception {
        return mvc.perform(get("/api/v1/contacts/" + contactId + "/notes").with(who));
    }

    private JsonNode notes(String contactId, JwtRequestPostProcessor who) throws Exception {
        return data(notesRaw(contactId, who).andExpect(status().isOk()).andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8));
    }

    private static boolean canEditOf(JsonNode list, String noteId) {
        for (JsonNode n : list) {
            if (n.get("id").asText().equals(noteId)) {
                return n.get("canEdit").asBoolean();
            }
        }
        throw new AssertionError("không thấy ghi chú " + noteId);
    }

    private ResultActions createTag(JwtRequestPostProcessor who, String body) throws Exception {
        return mvc.perform(post("/api/v1/tags").with(who).contentType(MediaType.APPLICATION_JSON).content(body));
    }

    private String tagId(UUID tenant, String name) throws Exception {
        return data(createTag(as(tenant), "{\"name\":\"" + name + "\"}")
                .andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8)).get("id").asText();
    }

    private int usage(UUID tenant, String tagId) throws Exception {
        String res = mvc.perform(get("/api/v1/tags").with(as(tenant))).andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8);
        for (JsonNode t : data(res)) {
            if (t.get("id").asText().equals(tagId)) {
                return t.get("usageCount").asInt();
            }
        }
        throw new AssertionError("không thấy thẻ " + tagId);
    }

    private java.util.List<String> contactTags(String contactId) throws Exception {
        String res = mvc.perform(get("/api/v1/contacts/" + contactId).with(as(TENANT_A)))
                .andReturn().getResponse().getContentAsString(java.nio.charset.StandardCharsets.UTF_8);
        return data(res).get("tags").findValuesAsText("name");
    }
}
