# ADR-0034 — Chốt cấp vCPU: ai-embed 4, ai-rerank 4, ghim luồng bắt buộc; bench ở `inference/bench/`

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-11
- **Làn sở hữu:** Track B (module AI)
- **Quan hệ:** kế hoạch Ngày 15 Khối B · Master Plan §3.9.2, §5.3, §5.4, §5.4.1, §5.6 ·
  [ADR-0006](0006-hybrid-search-rrf-rerank.md) (rerank bật, 20 ứng viên) ·
  [ADR-0015](0015-cau-truc-src-hai-tang-theo-master-plan-v8.md) (tầng suy luận) ·
  [ADR-0019](0019-chot-nhanh-ship-intent-router-va-nguong-abstention.md) mục 0 ·
  [ADR-0021](0021-cong-parity-int8-truot-phan-xu-bang-recall.md) ·
  số đo: [`docs/report/benchmark-ngay15-2026-10-11.md`](../report/benchmark-ngay15-2026-10-11.md)

## Bối cảnh

- `inference/compose.inference.yml` đặt **tạm** ai-embed 4 vCPU, ai-rerank 2, ai-classify 2, ghi "chốt ở
  Ngày 21 dựa trên bảng benchmark". Lịch 21 ngày dời việc chốt về Ngày 15.
- Master Plan §5.6 giả định **ma trận nhiều ứng viên** (`e5-small`, `e5-base`, `ce-MiniLM`, `PhoRanker`…)
  để chọn model theo độ trễ. Hệ thống thật **mỗi vai chỉ có một model** (`artifacts/MODEL_REGISTRY.md`):
  bge-m3 INT8 nhúng, bge-reranker-v2-m3 INT8 xếp lại, router LogisticRegression phân loại. Không có ứng viên
  nào để so rồi loại — câu hỏi còn lại chỉ là **cấp bao nhiêu vCPU và cấu hình luồng ra sao**.
- `session.py` đã ghim `intra_op = OMP_NUM_THREADS`, `inter_op = 1`, và `/ready` kiểm `OMP_NUM_THREADS`
  khớp cgroup (bất biến 3). Chưa có số đo nào chứng minh kỷ luật này đáng giá.
- Khối A (cùng ngày) đo rerank qua HTTP: 4 vCPU **chậm hơn** 2 vCPU — nhưng hai lượt ở hai mức tải nền.
- Người dùng chốt 11/10/2026: **độ trễ chưa là cổng**. Vượt ngưỡng §5.3 không phải lý do tắt hay cắt.

## Các phương án đã cân nhắc

Số: p95 một yêu cầu, ghim luồng, Apple M1 — chi tiết ở phần Lập luận.

| Phương án | Ưu | Nhược |
|---|---|---|
| **A.** Giữ cấp tạm — embed 4, rerank 2 | Không đổi gì; tổng 6 vCPU, nhẹ máy dev | Rerank chậm hơn B 25–30% (p95 13,8 / 18,6 s so với 10,3 / 10,5 s) mà không được gì |
| **B.** embed 4, rerank 4 — **chọn** | Rerank nhanh nhất đo được; nạp kho nhanh hơn C ~30% | 8 vCPU = cả VM Docker của máy dev; lượt chat dùng embed 4 vCPU đốt dư 2 lõi |
| **C.** embed 2, rerank 4 | Cùng tổng 6 vCPU như A; lượt chat nhanh như B (câu hỏi 68 ≈ 69 ms) | Nhúng đoạn chậm hơn ~30% (p95 911 so với 638 ms) — worker UC019 nạp kho chậm hơn |
| **D.** Không ghim, để ONNX Runtime tự chọn luồng | Không phải cấu hình gì | Chậm 2,2–13,3 lần (đo) — và `/ready` **không** bắt được: bất biến 3 chỉ so biến môi trường `OMP_NUM_THREADS` với cgroup, không kiểm số luồng thật của session |

Người dùng chốt **B** ngày 11/10/2026 sau khi xem bảng số.

## Quyết định

| Service | vCPU = `OMP_NUM_THREADS` | Trước | Căn cứ (ghim luồng, M1, một luồng yêu cầu) |
|---|---|---|---|
| `ai-embed` | **4** | 4 (tạm) | Câu hỏi: p95 68 ms ở 2 ≈ 69 ms ở 4 vCPU. Đoạn (nạp kho UC019): p95 911 → **638 ms** |
| `ai-rerank` | **4** | 2 (tạm) | 20 cặp: p50 11,1 / 12,5 s → **7,8 / 9,0 s**; p95 13,8 / 18,6 s → **10,3 / 10,5 s** (hai lượt mỗi mức) |
| `ai-classify` | 2 — **vẫn tạm** | 2 (tạm) | Chưa có `router_model.onnx`; đo bù khi có |

Kèm theo, không đổi mà nay có số:

1. **Ghim luồng bắt buộc:** `intra_op_num_threads = OMP_NUM_THREADS = limits.cpu`, `inter_op = 1`,
   `requests.cpu = limits.cpu`. Để mặc định thì p95 chậm **2,2–13,3 lần** (bảng dưới).
2. **Bench ở `inference/bench/bench_cpu.py`, nhãn `[R&D]`** — lệch Master Plan §3.9.2 (`inference/src/
   bench_cpu.py`). Bench không phục vụ request nên không phải `[PRODUCTION]`; `[R&D]` thì không được vào
   image — mà `src/` bị `COPY src/ src/` chép trọn vào image. Đặt ngoài `src/`, mount lúc đo: chạy đúng
   onnxruntime và `session.py` của image ship, sửa bench không phải build lại image. CI vẫn biên dịch
   `bench/` (`compileall -q src bench`).
3. **Không model nào bị loại ở Ngày 15** — mỗi vai một model, và độ trễ chưa là cổng. Trường hợp duy nhất
   của dự án bị loại vì độ trễ là **router nhánh B XLM-R: p95 72,4 ms (INT8) > 60 ms**, đo thật ngày 05/10 —
   [ADR-0019](0019-chot-nhanh-ship-intent-router-va-nguong-abstention.md) **mục 0** (con số 168,2 ms ở thân
   ADR-0019 đã bị thu hồi, không dẫn).

## Lập luận

**Ghim luồng — điều (2) của kế hoạch, đã chứng minh.** Để mặc định, ONNX Runtime tạo pool **8 luồng
intra-op** theo số CPU của VM, bất kể `--cpus 2` hay `--cpus 4` (đếm `Threads` trước/sau khi nạp: +7 ở mọi
cấu hình mặc định; ghim N luồng: +N−1):

| Model — tải | vCPU | p95 ghim / mặc định | Mặc định ÷ ghim | Chu kỳ cgroup bị chặn |
|---|---|---|---|---|
| bge-m3 — câu hỏi | 2 | 68 ms / 906 ms | **× 13,3** | 36% / 100% |
| bge-m3 — câu hỏi | 4 | 69 ms / 310 ms | × 4,5 | 41% / 99% |
| bge-m3 — đoạn | 2 | 911 ms / 3,5 s | × 3,8 | 31% / 100% |
| bge-m3 — đoạn | 4 | 638 ms / 1,4 s | × 2,2 | 33% / 100% |
| reranker — 20 cặp | 2 | 13,8 s / 57,6 s | × 4,2 | 31% / 100% |
| reranker — 20 cặp | 4 | 10,3 s / 25,6 s | × 2,5 | 36% / 100% |

Các lượt "mặc định" đều chạy với `OMP_NUM_THREADS` = số vCPU trong môi trường — ORT **không đọc** biến
này; thứ ghim được luồng là `intra_op_num_threads` mà `make_session` đặt từ nó. Tám luồng chia hạn mức
2 vCPU: hạn mức cạn giữa mỗi chu kỳ 100 ms, cả tiến trình bị dừng tới chu kỳ sau.
CPU dùng không đổi (2,00 lõi) — chỉ bị phí. Không log nào báo. Hạn mức càng chật, việc càng nhỏ thì phạt
càng nặng.

**ai-rerank 4 vCPU.** Tăng tốc dưới tuyến tính (gấp đôi vCPU, p50 giảm 25–30%) nhưng chắc chắn: lượt *chậm
nhất* ở 4 vCPU (p95 10,5 s) vẫn nhanh hơn lượt *nhanh nhất* ở 2 vCPU (13,8 s), trong khi hai lượt cùng cấu
hình trôi tới +35% theo tải máy. Rerank là tầng chậm nhất của lượt chat (ADR-0006), nên 3 s bớt được ở đây
là 3 s người dùng thấy. RAM không đổi (~830 MB đỉnh).

**ai-embed giữ 4.** Lượt chat chỉ nhúng một câu hỏi (trung vị 13 token): 2 ≈ 4 vCPU, chênh nằm trong biên
trôi — và 4 vCPU đốt gấp đôi CPU (3,95 so với 1,99 lõi) cho cùng p95. Nhưng cùng service còn nhúng đoạn khi
worker UC019 nạp kho: ở đó 4 vCPU nhanh hơn ~30% (p95 911 → 638 ms; 2,86 → 3,99 đoạn/s). Chọn theo việc
nặng hơn của service.

**Đính chính Khối A.** "4 vCPU không nhanh hơn 2 vCPU trên M1" (`docs/report/rerank-ngay15-2026-10-11.md`
§3) **sai** khi đo cùng điều kiện. Số 2 vCPU của Khối A khớp bench (10,7 / 13,0 s qua HTTP so với
11,1 / 13,8 s); số 4 vCPU (13,0 / 16,8 s) thì không — lượt đó chạy lúc tải nền ~4, file override compose đã
mất nên không tái lập được nguyên nhân cụ thể.

## Rerank vượt ngưỡng kế hoạch 300 ms mà vẫn bật — năm đòn bẩy §5.4.1

Rerank p95 10,3 s ở 4 vCPU — gấp ~34 lần ngưỡng §5.3. Không loại vì độ trễ chưa là cổng và chất lượng thì
đạt (recall@5 0,74 → 0,87, ADR-0006). §5.4.1 vẫn đòi ghi đã thử gì:

| # | Đòn bẩy | Đã thử? | Số đo |
|---|---|---|---|
| 1 | Nâng vCPU | **Đã thử** 2 → 4 (Khối B) | p95 13,8 / 18,6 s → 10,3 / 10,5 s. 8 vCPU chưa thử — máy dev chỉ có 8 CPU cho cả VM |
| 2a | Giảm số ứng viên 20 → 12 | **Đã thử** (Khối A) | p50 / p95 5,7 / 9,0 s ở 2 vCPU qua HTTP — nhưng trần recall@5 tụt 0,95 → 0,83 < 0,85 §1.6, đo thật 0,87 → 0,80. Không dùng |
| 2b | Chỉ xếp lại khi mơ hồ | **Đã thử** (Khối A) — đang bật | Cổng đánh dấu 93% câu ⇒ gần như không bớt lượt nào. Hiệu chỉnh `AMBIGUITY_GAP` **chưa thử** (đổi chất lượng lấy độ trễ — cần người dùng chốt) |
| 2c | `RERANK_MAX_LENGTH` 512 → 256 | **Chưa thử** | Cặp > 256 token = 20% số cặp nhưng ~50% thời gian ⇒ ước ~25% nhanh hơn. Phải đo lại nDCG@5 trước khi bật |
| 2d | Ghép lô nhiều cặp | **Không làm** | Ghép lô làm điểm một cặp phụ thuộc cặp đi cùng (`DynamicQuantizeLinear`, xem `rerank.py`); cổng parity đo theo lô 1 |
| — | Ghim luồng đúng (không phải đòn bẩy, là điều kiện đúng) | **Đã thử** | Mặc định chậm × 2,5–4,2 |
| 3 | Phân bổ lại ngân sách §5.3 | **Không áp dụng** | Độ trễ chưa là cổng |
| 4 | Distil / thu nhỏ model | **Chưa thử** | 1–2 ngày GPU — ngoài phạm vi đợt này |
| 5 | Ứng viên nhì | **Không có** | Mỗi vai một model; bản Jaccard cũ là giả, không phải ứng viên |

## Đánh đổi

- **ai-rerank 4 vCPU = gấp đôi CPU cho 25–30% độ trễ.** Trên cloud, theo hướng "chỉ bật khi demo, tiền theo
  giờ nhỏ" (memory `cloud-chi-bat-khi-demo`), đây là giá rẻ. Trên máy dev, ai-embed 4 + ai-rerank 4 = cả 8
  vCPU của VM Docker: trong một lượt chat hai bước chạy nối tiếp nên không tranh nhau, nhưng worker nạp kho
  chạy cùng lúc với lượt chat thì có. Cần nhẹ máy thì `RERANK_ENABLED=false` (ADR-0006) hoặc trả ai-rerank về
  2 vCPU — đổi compose, không đổi code.
- **ai-embed 4 vCPU đốt dư CPU cho lượt chat** (2 lõi quay chờ). Chấp nhận để nạp kho nhanh hơn. Tách hai
  việc thành hai deployment (câu hỏi 2 vCPU, đoạn 4 vCPU) là đúng hơn về tài nguyên nhưng thêm một service —
  không đáng ở quy mô đồ án.
- **Số đo trên Apple M1** (ARM; 4 nhân hiệu năng + 4 tiết kiệm điện; VM Docker Desktop), một luồng yêu cầu.
  Chốt cho máy dev; **x86 đo lại ở N20** (hoãn) trước khi coi là số production — "vCPU" trên EC2 là siêu
  luồng, kernel INT8 là AVX thay vì NEON.
- **Bất biến 3 chỉ canh biến môi trường, không canh session.** Ai đó sửa `make_session` bỏ dòng
  `intra_op_num_threads` thì `/ready` vẫn xanh trong khi p95 chậm vài lần. Chốt chặn duy nhất hiện có là
  đọc code; kiểm `Threads` của tiến trình ở `/ready` (cách bench đếm) là việc nhỏ cho sau — `session.py` là
  file của Dev B, báo chứ không sửa hộ.
- **Ghim luồng vẫn bị chặn 31–41% chu kỳ** — luồng tách từ và luồng Python ngoài pool ORT dùng chung hạn
  mức. Tắt spin của ORT (`session.intra_op.allow_spinning = 0`) có thể giảm CPU đốt khi chờ; **chưa thử**.

## Hệ quả

- `inference/compose.inference.yml`: ai-rerank `cpus` 2 → 4, `OMP_NUM_THREADS` 2 → 4; comment "chốt ở Ngày
  21" thay bằng trỏ về ADR này. ai-classify giữ 2, ghi rõ còn tạm.
- `artifacts/MODEL_REGISTRY.md`: cột *Cấp vCPU* và *p95 đo thật* của `bge-m3-int8` và
  `bge-reranker-v2-m3-int8`.
- `inference/bench/bench_cpu.py` thay khung rỗng `inference/src/bench_cpu.py`; CI biên dịch thêm `bench/`.
- `session.py` (Dev B) còn ghi "Cấp S/M/L chốt ở Ngày 21" và "chạy `bench_cpu.py`… trong pod" — không sửa
  hộ, báo trong mô tả PR.
- **Còn mở:** điều (1) "model nhỏ tăng vCPU không nhanh hơn" và vCPU của ai-classify — chờ
  `router_model.onnx`; bench thêm vai `classify` khi có model. Đo x86 ở N20; đo dưới tải song song ở N19.
