# Ôn tập Ngày 15 Khối B — Benchmark CPU, vì sao phải ghim luồng, và chốt vCPU

> Viết 11/10/2026 (lịch gốc 05/10). Số liệu: [`docs/report/benchmark-ngay15-2026-10-11.md`](../report/benchmark-ngay15-2026-10-11.md).
> Quyết định: [ADR-0034](../adr/0034-chot-cap-vcpu-ai-embed-ai-rerank.md). Mã: `inference/bench/bench_cpu.py` ·
> `inference/src/session.py` · `inference/compose.inference.yml`. Khối A: [`ngay-15-rerank-that.md`](ngay-15-rerank-that.md).
>
> **Trạng thái:** Khối B xong — **ai-embed 4 vCPU, ai-rerank 4 vCPU** (người dùng chốt 11/10) · **ai-classify
> 1 vCPU** (người dùng chốt 17/10, đo bù router — mục 6). Ngày 15 đóng trọn.

## 1. Ba con số phải nhớ

| | Ghim luồng | Để mặc định | Chậm hơn |
|---|---|---|---|
| Nhúng một câu hỏi, 2 vCPU — p95 | 68 ms | 906 ms | **× 13** |
| Rerank 20 cặp, 2 vCPU — p95 | 13,8 s | 57,6 s | **× 4,2** |

Và: **rerank ở 4 vCPU nhanh hơn 2 vCPU ~25–30%** (p50 7,8 / 9,0 s so với 11,1 / 12,5 s) — ngược với điều
Khối A đã ghi buổi chiều. Để mặc định, ONNX Runtime luôn tạo **8 luồng** (theo 8 CPU của VM), dù container
chỉ được 2 hay 4.

## 2. Bốn câu "phải giải thích được"

**Vì sao `inter_op_num_threads = 1`?**
ONNX Runtime có hai pool luồng. *Intra-op* chia MỘT phép tính (một MatMul 1024 × 1024) cho nhiều luồng.
*Inter-op* chạy song song các NÚT ĐỘC LẬP của graph — và chỉ dùng tới khi `execution_mode = PARALLEL`.
Encoder và cross-encoder là chồng 24 lớp transformer nối tiếp: lớp sau cần kết quả lớp trước, không có
hai nhánh nào chạy song song được. Pool inter-op vì thế không có việc để làm, chỉ thêm luồng tranh vCPU.
Code đặt `ORT_SEQUENTIAL` **và** `inter_op = 1` — đặt cả hai để ai lỡ bật `PARALLEL` sau này cũng không
đẻ thêm pool.

**Vì sao chạy benchmark từng model một? Nếu chạy song song thì số sai theo hướng nào?**
`--cpus 2` (và `limits.cpu` của k8s) là **hạn mức thời gian CPU**, không phải hai nhân riêng. Hai container
đo cùng lúc tranh cùng 8 vCPU của VM, cộng tiến trình của macOS. Số sai theo hướng **chậm hơn thật** — và
không đều: p95 đội nhiều hơn p50 (tranh chấp đến theo đợt, rơi vào vài mẫu), model chạy lâu hơn chịu nhiều
hơn. Tệ nhất là kết luận đảo chiều — đúng điều đã xảy ra ở Khối A (mục 3). Ngay cả chạy nối tiếp, hai lượt
cùng cấu hình hôm nay vẫn trôi tới +35% p95 khi tải máy chủ tăng từ ~3 lên ~7.

**Vì sao model nhỏ tăng vCPU không nhanh hơn?**
Mỗi nút của graph, ORT chia việc cho N luồng rồi chờ cả N xong (một rào chắn). Việc càng nhỏ thì phần
chia–đánh thức–chờ càng lớn so với phần tính. Tới lúc nào đó thêm luồng chỉ thêm chi phí đồng bộ; phần chạy
tuần tự (tách từ, Python, chép tensor) thì không chia được (định luật Amdahl). "Nhỏ" là **khối lượng một
lượt chạy** = model × độ dài chuỗi, không phải riêng số tham số. Bằng chứng gián tiếp đo được hôm nay:
nhúng một câu hỏi (trung vị 13 token) bằng bge-m3 — model 568 triệu tham số — p95 **68 ms ở 2 vCPU và
69 ms ở 4 vCPU**, trong khi nhúng một đoạn (dài hơn nhiều) thì 4 vCPU nhanh hơn 30%. Bằng chứng trực tiếp
đo 17/10 trên router (mục 6): p95 **0,176 · 0,177 · 0,176 ms ở 1 · 2 · 4 vCPU** — và ở cỡ này ORT thậm chí
không chia việc cho pool luồng (lõi dùng 1,00 ở mọi mức).

**Vì sao số đo trên M1 không dùng thẳng cho máy x86 lúc lên production?**
1. **Nhân không đồng nhất:** M1 có 4 nhân hiệu năng + 4 nhân tiết kiệm điện; macOS quyết định luồng của
   VM Docker chạy trên nhân nào. Máy cloud x86 có nhân đồng nhất.
2. **"vCPU" khác nghĩa:** trên `c7i`, 2 vCPU là **một** nhân vật lý chạy hai siêu luồng; trên VM Docker
   Desktop, 2 vCPU gần với hai nhân thật.
3. **Nhân tính INT8 khác nhau:** ORT dùng kernel NEON trên ARM, AVX2/AVX-512 VNNI trên x86. Khối A đã thấy
   thứ hạng rerank lệch ở biên giữa hai kiến trúc (≤ 0,7 điểm nDCG@5).
4. **Lớp ảo hoá:** VM của Docker Desktop thêm một tầng lập lịch mà EC2 không có.

Thứ mang sang được là **hình dạng** của kết quả (ghim luồng tốt hơn mặc định nhiều lần; câu hỏi ngắn không
cần thêm vCPU), không phải con số tuyệt đối. Số tuyệt đối đo lại ở N20 trên đúng máy cloud.

## 3. Bốn phát hiện hội đồng có thể hỏi

1. **Khối A kết luận sai, Khối B sửa.** Buổi chiều: "4 vCPU không nhanh hơn 2 vCPU trên M1", kèm giả thuyết
   luồng rơi vào nhân tiết kiệm điện. Buổi tối đo trực tiếp, cùng điều kiện, **hai lượt mỗi mức**: lượt chậm
   nhất ở 4 vCPU (p95 10,5 s) vẫn nhanh hơn lượt nhanh nhất ở 2 vCPU (13,8 s). Lượt 4 vCPU của Khối A chạy
   lúc tải nền cao. Bài học: một so sánh chỉ có nghĩa khi hai vế đo cùng điều kiện — và nên chạy lặp để biết
   biên nhiễu trước khi tin một chênh lệch.
2. **Ghim luồng là điều kiện đúng chứ không phải tinh chỉnh.** Master Plan cảnh báo "tệ gấp ba"; đo được tới
   **mười ba lần**. Cơ chế nhìn thấy trong `cpu.stat`: 8 luồng chia hạn mức 2 vCPU ⇒ hạn mức cạn giữa mỗi chu
   kỳ 100 ms, cả tiến trình bị dừng ⇒ **100% chu kỳ bị chặn**. CPU dùng vẫn đúng 2,00 lõi — không ít đi, chỉ
   bị phí. Không log nào báo.
3. **Thêm vCPU luôn bị dùng hết, kể cả khi không nhanh hơn.** Câu hỏi ở 4 vCPU dùng 3,95 lõi, ở 2 vCPU dùng
   1,99 lõi — cùng p95. Hai lõi thêm là luồng ORT quay chờ việc (spin). Vì thế "chọn dư cho chắc" không miễn
   phí: ai-embed 4 vCPU đốt dư CPU mỗi lượt chat, đổi lấy nạp kho nhanh hơn 30% (ADR-0034 Đánh đổi).
   *Đúng với bge-m3 và reranker; router thì không — xem mục 6.*
4. **`/ready` không canh được lỗi này.** Bất biến 3 so biến môi trường `OMP_NUM_THREADS` với cgroup — nhưng
   ONNX Runtime **không đọc biến đó**: mọi lượt "mặc định" hôm nay đều chạy với `OMP_NUM_THREADS=2` (hoặc 4)
   mà ORT vẫn tạo 8 luồng. Thứ quyết định là dòng `intra_op_num_threads` trong `make_session`. Xoá dòng đó thì `/ready` vẫn xanh, p95 chậm vài lần. Đã báo Dev B (`session.py`).

## 4. Rerank chậm — đòn bẩy nào còn lại

| Đòn bẩy | Trạng thái | Số |
|---|---|---|
| vCPU 2 → 4 | **đã làm** | p95 13,8 / 18,6 s → 10,3 / 10,5 s |
| 20 → 12 ứng viên | đã đo, **không dùng** | nhanh ~2 lần nhưng trần recall@5 0,83 < 0,85 |
| Chỉ khi mơ hồ | đang bật, gần như vô tác dụng | cổng đánh dấu 93% câu |
| `max_length` 512 → 256 | **chưa thử** | cặp > 256 token: 20% số cặp, ~50% thời gian ⇒ ước ~25% nhanh hơn — phải đo lại nDCG@5 |
| Distil model | chưa thử | 1–2 ngày GPU |

## 5. Lệnh để tự chạy lại

```bash
cd <gốc repo>
docker run --rm --cpus 2 -e OMP_NUM_THREADS=2 -e TZ=ICT-7 -e TAI_MAY_CHU="$(sysctl -n vm.loadavg)" \
  -v "$PWD/artifacts:/app/artifacts:ro" -v "$PWD/ai-service/tests/eval:/app/eval:ro" \
  -v "$PWD/inference/bench:/app/bench:ro" -v "$PWD/reports/eval:/app/reports/eval" \
  ai-inference:dev python -m bench.bench_cpu chay --vai embed --che-do mac-dinh --nhan thu   # ~2 phút
python3 inference/bench/bench_cpu.py bang reports/eval/bench-thu-*.json
```

Đổi `--che-do ghim` để thấy chênh lệch ngay trên máy mình: dòng in ra có số luồng ORT tạo (`+1` so với `+7`)
và tỉ lệ chu kỳ bị chặn.

## 6. Cập nhật 17/10 — router `ai-classify`: điều (1) và 1 vCPU

Số: báo cáo benchmark §9 · quyết định: ADR-0034 mục "Cập nhật 17/10".

**Ba con số phải nhớ** (lượt dài, 112.000 câu mỗi cấu hình, ghim luồng):

| | 1 vCPU | 2 vCPU | 4 vCPU |
|---|---|---|---|
| p95 một câu (băm + `run`) | **0,176 ms** | 0,177 ms | 0,176 ms |
| Lõi dùng TB | **1,00** | 1,00 | 1,00 |

Và: **77%** thời gian một câu là **băm n-gram trong Python**, chỉ 17% là ONNX Runtime.

**Vì sao router tăng vCPU không nhanh hơn — câu trả lời ngắn:** việc một lượt quá nhỏ (một tích
1 × 1024 với 1024 × 7) nên ORT **không chia cho pool luồng** — luồng thêm vào nằm ngủ, lõi dùng đứng ở
1,00. Phần lớn thời gian lại nằm ở đoạn Python một luồng. Không có gì để song song hoá thì thêm nhân không
giúp gì. Khác bge-m3: ở đó ORT có chia việc, thêm vCPU bị dùng hết (3,95 lõi), chỉ là không nhanh hơn với
câu ngắn.

**Ba điều hội đồng có thể hỏi:**

1. **"Router để mặc định cũng không chậm — vậy ghim luồng để làm gì?"** Đúng là với router, mặc định ÷ ghim
   = × 0,98–1,00: ORT tạo 8 luồng nhưng không giao việc cho chúng, nên không quay chờ, không tranh hạn mức.
   Phạt chỉ hiện ở **đuôi cực xa của 1 vCPU** (mẫu lâu nhất 78 ms so với 15 ms khi ghim). Vẫn ghim vì: luật
   áp chung cho cả ba vai, bất biến 3 kiểm như nhau, ghim không tốn gì — và đổi sang model lớn hơn (ví dụ
   XLM-R nhánh B) thì phạt × 2–13 quay lại ngay.
2. **"Sao lại có hai lượt đo, lượt dài thêm vào lúc nào?"** Cách đo chốt trước là 1.120 câu. Lượt chạy thử
   kiểm code (chưa phải số đo) cho thấy 112 câu xong trong ~10 ms ⇒ 1.120 câu chỉ ~0,1 s, khoảng **một chu
   kỳ CFS 100 ms** — cơ chế cgroup chặn tiến trình không kịp hiện ra. Lượt dài được **ghi vào báo cáo trước
   khi chạy ma trận**, và tiêu chí phải đạt ở **cả hai** lượt (siết, không nới). Lượt ngắn quả thật trôi
   54% giữa hai lần chạy — đúng điều đã lo.
3. **"1 vCPU có chật quá không?"** Có đánh đổi: chạy liên tục 100% một lõi thì 23–49% chu kỳ bị chặn, mẫu
   lâu nhất 15 ms (2 vCPU: 10 ms); p95, p99 không đổi. Chỗ **chưa đo**: HTTP + uvicorn + log chạy chung lõi
   đó. Số HTTP duy nhất là của Dev B ở 2 vCPU: p95 5,3 ms — gấp ~30 lần phần model. Lên tải (N19) mà HTTP
   chậm đi thì trả về 2 vCPU, chỉ đổi compose. Thêm vCPU cũng **không** thêm thông lượng: uvicorn một tiến
   trình, handler `async` gọi ONNX đồng bộ ⇒ yêu cầu đồng thời xếp hàng trên event loop.

**Tự chạy lại một cấu hình:**

```bash
docker run --rm --cpus 1 -e OMP_NUM_THREADS=1 -e TZ=ICT-7 -e TAI_MAY_CHU="$(sysctl -n vm.loadavg)" \
  -v "$PWD/artifacts:/app/artifacts:ro" -v "$PWD/ai-service/tests/eval:/app/eval:ro" \
  -v "$PWD/inference/bench:/app/bench:ro" -v "$PWD/reports/eval:/app/reports/eval" \
  ai-inference:dev python -m bench.bench_cpu chay --vai classify --che-do ghim --nhan thu --vong 1000  # ~10 s
```
