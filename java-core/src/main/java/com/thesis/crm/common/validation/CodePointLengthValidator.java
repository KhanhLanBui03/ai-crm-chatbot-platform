package com.thesis.crm.common.validation;

import com.thesis.crm.common.util.Texts;
import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;

/** Kiểm {@link CodePointLength}. */
public class CodePointLengthValidator implements ConstraintValidator<CodePointLength, String> {

    private int min;
    private int max;

    @Override
    public void initialize(CodePointLength annotation) {
        this.min = annotation.min();
        this.max = annotation.max();
    }

    @Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        if (value == null) {
            return true;
        }
        int n = Texts.codePointLength(value);
        return n >= min && n <= max;
    }
}
