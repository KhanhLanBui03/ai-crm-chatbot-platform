package com.thesis.crm.engagement.widget;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.engagement.widget.AiChatClient.AiReply;
import com.thesis.crm.engagement.widget.AiChatClient.Turn;
import com.thesis.crm.security.TenantTransactionScope;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC009 phía quản trị viên (SCR018): sinh mã nhúng, xem/lưu cấu hình, lấy thẻ script, và khung
 * THỬ chatbot ngay trên trang cấu hình.
 *
 * <p>Cấu hình nằm trong {@code engagement.channels.config} của kênh {@code WEB_WIDGET} — CSDL không
 * có bảng {@code widget_configs} như hợp đồng cũ mô tả. Mỗi doanh nghiệp một widget.
 */
@Service
public class WidgetConfigService {

    public record WidgetConfig(String publicKey, String primaryColor, String position, String greetingMessage,
                               String avatarUrl, List<String> allowedDomains, boolean isActive) {}

    public record SaveRequest(String primaryColor, String position, String greetingMessage, String avatarUrl,
                              List<String> allowedDomains, Boolean isActive) {}

    public record Snippet(String publicKey, String snippet) {}

    public record TestTurn(String role, String content) {}

    public record TestReply(String answer, List<WidgetDtos.CitationDto> citations, boolean handoff,
                            boolean refused) {}

    private static final Pattern HEX = Pattern.compile("^#[0-9A-Fa-f]{6}$");
    private static final Pattern DOMAIN = Pattern.compile("^(\\*\\.)?[a-z0-9]([a-z0-9-]*[a-z0-9])?(\\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$");
    private static final int MAX_DOMAINS = 20;
    private static final int MAX_GREETING = 300;
    private static final SecureRandom RANDOM = new SecureRandom();

    private final NamedParameterJdbcTemplate jdbc;
    private final TenantTransactionScope scope;
    private final AuditLogWriter audit;
    private final AiChatClient ai;
    private final ObjectMapper json;
    private final String scriptUrl;
    private final String publicApiUrl;

    public WidgetConfigService(NamedParameterJdbcTemplate jdbc, TenantTransactionScope scope, AuditLogWriter audit,
                               AiChatClient ai, ObjectMapper json,
                               @Value("${widget.script-url}") String scriptUrl,
                               @Value("${widget.public-api-url}") String publicApiUrl) {
        this.jdbc = jdbc;
        this.scope = scope;
        this.audit = audit;
        this.ai = ai;
        this.json = json;
        this.scriptUrl = scriptUrl;
        this.publicApiUrl = publicApiUrl;
    }

    private record Row(UUID id, String key, String status, String config) {}

    @Transactional(readOnly = true)
    public WidgetConfig get(UUID tenantId) {
        scope.apply(tenantId);
        return toDto(require(tenantId));
    }

    /** UC009 bước 6–7: sinh khoá công khai + kênh WEB_WIDGET. */
    @Transactional
    public WidgetConfig create(UUID tenantId, UUID actorUserId) {
        scope.apply(tenantId);
        if (find(tenantId).isPresent()) {
            throw new AppException("Doanh nghiệp đã có widget — mỗi doanh nghiệp một mã nhúng.", HttpStatus.CONFLICT);
        }
        String key = newKey();
        ObjectNode config = json.createObjectNode();
        config.put("primaryColor", "#4F46E5");
        config.put("position", "BOTTOM_RIGHT");
        config.put("greetingMessage", "Xin chào! Mình có thể giúp gì cho bạn?");
        config.putNull("avatarUrl");
        config.putArray("allowedDomains");
        UUID id;
        try {
            id = jdbc.queryForObject("""
                    INSERT INTO engagement.channels (tenant_id, type, name, widget_key, status, config, created_by)
                    VALUES (:t, 'WEB_WIDGET', 'Web Widget', :k, 'ACTIVE', CAST(:c AS jsonb), :u) RETURNING id
                    """,
                    new MapSqlParameterSource("t", tenantId).addValue("k", key).addValue("c", config.toString())
                            .addValue("u", actorUserId), UUID.class);
        } catch (DuplicateKeyException e) {
            // Hai quản trị viên bấm cùng lúc — người đến sau thua ở uq_channels_one_widget (V127)
            throw new AppException("Doanh nghiệp đã có widget — mỗi doanh nghiệp một mã nhúng.", HttpStatus.CONFLICT);
        }
        audit.recordUserAction(tenantId, actorUserId, "WIDGET_CREATED", "CHANNEL", id, Map.of("type", "WEB_WIDGET"));
        return toDto(require(tenantId));
    }

    /** Đổi có hiệu lực ngay trên mọi trang đã nhúng — widget đọc cấu hình động (UC009 4a). */
    @Transactional
    public WidgetConfig save(UUID tenantId, UUID actorUserId, SaveRequest req) {
        scope.apply(tenantId);
        Row row = require(tenantId);
        ObjectNode config = (ObjectNode) readJson(row.config());

        if (req.primaryColor() != null) {
            if (!HEX.matcher(req.primaryColor()).matches()) {
                throw invalid("Màu chủ đạo phải có dạng #RRGGBB.");
            }
            config.put("primaryColor", req.primaryColor().toUpperCase());
        }
        if (req.position() != null) {
            if (!List.of("BOTTOM_RIGHT", "BOTTOM_LEFT").contains(req.position())) {
                throw invalid("Vị trí chỉ nhận BOTTOM_RIGHT hoặc BOTTOM_LEFT.");
            }
            config.put("position", req.position());
        }
        if (req.greetingMessage() != null) {
            String g = req.greetingMessage().strip();
            if (g.length() > MAX_GREETING) {
                throw invalid("Lời chào tối đa " + MAX_GREETING + " ký tự.");
            }
            config.put("greetingMessage", g.isEmpty() ? null : g);
        }
        if (req.avatarUrl() != null) {
            String a = req.avatarUrl().strip();
            if (!a.isEmpty() && !a.startsWith("https://")) {
                throw invalid("Ảnh đại diện phải là địa chỉ https://.");
            }
            config.put("avatarUrl", a.isEmpty() ? null : a);
        }
        List<String> domains = null;
        if (req.allowedDomains() != null) {
            domains = normalizeDomains(req.allowedDomains());
            config.set("allowedDomains", json.valueToTree(domains));
        }
        String status = row.status();
        if (req.isActive() != null) {
            status = req.isActive() ? "ACTIVE" : "DISCONNECTED";
        }
        jdbc.update("""
                UPDATE engagement.channels SET config = CAST(:c AS jsonb), status = :s, updated_at = now()
                WHERE tenant_id = :t AND id = :id
                """,
                new MapSqlParameterSource("t", tenantId).addValue("id", row.id()).addValue("c", config.toString())
                        .addValue("s", status));
        // Không chép lời chào / tên miền vào nhật ký — chỉ ghi điều cần chứng minh
        audit.recordUserAction(tenantId, actorUserId, "WIDGET_CONFIG_UPDATED", "CHANNEL", row.id(), Map.of(
                "domainCount", domains == null ? -1 : domains.size(),
                "isActive", "ACTIVE".equals(status)));
        return toDto(require(tenantId));
    }

    @Transactional(readOnly = true)
    public Snippet snippet(UUID tenantId) {
        scope.apply(tenantId);
        Row row = require(tenantId);
        return new Snippet(row.key(), "<script src=\"" + scriptUrl + "\" data-widget-key=\"" + row.key()
                + "\" data-api-url=\"" + publicApiUrl + "\" async></script>");
    }

    /**
     * Khung thử chatbot (kiểu khung test của Copilot Studio): gọi AI THẬT nhưng KHÔNG ghi gì vào CSDL —
     * không hội thoại, không hồ sơ khách, không tính hạn mức. Lịch sử thử do trình duyệt giữ và gửi lại.
     */
    public TestReply testChat(UUID tenantId, String message, List<TestTurn> history, String traceId) {
        String m = message == null ? "" : message.strip();
        if (m.isEmpty() || m.length() > WidgetService.MAX_CONTENT) {
            throw invalid("Tin thử phải có từ 1 đến 1.000 ký tự.");
        }
        List<Turn> turns = new ArrayList<>();
        if (history != null) {
            history.stream().skip(Math.max(0, history.size() - 10))
                    .filter(t -> t.content() != null && ("user".equals(t.role()) || "assistant".equals(t.role())))
                    .forEach(t -> turns.add(new Turn(t.role(), t.content())));
        }
        AiReply r = ai.chat(tenantId, UUID.randomUUID(), m, turns, traceId)
                .orElseThrow(() -> new AppException(
                        "Trợ lý AI chưa phản hồi được (dịch vụ AI không chạy hoặc quá giờ chờ). Trên website thật, "
                                + "khách sẽ được chuyển cho nhân viên.", HttpStatus.SERVICE_UNAVAILABLE));
        return new TestReply(r.answer(), r.citations().stream()
                .map(c -> new WidgetDtos.CitationDto(c.documentId(), c.title(), c.snippet())).toList(),
                r.handoff(), r.refused());
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    private Optional<Row> find(UUID tenantId) {
        return jdbc.query("""
                SELECT id, widget_key, status, config::text AS config FROM engagement.channels
                WHERE tenant_id = :t AND type = 'WEB_WIDGET' ORDER BY created_at LIMIT 1
                """,
                new MapSqlParameterSource("t", tenantId),
                (rs, i) -> new Row(rs.getObject("id", UUID.class), rs.getString("widget_key"),
                        rs.getString("status"), rs.getString("config")))
                .stream().findFirst();
    }

    private Row require(UUID tenantId) {
        return find(tenantId).orElseThrow(() -> new AppException(
                "Chưa có widget — bấm \"Sinh mã nhúng\" để tạo.", HttpStatus.NOT_FOUND));
    }

    private WidgetConfig toDto(Row row) {
        JsonNode c = readJson(row.config());
        List<String> domains = new ArrayList<>();
        c.path("allowedDomains").forEach(d -> domains.add(d.asText()));
        return new WidgetConfig(row.key(), text(c, "primaryColor"), c.path("position").asText("BOTTOM_RIGHT"),
                text(c, "greetingMessage"), text(c, "avatarUrl"), domains, "ACTIVE".equals(row.status()));
    }

    /** Chuẩn hoá ("https://Shop.vn/" → "shop.vn"), bỏ trùng, kiểm dạng. */
    static List<String> normalizeDomains(List<String> raw) {
        LinkedHashSet<String> out = new LinkedHashSet<>();
        for (String r : raw) {
            String d = WidgetOriginPolicy.normalize(r);
            if (d.isEmpty()) {
                continue;
            }
            if (!DOMAIN.matcher(d).matches()) {
                throw invalid("Tên miền không hợp lệ: " + r.strip());
            }
            if (WidgetOriginPolicy.isTooBroadWildcard(d)) {
                throw invalid("\"" + r.strip() + "\" phủ quá rộng (mọi website cùng đuôi). Khai "
                        + "*.ten-mien-cua-ban.vn thay vì *.vn hay *.com.vn.");
            }
            out.add(d);
        }
        if (out.size() > MAX_DOMAINS) {
            throw invalid("Tối đa " + MAX_DOMAINS + " tên miền.");
        }
        return List.copyOf(out);
    }

    /** "wk_" + 32 ký tự hex ngẫu nhiên (128 bit) — đoán không ra, dù khoá này không phải bí mật. */
    private static String newKey() {
        byte[] b = new byte[16];
        RANDOM.nextBytes(b);
        StringBuilder sb = new StringBuilder("wk_");
        for (byte x : b) {
            sb.append(String.format("%02x", x));
        }
        return sb.toString();
    }

    private static AppException invalid(String msg) {
        return new AppException(msg, HttpStatus.UNPROCESSABLE_ENTITY);
    }

    private static String text(JsonNode c, String f) {
        return c.hasNonNull(f) ? c.get(f).asText() : null;
    }

    private JsonNode readJson(String raw) {
        try {
            JsonNode n = raw == null ? null : json.readTree(raw);
            return n != null && n.isObject() ? n : json.createObjectNode();
        } catch (JsonProcessingException e) {
            return json.createObjectNode();
        }
    }
}
