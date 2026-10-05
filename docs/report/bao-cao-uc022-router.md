# Báo cáo UC022 — Phân loại ý định và định tuyến

> Phần báo cáo cho Chương 5 (thực nghiệm). Cập nhật 2026-10-05.
> **Mọi con số đều kèm lệnh tái lập.** Số nào chưa đo được ghi "chưa đo" — không ước lượng.

---

## 1. Bài toán

Mỗi tin nhắn của khách đi qua UC022 trước mọi xử lý khác. Mục tiêu: chọn nhánh xử lý **rẻ nhất mà
vẫn đủ đúng**, để ≥ 55% số lượt không phải gọi mô hình ngôn ngữ (§1.6) — gọi LLM tốn ~2.500 ms và
tính tiền, còn router chạy trên CPU trong vài mili-giây.

Router gán câu vào 7 ý định (`GREETING`, `KB_SEARCH`, `PRICING_POLICY`, `COMPLAINT_SUPPORT`,
`HANDOFF_HUMAN`, `TECH_ERROR`, `BUYING_INTENT`); ý định + độ tự tin quyết định 1 trong 7 nhánh xử lý
của bảng `ai.ai_interactions` (V204).

## 2. Dữ liệu

| Tập | Cỡ | Nguồn | SHA-256 |
|---|---|---|---|
| Train | 1.941 câu (từ 3.000 thô) | Sinh bằng **template** + 6 văn phong, seed 42 | `d8c2bfc4…4562d` |
| Test người thật | 200 câu, 28–30 câu/ý định | Gõ tay (cần xác nhận lại — xem §8) | `8cc500dc…a1ecf` |

- Khử trùng lặp gần giống: Jaccard character 3-gram ≥ 0,88 trong cùng ý định; đã kiểm không còn cặp
  nào vượt ngưỡng. Tỉ lệ loại 35,3% phản ánh số bản sao **do script tự chèn** để đủ 3.000 câu, không
  phải đặc tính dữ liệu tự nhiên.
- **Đồng thuận gán nhãn (Cohen's Kappa): chưa đo.** Phiếu gán nhãn mù đã sẵn ở `data/annotations/`;
  tính bằng `python scripts/compute_annotation_kappa.py` sau khi hai người điền xong.

## 3. Kiến trúc router 3 tầng

```
câu khách ─► Tầng 1: luật từ khoá ──khớp──► nhãn, conf 0,93–0,98
                    │ không khớp
                    ▼
             Tầng 2: embedder + LogisticRegression (ONNX INT8)
                    │
                    ├─ conf ≥ τ = 0,65 ─► nhãn của mô hình
                    └─ conf < τ ───────► bỏ phiếu trắng → ai-service hỏi lại khách (CLARIFY)
```

**Embedder tầng 2 là feature hashing** (từ + n-gram ký tự 3/4, băm MD5/SHA-1 vào 1.024 chiều, trọng
số IDF) — **không phải vector BGE-M3** của `ai-embed` như thiết kế ban đầu (ADR-0018 mục 0).

## 4. So sánh hai nhánh

Tái lập: `python scripts/evaluate_router_branches_comparison.py --no-export`
(số liệu gốc: `docs/report/router_branches_comparison_report.json`).

| Tiêu chí (200 câu test người thật) | Nhánh C — embedder băm + LogReg (ship) | Nhánh B — XLM-R base fine-tune |
|---|---|---|
| Macro-F1 | 0,6755 | **0,7210** |
| KTC 95% bootstrap (B = 1.000) | [0,6131 ; 0,7327] | [0,6606 ; 0,7747] |
| Accuracy | 0,675 | 0,725 |
| p95 CPU một câu, 2 luồng | 0,33 ms (embed + ONNX) | **72,4 ms** (INT8 dynamic) · 91,8 ms (FP32) |
| Kích thước | 35,9 KB ONNX + 72 KB bảng IDF | 1.077 MB |
| Macro-F1 trên validation (dữ liệu template) | — | 0,975 |

**Paired bootstrap B − C** (B = 1.000, seed 42): Δ trung bình +0,044, KTC 95% **[−0,040 ; +0,131]**,
p = 0,151 — **không có ý nghĩa thống kê**.

**Quyết định theo §5.9 — cả hai quy tắc cùng chỉ về nhánh C:**
1. Nhánh B vượt ngân sách độ trễ (p95 72,4 ms > 60 ms, ngay cả bản INT8 nhanh hơn) → loại.
2. Chênh lệch chất lượng không có ý nghĩa → ship nhánh có p95 thấp hơn → nhánh C.

**Lưu ý khi trích dẫn:** nhánh B huấn luyện trên CPU laptop (i5-1235U, 38,8 phút, transformers 4.46.3,
seed 42) bằng `notebooks/05_train_router_xlmr.py`; độ trễ đo trên cùng laptop, batch 1, gồm tokenize
— chưa phải CPU production. Validation 0,975 nhưng test 0,721: cùng hiện tượng lệch phân phối
template ↔ câu người thật như nhánh C. Kết quả gốc: `docs/report/router_branch_b_*.json(l)`.

Tham khảo, cùng embedding: kNN (k = 9, cosine) đạt Macro-F1 **0,7582** nhưng không phải mô hình được
export. Lý do chọn LogisticRegression để ship chưa được ghi lại — cần quyết định.


## 5. Cả router 3 tầng — đúng như `ai-classify` chạy

| Chỉ số | Giá trị |
|---|---|
| Macro-F1 nhãn router | **0,712** |
| Tầng 1 (luật) | 72 câu, đúng 79% |
| Tầng 2, conf ≥ 0,65 | 49 câu, đúng 92% |
| Bỏ phiếu trắng (conf < 0,65) | 79 câu (39,5%); nhãn đoán đúng 52% — hỏi lại là hành vi đúng |

### Đường cong bỏ phiếu trắng (riêng tầng 2)

| τ | 0,40 | 0,50 | 0,60 | **0,65** | 0,70 | 0,80 |
|---|---|---|---|---|---|---|
| Độ chính xác phần giữ lại | 0,794 | 0,850 | 0,911 | **0,924** | 0,937 | 1,000 |
| Coverage | 0,775 | 0,565 | 0,450 | **0,395** | 0,315 | 0,210 |

Đặc tả chọn τ tại điểm ≈ 0,95 → τ = 0,80 nhưng chỉ giữ 21%. Hệ thống chạy **τ = 0,65** (0,924 / 39,5%)
— đánh đổi có chủ ý để không hỏi lại khách 79% số lượt.

## 6. Đường remote `ai-service → ai-classify`

Tái lập: `docker compose -f inference/compose.inference.yml up -d --build ai-classify` rồi
`python scripts/bench_remote_classify.py --url http://127.0.0.1:8083`.
200 câu test × 3 vòng; `ai-classify` trong Docker `cpus=2`, `OMP_NUM_THREADS=2`; client trên host
Windows. Ngân sách §5.3: p95 ≤ 60 ms.

| Chế độ | p95 trước sửa | p95 sau sửa | Đạt |
|---|---|---|---|
| Tuần tự, `RemoteClassifyClient` của ai-service | 265 ms | **5,3 ms** | ✅ |
| 5 request đồng thời | 1.287 ms | **18,8 ms** | ✅ |
| Tuần tự, kết nối giữ sẵn (đối chứng) | 3,6 ms | 6,9 ms | ✅ |

**Hai lỗi tìm ra khi đo, đã sửa:**
1. **Container `ai-classify` không chạy mô hình** — cần `joblib` + pickle + code ai-service mà image
   không có; lỗi bị nuốt và rơi về luật từ khoá (câu không khớp luật mặc định `KB_SEARCH` 0,85). Sửa:
   xuất bảng IDF ra `artifacts/router_embedder.json`, port embedder sang numpy trong `inference/`, nạp
   hỏng thì `/ready` trả 503. Test parity: vector khớp tuyệt đối, nhãn ONNX khớp 200/200 (commit `3a8eb7d`).
2. **Client tạo `httpx.AsyncClient` mới cho mỗi lần gọi** — tốn ~200 ms và chiếm event loop nên các
   request đồng thời xếp hàng. Sửa: dùng chung một client cho mỗi (event loop, base URL) (commit `498733e`).

Ghi chú môi trường: gọi `localhost` trên Windows thêm ~48 ms vì thử IPv6 trước; trong Docker gọi bằng
tên service nên không gặp.

## 7. Định tuyến trong `/v1/ai/chat` và guardrails

Phân bố nhánh trên 200 câu test qua router thật: **CLARIFY 39,5% · RAG 28% · HANDOFF 12,5% ·
SMALL_TALK 11% · TOOL_CALL 9%**. Tỉ lệ không gọi LLM = 72%, trong đó 39,5% là hỏi lại khách — trình bày
tách bạch, không coi là thành tích.

Guardrails (thuần Python): báo nhầm tiêm chỉ thị **0/200** câu test và **0/1.941** câu train,
~60–70 µs/câu. Tỉ lệ chặn trên bộ adversarial: **chưa đo** (`tests/eval/adversarial.jsonl` còn rỗng).

### Thí nghiệm âm — siết luật tầng 1

Giữ luật có precision ≥ 95% trên train: tầng 1 đúng 100% trên train nhưng 87% trên test (lệch phân
phối template ↔ người thật); lỗi tự tin sai 14 → 5, nhưng hỏi lại 39,5% → 55,5% và Macro-F1
0,712 → 0,680. **Giữ luật gốc** — nút thắt là tầng 2 tự tin quá ít, không phải tầng luật.

## 8. Giới hạn

1. Embedder không ngữ nghĩa (feature hashing) — nguyên nhân chính khiến chỉ ~40% câu vượt τ.
2. Train sinh từ template, lệch phân phối so với câu người thật.
3. Chưa có Cohen's Kappa — chưa định lượng độ tin cậy của nhãn vàng.
4. Nhánh B huấn luyện và đo độ trễ trên laptop, chưa trên CPU production; chỉ một lần chạy (một seed).
5. Nguồn gốc tập test cần xác nhận: file được commit lần đầu 04/10, muộn hơn mốc đóng băng Ngày 2 của kế hoạch.
6. Số đo độ trễ là của môi trường (C) trên Windows/Docker Desktop, chưa phải pod EKS.
