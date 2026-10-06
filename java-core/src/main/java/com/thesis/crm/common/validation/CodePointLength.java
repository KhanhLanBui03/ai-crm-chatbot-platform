package com.thesis.crm.common.validation;

import jakarta.validation.Constraint;
import jakarta.validation.Payload;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Độ dài chuỗi tính theo CODE POINT, không theo đơn vị UTF-16 như {@code @Size}.
 *
 * <p>{@code @Size} đếm {@code String.length()}: một emoji ngoài BMP tính là 2. ai-service
 * (Python {@code len()}) và cột {@code varchar(n)} của Postgres đều đếm code point — dùng
 * {@code @Size} thì hai tầng lệch nhau đúng ở những chuỗi có emoji. {@code null} hợp lệ; ghép
 * với {@code @NotNull} khi trường bắt buộc.
 */
@Target({ElementType.FIELD, ElementType.PARAMETER, ElementType.RECORD_COMPONENT})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = CodePointLengthValidator.class)
public @interface CodePointLength {

    int min() default 0;

    int max() default Integer.MAX_VALUE;

    String message() default "phải từ {min} đến {max} ký tự";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};
}
