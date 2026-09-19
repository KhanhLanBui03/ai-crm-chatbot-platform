# ADR-0016 — Tên role runtime `ai_app` và chỗ đặt nhãn kết quả Lead

- **Trạng thái:** Đề xuất
- **Ngày:** 2026-09-19
- **Làn sở hữu:** Track B (module AI) · **quyết định 2 cần Track A thực thi**
- **Quan hệ:** thi hành [ADR-0001](0001-multi-tenant-isolation-rls.md) và
  [ADR-0002](0002-ai-service-khong-truy-cap-db-truc-tiep.md) · tiếp nối
  [ADR-0015](0015-cau-truc-src-hai-tang-theo-master-plan-v8.md)

## Bối cảnh

Đợt tái cấu trúc theo Master Plan v8.0 (ADR-0015) để lại bốn mâu thuẫn tài liệu chưa chốt.
ADR này chốt hai mâu thuẫn có tính kiến trúc; hai mâu thuẫn còn lại là việc điều hành, ghi ở
mục *Hệ quả*.

---

## Quyết định 1 — Role runtime của ai-service tên là `ai_app`

### Bối cảnh

Master Plan §4.2 và §4.3 gọi role chạy ai-service là `ai_service`. Repo gọi nó là `ai_app`.

Điều **quan trọng** ở đây không phải cái tên mà là tính chất: role runtime **không được là
chủ bảng**. PostgreSQL cho phép chủ sở hữu bảng bỏ qua Row Level Security, nên nếu ai-service
chạy bằng `crm_owner` thì nó đọc được dữ liệu của mọi tenant **mà không báo lỗi gì**. Cả hai
tên đều thoả tính chất đó — đây thuần tuý là xung đột đặt tên.

### Quyết định

**Giữ `ai_app`.** Master Plan là chỗ lệch duy nhất.

Ba nơi trong repo đã nhất quán dùng `ai_app`:

| Nơi | Dòng |
|---|---|
| `scripts/init-db.sql:26` | `CREATE ROLE ai_app LOGIN PASSWORD ...` |
| `ai-service/migration/V206__grants_cho_ai_app.sql:6` | `GRANT ... IN SCHEMA knowledge, ai, integration TO ai_app` |
| `docker-compose.yml:239` | `DB_USERNAME: ${AI_DB_USERNAME:-ai_app}` |

Thêm nữa, `ai_app` **cùng cách đặt tên** với `crm_app` của Track A (`<làn>_app`), nên bộ ba
`crm_owner` / `crm_app` / `ai_app` đọc lên là một hệ thống nhất quán. `ai_service` phá cặp đó
và còn dễ nhầm với **tên service** `ai-service`.

### Lập luận

Đổi sang `ai_service` phải sửa `init-db.sql` + `V206` + `docker-compose.yml`, và vì `V206` đã
chạy thật nên còn phải thêm một migration `ALTER ROLE ... RENAME` — đổi tên role đang có kết
nối mở là thao tác phải dừng service. Tất cả chi phí đó để đổi một cái tên không sai.

Rủi ro của việc **không chốt** thì có thật: ai đó viết theo Master Plan sẽ gặp
`role "ai_service" does not exist` — và lỗi này nổ **lúc chạy container**, không nổ lúc build,
nên nó lọt qua CI.

### Đánh đổi

1. **Tài liệu chuẩn (§4.2, §4.3) nay sai ở một danh từ.** Ai đọc Master Plan rồi viết code sẽ
   vấp. Giảm nhẹ bằng ADR này và bằng việc ghi rõ ở `CLAUDE.md` gốc — nhưng không xoá được
   hoàn toàn khả năng nhầm.
2. **Không sửa được file `.docx` gốc** để đồng bộ, vì đó là tài liệu nộp. Độ lệch sẽ tồn tại
   tới cuối kỳ.

---

## Quyết định 2 — Nhãn kết quả Lead thêm vào `sales.lead_scores`, KHÔNG tạo `ai.lead_features`

### Bối cảnh

Master Plan §5.10.2 mô tả bảng `ai.lead_features` để lưu **ảnh chụp đặc trưng tại thời điểm
chấm điểm**, kèm cột `outcome` do java-core cập nhật ngược khi thương vụ đóng. Kế hoạch 49
ngày nhắc bảng này ở Ngày 3 và Ngày 29, và gọi nó là *"cầu nối duy nhất biến dữ liệu vận hành
thành dữ liệu huấn luyện"*.

Không có vòng phản hồi này thì UC030 chấm điểm mãi mà **model không bao giờ học được từ thực
tế** — toàn bộ §5.10.6 (vòng đời model, kế hoạch trôi dữ liệu) không bao giờ xảy ra.

**Nhưng bảng đó chưa từng được tạo.** Đã rà `V201`–`V209`: không migration nào có nó.

Rà tiếp thì thấy lý do: **`sales.lead_scores` (Track A, `V113`) đã phủ gần hết**.

| `ai.lead_features` (§5.10.2) | `sales.lead_scores` (V113, đang chạy) |
|---|---|
| `snapshot_id` | `id` ✅ |
| `tenant_id` · `contact_id` · `scored_at` | ✅ đủ ba |
| `features` jsonb | `features` jsonb ✅ |
| `model_score` · `model_version` | `score` (0..100) · `model_version` ✅ |
| — | `top_factors` jsonb ✅ *(chính là 3 mã lý do của UC030)* |
| — | `confidence` ✅ |
| `rule_score` | ❌ **thiếu** |
| **`outcome`** | ❌ **thiếu** |
| **`outcome_at`** | ❌ **thiếu** |

### Các phương án đã cân nhắc

| Phương án | Ưu | Nhược |
|---|---|---|
| **Thêm 3 cột vào `sales.lead_scores`** (đã chọn) | Một nguồn sự thật duy nhất cho "một lần chấm điểm". 0 cột trùng | Phụ thuộc Track A thực thi (dải V1xx). Ghi `outcome` phải qua API |
| Tạo `ai.lead_features` đầy đủ ở V210 | Track B tự chủ hoàn toàn | **Nhân đôi 7 cột.** Hai bảng cùng mô tả một lần chấm điểm sẽ lệch nhau — và lúc đó không ai biết bảng nào đúng |
| Tạo `ai.lead_outcomes` mỏng (chỉ `contact_id` + `outcome` + `outcome_at`) | Không trùng cột, Track B tự chủ | Lúc huấn luyện phải join `features` (schema `sales`) với `outcome` (schema `ai`) — mà **ADR-0002 cấm ai-service đọc thẳng `sales`**. Bế tắc đúng ở chỗ cần dùng nhất |

### Quyết định

**Đề nghị Track A thêm ba cột vào `sales.lead_scores`** bằng một migration dải V1xx:

```sql
ALTER TABLE sales.lead_scores
    ADD COLUMN rule_score  smallint,       -- điểm quy tắc, làm đối chứng cho model
    ADD COLUMN outcome     varchar(10),    -- WON | LOST | NULL nếu chưa biết
    ADD COLUMN outcome_at  timestamptz;

ALTER TABLE sales.lead_scores
    ADD CONSTRAINT ck_lead_scores_outcome
        CHECK (outcome IS NULL OR outcome IN ('WON','LOST'));

-- Nhãn chỉ có nghĩa khi biết nó được gán lúc nào.
ALTER TABLE sales.lead_scores
    ADD CONSTRAINT ck_lead_scores_outcome_at
        CHECK ((outcome IS NULL) = (outcome_at IS NULL));
```

**Không tạo `ai.lead_features`.** Đề xuất cụ thể gửi Track A:
[`docs/contracts/de-xuat-track-a-lead-scores-outcome.md`](../contracts/de-xuat-track-a-lead-scores-outcome.md).

### Vòng phản hồi — ai ghi cột `outcome`

Đây là phần Master Plan §5.10.2 nói *"phải thống nhất với Backend ngay Tuần 1"*, và ước lượng
**2 giờ nếu chốt sớm, vài ngày nếu phát hiện ở Tuần 6**.

```
java-core                                  ai-service
─────────                                  ──────────
thương vụ đóng
   └─► phát crm.deal.closed
       { contact_id, lead_id, outcome, closed_at }
                    │
                    └──────────────────────► ai-worker consume
                                                  │
                                                  └─► gọi API java-core
                                                      PATCH .../lead-scores/{id}/outcome
```

Hai điểm bắt buộc:

- **ai-service KHÔNG ghi thẳng `sales.lead_scores`** (ADR-0002 · luật #1 của `.claude/CLAUDE.md`
  đã nêu đúng bảng này là ngoại lệ: *"Track A tạo bảng, Track B ghi qua API chứ không ghi thẳng"*).
  Quyết định này **giữ nguyên** ngoại lệ đó, chỉ mở rộng phạm vi từ `score` sang `outcome`.
- **Chống trùng theo `event_id`** phải có sẵn **trước** consumer đầu tiên. Một thương vụ đóng
  có thể sinh sự kiện lặp; ghi `outcome` hai lần không sai, nhưng ghi đè `outcome_at` bằng mốc
  muộn hơn thì làm hỏng phép chia theo thời gian ở §5.10.3.

### Lập luận

**Vì sao không nhân đôi bảng cho tiện.** `features` là cột đắt nhất trong cả hai thiết kế —
nó là ảnh chụp đặc trưng, và toàn bộ giá trị của nó nằm ở chỗ **có đúng một bản**. Hai bảng
cùng lưu `features` cho cùng một lần chấm điểm thì chỉ cần một lần ghi lệch là không còn biết
bản nào phản ánh đúng thứ model đã đọc — mà đó chính là câu hỏi hội đồng sẽ hỏi
(*"vì sao khách này 92 điểm?"*).

**Vì sao `rule_score` đáng thêm dù không bắt buộc.** §5.10.1 yêu cầu so model với bảng điểm
theo luật làm đối chứng. Để `rule_score` cạnh `score` trong cùng một dòng thì phép so là một
câu `SELECT`; để hai nơi thì phải join theo thời điểm, và "thời điểm" ở đây là xấp xỉ.

### Đánh đổi

1. **Phụ thuộc Track A.** Track B không tự mở khoá được việc này. Nếu Track A không làm kịp,
   UC030 vẫn chấm điểm được nhưng **không thu được nhãn** — và mỗi tuần trôi qua là mất đúng
   chừng đó dữ liệu huấn luyện, không lấy lại được.
2. **Lệch Master Plan §5.10.2** ở tên bảng và tên schema. Ai đọc kế hoạch rồi đi tìm
   `ai.lead_features` sẽ không thấy.
3. **Ghi `outcome` qua API chậm hơn ghi thẳng**, và thêm một bề mặt có thể hỏng. Nhưng đây là
   đường bất đồng bộ (không ai đang chờ), nên độ trễ không phải vấn đề — và ADR-0002 là phòng
   thủ chính chống rò rỉ chéo tenant, không đánh đổi được.
4. **`sales.lead_scores` nay phục vụ hai mục đích**: lịch sử chấm điểm cho nghiệp vụ, và tập
   huấn luyện cho model. Hai vòng đời dữ liệu khác nhau — nếu sau này Track A muốn xoá bớt
   bản ghi cũ để gọn bảng, đó là xoá mất dữ liệu huấn luyện. **Phải ghi rõ trong đề xuất.**

---

## Hệ quả

| File | Thay đổi |
|---|---|
| `CLAUDE.md` (gốc) | Bảng mâu thuẫn: mục 2 và 3 → đã chốt; mục 4 → 7 tuần / 2 người |
| `docs/contracts/README.md` | Mục 2, 3 chuyển sang "đã chốt"; thêm đề xuất gửi Track A |
| `docs/contracts/de-xuat-track-a-lead-scores-outcome.md` | **Mới** — bản gửi Track A |
| `.claude/agents/build/rag-engineer.md` · `gate/security-reviewer.md` | Bỏ `[CẦN XÁC NHẬN]` role, ghi thẳng `ai_app` |
| `.claude/agents/build/ml-researcher.md` · `integration-engineer.md` | Ghi chỗ đặt nhãn `outcome` và luật ghi qua API |
| `.claude/agents/docs/thesis-writer.md` | Cập nhật bảng mâu thuẫn |
| `CHANGELOG.md` | Ghi hai quyết định |

### Hai việc điều hành, không phải quyết định kiến trúc

**Lịch và nhân sự: 7 tuần, 2 người.** Master Plan ghi 3 người (Huy · Khanh Lan · AI R&D),
`.claude/CLAUDE.md` ghi 19 tuần. Thực tế: **7 tuần / 49 ngày theo kế hoạch xlsx, nhóm 2 người**.
Hệ quả cần nhớ: Ngày 7 của kế hoạch dự kiến *"buổi 3 người gõ tay 250–300 câu hỏi"* — với 2
người thì hoặc kéo dài buổi đó, hoặc giảm chỉ tiêu và ghi rõ trong báo cáo. **Không** giảm
xuống dưới 250 mẫu: đó là điều kiện cần của toàn bộ Chương 5.

**Bộ tên topic Kafka: hoãn có chủ đích.** §2.6 khai 8 topic, repo đang có 5 topic `crm.*.v1`.
Chốt khi thực sự viết producer/consumer đầu tiên (Ngày 12), không chốt trước — lúc đó mới biết
payload thật cần gì. Đây là **hoãn**, không phải bỏ quên: `integration-engineer` phải hỏi trước
khi viết dòng Kafka đầu tiên.

## Kiểm chứng

```bash
# Role đúng tên và KHÔNG phải chủ bảng
docker compose exec -T postgres psql -U ai_app -d thesis_crm -c "SELECT current_user;"
docker compose exec -T postgres psql -U crm_owner -d thesis_crm -c \
  "SELECT tablename, tableowner FROM pg_tables WHERE schemaname='ai';"   # owner phải là crm_owner

# Ba cột mới (sau khi Track A chạy migration)
docker compose exec -T postgres psql -U crm_owner -d thesis_crm -c \
  "\d sales.lead_scores" | grep -E "rule_score|outcome"

# ai_app KHÔNG chạm được schema sales — ADR-0002 còn hiệu lực
docker compose exec -T postgres psql -U ai_app -d thesis_crm -c \
  "SELECT 1 FROM sales.lead_scores LIMIT 1;"     # phải nổ: permission denied for schema sales
```
