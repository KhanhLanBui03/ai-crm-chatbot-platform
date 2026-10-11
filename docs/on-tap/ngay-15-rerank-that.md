# Ôn tập Ngày 15 Khối A — Rerank thật, và vì sao 20 ứng viên chứ không phải 12

> Viết 11/10/2026 (lịch gốc 05/10). Số liệu: [`docs/report/rerank-ngay15-2026-10-11.md`](../report/rerank-ngay15-2026-10-11.md).
> Quyết định: [ADR-0006](../adr/0006-hybrid-search-rrf-rerank.md) cập nhật 11/10. Model:
> [`MODEL_CARD_reranker.md`](../MODEL_CARD_reranker.md). Mã: `inference/src/roles/rerank.py` ·
> `ai-service/src/ai/rag/rerank/quyet_dinh.py` · `notebooks/07_export_reranker.py`.
>
> **Trạng thái:** Khối A xong — rerank **BẬT**, 20 ứng viên (người dùng chốt). Khối B (benchmark, ADR
> vCPU) xong cùng ngày: [`ngay-15-khoi-b-benchmark-vcpu.md`](ngay-15-khoi-b-benchmark-vcpu.md).

## 1. Ba con số phải nhớ

| | recall@5 | nDCG@5 |
|---|---|---|
| Hybrid RRF, không rerank | 0,740 | 0,631 |
| + rerank 20 ứng viên (ship) | **0,870** | **0,752** (+12,1 điểm, KTC [+6,2; +18,5]) |

Và giá: **một lượt rerank 20 cặp mất ~11 s** (p50, 2 vCPU, máy dev). Đây là lần đầu recall@5 vượt
ngưỡng 0,85 của §1.6, và cũng là lần đầu một tầng của đường ống chậm hơn LLM nhiều lần.

## 2. Bốn câu "phải giải thích được"

**Bi-encoder và cross-encoder khác nhau ở đâu? Vì sao cross-encoder chính xác hơn mà vẫn không thay được
bi-encoder ở bước tìm?**
Bi-encoder (bge-m3) nhúng câu hỏi và đoạn **riêng rẽ** thành hai vector rồi so cosine. Vector của đoạn
tính sẵn lúc nạp, nên tìm trên cả kho chỉ tốn một phép nhúng câu hỏi + một truy vấn HNSW. Cross-encoder
(bge-reranker-v2-m3) đọc câu hỏi và đoạn **cùng lúc** trong một chuỗi `<s> câu hỏi </s></s> đoạn </s>`:
attention nối từng từ của câu hỏi với từng từ của đoạn, nên nó thấy được "mất hóa đơn" khớp với "tra theo
số serial". Đổi lại, nó không có gì để tính sẵn — mỗi cặp một lượt chạy model. Riêng kho đo 190 đoạn ×
~0,5 s đã là ~1,5 phút cho một câu hỏi; kho thật hàng nghìn đoạn thì hàng chục phút. Vì vậy: bi-encoder **tìm** (rẻ, cả kho), cross-encoder **xếp lại** (đắt,
vài chục ứng viên).

**Vì sao parity của cross-encoder đo thứ hạng chứ không đo cosine như encoder?**
Đầu ra của encoder là vector đem đi so cosine với vector đã lưu trong CSDL — vector INT8 lệch so với fp32
là lệch không gian, hỏng truy hồi, nên đo cosine(fp32, INT8). Đầu ra của cross-encoder là **một số**, và
ai-service chỉ dùng nó để **sắp xếp**. INT8 cho điểm 2,3 thay vì 2,6 không sao, miễn thứ tự giữ. Nên cổng
đo thứ đúng cái được dùng: nDCG@5 sau rerank, INT8 so với fp32, chênh < 1 điểm (đạt: +0,54 / −0,23). Spearman
min 0,893 cho thấy INT8 có đảo thứ tự — nhưng đảo giữa các đoạn sai với nhau, nên đầu ra không đổi.

**"Trần của rerank" là gì, và vì sao 12 ứng viên có trần 0,83?**
Rerank chỉ sắp lại những gì nó được đưa. Đoạn đúng không nằm trong N ứng viên thì xếp hoàn hảo cũng
không cứu được. Trần = (câu đã trúng top-5 sẵn + câu có đoạn đúng ở hạng 6..N) / số câu. Với hybrid: 74 câu
trúng sẵn; 9 câu có đoạn đúng ở hạng 7–12, thêm 12 câu ở hạng 13–20. Nên trần là (74 + 9) / 100 = **0,83**
với N = 12 và (74 + 21) / 100 = **0,95** với N = 20. Trần 0,83 < 0,85 ⇒ với 12 ứng viên, không model nào
đạt được ngưỡng §1.6. Đó là lý do đổi sang 20 — và giả định cũ của Ngày 8 ("đoạn đúng ngoài top-12 gần
như không bao giờ được kéo về") chưa từng được đo.

**Rerank có thể tăng nDCG@5 mà recall@5 giữ nguyên không? Vì sao?**
Có. recall@5 chỉ hỏi "đoạn đúng có trong top-5 không"; nDCG@5 hỏi thêm "ở hạng mấy" (1/log₂(1 + hạng)).
Rerank kéo đoạn đúng từ hạng 4 lên hạng 1: recall@5 không đổi (vẫn trong top-5), nDCG@5 của câu đó từ 0,43
lên 1,0. Chiều ngược lại cũng có: rerank đẩy 2 câu đang đúng ra khỏi top-5 — xếp lại không phải phép toán
chỉ có lợi, và bảng số phải ghi cả cột "bị đẩy ra".

## 3. Ba phát hiện hội đồng có thể hỏi

1. **Cổng "mơ hồ" đánh dấu 93% câu**, không phải 30–40%. Cổng so cosine hạng 1 với hạng 3, nhưng thứ tự
   là của RRF chứ không phải của cosine, nên hiệu thường nhỏ hoặc âm. Hệ quả: "chỉ khi mơ hồ" gần như
   bằng "mọi câu". Chưa sửa — sửa là đổi chất lượng lấy độ trễ.
2. ~~**4 vCPU không nhanh hơn 2 vCPU trên M1.**~~ **Đính chính ở Khối B:** đo cùng điều kiện thì 4 vCPU
   nhanh hơn ~25–30% — xem [`ngay-15-khoi-b-benchmark-vcpu.md`](ngay-15-khoi-b-benchmark-vcpu.md). Ghi chép gốc: Cùng 30 câu, 12 cặp: p50 8,2 s (4 vCPU) so với 5,7 s
   (2 vCPU). Giả thuyết: luồng rơi vào nhân tiết kiệm điện, bước song song chờ luồng chậm nhất. Chưa chứng
   minh — hai lượt chạy ở hai mức tải nền khác nhau. Đây là đầu vào của Khối B.
3. **Ước lượng độ trễ trước khi đo sai 5–8 lần** (~1,2 s → thật 5,7 s cho 12 cặp). Ước lượng suy từ thông
   lượng ai-embed, nhưng cặp (câu hỏi + đoạn) dài hơn đoạn, và 8% cặp chạm trần 512 token, mất 2–3 s mỗi
   cặp. Bài học: ước lượng chỉ để biết rủi ro, quyết định phải đợi số đo.

## 4. Ba thay đổi không phải model nhưng quan trọng như model

| Thay đổi | Vì sao |
|---|---|
| ai-rerank thiếu model ⇒ `/ready` 503, **không** lùi về Jaccard | Điểm giả mang nhãn model thật là đúng thứ bất biến 1 sinh ra để chặn |
| ai-rerank lỗi ⇒ `answerer.py` giữ thứ hạng RRF | Ma trận suy giảm §3.8.1 ghi vậy, nhưng code cũ không bắt lỗi — ai-rerank chết là hỏng cả lượt chat. Kiểm thật: `docker stop ai-rerank` → chat vẫn HTTP 200 |
| Chuỗi hạn chờ 60 s (ai-rerank) < 90 s (java-core) < 120 s (ALB) | java-core mặc định chờ 10 s: bật rerank mà không đổi thì phần lớn lượt chat qua widget không có câu trả lời |

## 5. Lệnh để tự chạy lại

```bash
docker compose -f inference/compose.inference.yml up -d ai-embed ai-rerank
cd ai-service && source .venv/bin/activate
AI_MODE=remote EMBED_URL=http://localhost:8091 INFERENCE_RERANK_URL=http://localhost:8082 \
python -m tests.eval.danh_gia_truy_hoi chay --nhan n15 tests/eval/configs/e3_hybrid.yaml \
    tests/eval/configs/n15_rerank_20_mo_ho.yaml        # ~20 phút cho 100 câu ở 2 vCPU
```
