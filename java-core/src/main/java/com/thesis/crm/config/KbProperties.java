package com.thesis.crm.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.util.unit.DataSize;

/**
 * Tham số kho tri thức — UC018.
 *
 * @param maxFileSize dung lượng tối đa mỗi tệp. {@code spring.servlet.multipart.max-file-size}
 *                    đọc lại đúng giá trị này, nên giới hạn ở servlet và lớp kiểm thứ hai trong
 *                    service không thể lệch nhau
 */
@ConfigurationProperties(prefix = "crm.kb")
public record KbProperties(DataSize maxFileSize) {
}
