package com.thesis.crm.engagement.widget;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Quy tắc tên miền (UC009 bước 10) và giờ làm việc (UC010 7.1) — thuần Java, không cần CSDL. */
class WidgetOriginPolicyTest {

    @Test
    void khopDung_vaTuNhanWww_khongNhanTenMienConKhac() {
        List<String> ds = List.of("congtya.vn");
        assertThat(WidgetOriginPolicy.allowed("https://congtya.vn", ds)).isTrue();
        assertThat(WidgetOriginPolicy.allowed("https://www.congtya.vn", ds)).isTrue();
        assertThat(WidgetOriginPolicy.allowed("http://congtya.vn:8080", ds)).isTrue();
        assertThat(WidgetOriginPolicy.allowed("https://shop.congtya.vn", ds)).isFalse();
        assertThat(WidgetOriginPolicy.allowed("https://congtya.vn.ke-gian.com", ds)).isFalse();
        assertThat(WidgetOriginPolicy.allowed("https://fakecongtya.vn", ds)).isFalse();
    }

    @Test
    void kyTuSao_nhanMoiTenMienCon() {
        List<String> ds = List.of("*.congtya.vn");
        assertThat(WidgetOriginPolicy.allowed("https://shop.congtya.vn", ds)).isTrue();
        assertThat(WidgetOriginPolicy.allowed("https://congtya.vn", ds)).isTrue();
        assertThat(WidgetOriginPolicy.allowed("https://evilcongtya.vn", ds)).isFalse();
    }

    @Test
    void localhostChiKhiKhaiRo_danhSachRong_hoacThieuOrigin_thiTuChoi() {
        assertThat(WidgetOriginPolicy.allowed("http://localhost:5174", List.of("congtya.vn"))).isFalse();
        assertThat(WidgetOriginPolicy.allowed("http://localhost:5174", List.of("localhost"))).isTrue();
        assertThat(WidgetOriginPolicy.allowed("https://congtya.vn", List.of())).isFalse();
        assertThat(WidgetOriginPolicy.allowed(null, List.of("congtya.vn"))).isFalse();
        assertThat(WidgetOriginPolicy.allowed("null", List.of("congtya.vn"))).isFalse();
    }

    @Test
    void nguoiDungDanCaDuongDan_vanHieu() {
        assertThat(WidgetOriginPolicy.allowed("https://congtya.vn",
                List.of("https://CongtyA.vn/lien-he"))).isTrue();
    }

    @Test
    void gioLamViec_trongVaNgoaiGio_vaMoTaGopNgay() throws Exception {
        var hours = new ObjectMapper().readTree("""
                {"mon":{"open":"08:00","close":"17:30"},"tue":{"open":"08:00","close":"17:30"},
                 "wed":{"open":"08:00","close":"17:30"},"thu":{"open":"08:00","close":"17:30"},
                 "fri":{"open":"08:00","close":"17:30"},"sat":{"open":"08:00","close":"12:00"},"sun":null}""");
        BusinessHours b = new BusinessHours(hours, "Asia/Ho_Chi_Minh");
        ZoneId vn = ZoneId.of("Asia/Ho_Chi_Minh");
        // 06/10/2026 là thứ Ba
        assertThat(b.isOpen(ZonedDateTime.of(2026, 10, 6, 9, 0, 0, 0, vn))).isTrue();
        assertThat(b.isOpen(ZonedDateTime.of(2026, 10, 6, 18, 0, 0, 0, vn))).isFalse();
        assertThat(b.isOpen(ZonedDateTime.of(2026, 10, 11, 9, 0, 0, 0, vn))).isFalse();   // Chủ nhật
        assertThat(b.describe()).isEqualTo("Thứ Hai–Thứ Sáu 08:00–17:30; Thứ Bảy 08:00–12:00");
    }

    @Test
    void chuaKhaiGio_coiNhuLuonTrongGio() throws Exception {
        BusinessHours b = new BusinessHours(new ObjectMapper().readTree("{}"), "Asia/Ho_Chi_Minh");
        assertThat(b.isOpenNow()).isTrue();
        assertThat(b.describe()).isEmpty();
    }

    @Test
    void dongCua2400_hieuLaHetNgay_khongPhaiNgayNghi() throws Exception {
        // Lỗ hổng R5: "24:00" không phải LocalTime hợp lệ → cả ngày bị coi là NGHỈ, khách luôn nghe
        // "ngoài giờ làm việc" dù doanh nghiệp mở 24/7.
        var hours = new ObjectMapper().readTree("""
                {"mon":{"open":"00:00","close":"24:00"},"tue":{"open":"00:00","close":"24:00"},
                 "wed":{"open":"00:00","close":"24:00"},"thu":{"open":"00:00","close":"24:00"},
                 "fri":{"open":"00:00","close":"24:00"},"sat":{"open":"00:00","close":"24:00"},
                 "sun":{"open":"00:00","close":"24:00"}}""");
        BusinessHours b = new BusinessHours(hours, "Asia/Ho_Chi_Minh");
        assertThat(b.isOpen(ZonedDateTime.of(2026, 10, 6, 23, 30, 0, 0, ZoneId.of("Asia/Ho_Chi_Minh")))).isTrue();
        assertThat(b.describe()).isEqualTo("Thứ Hai–Chủ nhật 00:00–24:00");
    }

    @Test
    void kyTuSaoQuaRong_bitBoQua_ngayCaKhiDaNamTrongCsdl() {
        // Lớp thứ hai cho dữ liệu lưu trước khi WidgetConfigService biết từ chối
        assertThat(WidgetOriginPolicy.allowed("https://bat-ky.vn", List.of("*.vn"))).isFalse();
        assertThat(WidgetOriginPolicy.allowed("https://shop.com.vn", List.of("*.com.vn"))).isFalse();
        assertThat(WidgetOriginPolicy.allowed("https://shop.congtya.com.vn", List.of("*.congtya.com.vn"))).isTrue();
        assertThat(WidgetOriginPolicy.isTooBroadWildcard("*.congtya.vn")).isFalse();
    }

    @Test
    void tenMienCoDau_quyVePunycode() {
        String ascii = java.net.IDN.toASCII("cửahàng.vn");
        assertThat(WidgetOriginPolicy.normalize("https://CửaHàng.vn/")).isEqualTo(ascii);
        assertThat(WidgetOriginPolicy.allowed("https://www." + ascii, List.of("cửahàng.vn"))).isTrue();
    }
}
