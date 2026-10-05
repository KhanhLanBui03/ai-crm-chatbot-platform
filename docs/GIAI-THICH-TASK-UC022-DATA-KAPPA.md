# DỮ LIỆU HUẤN LUYỆN VÀ GÁN NHÃN CHÉO (UC022 — 1/4)

> Tài liệu này mô tả **đúng như code đang chạy** cho task UC022 (1/4) của kế hoạch 21 ngày.
>
> ⚠️ **Viết lại 2026-10-05.** Bản trước báo Cohen's Kappa κ = 0,9300 (và nơi khác 0,887 / 0,892)
> kèm 13 ca bất đồng "đã họp thống nhất". Con số đó **không có thật**: script cũ lấy nhãn vàng làm
> nhãn Dev B và dựng nhãn Dev A bằng cách sửa 13 câu viết cứng trong code. Không có buổi gán nhãn
> độc lập nào. Bản trước cũng trình bày tỉ lệ khử trùng lặp 35,3% như bằng chứng cho cảnh báo
> "~30% là bản sao" — trong khi chính script đã chèn các bản sao đó vào.

---

## I. Ba việc của task và trạng thái

| Việc | Trạng thái |
|---|---|
| Tập train theo 6 văn phong | **Có** — sinh bằng template, xem mục II |
| Khử trùng lặp gần giống | **Có** — thuật toán chạy thật, nhưng dữ liệu đầu vào có bản sao do script tự chèn |
| Cohen's Kappa giữa hai người gán nhãn độc lập | **Chưa làm** — phiếu đã sẵn sàng, xem mục IV |

---

## II. Tập train: sinh bằng template

`scripts/build_router_data_and_eval.py` (seed 42) tổ hợp câu từ các ô từ vựng `SLOTS` của từng ý
định bằng `random.choice`, rồi biến đổi theo văn phong (bỏ dấu, gõ sai, chèn emoji…).
**Không gọi LLM** — khác với mô tả "sinh 3.000 mẫu bằng LLM" của kế hoạch.

| Văn phong | Chỉ tiêu tập thô | Còn lại sau khử trùng lặp |
|---|---|---|
| `polite_full` — lịch sự đầy đủ | 750 (25%) | 384 |
| `short_abbrev` — chat ngắn viết tắt | 750 (25%) | 639 |
| `no_accent` — không dấu | 600 (20%) | 426 |
| `typo` — lỗi chính tả nhẹ | 450 (15%) | 249 |
| `en_mix` — pha tiếng Anh | 300 (10%) | 172 |
| `emoji` — kèm emoji | 150 (5%) | 71 |
| **Tổng** | **3.000** | **1.941** |

Phân bố sau khử trùng lặp **lệch khỏi chỉ tiêu** (vd `polite_full` từ 25% xuống 20%, `emoji` từ 5%
xuống 3,7%) vì văn phong càng ít biến thể template thì càng nhiều câu bị loại.

**Hệ quả đã đo được:** dữ liệu template lệch phân phối so với câu người thật. Luật từ khoá chọn
trên tập train đạt 100% trên train nhưng chỉ 87% trên 200 câu test (thí nghiệm 2026-10-05).

---

## III. Khử trùng lặp gần giống

- **Thuật toán:** Jaccard trên tập character 3-gram, loại câu có J ≥ 0,88 với một câu đã giữ,
  trong cùng ý định.
- **Kết quả:** 3.000 → 1.941 câu, loại 1.059 (35,3%).
- **Cách đọc đúng con số này:** số câu độc nhất mà template sinh được ít hơn chỉ tiêu 3.000, nên
  script **chủ động chèn bản sao gần giống** (thêm " ạ", " nhé", " với"… hoặc khoảng trắng) cho đủ
  số lượng — xem `create_dataset_with_natural_duplicates`. Bước khử trùng lặp sau đó loại lại đúng
  những bản sao này. 35,3% là thước đo của pipeline, **không phải** số đo về dữ liệu tự nhiên, và
  không dùng được làm bằng chứng cho cảnh báo "~30% là bản sao" của kế hoạch.
- **Điều kiểm được:** thuật toán dedup chạy đúng, và tập 1.941 câu không còn cặp nào J ≥ 0,88
  trong cùng ý định.

---

## IV. Cohen's Kappa — quy trình đúng (chưa thực hiện)

Mục đích: đo xem hai người có hiểu taxonomy 7 ý định giống nhau không. Bất đồng nhãn ở tập test
biến thành sai số hệ thống của mọi chỉ số Macro-F1 về sau.

**Bước 1 — phiếu mù** (đã tạo, đã commit):

```powershell
python scripts/compute_annotation_kappa.py --make-sheets
```

`data/annotations/dev_a.csv` và `dev_b.csv` chỉ có `id` và `text`, cột `intent` để trống, **không
có nhãn vàng**. Thứ tự câu được xáo trộn khác nhau cho từng người — tập test gốc xếp theo nhãn
(28 câu đầu đều GREETING), giữ thứ tự là lộ nhãn qua vị trí.

**Bước 2 — gán nhãn độc lập** (~1 giờ mỗi người): mỗi người mở file của mình bằng Excel, điền một
trong 7 nhãn. Không xem file người kia, không xem `data/intent_test_human.jsonl`.

**Bước 3 — tính Kappa:**

```powershell
python scripts/compute_annotation_kappa.py
```

Script từ chối nếu còn dòng trống, nhãn ngoài 7 nhãn, id lặp hoặc thiếu câu — không bao giờ tự
điền nhãn. Báo cáo `reports/eval/annotation_kappa_report.json` gồm κ, p_o, p_e, ma trận nhầm lẫn
Dev A × Dev B, mức khớp của từng người với nhãn vàng hiện tại, và danh sách từng ca bất đồng.

**Bước 4 — họp thống nhất:** xem lại các ca bất đồng, ghi biên bản. Nhãn vàng là tập test đã
đóng băng — nếu buổi họp kết luận nhãn vàng sai, ghi nhận trong báo cáo chứ **không sửa**
`data/intent_test_human.jsonl`.

**Nếu không kịp làm trước ngày nộp:** ghi trong báo cáo "chưa đo đồng thuận gán nhãn" và nêu là
giới hạn của thực nghiệm. Không dùng con số κ cũ.

---

## V. Tái lập

```powershell
# Kiểm thử pipeline dữ liệu và phép tính Kappa (đối chiếu sklearn)
python -m pytest ai-service/tests/unit/test_router_data_pipeline.py -v

# Kiểm hash tập train và tập test
Get-FileHash data/intent_train_dedup.jsonl, data/intent_test_human.jsonl -Algorithm SHA256
```

Kỳ vọng hash khớp `artifacts/DATA_HASHES.txt`:

```text
data/intent_test_human.jsonl:8cc500dc96ebd15f18af01ca386b53a3b85941dba9c06ce12f46ffa24d0a1ecf
data/intent_train_dedup.jsonl:d8c2bfc45292629df653a5e1d719d27b0b35e78fb2fe1bccf3fe0c6a75b4562d
```

**Lưu ý:** đừng chạy lại `scripts/build_router_data_and_eval.py` khi không cần — nó sinh lại dữ
liệu train và ghi đè hash của `intent_train_dedup.jsonl` trong `DATA_HASHES.txt`.
