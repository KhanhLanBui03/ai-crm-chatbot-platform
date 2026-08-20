# eureka-server — Track A

Service registry. Gateway định tuyến qua `lb://` nhờ đăng ký ở đây (ADR-0004).

- Cổng: **8761** · Bảng điều khiển: http://localhost:8761
- Đăng ký vào đây: `gateway`, `java-core`, `ai-service`

## Cấu hình đã đặt sẵn cho môi trường phát triển

| Thiết lập | Giá trị | Vì sao |
|---|---|---|
| `enable-self-preservation` | `false` | Self-preservation giữ lại bản ghi đã chết khi tỉ lệ nhịp tim giảm — hợp lý khi vận hành thật, gây nhầm lẫn khi phát triển |
| `lease-renewal-interval` (phía client) | 10s | Mặc định 30s/90s khiến gateway định tuyến lỗi ~1,5 phút sau mỗi lần restart |
| `lease-expiration-duration` (phía client) | 30s | như trên |

Vận hành thật thì đảo ngược cả ba.

## Bẫy với `ai-service` (Python)

FastAPI **không tự đăng ký** với Eureka. Dùng `py-eureka-client`: đăng ký lúc khởi động,
gửi nhịp tim định kỳ, **hủy đăng ký lúc tắt**. Quên hủy thì Eureka vẫn định tuyến tới một
tiến trình đã chết trong khoảng 90 giây. Xem kế hoạch mục 4.4.

## TODO

- [ ] `EurekaServerApplication.java` + `@EnableEurekaServer`
