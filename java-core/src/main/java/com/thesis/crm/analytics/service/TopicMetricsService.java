package com.thesis.crm.analytics.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.thesis.crm.analytics.entity.TopicConversation;
import com.thesis.crm.analytics.entity.TopicConversation.KetQua;
import com.thesis.crm.analytics.entity.TopicConversation.Key;
import jakarta.persistence.EntityManager;
import jakarta.persistence.LockModeType;
import java.time.Instant;
import java.time.LocalDate;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC038 lớp 1 — cộng MỘT lượt vào {@code analytics.topic_conversations} theo ý định router.
 *
 * <p>Gọi từ {@link TurnMetricsService#ghiNhan} SAU bước chống trùng, trong CÙNG transaction: sự kiện giao
 * lại đã bị chặn ở đó nên ở đây không cần chống trùng lần nữa.
 */
@Service
public class TopicMetricsService {

    /** Nhãn hiển thị của 7 ý định UC022 — chụp vào {@code topic_label} lúc ghi. */
    public static final Map<String, String> NHAN_Y_DINH = Map.of(
            "GREETING", "Chào hỏi",
            "KB_SEARCH", "Tra cứu thông tin",
            "PRICING_POLICY", "Giá và chính sách",
            "COMPLAINT_SUPPORT", "Khiếu nại, cần hỗ trợ",
            "TECH_ERROR", "Lỗi kỹ thuật",
            "HANDOFF_HUMAN", "Muốn gặp nhân viên",
            "BUYING_INTENT", "Ý định mua hàng");

    private final EntityManager em;

    public TopicMetricsService(EntityManager em) {
        this.em = em;
    }

    /**
     * @return {@code false} nếu lượt không mang ý định hợp lệ hoặc không thuộc hội thoại nào — bỏ qua phần
     *     chủ đề, phần UC039 vẫn được cộng bình thường
     */
    @Transactional(propagation = Propagation.MANDATORY)
    public boolean congTheoYDinh(UUID tenantId, LocalDate ngay, JsonNode p, Instant luc) {
        String yDinh = p.path("intent").asText(null);
        UUID hoiThoai = uuid(p.path("conversation_id").asText(null));
        if (yDinh == null || !NHAN_Y_DINH.containsKey(yDinh) || hoiThoai == null || !coHoiThoai(tenantId, hoiThoai)) {
            return false;
        }
        Key k = new Key(tenantId, TopicConversation.INTENT, yDinh, ngay, hoiThoai);
        // Khoá dòng: hai lượt cùng hội thoại tới gần nhau vẫn cộng tuần tự (cùng phân vùng Kafka thì vốn đã
        // tuần tự — khoá ở đây để đúng cả khi có người chạy lại tay)
        TopicConversation dong = em.find(TopicConversation.class, k, LockModeType.PESSIMISTIC_WRITE);
        if (dong == null) {
            dong = new TopicConversation(k, NHAN_Y_DINH.get(yDinh), luc);
            em.persist(dong);
        }
        dong.cong(phanLoai(p), luc);
        return true;
    }

    /**
     * Từ chối = lượt chạy XONG mà tác tử không trả lời được và không đưa cho người. Ba trường hợp không tính:
     * chuyển giao (đưa cho người là đúng việc), hỏi lại (CLARIFY — chưa hiểu câu, không phải thiếu tài liệu)
     * và lỗi hệ thống (status ≠ SUCCESS — lỗi hạ tầng, không phải lỗ hổng tri thức).
     */
    static KetQua phanLoai(JsonNode p) {
        if (p.path("is_answered").asBoolean(false)) {
            return KetQua.TRA_LOI;
        }
        if (p.path("is_handoff").asBoolean(false)) {
            return KetQua.CHUYEN_GIAO;
        }
        if (!"SUCCESS".equals(p.path("status").asText("SUCCESS")) || "CLARIFY".equals(p.path("branch").asText())) {
            return KetQua.KHAC;
        }
        return KetQua.TU_CHOI;
    }

    /**
     * Khoá ngoại tới hội thoại: lượt của hội thoại không có ở CRM (đã xoá theo UC041, hoặc lượt thử từ công cụ
     * nội bộ) thì bỏ phần chủ đề — để INSERT vấp khoá ngoại sẽ kéo hỏng luôn phần số liệu UC039 cùng giao dịch.
     */
    private boolean coHoiThoai(UUID tenantId, UUID id) {
        return em.createQuery("SELECT count(c) FROM Conversation c WHERE c.tenantId = :t AND c.id = :id", Long.class)
                .setParameter("t", tenantId)
                .setParameter("id", id)
                .getSingleResult() > 0;
    }

    private static UUID uuid(String s) {
        try {
            return s == null ? null : UUID.fromString(s);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
