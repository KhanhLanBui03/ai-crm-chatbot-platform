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
    void chuoiTimKiemGomTenThuSoDienThoai() {
        assertThat(ContactNormalizer.searchText("Lê Văn Bình", "binh@shop.vn", "0912345678"))
                .isEqualTo("le van binh binh@shop.vn 0912345678");
        assertThat(ContactNormalizer.searchText(null, "a@b.vn", null)).isEqualTo("a@b.vn");
    }

    @Test
    void tuKhoaGiongSoDienThoaiDuocQuyVe0() {
        assertThat(ContactNormalizer.searchKeyword("+84 912 345")).isEqualTo("0912345");
        assertThat(ContactNormalizer.searchKeyword("0912.345")).isEqualTo("0912345");
        assertThat(ContactNormalizer.searchKeyword("Nguyễn")).isEqualTo("nguyen");
        assertThat(ContactNormalizer.searchKeyword("  ")).isNull();
    }
}
