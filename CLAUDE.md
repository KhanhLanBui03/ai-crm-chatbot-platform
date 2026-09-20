# Module AI — luật dùng chung cho mọi agent

Nền tảng Chatbot AI CRM. Module AI phụ trách **17 use case trong 21 ngày** (21/09 →
11/10/2026, 2 người), kiến trúc **hai tầng** theo `docs/MASTER_PLAN_AI_CRM_v8.md.docx`
(§3.9.2) và kế hoạch `docs/Ke-hoach-21-ngay-Module-AI-CRM.xlsx`.

Đặc tả có **20 UC**; ba UC nhóm MCP — **UC021, UC024, UC028** — đã chuyển sang *Mở rộng sau
đồ án*. Đừng khởi động chúng: cắt cả nhóm gọn hơn làm dở một phần. Nhưng **nhánh ý định
"gọi công cụ" vẫn giữ nguyên** trong taxonomy 7 nhánh của UC022, chỉ định tuyến sang chuyển
giao — bỏ nhánh khỏi taxonomy là làm lệch toàn bộ telemetry.

**Viết bằng tiếng Việt** — tài liệu, comment, commit message. Tên file và định danh trong code
thì không dấu.

## Triết lý xử lý: Rule → ML → LLM

Thứ tự này là **ràng buộc chi phí và độ trễ**, không phải sở thích:

```
1. Rule    regex, chuẩn hoá, allow-list   — thuần Python, ~0 ms,  0 đồng
2. ML      router ý định, lead scorer     — ONNX CPU,   ~60 ms,  0 đồng
3. LLM     sinh câu trả lời, trích xuất   — API ngoài, ~2.500 ms, tính tiền
```

**KPI: ≥ 55% lượt KHÔNG gọi LLM** (§1.6). Đường nhanh kích hoạt khi `confidence >= 0,85` và
intent thuộc danh sách đi nhanh. Trước khi thêm một lời gọi LLM, hỏi: bước này có làm được
bằng rule hay ML không?

## Sáu luật không bao giờ vi phạm

1. **`tenant_id` LUÔN từ ngữ cảnh đã xác thực** — header `X-Tenant-Id` do gateway gắn
   (`ai-service/src/api/deps.py`). **Không bao giờ** từ body/query/path. Thiếu thì ném lỗi
   ngay, không mặc định về tenant nào.
2. **AI không ghi bảng nghiệp vụ CRM.** Chỉ đọc qua REST hoặc phát sự kiện Kafka (§2.3,
   ADR-0002). Nối thẳng DB là biến mô hình ngôn ngữ thành đường vòng qua RLS — khi bị tiêm
   chỉ thị thì đó chính là đường khai thác.
3. **`SET LOCAL app.tenant_id` trong CÙNG transaction** với truy vấn, đặt ngay sau
   `pool.acquire()`. Runtime dùng role **không phải chủ bảng** — chủ bảng bypass RLS kể cả
   khi đã `FORCE`.
4. **Mọi truy vấn vector lọc `tenant_id` ngay trong truy vấn** (ADR-0007, bề mặt T6).
5. **`ai-service` không nạp model.** Train trên GPU Kaggle, chạy trên CPU ở `inference/`.
   Cổng chặn CI mỗi build: `pip list | grep -E "onnxruntime|torch|xgboost"` phải **RỖNG**.
6. **Contract-first.** Sửa `docs/openapi/` hay `docs/events/` là **đơn phương đổi hợp đồng
   liên làn** — báo Track A trước. Nháp để ở `docs/contracts/`.

## Nhãn `[R&D]` và `[PRODUCTION]`

Mỗi khối mã trong tài liệu và mỗi module mới ghi rõ một trong hai:

| Nhãn | Chạy ở đâu | Ví dụ |
|---|---|---|
| `[R&D]` | Kaggle GPU, notebook, không vào image nào | `notebooks/06_export_onnx.ipynb` |
| `[PRODUCTION]` | Trong image, phục vụ request thật | `ai-service/src/**`, `inference/src/**` |

Lẫn hai thứ là cách `torch` chui được vào image production.

## Mười agent — phân công thư mục

Đặt ở `.claude/agents/`. **Không agent nào có tool `Agent`** — người dùng là điều phối viên
duy nhất. Hook `.claude/hooks/guard_paths.py` chặn ghi ngoài phạm vi.

| Agent | Vai | Được ghi vào | UC sở hữu |
|---|---|---|---|
| `ml-researcher` | xây | `notebooks/` `artifacts/` `data/` | UC022, UC030, UC038 |
| `inference-engineer` | xây | `inference/` | — (sở hữu cổng SLO) |
| `rag-engineer` | xây | `ai-service/src/ai/{rag,db}/` `migration/` `tests/` | UC018–020, 023, 025, 041 |
| `agent-orchestrator` | xây | `src/ai/{orchestrator,extraction,guardrails,inference}/` `service.py` `tests/` | UC014, 026, 027, 029 |
| `integration-engineer` | xây | `src/{api,worker}/` `src/ai/{schemas.py,events,telemetry}/` `tests/` `docs/contracts/` | UC006, 031, 039, 040 — ~~021, 024, 028~~ đã hoãn |
| `platform-engineer` | xây | `*/Dockerfile` `*/k8s/` `*/requirements/` `.github/` `scripts/` | — (sở hữu hạ tầng) |
| `eval-gatekeeper` | gác cổng | **chỉ** `reports/eval/` | — (bảng chỉ số nghiệm thu) |
| `security-reviewer` | gác cổng | **không ghi được** | — (T1–T8) |
| `thesis-writer` | tài liệu | `docs/` `CHANGELOG.md` | — |
| `mentor` | kèm cặp | **không ghi được**, cấm dán lời giải | — |

`ai-service/tests/` dùng chung giữa bốn agent xây — **có chủ đích**. Đọc trước khi sửa.

### Chặn cứng với mọi agent

```
java-core/  gateway/  eureka-server/  web-dashboard/  web-widget/  loadtest/  docker/
data/intent_test_human.jsonl   bộ vàng đã đóng băng   artifacts/DATA_HASHES.txt
```

Hai tệp sau là **tập test đóng băng và sổ hash** — không bao giờ sửa để cải thiện điểm
(đóng băng ở Ngày 2 và Ngày 6). Sửa được chúng thì mọi con số macro-F1 và recall@5 trong báo
cáo mất ý nghĩa. *Chỗ đặt bộ vàng chưa chốt* — `ai-service/tests/eval/golden_set.jsonl` hay
`data/golden_qa.jsonl`; dù nằm ở đâu, đóng băng rồi là cấm sửa.

**Ngoại lệ có chủ đích về `java-core/`:** nhóm 2 người không có ai đóng vai Track A riêng, nên
việc CRM mà module AI cần (migration **V116**, 5 endpoint `/internal/*`, consumer `analytics-cg`)
do chính hai người làm. Nhưng **agent vẫn bị chặn cứng** ở đó — phần java-core làm ở phiên
chính, không giao cho agent AI.

## Bảy chỉ số nghiệm thu §1.6

| Chỉ số | Ngưỡng |
|---|---|
| p95 `/v1/ai/chat` | < 4.000 ms và **không tăng dần** |
| Tổng p95 suy luận CPU | < 480 ms |
| Tỉ lệ lượt không gọi LLM | ≥ 55% |
| recall@5 trên golden set | ≥ 0,85 |
| Độ phủ trích dẫn | ≥ 0,80 |
| Rò rỉ dữ liệu giữa tenant | 0 |
| Image `ai-service` sạch ML runtime | grep RỖNG |

Đầy đủ các chỉ số kèm ngày đo và người chịu trách nhiệm: sheet *Chỉ số nghiệm thu* của
`docs/Ke-hoach-21-ngay-Module-AI-CRM.xlsx`. ⚠️ `.claude/agents/gate/eval-gatekeeper.md` vẫn
liệt kê bảng 28 chỉ số của lịch 49 ngày — sửa trước lần gọi agent đó đầu tiên.

## Ba mốc cắt phạm vi — không lùi lịch, chỉ cắt việc

| Mốc | Hạn | Điều kiện thoát |
|---|---|---|
| **M1** Nền tảng dữ liệu | hết **Ngày 7** (27/09) | Tài liệu thật vào chunks, test cách ly tenant xanh, parity INT8 ≥ 0,995, router đã chốt nhánh ship |
| **M2** Demo luồng chính | hết **Ngày 14** (04/10) | `/v1/ai/chat` end-to-end, recall@5 ≥ 0,85, có video |
| **M3** Nghiệm thu | hết **Ngày 21** (11/10) | 7/7 chỉ số đạt, gói bàn giao, video demo 17 UC + slide |

**Phạm vi khoá ở 17 UC.** Trượt lịch thì cắt **độ sâu** theo đúng thứ tự: rerank → semantic
cache → chiều sâu UC038 → soak 1 giờ. **Không bao giờ bỏ nguyên một UC** — giảm độ sâu thì
được, bỏ hẳn là mất điểm trực tiếp. Lịch không còn ngày đệm thuần: một ngày trượt phải cắt
ngay trong ngày, không lùi sang ngày sau vì ngày sau đã đầy.

## Branch và commit

```
chore/…   feat/…   fix/…   docs/…   data/…
```

Commit message **tiếng Việt không dấu**, mô tả *vì sao* chứ không chỉ *cái gì*:

```
feat(rag): hybrid search mot cau SQL, RRF k=60

Gop lan vector va lan tu khoa trong mot truy van thay vi hai truy van roi
hop nhat o Python — tranh phai chuan hoa hai thang diem khac nhau.

Recall@5 0,87 tren golden set 84 cap (truoc: 0,79 dense-only).
```

Không ghi `Co-Authored-By: Claude` hay `Generated with Claude Code` vào commit lẫn PR.

## Đọc thêm ở đâu — đừng đoán

| Cần biết | Đọc |
|---|---|
| Cây thư mục, "đặt file mới ở đâu" | `ai-service/README.md` · `ai-service/CLAUDE.md` |
| Vì sao chọn như vậy | `docs/adr/` — 16 ADR (0001–0016), ADR kế tiếp là **0017** |
| Việc từng ngày, ngưỡng từng chỉ số | `docs/Ke-hoach-21-ngay-Module-AI-CRM.xlsx` — đọc sheet *Trạng thái xuất phát* trước |
| Đặc tả 20 UC AI (17 trong phạm vi) | `docs/Dac-ta-UseCase-Module-AI.docx` |
| Kiến trúc hai tầng, ngân sách độ trễ | `docs/MASTER_PLAN_AI_CRM_v8.md.docx` §3.2, §5.3 |
| Hợp đồng liên làn | `docs/openapi/` · `docs/events/` — nháp ở `docs/contracts/` |
| Bảo mật, dữ liệu cá nhân | `docs/threat-model.md` — T1–T8 |
| Cột · kiểu · khoá của bảng | `docs/erd-mermaid.md` |
| Quy ước code Python chi tiết | `.claude/rules/ai-service.md` |

## Mâu thuẫn tài liệu — trạng thái

**Đã chốt, đừng mở lại:**

| Vấn đề | Chốt | Nguồn |
|---|---|---|
| Số chiều vector | **1024** (không phải 768 như §4.2) | ADR-0015 |
| Schema kho tri thức | **`knowledge.knowledge_*`** (không phải `ai.chunks`) | ADR-0015 |
| Cổng chặn CI | **3 gói** `onnxruntime\|torch\|xgboost` (không phải 6) | ADR-0015 |
| Công cụ migration | **Flyway V2xx** (không phải Alembic) | ADR-0015 |
| Tên role runtime | **`ai_app`** (Master Plan §4.2 ghi `ai_service` — sai) | ADR-0016 |
| Nhãn huấn luyện UC030 | **`sales.lead_scores` + 3 cột**, KHÔNG tạo `ai.lead_features` | ADR-0016 |
| Lịch và nhân sự | **3 tuần / 21 ngày · 2 người** · 17 UC (Master Plan ghi 7 tuần, 3 người, 20 UC) | kế hoạch 21 ngày |

**Còn treo — hỏi, đừng tự quyết:**

| Vấn đề | Trạng thái |
|---|---|
| **Tên endpoint** — `service.py` ghi `/v1/ai/**`, `docs/openapi/` ghi `/v1/answer` | Chốt **trước Ngày 3** (route đầu tiên). Đề xuất theo `/v1/ai/**` (§2.5) |
| **Bộ tên topic Kafka** — 8 (§2.6) vs 5 `crm.*.v1` (repo) | Chốt **trước Ngày 5** (consumer đầu tiên). `crm.deal.closed` chưa có trong cả hai bộ mà UC030 cần ở Ngày 18 |
| **Chỗ đặt bộ vàng** — `tests/eval/golden_set.jsonl` vs `data/golden_qa.jsonl` | Chốt **trước Ngày 6**. Hai chỗ đang song song, một file rỗng một file chưa tồn tại |
| **Cỡ tập test người thật** — ADR-0016 ghi ≥ 250, lịch 21 ngày vừa 200 | Chốt **ở Ngày 2** (buổi gõ chung). Cả bốn dòng này gộp thành **ADR-0017** |
| **Ngưỡng recall@5** — §1.6 ghi 0,85, `.claude/rules/rag-eval.md` ghi 0,80 | Kế hoạch 21 ngày theo **0,85**; sửa rule cho khớp khi viết `rag/` |
| **Track A thêm 3 cột `sales.lead_scores`** | Đã soạn đề xuất, **chưa gửi**: `docs/contracts/de-xuat-track-a-lead-scores-outcome.md` |

Với 2 người thay vì 3: buổi gõ tay chuyển về **Ngày 2**, kế hoạch 21 ngày đặt **200 câu**
trong khi ADR-0016 ghi không dưới 250 (giả định 3 người). Chưa ADR nào chốt lại — quyết ở
Ngày 2 và **ghi rõ lý do vào ADR-0017 lẫn báo cáo**; im lặng rồi nộp 200 mới là thứ mất điểm.
Đây là điều kiện cần của toàn bộ Chương 5: không có tập test người thật thì hai nhánh đối
chứng §5.9 đang so trên một bài toán giả. Tập test đóng băng ngay sau buổi gõ.

Luật nào không truy được về `docs/` thì ghi `[CẦN XÁC NHẬN]` và hỏi — đừng đoán.
