# java-core — Track A

Modular monolith, 4 bounded context. Một Spring Boot app, ranh giới thể hiện bằng package
(ADR: xem `docs/adr/`). Cổng **8081**.

```
com.thesis.crm
├── platform/     tenant · user · auth · plan · subscription · usage · audit · outbox
├── engagement/   contact · channel · conversation · message · handoff
├── sales/        lead · deal · activity
├── analytics/    metrics · funnel · topic · consumer
└── common/       config · security · web · kafka · observability
```

## Luật ranh giới

1. Package của một context **không import** trực tiếp lớp nội bộ của context khác.
   Giao tiếp qua interface công khai đặt ở tầng trên cùng của mỗi context, hoặc qua sự kiện.
2. Mọi bảng nghiệp vụ có cột `tenant_id` và bật RLS (ADR-0001).
3. Mọi thay đổi trạng thái đáng kể ghi vào `platform.outbox_events` **trong cùng transaction**,
   không gọi Kafka trực tiếp (ADR-0003).
4. `ai-service` không đọc/ghi DB này — mọi thứ qua API nội bộ (ADR-0002),
   đặc tả ở `docs/openapi/java-core-to-ai-service.yaml`.

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

- [ ] `JavaCoreApplication.java`
- [ ] Migration V101–V112 (xem `db/migration/README.md`)
- [ ] Filter đặt `SET LOCAL app.tenant_id` từ JWT cho mỗi transaction
- [ ] `OutboxPublisher` `@Scheduled(500ms)`, lô 100
- [ ] Consumer analytics + chống trùng qua `analytics.processed_events`
- [ ] Log JSON có Trace ID qua MDC — **làm từ Sprint 0**, kế hoạch mục 4.5
