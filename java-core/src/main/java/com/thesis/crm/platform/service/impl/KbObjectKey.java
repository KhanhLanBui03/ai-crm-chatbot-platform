package com.thesis.crm.platform.service.impl;

import com.thesis.crm.common.util.Texts;
import java.util.Locale;
import java.util.UUID;

/**
 * Tên tệp và key trên kho S3 của UC018 — hợp đồng {@code docs/contracts/uc018-tai-tai-lieu.md}
 * mục 1.1 và mục 3.
 *
 * <p>Key: {@code {tenant_id}/{upload_id}/{tên đã làm sạch}}. Phía đọc
 * ({@code ai-service/src/ai/rag/ingest/luu_tru.py::kiem_uri_thuoc_tenant}) từ chối mọi key có phân
 * đoạn rỗng, {@code .}, {@code ..}, dấu {@code \}, ký tự điều khiển hoặc vô hình — lớp này bảo đảm
 * không bao giờ sinh ra key như vậy, để 403 ở phía kia chỉ còn nghĩa là "bị tấn công".
 */
final class KbObjectKey {

    /** Trần phần tên (không kể đuôi), tính theo code point. Key tối đa ~720 byte, dưới trần 1024 của S3. */
    static final int TEN_TOI_DA = 150;

    private KbObjectKey() {
    }

    /**
     * Tên tệp gốc → tên gửi ai-service ở trường {@code file_name} và hiển thị cho người dùng.
     *
     * <p>Lấy phần sau {@code /} hoặc {@code \} cuối (trình duyệt cũ trên Windows gửi cả
     * {@code C:\fakepath\…}), NFC, bỏ ký tự {@code Cc}/{@code Cf}, strip. Bỏ U+202E ở đây vì tên
     * này được HIỂN THỊ: {@code "bao-gia\u202Efdp.exe"} trông như {@code "bao-giaexe.pdf"}.
     */
    static String cleanFileName(String original) {
        if (original == null) {
            return "";
        }
        int cat = Math.max(original.lastIndexOf('/'), original.lastIndexOf('\\'));
        String ten = cat >= 0 ? original.substring(cat + 1) : original;
        return Texts.removeInvisible(Texts.nfcStrip(ten)).strip();
    }

    /**
     * Đuôi tệp, chữ thường, có dấu chấm — GƯƠNG của {@code pathlib.PurePath.suffix} mà ai-service
     * dùng: chấm cuối cùng, không ở đầu tên, không ở cuối tên. {@code ".bashrc"} và {@code "a."}
     * không có đuôi. Hai bên tính khác nhau thì một tệp qua được java-core rồi bị ai-service trả 415.
     */
    static String extension(String fileName) {
        int i = fileName.lastIndexOf('.');
        return (i > 0 && i < fileName.length() - 1) ? fileName.substring(i).toLowerCase(Locale.ROOT) : "";
    }

    /** Key của một lượt tải. {@code uploadId} mới mỗi lượt: tải lại cùng tên không ghi đè bản cũ. */
    static String build(UUID tenantId, UUID uploadId, String cleanFileName) {
        return tenantId + "/" + uploadId + "/" + sanitize(cleanFileName);
    }

    /**
     * Tên đã làm sạch cho phân đoạn cuối của key.
     *
     * <ol>
     *   <li>Giữ chữ, dấu kết hợp, số và {@code . - _}; mọi ký tự khác thành {@code -}, gộp các
     *       {@code -} liền nhau.
     *   <li>Bỏ {@code .} và {@code -} ở hai đầu — không còn {@code .}, {@code ..}, tệp ẩn.
     *   <li>Phần tên tối đa {@value #TEN_TOI_DA} code point, đuôi giữ nguyên (chữ thường).
     *   <li>Rỗng thì thành {@code tep}.
     * </ol>
     */
    static String sanitize(String cleanFileName) {
        String duoi = extension(cleanFileName);
        String ten = cleanFileName.substring(0, cleanFileName.length() - duoi.length());

        ten = catBien(thayKyTuLa(ten));
        if (ten.codePointCount(0, ten.length()) > TEN_TOI_DA) {
            ten = catBien(ten.substring(0, ten.offsetByCodePoints(0, TEN_TOI_DA)));
        }
        if (ten.isEmpty()) {
            ten = "tep";
        }
        // Đuôi đã qua extension(): bắt đầu bằng '.', phần sau có thể còn ký tự lạ ("a.p df").
        String duoiSach = duoi.isEmpty() ? "" : "." + catBien(thayKyTuLa(duoi.substring(1)));
        return duoiSach.equals(".") ? ten : ten + duoiSach;
    }

    private static String thayKyTuLa(String s) {
        StringBuilder sb = new StringBuilder(s.length());
        s.codePoints().forEach(cp -> {
            if (giuNguyen(cp)) {
                sb.appendCodePoint(cp);
            } else if (sb.isEmpty() || sb.charAt(sb.length() - 1) != '-') {
                sb.append('-');
            }
        });
        return sb.toString().replaceAll("-{2,}", "-");
    }

    private static boolean giuNguyen(int cp) {
        if (Character.isLetterOrDigit(cp) || cp == '.' || cp == '-' || cp == '_') {
            return true;
        }
        int type = Character.getType(cp);
        return type == Character.NON_SPACING_MARK
                || type == Character.COMBINING_SPACING_MARK
                || type == Character.ENCLOSING_MARK;
    }

    /** Bỏ {@code .} và {@code -} ở hai đầu. */
    private static String catBien(String s) {
        int dau = 0;
        int cuoi = s.length();
        while (dau < cuoi && (s.charAt(dau) == '.' || s.charAt(dau) == '-')) {
            dau++;
        }
        while (cuoi > dau && (s.charAt(cuoi - 1) == '.' || s.charAt(cuoi - 1) == '-')) {
            cuoi--;
        }
        return s.substring(dau, cuoi);
    }
}
