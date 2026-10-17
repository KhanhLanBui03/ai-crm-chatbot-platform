# Sổ đăng ký model — `artifacts/MODEL_REGISTRY.md`

Nguồn sự thật cho câu hỏi "model nào đang chạy ở đâu, phiên bản nào, đo được bao nhiêu".
Master Plan §3.9.2 · §5.8.

Mỗi artifact lên S3 **bắt buộc** có một dòng ở đây và một `MODEL_CARD_<tên>.md` kèm theo.
Không có Model Card thì artifact không được coi là đã bàn giao (§6.9).

---

## Bảng đăng ký

| model_id | Vai trò | Service | UC | Cấp vCPU | sha256 | parity | p95 đo thật | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| `bge-m3-int8` | encoder | `ai-embed` | UC019, UC023 | **4 vCPU** ([ADR-0034](../docs/adr/0034-chot-cap-vcpu-ai-embed-ai-rerank.md)) | `71e2aa91…2723510` (.onnx)<br>`65925f1e…3f2703` (.onnx.data) | **0,98476 — TRƯỢT, chưa phân xử** | câu hỏi: p50 24 / p95 **69 ms** · đoạn: p50 192 / p95 **638 ms**, 3,99 đoạn/s — 4 vCPU ghim luồng, Docker trên M1 (11/10); ngưỡng 120 ms là số kế hoạch | 🟢 **Ship 06/10** — lô 1, image `ai-inference:dev` 383 MB; recall@5 hybrid 0,740 / dense 0,800 trên bộ vàng v1 — [ADR-0021](../docs/adr/0021-cong-parity-int8-truot-phan-xu-bang-recall.md) |
| `bge-m3-fp32` | encoder (đối chứng) | — | — | — | `ff81fec3…415fa5f` (.onnx)<br>`303112e4…d8e1f0` (.data) | — (mốc gốc) | — | ⚪ **Bỏ đo đối chứng 06/10** — `.data` không có trên máy dev, không tải (ADR-0021 cập nhật 2) |

> **Đã đo Ngày 15 (11/10)** trên đúng cấu hình triển khai — `inference/bench/bench_cpu.py`, số đầy đủ ở
> `docs/report/benchmark-ngay15-2026-10-11.md`. Ghi chú gốc bên dưới giữ lại để biết vì sao số Kaggle không dùng.
>
> **Cột `p95 đo thật` cố ý để trống tới Ngày 15.** Đã đo thử trên Kaggle nhưng **con số không
> tái lập**: cùng một notebook, hai lượt chạy cho `fp32 124,5 / 63,8 ms` và `76,5 / 37,2 ms`
> — chênh 1,6 lần, vì máy batch sạch hơn máy của phiên tương tác. Ghi con số đó vào cột này là
> ghi một p95 không kiểm chứng được.
>
> Thứ **giữ nguyên** giữa hai lượt là **tỉ lệ fp32/INT8 ≈ 2,05 lần** — đó mới là kết luận dùng
> được: INT8 tăng tốc gấp đôi. p95 tuyệt đối đo ở Ngày 15 trên đúng cấu hình triển khai.
>
> Đối chiếu: 4 `sha256` ở trên **trùng khít** giữa hai lượt chạy độc lập ⇒ artifact tái lập
> được từng byte, chỉ có phép đo thời gian là không.
| `bge-reranker-v2-m3-int8` | cross-encoder | `ai-rerank` | UC023 | **4 vCPU** ([ADR-0034](../docs/adr/0034-chot-cap-vcpu-ai-embed-ai-rerank.md); Khối A ghi "4 không nhanh hơn" — đã đính chính) | `93cd7fb0…c1c0fde2` (.onnx)<br>`db41e6b7…e33eff97` (.onnx.data)<br>`69564b69…bf379c15` (tokenizer) | **ĐẠT** — nDCG@5 INT8 − fp32: +0,54 (N12) / −0,23 (N20) điểm, ngưỡng < 1 | 20 cặp: p50 7,8 s / p95 **10,3 s** (4 vCPU, 30 câu, ghim luồng, Docker trên M1); 2 vCPU: 11,1 / 13,8 s — ngưỡng 300 ms là số kế hoạch, chưa áp dụng | 🟢 **Ship 11/10, BẬT, 20 ứng viên** — nDCG@5 +12,1 điểm, recall@5 0,74 → 0,87; [ADR-0006](../docs/adr/0006-hybrid-search-rrf-rerank.md) cập nhật 11/10 · [Model Card](../docs/MODEL_CARD_reranker.md) |
| `intent-router-v1` | intent router (nhánh C: băm n-gram + IDF → LogisticRegression) | `ai-classify` | UC022 | **1 vCPU** ([ADR-0034](../docs/adr/0034-chot-cap-vcpu-ai-embed-ai-rerank.md) cập nhật 17/10) | `0cc5f770…78ec95e` (.onnx, QUInt8, 35,9 KB)<br>`6e15b469…f6ef1dd` (`router_embedder.json`) | **ĐẠT** — sklearn ↔ ONNX max \|ΔP\| 2,98 × 10⁻⁷ < 10⁻⁴, khớp nhãn 200/200 | một câu (băm + `run`): p50 0,074 / p95 **0,176 ms** — 1 vCPU ghim luồng, Docker trên M1 (17/10); 2 và 4 vCPU: 0,177 / 0,176 ms. Qua HTTP ở 2 vCPU: p95 5,3 ms tuần tự (Dev B 05/10, Windows). Ngưỡng 60 ms là số kế hoạch | 🟢 **Ship** — Macro-F1 0,6755 [0,6131 ; 0,7327] trên 200 câu người thật; τ = 0,65; định tuyến cộng theo ô ([ADR-0035](../docs/adr/0035-dinh-tuyen-duoi-nguong-cong-xac-suat-theo-o.md)) · [Model Card](../docs/MODEL_CARD_router.md) |
| _(chưa có)_ | lead scorer | `ai-classify` | UC030 | S | | < 1e-4 | < 1.000 ms | Chưa bắt đầu |
| _(chưa có)_ | K-Means + PCA | CronJob riêng | UC038 | — | | — | không trên đường request | Chưa bắt đầu |

---

## Hai cổng chặn — artifact không đạt thì KHÔNG lên S3

| Cổng | Ngưỡng | Mục |
|---|---|---|
| Parity encoder | `cosine(fp32, int8) ≥ 0,995` trên 500 mẫu tiếng Việt | §5.8 |
| Parity lead scorer | lệch `< 1e-4` so với sklearn | §5.10.4 |

Kèm theo: chạy recall@5 trên golden set với **cả hai** phiên bản, chênh lệch < 1 điểm.

Đây là cổng chặn chứ không phải báo cáo. Lượng tử hoá INT8 thường mất dưới 0,5% chất
lượng, nhưng khi nó hỏng thì hỏng âm thầm: model vẫn trả về vector đúng số chiều, chỉ
là vector sai. Không có cổng này, lỗi lộ ra ở Tuần 7 dưới dạng "recall tự nhiên tụt"
và mất nhiều ngày truy nguyên.

---

## Model bị loại — cũng phải ghi

| model | Đòn bẩy §5.4.1 đã thử | p95 đo được | ADR |
|---|---|---|---|
| `bge-m3-int8-matmul` | lượng tử hoá **chỉ `MatMul`**, giữ bảng nhúng fp32 — thí nghiệm kiểm chứng giả thuyết "bảng nhúng là nguyên nhân" | parity `mean` 0,98503 vs 0,98476 của bản đầy đủ ⇒ **không cải thiện**; kích thước 1 298 MB vs 541 MB | [ADR-0021](../docs/adr/0021-cong-parity-int8-truot-phan-xu-bang-recall.md) |

Dòng trên là một **giả thuyết bị bác bỏ**, không phải model bị loại vì chậm — nhưng vẫn
ghi ở đây, vì biết một hướng *không* dẫn tới đâu cũng là kết quả, và nó ngăn người sau
(kể cả chính mình ở Ngày 7) thử lại đúng hướng đó.

Mỗi model bị loại phải có ADR ghi rõ **đã thử đòn bẩy nào trong 5 đòn bẩy §5.4.1** và
số đo tương ứng. Một dòng "quá chậm" không kèm bảng số là **KHÔNG ĐỦ** để loại một
model — đây là một trong ba điều dễ mất điểm nhất khi nghiệm thu.

---

## Sổ hash dữ liệu

`artifacts/DATA_HASHES.txt` giữ `sha256` của các tập test đã đóng băng:

```
data/intent_test_human.jsonl    ≥ 250 mẫu, đóng băng Ngày 7
data/golden_qa.jsonl            ≥ 80 cặp,  đóng băng Ngày 27
```

**Không bao giờ sửa tập test để cải thiện điểm.** Đóng băng là đóng băng — đó là điều
kiện để ba nhánh đối chứng ở §5.9 có nghĩa. Hai tệp này và sổ hash được hook
`.claude/hooks/guard_paths.py` chặn ghi với mọi agent.
