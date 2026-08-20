# gateway — Track A

Spring Cloud Gateway: điểm vào duy nhất cho widget, dashboard và webhook kênh.

- Cổng: **8080**
- Trách nhiệm: xác thực **JWT RS256**, **rate limit** (counter ở Redis), gắn **`X-Trace-Id`**,
  định tuyến qua `lb://` (Eureka phân giải, không hardcode host:port)

## Bảng định tuyến

| Path | Đích | Ghi chú |
|---|---|---|
| `/api/v1/**` | `lb://java-core` | 20 req/s, burst 40 |
| `/ai/v1/**` | `lb://ai-service` | 5 req/s, burst 10 — gọi mô hình đắt hơn nhiều |

## Cấu trúc package

Phẳng — gateway chỉ có một miền, không có bounded context nào để tách.

```
com.thesis.crm.gateway
├── GatewayApplication.java
├── config/        CorsConfig · RouteConfig · SecurityConfig · RateLimiterConfig
├── filter/        TraceIdFilter · TenantContextFilter
├── security/      JwtAuthConverter · TenantKeyResolver (rate limit theo tenant)
└── exception/     GatewayExceptionHandler
```

## Quy ước bắt buộc

- Gateway **chỉ xác thực** JWT, không phát hành. `java-core` phát hành và công bố khóa
  công khai ở `/.well-known/jwks.json`.
- `X-Trace-Id` sinh ở đây nếu request chưa có, rồi truyền xuyên suốt mọi chặng —
  kể cả qua Kafka (đặt ở **header** bản tin, không phải payload — kế hoạch mục 4.5).
- `prefer-ip-address: true` — bắt buộc trong Docker.

## TODO

- [ ] Filter gắn `X-Trace-Id` vào MDC
- [ ] `KeyResolver` cho rate limit theo `tenant_id`, không theo IP
- [ ] Nginx đứng trước (TLS, chặn rác, giới hạn kích thước body)
