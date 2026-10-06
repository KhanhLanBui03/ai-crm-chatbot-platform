package com.thesis.crm.common.util;

import java.text.Normalizer;

/**
 * Chuẩn hoá chuỗi người dùng nhập — cùng quy tắc với ai-service ({@code schemas.py}).
 *
 * <p>Vì sao phải NFC trước khi đếm: chữ tiếng Việt dạng NFD (hay gặp khi dán từ macOS) tách
 * {@code ệ} thành 3 code point, nên một tiêu đề nhìn thấy ~150 chữ đã có thể vượt 255. Hai tầng
 * cùng NFC rồi mới đếm thì cùng ra một con số, và tiêu đề lưu xuống CSDL ở đúng một dạng — so
 * trùng tiêu đề để tăng {@code version} mới đúng.
 */
public final class Texts {

    private Texts() {
    }

    /** NFC rồi strip. {@code null} giữ nguyên {@code null}. */
    public static String nfcStrip(String s) {
        return s == null ? null : Normalizer.normalize(s, Normalizer.Form.NFC).strip();
    }

    /**
     * Bỏ ký tự điều khiển ({@code Cc}) và ký tự định dạng vô hình ({@code Cf}): rộng bằng không
     * U+200B, đảo chiều chữ U+202E (giả tên {@code "gnp.exe"} thành {@code "exe.png"}), BOM.
     * Đúng hai nhóm mà {@code luu_tru.kiem_uri_thuoc_tenant} của ai-service từ chối.
     */
    public static String removeInvisible(String s) {
        if (s == null) {
            return null;
        }
        StringBuilder sb = new StringBuilder(s.length());
        s.codePoints()
                .filter(cp -> {
                    int type = Character.getType(cp);
                    return type != Character.CONTROL && type != Character.FORMAT;
                })
                .forEach(sb::appendCodePoint);
        return sb.toString();
    }

    /** Số code point — cách {@code len()} của Python và {@code varchar(n)} của Postgres đếm. */
    public static int codePointLength(String s) {
        return s.codePointCount(0, s.length());
    }
}
