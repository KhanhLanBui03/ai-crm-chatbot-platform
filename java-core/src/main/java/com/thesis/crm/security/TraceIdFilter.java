package com.thesis.crm.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import java.util.regex.Pattern;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Đưa {@code X-Trace-Id} vào MDC cho mọi request — kế hoạch mục 4.5.
 *
 * <p>Chạy TRƯỚC chuỗi filter của Spring Security ({@code HIGHEST_PRECEDENCE}), để cả phản hồi
 * 401/403 cũng mang {@code traceId}. Gateway gắn header này; gọi thẳng java-core (dev, test) thì
 * tự sinh. Giá trị gửi vào phải khớp một khuôn chặt — header do phía gọi kiểm soát, đi thẳng vào
 * log, nên nhận nguyên văn là mở đường tiêm dòng log giả.
 *
 * <p>Khoá MDC là {@code trace_id}, KHÔNG phải {@code traceId}: {@code micrometer-tracing-bridge-brave}
 * ghi đè khoá {@code traceId} bằng mã trace của Brave mỗi khi mở một span — đã đo, test gửi
 * {@code X-Trace-Id: trace-uc018-1} thì ai-service nhận một chuỗi hex 32 ký tự lạ. {@code trace_id}
 * cũng là tên trường ai-service dùng trong log ({@code telemetry/logging.py}).
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class TraceIdFilter extends OncePerRequestFilter {

    public static final String HEADER = "X-Trace-Id";
    public static final String MDC_KEY = "trace_id";

    private static final Pattern HOP_LE = Pattern.compile("[A-Za-z0-9._-]{1,64}");

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
            FilterChain chain) throws ServletException, IOException {
        String traceId = request.getHeader(HEADER);
        if (traceId == null || !HOP_LE.matcher(traceId).matches()) {
            traceId = UUID.randomUUID().toString();
        }
        MDC.put(MDC_KEY, traceId);
        response.setHeader(HEADER, traceId);
        try {
            chain.doFilter(request, response);
        } finally {
            // Luồng của Tomcat dùng lại cho request sau — không xoá thì request sau mang
            // nhầm traceId của request trước.
            MDC.remove(MDC_KEY);
        }
    }
}
