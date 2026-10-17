package com.thesis.crm.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.hibernate.cfg.AvailableSettings;
import org.hibernate.type.format.jackson.JacksonJsonFormatMapper;
import org.springframework.boot.autoconfigure.orm.jpa.HibernatePropertiesCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Hibernate đọc/ghi cột {@code jsonb} của Entity ({@code @JdbcTypeCode(SqlTypes.JSON)}) bằng CHÍNH
 * {@link ObjectMapper} của Spring.
 *
 * <p>Mặc định Hibernate tự dựng một ObjectMapper riêng và gọi {@code findAndRegisterModules()} — nạp mọi
 * module Jackson tìm thấy trên classpath, kể cả {@code jackson-module-scala} đi kèm thư viện Kafka. Khi đó
 * {@code Map<String, Object>} đọc từ CSDL chứa {@code scala.collection.List}/{@code Map} thay vì của Java:
 * trích dẫn trong {@code messages.metadata} ghi ra lại thành {@code {"empty":false,…}} (phát hiện khi chuyển
 * hộp thư sang JPA). Dùng chung mapper của Spring thì JSON trong Entity, trong API và trong nhật ký kiểm
 * toán có cùng một cấu hình (ngày giờ dạng ISO, không có module lạ).
 */
@Configuration
public class HibernateJsonConfig {

    @Bean
    HibernatePropertiesCustomizer jsonFormatMapper(ObjectMapper objectMapper) {
        return props -> props.put(AvailableSettings.JSON_FORMAT_MAPPER, new JacksonJsonFormatMapper(objectMapper));
    }
}
