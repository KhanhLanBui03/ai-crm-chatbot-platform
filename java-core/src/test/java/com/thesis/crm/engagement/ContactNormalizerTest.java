package com.thesis.crm.engagement;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.thesis.crm.engagement.util.ContactNormalizer;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;
import org.junit.jupiter.api.Test;

/** UC016 — chuẩn hoá số điện thoại và chuỗi tìm kiếm không dấu. */
class ContactNormalizerTest {

    @ParameterizedTest
    @CsvSource({
            "0912345678,      0912345678",
            "0912 345 678,    0912345678",
            "0912.345.678,    0912345678",
            "091-234-5678,    0912345678",
            "+84912345678,    0912345678",
            "+84 912 345 678, 0912345678",
            "84912345678,     0912345678",
            "(028) 3822 1234, 02838221234",
    })
    void soDienThoaiQuyVeMotDang(String raw, String expected) {
        assertThat(ContactNormalizer.normalizePhone(raw)).isEqualTo(expected);
    }

    @ParameterizedTest
    @ValueSource(strings = {"12345", "abc", "0912", "+1 202 555 0100", "09123456789012"})
    void soDienThoaiSaiBiTuChoi(String raw) {
        assertThatThrownBy(() -> ContactNormalizer.normalizePhone(raw))
                .isInstanceOf(IllegalArgumentException.class);
    }

    // ── Hồi quy rà soát 06/10 ───────────────────────────────────────────────────

    @ParameterizedTest
    @CsvSource({
            // Người dùng gõ cả mã quốc gia lẫn số 0 đầu — trước đây lưu thành "00912345678"
            "+84 0912 345 678, 0912345678",
            "840912345678,     0912345678",
            // Số di động gõ thiếu số 0 đầu — trước đây bị từ chối
            "912345678,        0912345678",
            "912 345 678,      0912345678",
            // Gõ dư một số 0 đầu — cùng quy tắc với "+84 0…"
            "00912345678,      0912345678",
    })
    void soDienThoaiNhapKieuThuongGap(String raw, String expected) {
        assertThat(ContactNormalizer.normalizePhone(raw)).isEqualTo(expected);
    }

    @ParameterizedTest
    @ValueSource(strings = {"0012345678", "000912345678", "123456789", "0123456789"})
    void khongPhaiSoVietNamHopLeBiTuChoi(String raw) {
        assertThatThrownBy(() -> ContactNormalizer.normalizePhone(raw))
                .isInstanceOf(IllegalArgumentException.class);
    }

    @Test
    void chuDungDangTachDauNfdVanBoDauDung() {
        // Bàn phím macOS/iOS có thể gửi "ễ" thành e + dấu mũ + dấu ngã (NFD)
        String nfd = java.text.Normalizer.normalize("Nguyễn Ánh", java.text.Normalizer.Form.NFD);
        assertThat(ContactNormalizer.foldAccents(nfd)).isEqualTo("nguyen anh");
    }

    @Test
    void tuKhoaNhieuTuTachThanhTung() {
        assertThat(ContactNormalizer.searchTokens("  Nguyễn   0912.345 ")).containsExactly("nguyen", "0912345");
        assertThat(ContactNormalizer.searchTokens("+84 912 345 678")).containsExactly("0912345678");
        assertThat(ContactNormalizer.searchTokens(" ")).isEmpty();
    }

    @Test
    void rongThanhNull() {
        assertThat(ContactNormalizer.normalizePhone("  ")).isNull();
        assertThat(ContactNormalizer.normalizeEmail("")).isNull();
        assertThat(ContactNormalizer.normalizeEmail(" An@Shop.VN ")).isEqualTo("an@shop.vn");
    }

    @Test
    void boDauTiengViet() {
        assertThat(ContactNormalizer.foldAccents("Nguyễn Đức Ánh")).isEqualTo("nguyen duc anh");
        assertThat(ContactNormalizer.foldAccents("Trần Thị Hồng Nhung")).isEqualTo("tran thi hong nhung");
        assertThat(ContactNormalizer.foldAccents("ĐẶNG VĂN LƯƠNG")).isEqualTo("dang van luong");
    }

    @Test
    void tuKhoaGiongSoDienThoaiDuocQuyVe0() {
        assertThat(ContactNormalizer.searchTokens("+84 912 345")).containsExactly("0912345");
        assertThat(ContactNormalizer.searchTokens("0912.345")).containsExactly("0912345");
        assertThat(ContactNormalizer.searchTokens("Nguyễn")).containsExactly("nguyen");
        assertThat(ContactNormalizer.searchTokens("  ")).isEmpty();
    }
}
