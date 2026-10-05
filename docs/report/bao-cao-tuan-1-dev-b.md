# Báo cáo Tuần 1 — Dev B (Module AI)

> Kỳ: Tuần 1 kế hoạch 21 ngày (21–27/09/2026). Lập ngày 2026-10-05.
> Nguồn: bảng kế hoạch `docs/Ke-hoach-21-ngay-Module-AI-CRM.xlsx`, lịch sử Git, số đo chạy lại ngày 05/10.

## 1. Tóm tắt

- **Trễ lịch:** toàn bộ việc Tuần 1 của Dev B được commit vào **04–05/10** (Ngày 14–15), không phải
  21–27/09 như kế hoạch.
- **Đính chính số liệu:** rà soát 05/10 phát hiện một phần số liệu Tuần 1 không phải số đo (mục 4).
  Đã gỡ khỏi code và tài liệu; số liệu trong báo cáo này là số đo thật.
- **Trạng thái:** cả 7 ngày đều có phần đã làm thật và có bằng chứng, nhưng **chưa ngày nào hết nợ**.
  Đạt ngưỡng: p95 phân loại qua remote, cổng CI, parity ONNX, báo nhầm guardrails. Còn nợ: việc cần
  người (gán nhãn Kappa, chạy Kaggle nhánh B, bộ adversarial) và việc phụ thuộc Dev A (tải hỗn hợp).

## 2. Từng ngày

| Ngày | Task | Đã làm thật (bằng chứng) | Còn nợ |
|---|---|---|---|
| 1 | Chốt 4 mâu thuẫn hợp đồng + siết CI dung lượng | ADR-0017; CI exit 1 khi image ≥ 400 MB; **6/6 cổng CI xanh, image 232 MB** (`bash scripts/check_ci_gates.sh`) — `870b150`, `4c9cd24` | `create-topics.sh` tạo 14 topic, ADR chốt 9 — cần thống nhất với Dev A |
| 2 | Tầng suy luận thật + gõ tập test | 3 service, `/ready` fail-closed 3 bất biến, client remote/mock; tập test 200 câu + hash — `870b150` | Xác nhận nguồn gốc 200 câu (commit lần đầu 04/10); ảnh chụp `/ready` 503 |
| 3 | UC022 (1/4) dữ liệu + gán nhãn chéo | 1.941 câu train (template), dedup Jaccard; script Kappa đọc nhãn thật + phiếu mù — `a005547`, `98f327b` | **Kappa chưa đo** — cần hai người gán nhãn (~1 giờ/người) |
\1; **nhánh B huấn luyện thật trên CPU: Macro-F1 0,721, p95 72,4 ms** — `fa15bed`, `b553bde` | Quyết định LogReg/kNN và embedder băm/BGE-M3 |
| 5 | UC022 (3/4) so sánh + ship + ONNX | ONNX INT8 parity 2,98 × 10⁻⁷, khớp 200/200; đường cong abstention; ADR-0019 (có đính chính) — `f99c6b2`, `98f327b` | — (đã có bảng B–C + paired bootstrap: ship C theo cả hai quy tắc §5.9) |
| 6 | UC022 (4/4) API 7 nhánh + guardrails | Guardrails sửa + đo (0 báo nhầm / 2.141 câu); `/v1/ai/chat` định tuyến 7 nhánh, 26 test — `10769c5`, `5974882` | Bộ ≥ 60 câu adversarial; ảnh lượt TOOL_CALL → chuyển giao |
| 7 | Kiểm chứng remote, tải hỗn hợp, báo cáo | **p95 phân loại qua remote 5,3 ms** (5 đồng thời 18,8 ms) sau khi sửa 2 lỗi; cổng CI xanh; báo cáo UC022 — `3a8eb7d`, `498733e`, `4c9cd24` | **Tải hỗn hợp: BLOCKED** (mục 5) |

## 3. Chỉ số

| Chỉ số | Ngưỡng | Đo được | Lệnh tái lập |
|---|---|---|---|
| p95 phân loại qua remote | ≤ 60 ms | **5,3 ms** tuần tự · 18,8 ms 5 đồng thời | `python scripts/bench_remote_classify.py --url http://127.0.0.1:8083` |
| Image ai-service sạch ML runtime | grep rỗng | **rỗng** | `bash scripts/check_ci_gates.sh` |
| Dung lượng image ai-service | < 400 MB | **232 MB** | như trên |
\1| Nhánh B vs C (paired bootstrap) | — | Δ +0,044 [−0,040 ; +0,131], không ý nghĩa; B p95 72,4 ms > 60 ms | `python scripts/evaluate_router_branches_comparison.py --no-export` |\n| Macro-F1 router 3 tầng | — | 0,712 | xem `docs/report/bao-cao-uc022-router.md` |
| Báo nhầm tiêm chỉ thị | < 1% | 0/200 test · 0/1.941 train | `python -m pytest ai-service/tests/unit/test_guardrails.py` |
| Không gọi LLM | ≥ 55% | 72% (trong đó 39,5% hỏi lại) | mô phỏng 200 câu qua `run_turn` |
| p95 không xấu đi > 15% khi đang nạp | — | **chưa đo** | BLOCKED |
| Rò rỉ tenant trên `knowledge_chunks` | 0 | **chưa đo** | BLOCKED (test RLS của Dev A) |
| Cohen's Kappa | — | **chưa đo** | `python scripts/compute_annotation_kappa.py` |

## 4. Đính chính số liệu (rà soát 05/10)

| Số liệu cũ | Thực tế | Xử lý |
|---|---|---|
| Cohen's Kappa 0,93 / 0,887 | Nhãn "Dev A" dựng từ nhãn vàng + 13 ca viết cứng trong code | Gỡ; script mới đọc nhãn thật — `98f327b` |
| Nhánh B XLM-R F1 0,8947, p95 168,2 ms | Dự đoán sinh ngẫu nhiên, độ trễ gán cứng | Gỡ; nhánh B = NOT_EVALUATED — `98f327b` |
| Log Kaggle "Val F1 0,9395, 3 giờ 21 phút" | Log dựng sẵn; nhánh B chưa từng chạy | Xoá — `a7abb81` |
| Nhánh C dùng BGE-M3 | Feature hashing n-gram + IDF | Đính chính ADR-0018/0019, MODEL_CARD — `73c3b3a` |
| Nhánh C Macro-F1 0,7582 | Là kNN; mô hình ship (LogReg) = 0,6755 | Đánh giá đúng mô hình ship — `98f327b` |
| Container ai-classify chạy router | Âm thầm chạy luật từ khoá | Sửa + fail-closed — `3a8eb7d` |

## 5. Tải hỗn hợp — BLOCKED, kịch bản chờ chạy

**Chặn bởi:** worker nạp tài liệu (`ai-service/src/worker/main.py` còn `NotImplementedError`),
`rag/ingest/` rỗng, `ai-embed` trả vector giả — UC018/UC019 của Dev A; và test RLS `knowledge_chunks`.
Kế hoạch cũng ghi chạy **sau** khi Dev A reindex fine-tune xong để không tranh CPU.

**Kịch bản khi đủ điều kiện:**
1. Đo p95 nền: `bench_remote_classify.py` (và `/v1/ai/chat` qua gateway) khi hệ thống rảnh.
2. Bắt đầu nạp một tài liệu ~3.000 đoạn qua UC018.
3. Trong lúc nạp, bắn 20 request đồng thời liên tục; đo p95 lần hai.
4. Đạt nếu p95 lúc nạp ≤ 1,15 × p95 nền; ghi bảng 2 cột trước/trong.
5. Song song chạy test RLS: tenant A đọc chunk của tenant B trả rỗng.

## 6. Phụ thuộc Dev A

| Việc | Cần gì từ Dev A |
|---|---|
| Kappa (Ngày 3) | Gán nhãn độc lập `data/annotations/dev_a.csv` + họp các ca bất đồng |
| Tập test (Ngày 2) | Xác nhận 200 câu do hai người gõ tay |
| Bộ topic (Ngày 1) | Thống nhất 9 hay 14 topic trước khi viết consumer UC019 |
| Guardrails (Ngày 6) | Dev A gắn vào node guard Ngày 8 — thống nhất ranh giới với `src/ai/orchestrator/turn.py` đã có |
| Tải hỗn hợp (Ngày 7) | UC018/UC019 chạy được + reindex xong |

## 7. Việc tiếp theo

1. Buổi gán nhãn chung với Dev A → Kappa.
3. Nhánh RAG (UC023) — `/v1/ai/chat` hiện từ chối mọi câu cần tra tài liệu; chặn mốc M2.
4. Bộ ≥ 60 câu adversarial.
5. Tải hỗn hợp khi Dev A xong UC018/UC019.
