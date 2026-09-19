# Module AI — luật dùng chung cho mọi agent

Nền tảng Chatbot AI CRM. Module AI phụ trách **20 use case**, kiến trúc **hai tầng** theo
`docs/MASTER_PLAN_AI_CRM_v8.md.docx` (§3.9.2) và kế hoạch 49 ngày
`docs/Ke-hoach-49-ngay-Module-AI-CRM.xlsx`.

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
| `integration-engineer` | xây | `src/{api,worker}/` `src/ai/{schemas.py,mcp_client,events,telemetry}/` `tests/` `docs/contracts/` | UC006, 021, 024, 028, 031, 039, 040 |
| `platform-engineer` | xây | `*/Dockerfile` `*/k8s/` `*/requirements/` `.github/` `scripts/` | — (sở hữu hạ tầng) |
| `eval-gatekeeper` | gác cổng | **chỉ** `reports/eval/` | — (28 chỉ số) |
| `security-reviewer` | gác cổng | **không ghi được** | — (T1–T8) |
| `thesis-writer` | tài liệu | `docs/` `CHANGELOG.md` | — |
| `mentor` | kèm cặp | **không ghi được**, cấm dán lời giải | — |

`ai-service/tests/` dùng chung giữa bốn agent xây — **có chủ đích**. Đọc trước khi sửa.

### Chặn cứng với mọi agent

```
java-core/  gateway/  eureka-server/  web-dashboard/  web-widget/  loadtest/  docker/
data/intent_test_human.jsonl   data/golden_qa.jsonl   artifacts/DATA_HASHES.txt
```

Ba tệp sau là **tập test đóng băng và sổ hash** — không bao giờ sửa để cải thiện điểm
(Ngày 7, Ngày 27). Sửa được chúng thì mọi con số macro-F1 và recall@5 trong báo cáo mất ý nghĩa.

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

Đầy đủ **28 chỉ số** kèm ngày đo: sheet *Chỉ số nghiệm thu* của kế hoạch 49 ngày, và
`.claude/agents/gate/eval-gatekeeper.md`.

## Ba mốc cắt phạm vi — không lùi lịch, chỉ cắt việc

| Mốc | Hạn | Điều kiện thoát |
|---|---|---|
| **M1** Nền tảng dữ liệu | hết Ngày 14 | Nạp được tài liệu thật vào chunks, test cách ly tenant xanh, parity ≥ 0,995 |
| **M2** Demo luồng chính | hết Ngày 28 | `/v1/ai/chat` end-to-end, recall@5 ≥ 0,85, có video. **Chưa đạt → CẮT rerank và UC024/UC028**, dồn sang Tuần 6 |
| **M3** Nghiệm thu | hết Ngày 49 | 7/7 chỉ số đạt, gói bàn giao 9 hạng mục, p95 EKS lệch < 20% so với (C) |

**Không nhận thêm UC mới sau Tuần 5** — Tuần 6 và 7 đã khoá cho tích hợp và ổn định hoá (§2.3).

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
| Vì sao chọn như vậy | `docs/adr/` — 15 ADR |
| Việc từng ngày, ngưỡng từng chỉ số | `docs/Ke-hoach-49-ngay-Module-AI-CRM.xlsx` |
| Đặc tả 20 UC AI | `docs/Dac-ta-UseCase-Module-AI.docx` |
| Kiến trúc hai tầng, ngân sách độ trễ | `docs/MASTER_PLAN_AI_CRM_v8.md.docx` §3.2, §5.3 |
| Hợp đồng liên làn | `docs/openapi/` · `docs/events/` — nháp ở `docs/contracts/` |
| Bảo mật, dữ liệu cá nhân | `docs/threat-model.md` — T1–T8 |
| Cột · kiểu · khoá của bảng | `docs/erd-mermaid.md` |
| Quy ước code Python chi tiết | `.claude/rules/ai-service.md` |

## Mâu thuẫn tài liệu chưa chốt — hỏi, đừng tự quyết

| # | Vấn đề | Hai nguồn |
|---|---|---|
| 1 | Bộ tên topic Kafka | 8 topic (§2.6) vs 5 `crm.*.v1` (`create-topics.sh`, `docs/events/`) |
| 2 | Tên role runtime | `ai_service` (Master Plan §4.2) vs `ai_app` (repo, `docker-compose.yml:239`) |
| 3 | Bảng `ai.lead_features` | Kế hoạch cần (Ngày 3, 29); **không migration nào tạo** |
| 4 | Lịch và nhân sự | 7 tuần / 3 người (Master Plan) vs 19 tuần / 2 người (`.claude/CLAUDE.md`) |

Đã chốt ở **ADR-0015**: vector **1024** chiều · schema `knowledge.*` · cổng chặn CI **3 gói** ·
giữ Flyway V2xx thay vì Alembic.

Luật nào không truy được về `docs/` thì ghi `[CẦN XÁC NHẬN]` và hỏi — đừng đoán.
