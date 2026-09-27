package com.thesis.crm.platform.service.impl;

import static org.assertj.core.api.Assertions.assertThat;

import java.text.Normalizer;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Tên tệp và key S3 của UC018. Hai tính chất phải giữ: đuôi tính GIỐNG HỆT
 * {@code pathlib.PurePath.suffix} của ai-service, và key sinh ra luôn qua được
 * {@code luu_tru.kiem_uri_thuoc_tenant} ở phía bên kia.
 */
class KbObjectKeyTest {

    /**
     * Cột phải chép từ Python 3.11: {@code PurePath(ten).suffix.lower()} — đúng cách
     * {@code mime.py::nhan_dien_tep} lấy đuôi (đã chạy 27/09/2026).
     */
    @ParameterizedTest
    @CsvSource({
            "a.PDF,        .pdf",
            ".bashrc,      ''",
            "a.,           ''",
            "a.tar.gz,     .gz",
            "x,            ''",
            ".pdf,         ''",
            "a..pdf,       .pdf",
            "'bao gia .pdf', .pdf",
    })
    void extensionGiongPathSuffixCuaPython(String ten, String duoi) {
        assertThat(KbObjectKey.extension(ten)).isEqualTo(duoi);
    }

    @Test
    void cleanFileNameBoDuongDanVaKyTuVoHinh() {
        String nfd = Normalizer.normalize("Bảng giá.pdf", Normalizer.Form.NFD);
        assertThat(KbObjectKey.cleanFileName("C:\\fakepath\\" + nfd)).isEqualTo("Bảng giá.pdf");
        assertThat(KbObjectKey.cleanFileName("../../etc/passwd.txt")).isEqualTo("passwd.txt");
        // U+202E đảo chiều hiển thị: "bao-gia‮fdp.exe" trông như "bao-giaexe.pdf".
        assertThat(KbObjectKey.cleanFileName("bao-gia\u202Efdp.exe")).isEqualTo("bao-giafdp.exe");
        assertThat(KbObjectKey.cleanFileName("\u200Bten\u0000.txt  ")).isEqualTo("ten.txt");
        assertThat(KbObjectKey.cleanFileName(null)).isEmpty();
        assertThat(KbObjectKey.cleanFileName("thu-muc/")).isEmpty();
    }

    @ParameterizedTest
    @CsvSource({
            "'Bảng giá 2026.pdf',   'Bảng-giá-2026.pdf'",
            "'a  b??c#1.PDF',       'a-b-c-1.pdf'",
            "'.hidden.txt',         'hidden.txt'",
            "'...txt',              'tep.txt'",
            "'---.md',              'tep.md'",
            "'',                    'tep'",
            "'a/b\\c.html',         'a-b-c.html'",
            "'chinh_sach-v2.docx',  'chinh_sach-v2.docx'",
            "'a..b.pdf',            'a..b.pdf'",
            "'a.p df',              'a.p-df'",
    })
    void sanitize(String vao, String ra) {
        assertThat(KbObjectKey.sanitize(vao)).isEqualTo(ra);
    }

    @Test
    void sanitizeCatTenDaiNhungGiuDuoi() {
        String ra = KbObjectKey.sanitize("ệ".repeat(300) + ".pdf");
        assertThat(ra).endsWith(".pdf");
        assertThat(ra.codePointCount(0, ra.length())).isEqualTo(KbObjectKey.TEN_TOI_DA + 4);
    }

    @Test
    void keyBatDauBangTenantVaMoiPhanDoanDeuQuaKiemCuaAiService() {
        UUID tenant = UUID.fromString("11111111-1111-1111-1111-111111111111");
        UUID upload = UUID.randomUUID();
        List<String> tenDoc = List.of("..", ".", "", "/", "\\", "a\\..\\b.pdf", "\u202E\u200B.pdf",
                "\u0000\u001F.txt", " . ", "tên có dấu cách.md", "%2e%2e.pdf", "a#b?c.html");

        for (String ten : tenDoc) {
            String key = KbObjectKey.build(tenant, upload, KbObjectKey.cleanFileName(ten));
            String[] phanDoan = key.split("/", -1);

            assertThat(phanDoan).as(key).hasSize(3);
            assertThat(phanDoan[0]).isEqualTo(tenant.toString());
            assertThat(phanDoan[1]).isEqualTo(upload.toString());
            for (String p : phanDoan) {
                // Đúng bốn điều kiện của luu_tru._phan_doan_bat_thuong.
                assertThat(p).as(key).isNotIn("", ".", "..").doesNotContain("\\");
                assertThat(p.codePoints()).as(key).noneMatch(cp -> {
                    int type = Character.getType(cp);
                    return type == Character.CONTROL || type == Character.FORMAT;
                });
            }
        }
    }
}
