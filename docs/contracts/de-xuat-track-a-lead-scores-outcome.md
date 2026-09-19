# Đề xuất gửi Track A — thêm 3 cột vào `sales.lead_scores`

**Từ:** Track B (module AI) · **Gửi:** Track A (java-core)
**Ngày:** 19/09/2026 · **Căn cứ:** ADR-0016 · Master Plan §5.10.2 · kế hoạch 49 ngày Ngày 3, 29
**Ước lượng:** ~2 giờ. Master Plan ghi rõ: *"mất 2 giờ nếu chốt ở Tuần 1, mất vài ngày nếu
phát hiện ở Tuần 6."*

---

## Tóm tắt một đoạn

UC030 chấm điểm Lead và ghi vào `sales.lead_scores`. Nhưng bảng đó **không có chỗ ghi kết quả
thực tế** — khách đó cuối cùng có mua hay không. Thiếu cột này thì model chấm điểm mãi mà
không bao giờ học được từ thực tế: không có nhãn thì không có dữ liệu huấn luyện cho phiên
bản sau.

Xin Track A thêm **3 cột** vào bảng đã có, thay vì Track B tạo một bảng mới nhân đôi 7 cột.

## Vì sao là việc của Track A

`sales.lead_scores` nằm trong schema `sales` — **schema của Track A**, tạo ở `V113`, dải V1xx.
Luật #1 của dự án: hai làn không bao giờ ghi vào dải migration của nhau. Track B không tự
thêm cột được.

Track B **đã cân nhắc tự tạo bảng riêng** `ai.lead_features` trong dải V2xx và **quyết định
không làm**, vì bảng đó sẽ nhân đôi 7 cột đã có ở `sales.lead_scores` — trong đó có `features`
(ảnh chụp đặc trưng). Hai bảng cùng mô tả một lần chấm điểm thì sớm muộn lệch nhau, và lúc đó
không ai biết bản nào phản ánh đúng thứ model đã đọc. Lập luận đầy đủ: ADR-0016.

## Migration đề nghị

Dải V1xx, số hiệu do Track A chọn (dự kiến `V116`):

```sql
-- V116__lead_scores_nhan_ket_qua.sql
--
-- Vòng phản hồi cho UC030: biến dữ liệu vận hành thành dữ liệu huấn luyện.
-- Không có ba cột này thì model chấm điểm không bao giờ học được từ thực tế.
-- Căn cứ: Master Plan §5.10.2 · ADR-0016.

ALTER TABLE sales.lead_scores
    ADD COLUMN rule_score  smallint,       -- điểm theo bảng luật, làm đối chứng cho model
    ADD COLUMN outcome     varchar(10),    -- WON | LOST | NULL nếu chưa biết kết quả
    ADD COLUMN outcome_at  timestamptz;    -- thời điểm biết kết quả

ALTER TABLE sales.lead_scores
    ADD CONSTRAINT ck_lead_scores_rule_score
        CHECK (rule_score IS NULL OR rule_score BETWEEN 0 AND 100);

ALTER TABLE sales.lead_scores
    ADD CONSTRAINT ck_lead_scores_outcome
        CHECK (outcome IS NULL OR outcome IN ('WON','LOST'));

-- Nhãn chỉ có nghĩa khi biết nó được gán lúc nào: hai cột phải cùng NULL
-- hoặc cùng có giá trị. Thiếu ràng buộc này thì phép chia theo thời gian
-- khi huấn luyện (§5.10.3) không kiểm được.
ALTER TABLE sales.lead_scores
    ADD CONSTRAINT ck_lead_scores_outcome_at
        CHECK ((outcome IS NULL) = (outcome_at IS NULL));

-- Truy vấn huấn luyện luôn là "lấy các bản ghi ĐÃ có nhãn, theo tenant, theo thời gian".
CREATE INDEX idx_lead_scores_outcome
    ON sales.lead_scores (tenant_id, outcome_at)
    WHERE outcome IS NOT NULL;

COMMENT ON COLUMN sales.lead_scores.rule_score IS
    'Điểm theo bảng luật tại cùng thời điểm, làm đối chứng cho model (§5.10.1)';
COMMENT ON COLUMN sales.lead_scores.outcome IS
    'Kết quả thực tế, java-core cập nhật ngược khi deal đóng. Nhãn huấn luyện của UC030';
```

Ba cột đều `NULL`-able nên **không cần backfill** và không ảnh hưởng bản ghi đang có.

## Vòng phản hồi — ai ghi cột `outcome`

```
java-core                                     ai-service
─────────                                     ──────────
deal chuyển sang CLOSED_WON / CLOSED_LOST
   └─► phát crm.deal.closed
       { event_id, tenant_id, contact_id,
         lead_id, outcome, closed_at }
                    │
                    └─────────────────────────► ai-worker consume
                                                     │  (chống trùng theo event_id)
                                                     └─► PATCH /api/v1/lead-scores/{id}/outcome
                                                         { outcome, outcomeAt }
```

**Track B không ghi thẳng `sales.lead_scores`** — đi qua API của java-core, đúng ADR-0002 và
đúng ngoại lệ đã ghi ở luật #1 (*"Track A tạo bảng, Track B ghi qua API chứ không ghi thẳng"*).
Quyết định này giữ nguyên ngoại lệ đó, chỉ mở rộng phạm vi từ `score` sang `outcome`.

### Track A cần làm 3 việc

| # | Việc | Ghi chú |
|---|---|---|
| 1 | Chạy migration V116 ở trên | Số hiệu do Track A chọn |
| 2 | Phát sự kiện `crm.deal.closed` khi deal đóng | Kèm `contact_id`, `lead_id`, `outcome`, `closed_at`, và `event_id` để chống trùng |
| 3 | Mở endpoint `PATCH /api/v1/lead-scores/{id}/outcome` | Hoặc đề xuất đường khác — Track B theo |

### Track B sẽ làm

| # | Việc | Khi nào |
|---|---|---|
| 1 | Consumer `crm.deal.closed`, chống trùng theo `event_id` | Ngày 29 (UC030) |
| 2 | Gọi API cập nhật `outcome` | Ngày 29 |
| 3 | Ghi `rule_score` cùng lúc ghi `score` | Ngày 29 |

## Hai điều xin Track A lưu ý

**1. Đừng xoá bản ghi cũ để gọn bảng.** Sau thay đổi này `sales.lead_scores` phục vụ **hai
mục đích**: lịch sử chấm điểm cho nghiệp vụ, và tập huấn luyện cho model. Hai vòng đời dữ
liệu khác nhau. Xoá bản ghi 6 tháng trước là xoá mất đúng phần dữ liệu có nhãn đầy đủ nhất —
vì nhãn chỉ đến sau khi deal đóng, tức là các bản ghi **cũ** mới là các bản ghi **có nhãn**.
Cần dọn bảng thì báo Track B trước.

**2. `outcome_at` là thời điểm biết kết quả, không phải thời điểm chấm điểm.** Khoảng cách
giữa `scored_at` và `outcome_at` chính là thứ dùng để chia tập train/test **theo thời gian**.
Chia ngẫu nhiên sẽ gây rò rỉ thời gian và PR-AUC đẹp giả tạo (§5.10.3) — nên hai mốc này phải
tách bạch, không dùng chung một cột.

## Nếu Track A không làm kịp

UC030 vẫn chấm điểm được — chỉ là **không thu được nhãn**. Mỗi tuần trôi qua là mất đúng chừng
đó dữ liệu huấn luyện, và **không lấy lại được** (không thể hồi tố `features` tại thời điểm đã
qua). Vì vậy việc này nên làm sớm ngay cả khi UC030 chưa xong.

Phương án dự phòng nếu bị từ chối: Track B tạo `ai.lead_features` đầy đủ ở dải V2xx, chấp nhận
nhân đôi 7 cột. Track B **không muốn** phương án này — lý do ở ADR-0016 mục *Các phương án đã
cân nhắc*.
