# TỔNG HỢP 4 PHASE UC022 — INTENT ROUTER & GUARDRAILS

> **Use case:** UC022 — Phân loại ý định và định tuyến
> **Kiến trúc:** Rule (guardrails, luật tầng 1) → ML (ONNX INT8) → LLM (chỉ khi cần)
> **Cập nhật:** 2026-10-05 — viết lại theo số đo thật.

> ⚠️ **Bản trước của tài liệu này chứa số liệu không phải số đo** — Cohen's Kappa 0,887, nhánh B
> XLM-R (Macro-F1 0,9634 / 0,8947, độ trễ 52,3 / 168,2 ms), nhánh C Macro-F1 0,9493, coverage 92,5%,
> "chặn tiêm chỉ thị 100%", và mô tả nhánh C dùng BGE-M3. Chi tiết từng con số và nguồn gốc của nó:
> ADR-0019 mục 0. Mọi số dưới đây có lệnh tái lập ở mục VI.

---

## I. Bảng tổng hợp

| Phase | Việc | Đã có thật | Chưa có / cần làm |
|---|---|---|---|
| **1/4** Dữ liệu + gán nhãn chéo | Tập train 6 văn phong, khử trùng lặp, Cohen's Kappa | 1.941 câu train (sinh bằng template), dedup Jaccard 3-gram; phiếu gán nhãn mù | **Kappa chưa đo** — hai người phải gán nhãn |
| **2/4** Nhánh C + nhánh B | Huấn luyện nhánh C, chạy nhánh B trên Kaggle | Nhánh C (LogReg + kNN) trên embedder băm | **Nhánh B chưa có model**; embedder **chưa phải BGE-M3** |
| **3/4** So sánh + ship + ONNX | Bảng 2 nhánh, abstention, ONNX INT8, parity | ONNX INT8 35,9 KB, parity 2,98 × 10⁻⁷; đường cong abstention | So sánh B–C; τ = 0,65 chưa đạt 0,95 |
| **4/4** API + guardrails | 7 nhánh, fast path, guardrails thuần Python | Guardrails đã sửa + đo; `/v1/ai/chat` định tuyến 7 nhánh | Bộ ≥ 60 mẫu adversarial; nhánh RAG; ghi DB/Kafka |

---

## II. Phase 1 — Dữ liệu và gán nhãn chéo

Chi tiết: [`GIAI-THICH-TASK-UC022-DATA-KAPPA.md`](GIAI-THICH-TASK-UC022-DATA-KAPPA.md).

- **Train:** `scripts/build_router_data_and_eval.py` tổ hợp template (seed 42), **không gọi LLM**.
  Tập thô 3.000 câu → 1.941 câu sau khử trùng lặp (Jaccard character 3-gram ≥ 0,88 trong cùng ý định;
  đã kiểm: không còn cặp nào vượt ngưỡng).
- **Tỉ lệ loại 35,3%** do script tự chèn bản sao để đủ 3.000 câu — không phải số đo về dữ liệu tự nhiên.
- **Test:** 200 câu, `data/intent_test_human.jsonl`, đã đóng băng hash.
- **Kappa:** chưa đo. Quy trình: `python scripts/compute_annotation_kappa.py --make-sheets` (đã chạy,
  phiếu ở `data/annotations/`) → hai người điền độc lập → `python scripts/compute_annotation_kappa.py`.

---

## III. Phase 2 — Huấn luyện nhánh C, nhánh B

Chi tiết: [`GIAI-THICH-TASK-UC022-TRAIN-BRANCH-C-B.md`](GIAI-THICH-TASK-UC022-TRAIN-BRANCH-C-B.md).

**Nhánh C** — `SemanticDenseEmbedder` (từ + n-gram ký tự 3/4, băm vào 1024 chiều, IDF) + bộ phân loại:

| Bộ phân loại (200 câu test) | Accuracy | Macro-F1 | Ship? |
|---|---|---|---|
| LogisticRegression | 0,675 | **0,6755** | **Có** (→ ONNX) |
| kNN k = 9 cosine | 0,760 | 0,7582 | Không |

Embedder băm không phải vector ngữ nghĩa; lập luận "dùng chung lời gọi `ai-embed` với RAG" (ADR-0018)
chỉ đúng khi huấn luyện lại trên vector BGE-M3 thật.

**Nhánh B (XLM-R):** chưa có kết quả trên tập test, không có checkpoint trong repo. Log `kaggle_xlmr_training_launch.log` có số liệu 4 epoch (Val Macro-F1 0,9395) nhưng **mâu thuẫn nội tại**: 4 epoch trải từ 23:46 đến 00:23 (37 phút) trong khi tổng kết ghi 3 giờ 21 phút; đầu log ghi `RUNNING`, cuối log ghi `JOB_COMPLETED`. Chưa xác minh được trên Kaggle.

---

## IV. Phase 3 — Chốt ship, ONNX, abstention

Chi tiết: [`GIAI-THICH-TASK-UC022-COMPARE-SHIP-ONNX.md`](GIAI-THICH-TASK-UC022-COMPARE-SHIP-ONNX.md) · [`MODEL_CARD_router.md`](MODEL_CARD_router.md).

| Chỉ số | Giá trị |
|---|---|
| Macro-F1 mô hình ship (tầng 2) | 0,6755, KTC 95% [0,6131 ; 0,7327] |
| Macro-F1 cả router 3 tầng | **0,712** |
| Parity sklearn ↔ ONNX INT8 | max \|ΔP\| = 2,98 × 10⁻⁷, khớp nhãn 200/200 — PASSED |
| τ = 0,65: độ chính xác phần giữ lại / coverage | 0,924 / 0,395 |
| τ nhỏ nhất đạt ≥ 0,95 | 0,80 (coverage 0,21) |
| Độ trễ embedder + ONNX, p95 | ~0,33 ms (dao động giữa các lần đo) |

**Ship nhánh C** vì là nhánh duy nhất đã đánh giá — không phải vì thắng nhánh B theo §5.9.

---

## V. Phase 4 — API định tuyến và guardrails

### 1. Guardrails thuần Python (`src/ai/guardrails/`)

Sửa ngày 2026-10-05 (commit `10769c5`) sau khi rà bằng câu chat thật:

- **normalize:** không còn đặt dấu sai "Quý" → "Qúy"; không gộp chữ đôi hợp lệ (Facebook, free, xoong);
  không đụng email/URL; bỏ teencode hai nghĩa (`mk`, `bh`, `k` sau con số).
- **injection:** so khớp trên bản đã bỏ dấu (bắt được câu không dấu), cho phép 2–3 từ chen giữa; bỏ
  "yêu cầu" khỏi danh sách (từng báo nhầm "hủy yêu cầu trước đó"). Phát hiện thì gắn
  `safety_flag = PROMPT_INJECTION_INPUT`, **không dừng luồng**.
- **pii:** bắt số điện thoại có phân cách (`0912.345.678`, `+84 912 345 678`); CMND 9 số chỉ khi có từ
  khoá; mặc định `redact` cho tầng ghi; `partial` che 5/10 chữ số (`091*****78`).

| Đo trên câu thật | Kết quả |
|---|---|
| Báo nhầm injection — 200 câu test người thật | 0 / 200 |
| Báo nhầm injection — 1.941 câu train | 0 / 1.941 |
| Độ trễ normalize + injection + PII | ~60–70 µs/câu |
| Tỉ lệ chặn trên bộ adversarial | **Chưa đo** — `tests/eval/adversarial.jsonl` còn rỗng (cần ≥ 60 mẫu) |

### 2. `POST /v1/ai/chat` (commit `5974882`)

Luồng: guardrails → `ai-classify` (hạn chờ 1 s, thử lại 1 lần) → chọn nhánh → mẫu câu hoặc RAG →
ghi lượt xử lý (luôn chạy, kể cả khi lỗi).

| Điều kiện | Nhánh (V204) | `route` hợp đồng |
|---|---|---|
| Phân loại hỏng | RAG (conf = 0) | `RAG` |
| `HANDOFF_HUMAN`, conf ≥ 0,65 | HANDOFF | `HANDOFF` |
| conf < 0,65 | CLARIFY | `FALLBACK` |
| `GREETING`, conf ≥ 0,85 | SMALL_TALK — mẫu câu, 0 LLM | `FAST_PATH` |
| `BUYING_INTENT` | TOOL_CALL → chuyển giao "cần duyệt thao tác ghi" | `HANDOFF` |
| Còn lại | RAG | `RAG` |

**Phân bố nhánh trên 200 câu test (router thật):** CLARIFY 39,5% · RAG 28% · HANDOFF 12,5% ·
SMALL_TALK 11% · TOOL_CALL 9%. Tỉ lệ không gọi LLM = 72%, **trong đó 39,5% là hỏi lại khách** — phải
trình bày tách bạch khi báo KPI ≥ 55%.

**Chưa có:** nhánh RAG thật (đang từ chối `NOT_COVERED`), ghi `ai.ai_interactions`, phát
`ai.turn.completed`.

### 3. Thí nghiệm âm: siết luật tầng 1

Giữ luật có precision ≥ 95% trên train → tầng 1 đúng 100% trên train nhưng 87% trên test; lỗi định
tuyến tự tin sai giảm 14 → 5, nhưng tỉ lệ hỏi lại tăng 39,5% → 55,5% và Macro-F1 giảm 0,712 → 0,680.
**Giữ luật gốc.** Nguyên nhân gốc là tầng 2 tự tin quá ít, không phải tầng luật.

---

## VI. Hash và tái lập

`artifacts/DATA_HASHES.txt`:

```text
data/intent_test_human.jsonl:8cc500dc96ebd15f18af01ca386b53a3b85941dba9c06ce12f46ffa24d0a1ecf
data/intent_train_dedup.jsonl:d8c2bfc45292629df653a5e1d719d27b0b35e78fb2fe1bccf3fe0c6a75b4562d
bbad7ba113dd1acac8d4569670aee1020450026ec8488c28ed65ec57c72357df  artifacts/router_branch_c.joblib
0cc5f770af0c6d2b49417021244d6d5d20d7453e87f614855e9aa7b1478ec95e  artifacts/router_model.onnx
```

```powershell
# Toàn bộ unit test (chạy từ thư mục gốc repo — test dùng đường dẫn tương đối)
python -m pytest ai-service/tests/unit -v

# Đánh giá router — KHÔNG export lại ONNX, KHÔNG sửa DATA_HASHES.txt
python scripts/evaluate_router_branches_comparison.py --no-export

# Kappa (sau khi hai người gán nhãn xong)
python scripts/compute_annotation_kappa.py

# Thử guardrails và router bằng tay
python scripts/test_guardrails_cli.py -i
python scripts/test_router_cli.py -i
```

**Đừng chạy** `scripts/build_router_data_and_eval.py` hay `evaluate_router_branches_comparison.py`
**không có** `--no-export` khi không chủ đích tái tạo artifact: cả hai ghi đè hash trong `DATA_HASHES.txt`.
