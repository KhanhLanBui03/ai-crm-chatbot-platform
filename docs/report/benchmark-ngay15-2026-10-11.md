# Ngày 15 Khối B — benchmark CPU rút gọn: ghim luồng, 2 ↔ 4 vCPU, chốt cấp vCPU

- **Ngày đo:** 11/10/2026, 21:11–22:22, máy dev Apple M1 (4 nhân hiệu năng + 4 nhân tiết kiệm điện,
  8 GB RAM), Docker Desktop cấp VM 8 CPU / 5,8 GB. ONNX Runtime 1.30.0, `aarch64`.
- **Image:** `ai-inference:dev` (`sha256:c07b9cc3ced3…`), `src/` khớp từng byte với repo (kiểm sha256 của
  `session.py`, `roles/embed.py`, `roles/rerank.py`, `entrypoint.py` trước khi đo).
- **Model:** `bge-m3` INT8 `int8-71e2aa91` (ai-embed) · `bge-reranker-v2-m3` INT8 `int8-93cd7fb0` (ai-rerank).
- **Bench:** `inference/bench/bench_cpu.py` `[R&D]` — mount vào image, nạp session trực tiếp, gọi đúng
  `BoNhung.nhung` / `BoXepHang.cham` của production; chỉ thay hàm dựng session (ghim / mặc định).
- **Đầu vào:** `golden_set.jsonl` (sha256 `323baf73…`, 112 câu hỏi × 3 vòng = 336 mẫu, trung vị 13 token) ·
  `rerank_cap_100x20.jsonl` (sha256 `1f6c77ad…`): 30 dòng đầu G001–G033 × 20 cặp = 600 lượt chạy (đúng 30 câu
  lượt 2 ↔ 4 vCPU của Khối A), và 152 đoạn khác nhau trong các cặp đó cho tải "đoạn".
- **Cấp vCPU:** `docker run --cpus N -e OMP_NUM_THREADS=N` — chạy **từng cấu hình một**, nối tiếp.
- **Quyết định:** người dùng chốt 11/10 — **ai-embed 4 vCPU (giữ) · ai-rerank 4 vCPU (từ 2)** ·
  ai-classify giữ tạm 2; **17/10: ai-classify 1 vCPU** (từ 2, đo bù router — §9).
  [ADR-0034](../adr/0034-chot-cap-vcpu-ai-embed-ai-rerank.md).

**Ngưỡng §5.3 (embed 120 ms · rerank 300 ms · classify 60 ms) KHÔNG áp dụng** — người dùng chốt 11/10/2026:
độ trễ chưa là cổng. Cột ngưỡng ghi để biết khoảng cách.

---

## 1. Kết luận

1. **Ghim luồng là điều kiện đúng, không phải tinh chỉnh.** Để mặc định, ONNX Runtime tạo **8 luồng
   intra-op** (theo 8 CPU của VM) dù container chỉ được 2 hay 4 vCPU; cgroup bị chặn ở **99–100%** chu kỳ và
   p95 chậm **2,2–13,3 lần**. Điều (2) của kế hoạch — **đã chứng minh**.
2. **ai-rerank: 4 vCPU nhanh hơn 2 vCPU** — p50 7,8 / 9,0 s so với 11,1 / 12,5 s (hai lượt mỗi mức). **Đính
   chính Khối A**: kết luận "4 vCPU không nhanh hơn trên M1" (rerank report §3) đến từ hai lượt chạy ở hai
   mức tải nền khác nhau; đo cùng điều kiện thì ngược lại.
3. **ai-embed: câu hỏi ngắn không cần thêm vCPU** (p95 68 ms ở 2 vCPU, 69 ms ở 4 vCPU — trong biên nhiễu),
   nhưng **nhúng đoạn lúc nạp kho nhanh hơn ~30%** ở 4 vCPU (p95 911 → 638 ms).
4. **Thêm vCPU luôn bị dùng hết**, kể cả khi không nhanh hơn: ghim 4 vCPU dùng trung bình 3,95 lõi cho câu
   hỏi, ghim 2 vCPU dùng 1,99 lõi — cùng p95. Phần chênh là các luồng ORT quay chờ việc (spin).
5. **Rerank: cặp dài > 256 token chiếm 20% số cặp nhưng ~50% thời gian.** Đòn bẩy `max_length 512 → 256`
   **chưa thử**; bảng §5 là căn cứ ước lượng, không phải số đo.
6. **Điều (1)** — model nhỏ tăng vCPU không nhanh hơn — **chưa chứng minh trực tiếp**: model nhỏ duy nhất là
   router, chờ `artifacts/router_model.onnx`. Bằng chứng gián tiếp: khối lượng nhỏ (câu hỏi 13 token) trên
   model lớn cho 2 ≈ 4 vCPU. → **Cập nhật 17/10: đã chứng minh** trên router — p95 0,176 · 0,177 · 0,176 ms
   ở 1 · 2 · 4 vCPU, lõi dùng 1,00 ở mọi mức; ai-classify chốt 1 vCPU (§9).

---

## 2. Bảng chính — lượt đầu của mỗi cấu hình

| Model — tải | vCPU | Chế độ | Luồng ORT tạo | Mẫu | p50 | p95 | Lâu nhất | RSS nạp / đỉnh | Chu kỳ bị chặn | Lõi dùng TB | Ngưỡng §5.3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| bge-m3 — câu hỏi | 2 | ghim | +1 | 336 | 28 ms | **68 ms** | 106 ms | 667 / 694 MB | 36% | 1,99 | 120 ms |
| bge-m3 — câu hỏi | 4 | ghim | +3 | 336 | 24 ms | **69 ms** | 465 ms | 667 / 694 MB | 41% | 3,95 | 120 ms |
| bge-m3 — câu hỏi | 2 | mặc định | +7 | 336 | 206 ms | **906 ms** | 2,5 s | 667 / 694 MB | 100% | 2,00 | 120 ms |
| bge-m3 — câu hỏi | 4 | mặc định | +7 | 336 | 96 ms | **310 ms** | 1,1 s | 667 / 695 MB | 99% | 3,98 | 120 ms |
| bge-m3 — đoạn | 2 | ghim | +1 | 152 | 249 ms | **911 ms** | 2,4 s | 667 / 830 MB | 31% | 1,99 | — (nạp kho) |
| bge-m3 — đoạn | 4 | ghim | +3 | 152 | 192 ms | **638 ms** | 1,4 s | 668 / 831 MB | 33% | 3,97 | — (nạp kho) |
| bge-m3 — đoạn | 2 | mặc định | +7 | 152 | 1,4 s | **3,5 s** | 7,5 s | 668 / 831 MB | 100% | 2,00 | — (nạp kho) |
| bge-m3 — đoạn | 4 | mặc định | +7 | 152 | 459 ms | **1,4 s** | 2,8 s | 668 / 832 MB | 100% | 4,00 | — (nạp kho) |
| reranker — 20 cặp | 2 | ghim | +1 | 30 | 11,1 s | **13,8 s** | 14,7 s | 668 / 830 MB | 31% | 1,99 | 300 ms |
| reranker — 20 cặp | 4 | ghim | +3 | 30 | 7,8 s | **10,3 s** | 10,5 s | 668 / 832 MB | 36% | 3,97 | 300 ms |
| reranker — 20 cặp | 2 | mặc định | +7 | 30 | 45,9 s | **57,6 s** | 58,4 s | 669 / 834 MB | 100% | 2,00 | 300 ms |
| reranker — 20 cặp | 4 | mặc định | +7 | 30 | 18,9 s | **25,6 s** | 26,1 s | 669 / 833 MB | 100% | 4,00 | 300 ms |

- **Mẫu** = một yêu cầu: nhúng một câu hỏi · nhúng một đoạn · chấm một câu hỏi với 20 ứng viên (20 lượt
  `run`, lô 1, cộng tách từ). Phân vị theo hạng gần nhất, cùng cách tính của harness truy hồi.
- **Luồng ORT tạo** = chênh `Threads` của tiến trình trước/sau khi nạp session. Ghim N luồng ⇒ +N−1 (luồng
  gọi `run` là luồng thứ N).
- **Chu kỳ bị chặn** = `nr_throttled / nr_periods` của `cpu.stat` cgroup trong vòng đo; **lõi dùng TB** =
  `usage_usec` / thời gian đo.
- Tải "đoạn": 152 đoạn, trung vị 370 ký tự, dài nhất 1.782 ký tự; thông lượng 2,86 đoạn/s (2 vCPU) và
  3,99 đoạn/s (4 vCPU). Số 9,8 đoạn/s của ngày 06/10 đo **ngoài Docker** trên macOS, không so trực tiếp.

---

## 3. Ghim luồng ↔ để mặc định — điều (2)

| Model — tải | vCPU | Luồng ORT ghim / mặc định | p95 ghim / mặc định | **p95 mặc định ÷ ghim** | Chu kỳ bị chặn |
|---|---|---|---|---|---|
| bge-m3 — câu hỏi | 2 | +1 / +7 | 68 ms / 906 ms | **× 13,3** | 36% / 100% |
| bge-m3 — câu hỏi | 4 | +3 / +7 | 69 ms / 310 ms | **× 4,5** | 41% / 99% |
| bge-m3 — đoạn | 2 | +1 / +7 | 911 ms / 3,5 s | **× 3,8** | 31% / 100% |
| bge-m3 — đoạn | 4 | +3 / +7 | 638 ms / 1,4 s | **× 2,2** | 33% / 100% |
| reranker — 20 cặp | 2 | +1 / +7 | 13,8 s / 57,6 s | **× 4,2** | 31% / 100% |
| reranker — 20 cặp | 4 | +3 / +7 | 10,3 s / 25,6 s | **× 2,5** | 36% / 100% |

- **Cơ chế thấy được trong số:** để mặc định, ORT đọc 8 CPU của VM và dựng pool 8 luồng — `+7` ở cả 2 lẫn
  4 vCPU, **dù `OMP_NUM_THREADS` = 2 hoặc 4 có trong môi trường** (ORT không đọc biến này; chỉ
  `intra_op_num_threads` mà `make_session` đặt từ nó mới ghim được). Tám luồng chia hạn mức 2 vCPU ⇒ hạn mức cạn giữa mỗi chu kỳ 100 ms, **cả tiến trình** bị dừng tới
  chu kỳ sau (100% chu kỳ bị chặn). Lõi dùng vẫn đúng 2,00 — CPU không ít đi, chỉ bị phí vào chuyển ngữ cảnh,
  quay chờ và chờ rào chắn của luồng đang bị dừng.
- **Hạn mức càng chật, phạt càng nặng:** × 4,2 ở 2 vCPU so với × 2,5 ở 4 vCPU (rerank); × 13,3 so với × 4,5
  (câu hỏi). Việc càng nhỏ càng nặng vì chi phí đồng bộ cố định mỗi nút graph, không co theo việc.
- **Không log nào báo.** Service vẫn trả kết quả đúng, chỉ chậm. Master Plan §5.4 ước "tệ gấp ba lần" — đo
  được tới mười ba lần.
- **Ghim cũng bị chặn 31–41%** — luồng tách từ và luồng Python ngoài pool ORT vẫn ăn vào cùng hạn mức. Không
  phải lỗi; chặn giảm từ 100% xuống ~1/3 là thứ ghim luồng mua được.

---

## 4. 2 ↔ 4 vCPU — chạy lặp để kiểm độ trôi

| Model — tải | Lượt | Tải máy chủ lúc bắt đầu (1 phút) | 2 vCPU p50 / p95 | 4 vCPU p50 / p95 |
|---|---|---|---|---|
| bge-m3 — câu hỏi | đầu (21:11–21:12) | 2,6 / 2,9 | 28 / 68 ms | 24 / 69 ms |
| bge-m3 — câu hỏi | lặp (22:00) | 7,6 | 33 / 87 ms | — |
| reranker — 20 cặp | đầu (21:15–21:25) | 6,4 / 5,2 | 11,1 / 13,8 s | 7,8 / 10,3 s |
| reranker — 20 cặp | lặp (22:01–22:13) | 6,5 / 6,9 | 12,5 / 18,6 s | 9,0 / 10,5 s |
| bge-m3 — đoạn | đầu (22:14–22:15) | 6,0 / 4,5 | 249 / 911 ms | 192 / 638 ms |

- **Độ trôi giữa hai lượt cùng cấu hình tới +35% ở p95** (rerank 2 vCPU 13,8 → 18,6 s; câu hỏi 68 → 87 ms)
  khi tải máy chủ tăng. Chênh nào nhỏ hơn biên đó là **không phát hiện được**, không phải "bằng nhau".
- **Rerank 4 vCPU nhanh hơn chắc chắn:** lượt *chậm nhất* ở 4 vCPU (p95 10,5 s) vẫn nhanh hơn lượt *nhanh
  nhất* ở 2 vCPU (13,8 s). Tăng tốc dưới tuyến tính — gấp đôi vCPU, p50 giảm 25–30% — phần tuần tự (tách từ,
  20 lượt `run` nối tiếp, rào chắn mỗi nút) không chia được.
- **Câu hỏi 2 ≈ 4 vCPU:** × 1,01 ở p95, nằm trong biên trôi. 4 vCPU đốt gấp đôi CPU (3,95 so với 1,99 lõi).
- **Đoạn 4 vCPU nhanh hơn ~30% ở p95** (× 0,70) — một lượt đo, chênh vượt biên trôi.

**Đính chính Khối A** (`rerank-ngay15-2026-10-11.md` §3): Khối A đo qua HTTP được 4 vCPU p50/p95 13,0 /
16,8 s, chậm hơn 2 vCPU 10,7 / 13,0 s, và đặt giả thuyết luồng rơi vào nhân tiết kiệm điện. Đo trực tiếp,
cùng điều kiện, hai lượt mỗi mức: **4 vCPU nhanh hơn**. Số 2 vCPU của Khối A khớp bench (10,7 / 13,0 so với
11,1 / 13,8 s — phần HTTP nhỏ); số 4 vCPU thì không. Nguyên nhân cụ thể của lượt 4 vCPU đó không tái lập
được (file override compose của phiên trước đã mất); tải nền ~4 lúc chạy là ứng viên hàng đầu. Giả thuyết
nhân tiết kiệm điện không cần tới để giải thích số hôm nay — cũng không bị bác bỏ: tăng tốc dưới tuyến tính
có thể có phần của nó.

---

## 5. Rerank — một cặp theo độ dài (đầu vào cho đòn bẩy `max_length`)

| vCPU | Chế độ | ≤ 128 token: số cặp · p50 | 129–256 token | 257–512 token | Thời gian của cặp > 256 token |
|---|---|---|---|---|---|
| 2 | ghim | 261 · 203 ms | 222 · 462 ms | 117 · 1,4 s | 52% |
| 4 | ghim | 261 · 152 ms | 222 · 347 ms | 117 · 867 ms | 49% |
| 2 | mặc định | 261 · 1,1 s | 222 · 2,0 s | 117 · 4,7 s | 41% |
| 4 | mặc định | 261 · 398 ms | 222 · 813 ms | 117 · 2,0 s | 43% |

- 600 cặp, trung vị 145 token; 52 cặp (8,7%) chạm trần 512 — khớp 8% của notebook 07.
- **117 cặp dài (20%) ăn ~50% thời gian.** `RERANK_MAX_LENGTH=256` sẽ cắt chúng; ước lượng thô: cặp dài
  nhanh hơn ~2 lần ⇒ cả lượt nhanh hơn ~25%. **Chưa đo** — và cắt ngắn đoạn là đổi chất lượng: phải chạy
  lại nDCG@5 trên bộ vàng trước khi bật. Ghi ở ADR-0034 là "chưa thử".

---

## 6. Điều kiện đo

| # | Đo xong lúc | Cấu hình | Tải VM lúc bắt đầu | Tải máy chủ lúc bắt đầu | Thời gian đo |
|---|---|---|---|---|---|
| 1 | 21:11:59 | câu hỏi · 2 · ghim | 0,37 / 0,45 / 0,41 | 2,55 / 3,29 / 3,21 | 11 s |
| 2 | 21:12:14 | câu hỏi · 4 · ghim | 0,79 / 0,54 / 0,44 | 2,94 / 3,34 / 3,23 | 11 s |
| 3 | 21:14:09 | câu hỏi · 2 · mặc định | 1,26 / 0,66 / 0,48 | 4,78 / 3,72 / 3,36 | 105 s |
| 4 | 21:15:02 | câu hỏi · 4 · mặc định | 0,72 / 0,62 / 0,48 | 4,58 / 4,11 / 3,57 | 43 s |
| 5 | 21:21:15 | rerank · 2 · ghim | 1,94 / 1,06 / 0,64 | 6,43 / 4,57 / 3,76 | 342 s |
| 6 | 21:25:40 | rerank · 4 · ghim | 2,12 / 1,88 / 1,18 | 5,21 / 4,83 / 4,17 | 243 s |
| 7 | 21:50:23 | rerank · 2 · mặc định | 4,08 / 3,47 / 2,06 | 5,95 / 5,80 / 4,80 | 1.385 s |
| 8 | 22:00:30 | rerank · 4 · mặc định | 0,50 / 2,12 / 2,50 | 4,43 / 4,58 / 4,59 | 566 s |
| 9 | 22:00:50 | câu hỏi · 2 · ghim — lặp | 0,50 / 3,00 / 3,11 | 7,55 / 7,30 / 6,17 | 14 s |
| 10 | 22:08:11 | rerank · 2 · ghim — lặp | 1,05 / 2,97 / 3,10 | 6,46 / 7,07 / 6,10 | 413 s |
| 11 | 22:13:36 | rerank · 4 · ghim — lặp | 1,75 / 2,40 / 2,78 | 6,87 / 7,94 / 6,88 | 265 s |
| 12 | 22:14:45 | đoạn · 2 · ghim | 4,81 / 3,75 / 3,26 | 5,97 / 6,94 / 6,73 | 53 s |
| 13 | 22:15:33 | đoạn · 4 · ghim | 2,87 / 3,39 / 3,17 | 4,54 / 6,33 / 6,51 | 38 s |
| 14 | 22:20:24 | đoạn · 2 · mặc định | 4,20 / 3,71 / 3,29 | 6,51 / 6,62 / 6,61 | 253 s |
| 15 | 22:22:15 | đoạn · 4 · mặc định | 0,54 / 1,64 / 2,50 | 5,59 / 5,57 / 6,08 | 91 s |

- **Tải VM** (`/proc/loadavg` trong container) là tải của VM Docker — gồm chính lượt đo trước đó. **Tải máy
  chủ** (macOS) gồm tiến trình VM (≈ số vCPU đang đo) + Chrome (~80% một lõi) + IDE. `ai-embed`, `ai-rerank`
  vẫn chạy nhưng rảnh (~0,3% CPU, không ai gọi); `ai-service` và harness eval không chạy.
- Tải máy chủ tăng dần từ ~3 lên ~7 trong buổi đo — lý do có lượt lặp ở §4.

---

## 7. Lệnh

```bash
cd <gốc repo>
for vai in embed rerank; do for che_do in ghim mac-dinh; do for vcpu in 2 4; do
  docker run --rm --cpus $vcpu -e OMP_NUM_THREADS=$vcpu -e TZ=ICT-7 \
    -e TAI_MAY_CHU="$(sysctl -n vm.loadavg)" \
    -v "$PWD/artifacts:/app/artifacts:ro" -v "$PWD/ai-service/tests/eval:/app/eval:ro" \
    -v "$PWD/inference/bench:/app/bench:ro" -v "$PWD/reports/eval:/app/reports/eval" \
    ai-inference:dev python -m bench.bench_cpu chay --vai $vai --che-do $che_do --nhan n15
done; done; done
# tải đoạn: thêm "--vai embed --tai doan"; lượt lặp: "--nhan n15-lap"
python3 inference/bench/bench_cpu.py bang --ra reports/eval/bench-n15.md reports/eval/bench-n15-*.json
```

Rerank ước ~5 phút một cấu hình ghim, 10–25 phút một cấu hình mặc định. JSON thô (từng mẫu, từng lượt
`run`) ở `reports/eval/bench-n15*.json` — không commit, số đã chép vào đây.

---

## 8. Còn nợ

- ~~**Router (`ai-classify`)** — đo bù khi Dev B gửi `artifacts/router_model.onnx`; chứng minh điều (1) và
  chốt vCPU ai-classify (đang tạm 2).~~ **Xong 17/10** — bench thêm vai `classify`, ai-classify 1 vCPU (§9).
  Còn: đường HTTP của router ở 1 vCPU chưa đo (§9.5).
- **x86** — số trên M1 chỉ chốt cho máy dev. Đo lại trên đúng loại máy cloud ở N20 (hoãn).
- **Dưới tải song song** — mọi số ở đây là một luồng yêu cầu. Nhiều lượt chat cùng lúc chưa đo (N19 hoãn).
- **`max_length 256`** và **tắt spin của ORT** (`session.intra_op.allow_spinning = 0` — giảm CPU đốt khi chờ,
  không chắc giảm độ trễ) — chưa thử.

---

## 9. Cập nhật 17/10/2026 — router `ai-classify`: điều (1) và cấp vCPU

Đo bù phần còn mở của Khối B. `artifacts/router_model.onnx` có từ 11/10 (Dev B gửi, sha256 khớp sổ).

### 9.1. Cách đo — CHỐT TRƯỚC KHI CHẠY

Mục này viết xong **trước** khi có con số nào của router. Không sửa định nghĩa, tiêu chí hay ma trận sau
khi thấy số; phương án nghĩ ra sau khi thấy số sẽ đánh dấu `*`.

**Câu hỏi.** Điều (1) của kế hoạch: với model nhỏ, **tăng vCPU không giảm p95**. Router là model nhỏ duy
nhất của hệ thống.

**Model.** Router nhánh C — `LogisticRegression` 7 lớp × 1024 chiều, ONNX opset 15, lượng tử hoá động
`QUInt8`, 35,9 KB (`docs/MODEL_CARD_router.md`). `router_model.onnx` sha256 `0cc5f770…` ·
`router_embedder.json` sha256 `6e15b469…` — khớp dòng 6 và 7 của `artifacts/DATA_HASHES.txt`. Image
`ai-inference:dev` (`sha256:c07b9cc3ced3…`) — `session.py`, `roles/classify.py`, `roles/router_embedder.py`,
`entrypoint.py` khớp từng byte với repo (kiểm sha256 17/10).

**Đo gì.** Đúng tầng 2 của `classify.py` (dòng 257–262): `RouterEmbedder.transform_single(câu)` →
`session.run(None, {"float_input": vec.reshape(1, -1)})` → đọc nhãn và 7 xác suất. Bench dựng thẳng
`RouterEmbedder.from_json` + session, **không qua `classify()`**: tầng luật đứng trước ONNX, câu nào khớp từ
khoá thì không chạm ONNX. Không qua HTTP. Session dựng như 11/10: **ghim** = `make_session` của `session.py`
(`intra_op = OMP_NUM_THREADS`, `inter_op = 1`); **mặc định** = `SessionOptions` không đặt số luồng.

**Một mẫu = một câu.** 112 câu hỏi của `golden_set.jsonl` (chỉ đọc, sha256 `323baf73…`) × **10 vòng** =
1.120 mẫu; warm-up 20 câu, bỏ khỏi số đo. Mười vòng thay cho ba vòng của embed vì một mẫu dưới 1 ms
(Model Card §5 đo p95 0,33 ms trên Intel) — thêm mẫu gần như không tốn thời gian. Ghi tách hai chặng:
**băm** (`transform_single`, Python thuần, một luồng) và **`run`** (ONNX Runtime).

**Ma trận.** **1 · 2 · 4 vCPU × ghim / mặc định** = 6 cấu hình, `docker run --cpus N -e OMP_NUM_THREADS=N`,
nối tiếp, từng cấu hình một.

- Lượt đầu: ghim 1 → 2 → 4, rồi mặc định 1 → 2 → 4.
- Lượt lặp (`--nhan n15-router-lap`): đủ 6 cấu hình, **thứ tự ngược** (mặc định 4 → 2 → 1, rồi ghim
  4 → 2 → 1). Đảo thứ tự để tải nền trôi theo giờ không cùng chiều với số vCPU.

**Điều kiện.** `ai-classify` chạy rảnh (không ai gọi). `ai-embed`, `ai-rerank`, postgres, kafka, ai-service
và harness eval đều tắt. Ghi tải VM và tải máy chủ ở đầu mỗi lượt.

**Chỉ số.**

- **Chính:** p95 một mẫu (băm + `run` + đọc kết quả), chế độ ghim, **lượt đầu**.
- **Phụ:** p50 · p95 riêng `run` · số luồng ORT tạo · chu kỳ cgroup bị chặn · lõi dùng TB · RSS.
- **Biên trôi:** chênh tương đối lớn nhất của p95 giữa lượt đầu và lượt lặp, trên 3 cấu hình ghim.

**Tiêu chí điều (1).**

- **Đã chứng minh** nếu, ở chế độ ghim, p95 lượt đầu ở 2 vCPU và ở 4 vCPU đều **không thấp hơn** p95 ở
  1 vCPU quá biên trôi: `p95(N) ≥ p95(1) × (1 − biên trôi)` với N = 2 và N = 4.
- Nếu 2 hoặc 4 vCPU nhanh hơn 1 vCPU vượt biên trôi ⇒ ghi **bị bác bỏ** kèm số thật, không đổi định nghĩa.
- Biên trôi lớn (≥ 50%) thì phép thử yếu — ghi rõ, không coi "không phát hiện chênh" là "bằng nhau".

**Tiêu chí đề xuất cấp vCPU** (người dùng chốt bằng bảng số): mức **nhỏ nhất** trong {1, 2, 4} mà p95
ghim lượt đầu không chậm hơn mức nhanh nhất quá biên trôi. Ngưỡng §5.3 60 ms ghi để biết khoảng cách,
**chưa áp dụng**. Ghi trước, ngoài số đo:

- `ai-classify` còn phục vụ `/v1/lead-score` (UC030) — hiện chấm bằng luật, chưa có model, không chạy ONNX.
- uvicorn một tiến trình, handler `async` gọi ONNX đồng bộ ⇒ yêu cầu đồng thời xếp hàng trên một luồng
  event loop dù cấp bao nhiêu vCPU. Bench chỉ đo một luồng yêu cầu; dưới tải song song chưa đo (N19 hoãn).

**Không làm:** không chạy `scripts/evaluate_router_branches_comparison.py` (ghi lại `DATA_HASHES.txt`);
không đọc `data/intent_test_human.jsonl`.

**Bổ sung sau lượt chạy thử, TRƯỚC khi chạy ma trận (17/10).** Lượt chạy thử kiểm code (2 vCPU, ghim,
1 vòng, 112 mẫu, không dùng làm số) cho hai điều: (a) bench khớp production — câu "may giat nay bao hanh
may nam" ra `BUYING_INTENT` với **đúng 7 xác suất** như `POST /v1/classify` của container `ai-classify`;
(b) **112 mẫu đo xong trong ~10 ms** ⇒ 1.120 mẫu chỉ ~0,1 s, khoảng **một chu kỳ CFS 100 ms**. Cơ chế làm
chậm của cgroup (hạn mức cạn giữa chu kỳ, cả tiến trình dừng tới chu kỳ sau) gần như không có chỗ để hiện ra,
và cột "chu kỳ bị chặn" không có thông tin. Vì vậy thêm:

- **Lượt dài** (`--nhan n15-router-dai --vong 1000`, 112.000 mẫu, ~10 s một cấu hình ghim — cỡ lượt embed
  câu hỏi 11/10): đủ 6 cấu hình, cùng thứ tự lượt đầu; rồi lặp 3 cấu hình ghim theo thứ tự ngược
  (`n15-router-dai-lap`) để có biên trôi riêng.
- **Tiêu chí điều (1) và tiêu chí đề xuất vCPU áp dụng cho CẢ lượt ngắn lẫn lượt dài**, mỗi lượt với biên
  trôi của chính nó. Hai lượt cho kết luận khác nhau thì ghi cả hai, không chọn lượt đẹp hơn. Đây là siết
  thêm, không nới: phải đạt ở cả hai mới ghi "đã chứng minh".

### 9.2. Kết quả — lượt dài (112.000 mẫu một cấu hình)

Đo 17/10 21:00–21:02, `ai-classify` chạy rảnh, các container khác tắt; tải máy chủ 2,8–3,8 (1 phút).

| vCPU | Chế độ | Luồng ORT tạo | p50 | p95 | p99 | Lâu nhất | Chu kỳ bị chặn | Lõi dùng TB |
|---|---|---|---|---|---|---|---|---|
| 1 | ghim | +0 | 0,074 ms | **0,176 ms** | 0,236 ms | 15 ms | 23% | 1,00 |
| 2 | ghim | +1 | 0,075 ms | **0,177 ms** | 0,239 ms | 9,8 ms | 0% | 1,00 |
| 4 | ghim | +3 | 0,075 ms | **0,176 ms** | 0,236 ms | 7,9 ms | 0% | 1,00 |
| 1 | mặc định | +7 | 0,074 ms | **0,174 ms** | 0,232 ms | 78 ms | 66% | 0,99 |
| 2 | mặc định | +7 | 0,075 ms | **0,176 ms** | 0,239 ms | 4,9 ms | 0% | 1,00 |
| 4 | mặc định | +7 | 0,074 ms | **0,173 ms** | 0,231 ms | 3,3 ms | 0% | 1,00 |

**Lượt lặp ghim (thứ tự ngược):** 4 vCPU 0,208 ms (+18,0%) · 2 vCPU 0,183 ms (+3,4%) · 1 vCPU 0,177 ms
(+0,9%) ⇒ **biên trôi 18,0%**.

**Hai chặng của một mẫu** (giống nhau ở mọi cấu hình): băm n-gram p50 0,056 / p95 0,149–0,157 ms, **77%**
thời gian · `run` p50 0,014 / p95 0,017–0,020 ms, **17%** · đọc nhãn và 7 xác suất ~6%. RSS sau khi nạp 80–81 MB
(đỉnh 127 MB của lượt dài gồm danh sách 112.000 mẫu bench giữ trong bộ nhớ, không phải của router).

### 9.3. Kết quả — lượt ngắn (1.120 mẫu một cấu hình, như chốt ban đầu)

Đo 17/10 20:59, cùng điều kiện, mỗi lượt đo ~0,1 s.

| vCPU | p95 ghim lượt đầu / lặp | Chênh | p95 mặc định lượt đầu / lặp |
|---|---|---|---|
| 1 | 0,187 / 0,184 ms | −1,6% | 0,548 / 0,184 ms |
| 2 | 0,213 / 0,189 ms | −11,2% | 0,178 / 0,178 ms |
| 4 | 0,193 / 0,298 ms | **+54,2%** | 0,168 / 0,188 ms |

**Biên trôi 54,2%** — lượt ngắn quá ngắn để ổn định, đúng như lo ở §9.1. Cột "chu kỳ bị chặn" của lượt
ngắn (0% / 33% / 100% xen kẽ) dựa trên 1–2 chu kỳ CFS, không đọc được. Bảng đầy đủ:
`reports/eval/bench-n15-router.md` và `bench-n15-router-dai.md` (không commit).

### 9.4. Kết luận

1. **Điều (1) — model nhỏ tăng vCPU không nhanh hơn: ĐÃ CHỨNG MINH**, áp đúng tiêu chí §9.1:
   - *lượt dài:* cận dưới `0,176 × (1 − 0,18)` = 0,144 ms; p95 ở 2 vCPU 0,177 và ở 4 vCPU 0,176 ms đều
     trên cận ⇒ **đạt**;
   - *lượt ngắn:* biên trôi 54,2% ≥ 50% ⇒ **phép thử yếu**; cận 0,086 ms; p95 0,213 và 0,193 ms ⇒ đạt.

   **Cơ chế thấy được trong số:** lõi dùng TB **1,00 ở mọi mức vCPU**. Graph chỉ là một tích 1 × 1024 với
   1024 × 7 rồi softmax — ONNX Runtime không chia việc cỡ này cho pool luồng, các luồng thêm vào nằm ngủ.
   So với bge-m3 ghim 4 vCPU: dùng 3,95 lõi (§2). Thêm nữa, **77% thời gian một mẫu là băm n-gram** trong
   Python (MD5 + SHA-1 mỗi token, một luồng) — không vCPU nào tăng tốc được phần đó.
2. **Router không bị phạt khi để mặc định** — khác hẳn bge-m3 và reranker (§3: × 2,2–13,3). p95 mặc định ÷
   ghim = × 0,98–1,00 ở lượt dài. ORT vẫn tạo 8 luồng, nhưng luồng không có việc thì không quay chờ, không
   tranh hạn mức. Phạt chỉ hiện ở **đuôi cực xa của 1 vCPU**: 66% chu kỳ bị chặn, mẫu lâu nhất 78 ms (ghim:
   15 ms); p99 không đổi. Đây là quan sát sau khi thấy số; **không đổi kỷ luật ghim luồng**: luật áp cho cả
   ba vai, bất biến 3 kiểm như nhau, và ghim không tốn gì.
3. **Tiêu chí đề xuất §9.1 cho ra 1 vCPU** (lượt dài: 1 vCPU 0,176 ms bằng mức nhanh nhất; lượt ngắn: 1 vCPU
   là mức nhanh nhất). **Người dùng chốt 17/10: ai-classify 1 vCPU** (từ 2 tạm).
4. **So với ngưỡng 60 ms §5.3** (chưa áp dụng): p95 0,176 ms, khoảng 1/340 ngưỡng. Phần lớn độ trễ thật của
   router nằm ở **HTTP**: Dev B đo ngày 05/10 ở 2 vCPU, client Windows — p95 5,3 ms tuần tự, 18,8 ms với 5
   yêu cầu đồng thời (`docs/report/bao-cao-uc022-router.md` §6). Số 0,182 ms ADR-0019 từng ghi là **gán
   cứng, đã thu hồi** (ADR-0019 mục 0) — gần số đo hôm nay chỉ là tình cờ, vẫn không dẫn. Model Card §5 đo
   p95 0,33 ms trên Intel ngoài Docker — khác máy, không so trực tiếp.

### 9.5. Đánh đổi và chỗ chưa đo của 1 vCPU

- **Hạn mức chật.** Bench chạy một lõi liên tục 100%, nên ở 1 vCPU có 23–49% chu kỳ bị chặn (tổng ~0,06 s
  trên 10 s), mẫu lâu nhất 15–16 ms so với 8–10 ms ở 2–4 vCPU; p95, p99 không đổi. Service thật không chạy
  liên tục như vậy (mỗi lượt chat gọi router một lần).
- **HTTP, uvicorn và log chạy chung một lõi với router — chưa đo ở 1 vCPU.** Số HTTP duy nhất có là của
  2 vCPU. N19 (hoãn) mà thấy p95 qua HTTP dưới tải tăng thì trả về 2 vCPU: đổi compose, không đổi code.
- **Thêm vCPU cũng không thêm thông lượng:** uvicorn một tiến trình, handler `async` gọi ONNX đồng bộ ⇒ yêu
  cầu đồng thời xếp hàng trên một luồng event loop. Muốn thêm thông lượng phải thêm worker hoặc bản sao,
  không phải thêm vCPU cho một tiến trình.
- **Số trên Apple M1** — x86 đo lại ở N20 (hoãn), như embed và rerank.

### 9.6. Lệnh

```bash
cd <gốc repo>
docker compose -f inference/compose.inference.yml up -d ai-classify      # chỉ để kiểm /ready; bench không gọi nó
for nhan_vong in "n15-router 10" "n15-router-dai 1000"; do read -r nhan vong <<<"$nhan_vong"
  for che_do in ghim mac-dinh; do for vcpu in 1 2 4; do
    docker run --rm --cpus $vcpu -e OMP_NUM_THREADS=$vcpu -e TZ=ICT-7 \
      -e TAI_MAY_CHU="$(sysctl -n vm.loadavg)" \
      -v "$PWD/artifacts:/app/artifacts:ro" -v "$PWD/ai-service/tests/eval:/app/eval:ro" \
      -v "$PWD/inference/bench:/app/bench:ro" -v "$PWD/reports/eval:/app/reports/eval" \
      ai-inference:dev python -m bench.bench_cpu chay --vai classify --che-do $che_do \
      --nhan $nhan --vong $vong
  done; done
done
# lượt lặp: "--nhan n15-router-lap" (6 cấu hình) và "--nhan n15-router-dai-lap --vong 1000" (3 cấu hình
# ghim), thứ tự ngược
python3 inference/bench/bench_cpu.py bang --ra reports/eval/bench-n15-router.md \
  reports/eval/bench-n15-router-classify-*.json reports/eval/bench-n15-router-lap-*.json
python3 inference/bench/bench_cpu.py bang --ra reports/eval/bench-n15-router-dai.md \
  reports/eval/bench-n15-router-dai-*.json
```
