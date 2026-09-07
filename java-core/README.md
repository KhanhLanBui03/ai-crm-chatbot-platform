# java-core — Track A

Modular monolith, 4 bounded context. Một Spring Boot app, ranh giới thể hiện bằng package.
Cổng **8081**.

## Cấu trúc package

```
com.thesis.crm
├── JavaCoreApplication.java
│
│   ── cắt ngang cả 4 context ──
├── config/          Jackson · OpenAPI · Async · Kafka · WebClient
├── security/        JWT RS256 · TenantContextFilter · biến phiên RLS
├── client/          gọi ai-service — bề mặt DUY NHẤT (ADR-0002)
├── common/
│   ├── enums/       enum dùng chung nhiều context
│   ├── exception/   ngoại lệ + @RestControllerAdvice
│   ├── response/    ApiResponse, PageResponse
│   └── util/
│
│   ── 4 bounded context ──
├── platform/        tenant · user · auth · plan · subscription · usage · audit · outbox
│   ├── controller/  dto/{request,response}/  entity/  repository/  service/impl/
│   ├── messaging/   OutboxPublisher
│   └── scheduler/   @Scheduled 500ms, lô 100 (ADR-0003)
│
├── engagement/      contact · channel · conversation · message · handoff
│   ├── controller/  dto/{request,response}/  entity/  repository/  service/impl/
│   ├── messaging/   producer sự kiện hội thoại
│   └── websocket/   hội thoại thời gian thực
│
├── sales/           lead · deal · activity
│   ├── controller/  dto/{request,response}/  entity/  repository/  service/impl/
│   └── messaging/
│
└── analytics/       read model · metrics · funnel · topic
    ├── controller/  dto/response/  entity/  repository/  service/impl/
    └── messaging/   consumer analytics-cg + chống trùng processed_events
```

## Đặt file mới ở đâu

| Bạn đang viết | Đặt vào |
|---|---|
| Endpoint HTTP | `<context>/controller/` |
| Kiểu dữ liệu client gửi lên | `<context>/dto/request/` |
| Kiểu dữ liệu trả về client | `<context>/dto/response/` |
| Bảng CSDL | `<context>/entity/` |
| Truy vấn | `<context>/repository/` |
| Bề mặt nghiệp vụ (interface) | `<context>/service/` |
| Logic nghiệp vụ | `<context>/service/impl/` |
| Producer/consumer Kafka | `<context>/messaging/` |
| Việc chạy theo lịch | `<context>/scheduler/` |
| Gọi HTTP ra ai-service | `client/` (gốc) |
| `@Configuration` | `config/` (gốc) |
| Filter, JWT, ngữ cảnh tenant | `security/` (gốc) |
| Dùng bởi từ 2 context trở lên | `common/` (gốc) |

**Subdomain thể hiện bằng tên class, không phải thư mục.** `TenantController` và
`UserController` cùng nằm trong `platform/controller/` — đúng như layout microservice một
miền. Chỉ khi một tầng của một context vượt **~15 class** thì mới tách sub-package theo
subdomain (`platform/entity/billing/`, …).

**Vì sao `client/`, `config/`, `security/`, `common/` ở gốc:** chúng cắt ngang cả 4 context.
Nhét vào một context sẽ tạo phụ thuộc chéo — đúng thứ mà ranh giới context sinh ra để tránh.

## Bốn luật ranh giới

1. Package của một context **không import** lớp nội bộ của context khác. Giao tiếp qua
   interface trong `<context>/service/` hoặc qua sự kiện.
2. Mọi bảng nghiệp vụ có cột `tenant_id` và bật RLS (ADR-0001).
3. Mọi thay đổi trạng thái đáng kể ghi vào `platform.outbox_events` **trong cùng
   transaction** — không gọi `KafkaTemplate.send()` trực tiếp trong service (ADR-0003).
4. `ai-service` không đọc/ghi CSDL này. Mọi thứ qua API nội bộ (ADR-0002), đặc tả ở
   `docs/openapi/java-core-to-ai-service.yaml`.

## Lát cắt dọc mẫu — `sales` (lead)

Một luồng hoàn chỉnh đã viết sẵn làm chuẩn để copy. Nó chạm đúng ba mẫu quan trọng nhất:
cô lập tenant, cặp interface/impl, và ghi outbox trong cùng transaction.

```
sales/entity/Lead.java                     JPA entity, có tenantId
sales/repository/LeadRepository.java       JpaRepository — KHÔNG tự lọc tenant, RLS lo
sales/dto/request/CreateLeadRequest.java   record + Bean Validation, KHÔNG nhận tenantId
sales/dto/response/LeadResponse.java       record — không trả entity thẳng ra
sales/service/LeadService.java             interface
sales/service/impl/LeadServiceImpl.java    @Service @Transactional + TODO ghi outbox
sales/controller/LeadController.java       @RestController, không có logic nghiệp vụ
common/response/ApiResponse.java           vỏ phản hồi dùng chung, có traceId
```

Các phương thức `impl` hiện ném `UnsupportedOperationException` — cố ý, đây là file mẫu
chưa cài đặt. Nhưng chúng **compile được**: `mvn -f java-core/pom.xml compile`.

## Sở hữu

- **Schema:** `platform`, `engagement`, `sales`, `analytics`
- **Flyway:** dải **V1xx** — `src/main/resources/db/migration/` (xem README ở đó)
- **Kafka:** sản xuất `crm.conversation.v1`, `crm.lead.v1`, `crm.usage.v1`, `crm.document.v1`

## Hai tài khoản CSDL — không được nhầm

| Biến | Dùng cho | Lý do |
|---|---|---|
| `DB_MIGRATION_USER` | Flyway | Chủ bảng, có quyền DDL |
| `DB_USERNAME` | Runtime | **Không** phải chủ bảng — chủ bảng bypass RLS |

## TODO

- [ ] Migration V101–V112 (xem `db/migration/README.md`)
- [ ] `security/` — filter đặt `SET LOCAL app.tenant_id` từ JWT cho mỗi transaction
- [ ] `platform/messaging/OutboxPublisher` + `platform/scheduler/` @Scheduled 500ms, lô 100
- [ ] `analytics/messaging/` — consumer + chống trùng qua `analytics.processed_events`
- [ ] `common/exception/` — `@RestControllerAdvice` trả `ApiResponse.error(...)` kèm traceId
- [ ] Log JSON có Trace ID qua MDC — **làm từ Sprint 0**, kế hoạch mục 4.5
