# Ôn tập Ngày 13 — Eval harness một lệnh, 38 câu nên-từ-chối, ba cổng §1.6 đo lần đầu

> Viết 10/10/2026 (lịch gốc 03/10). Số liệu:
> [`docs/report/eval-ngay13-2026-10-10.md`](../report/eval-ngay13-2026-10-10.md). Mã:
> [`tests/eval/chay_tat_ca.py`](../../ai-service/tests/eval/chay_tat_ca.py) · cấu hình
> [`configs/n13_nghiem_thu.yaml`](../../ai-service/tests/eval/configs/n13_nghiem_thu.yaml).
> Đây là nguyên liệu chính cho **buổi đọc số Ngày 16**.

## 1. Hôm nay hệ thống có thêm gì, nằm đâu

```
configs/n13_nghiem_thu.yaml ──► chay_tat_ca.py chay --nhan lan1
                                   │ 0. kiểm sha256 ba tập — lệch là DỪNG
   PHA ĐO (ghi thô)                │
   1. danh_gia_truy_hoi.chay ──────┼─► truy_hoi/n13_<cấu hình>.csv     (3 cấu hình E3 × 100 câu)
   2. tìm lại câu trượt top-30 ────┼─► truot.csv
   3. nhúng từng câu một ──────────┼─► do_tre_embed.csv
   4. RagAnswerer + Gemini thật ────┼─► tra_loi.jsonl                  (112 + 38 + 30 câu)
                                   └─► meta.json (commit, sha, model, ngưỡng ship)
   PHA TÍNH (thuần, không mạng)
   tinh_chi_so(thư mục) ──► chi_so.csv · tong_hop.md · truy_hoi.png · tu_choi.png · do_tre.png

chay_tat_ca.py tinh-lai lan1        ── chạy lại PHA TÍNH, so từng ô ⇒ phần tính tất định
chay_tat_ca.py tai-lap lan1 lan2    ── so hai lượt ĐO độc lập
```

## 2. Đi theo dữ liệu qua các file

| Bước | File | Ghi nhớ |
|---|---|---|
| Cấu hình một lượt | `configs/n13_nghiem_thu.yaml` | ba tập + sha256, ngưỡng §1.6, dung sai LLM khai TRƯỚC |
| Harness | `tests/eval/chay_tat_ca.py` | hai pha; `tinh_chi_so` không gọi mạng, không đọc đồng hồ |
| Số truy hồi | `tests/eval/danh_gia_truy_hoi.py` `chi_so_ranx` | `ranx` + lớp tương đương; công thức tự cài kiểm chéo |
| Lượt trả lời | `tests/eval/hieu_chinh_tu_choi.py` `dung_answerer` / `hoi_mot_cau` | đúng `RagAnswerer` production; thêm `llm_raw`, `cosine_top_k`, `latency_breakdown` |
| Độ phủ theo câu | `src/ai/rag/generate/hau_kiem.py` `dem_cau_co_trich_dan` | cùng cách tách câu với `do_bam_nguon` |
| §5.12 | `hau_kiem.dem_trich_dan_tho` | đếm TRƯỚC khi lọc trích dẫn |
| 38 câu mới | `tests/eval/tu_choi_mo_rong.jsonl` | sha `bf44948e…`, commit `6dc0b24` trước lần đo đầu |

## 3. Quyết định hôm nay và vì sao

1. **Hai pha: đo rồi mới tính.** Pha đo chỉ ghi thô; pha tính là hàm thuần trên các tệp đó. Nhờ vậy
   "tái lập" tách được làm hai câu hỏi khác nhau: *phần tính có tất định không* (`tinh-lai`, phải khớp
   từng chữ số) và *phép đo có lặp lại được không* (`tai-lap`, hai lượt độc lập).
2. **`ranx` + lớp tương đương.** Mỗi câu một tài liệu liên quan `DUNG` đặt ở hạng đoạn đúng đầu tiên.
   Đưa mọi đoạn khớp căn cứ vào qrels thì `ranx` tính IDCG trên nhiều tài liệu ⇒ nDCG khác định nghĩa
   Ngày 6, không so được với số cũ. Công thức tự cài giữ làm kiểm chéo — lệch là dừng.
3. **Ba loại ô tái lập**, khai trong cấu hình TRƯỚC khi chạy: `tuyet_doi` (truy hồi), `dung_sai` ±3 điểm %
   (chỉ số cần LLM), `khong_xet` (độ trễ).
4. **Độ phủ trích dẫn: cổng là định nghĩa THEO CÂU** (người dùng chốt trước khi đo), ba định nghĩa kia
   vẫn tính để thấy vì sao hai định nghĩa "chính thức" luôn ra 1,0.
5. **38 câu nên-từ-chối là tệp MỚI**, bộ vàng không đổi; khoá sha và commit trước lần đo đầu.
6. **Classify "chưa đo"** — không tự export `router_model.onnx` của Dev B (người dùng chốt).
7. **Recall trượt ⇒ báo số + phân tích lỗi, không sửa truy hồi trong ngày** (người dùng chốt).
8. **Sau khi xem số (người dùng chốt):** độ phủ giữ định nghĩa, báo "sát ngưỡng" (0,797 / 0,805);
   recall ghi nợ, đi tiếp Ngày 14, quay lại sau Ngày 15 khi rerank có số thật.

## 4. "Phải giải thích được" — hai câu của kế hoạch Ngày 13

**Vì sao giữ nguyên các cặp cũ thay vì trộn hết thành một bộ mới?**

- Một con số chỉ so được với con số khác khi **cùng mẫu số**. recall@5 0,740 của hôm nay so được với
  0,740 của 06/10 và 08/10 chính vì cùng 100 câu, cùng tệp, cùng sha `323baf73…`. Trộn câu mới vào là mọi
  so sánh "trước/sau" trong chương 5 (E3, hiệu chỉnh ngưỡng Ngày 10, eval cuối Ngày 20) mất ý nghĩa.
- Bộ vàng đã đóng băng thì **không ai sửa được nó cho vừa hệ thống** — kể cả vô tình. Câu mới đi vào
  tệp riêng với sha riêng, chỉ dùng cho phép đo mới.
- Còn một lý do về thiết kế thí nghiệm: 12 câu nên-từ-chối của bộ vàng đã được dùng để **CHỌN** ngưỡng ở
  Ngày 10. Dùng lại chúng để **NGHIỆM THU** là tự chấm bài của mình. 38 câu mới chưa từng chạm vào luật
  hay lời nhắc nào ⇒ 38/38 là con số độc lập; 12/12 thì không.
- Lý do gốc trong kế hoạch (so fine-tune ↔ pretrained trên cùng mẫu số) đã hết hiệu lực vì fine-tune bị
  bỏ (ADR-0026), nhưng nguyên tắc "cùng mẫu số" vẫn đứng.

**Ghim seed ở đâu và ghim cái gì để chạy hai lần ra cùng số?**

| Nguồn ngẫu nhiên | Ghim bằng gì | Ở đâu |
|---|---|---|
| thứ tự câu | thứ tự dòng trong tệp đã khoá sha | `cac_cau_tra_loi` |
| paired bootstrap | `SEED = 42` | `danh_gia_truy_hoi.py` |
| xáo ứng viên 38 câu | seed 42 | ghi trong báo cáo |
| vector câu hỏi | cùng model + cùng `int8-71e2aa91`; harness dừng nếu ai-embed trả danh tính khác | `_nhung_cau_hoi` |
| HNSW (xấp xỉ) | cùng chỉ mục + cùng `ef_search=100` + cùng `iterative_scan` | cấu hình E3 |
| Gemini | `temperature=0` — **KHÔNG đủ**: Gemini không nhận seed (ADR-0032) | ⇒ dung sai ±3 điểm % |

Kết quả: truy hồi 300/300 top-k trùng giữa hai lượt; phần tính 52/52 ô khớp ở cả hai lượt; phần LLM
13/13 ô trong dung sai, lệch lớn nhất 1,6 điểm (groundedness).

## 5. Câu phản biện kiểu hội đồng

- **"Recall@5 0,74 mà vẫn ship hybrid, sao không dùng dense 0,80?"** Dense cũng trượt 0,85; chênh 6 điểm
  có KTC [−13; +1] chứa 0 (ADR-0006). Hôm nay biết thêm *vì sao* hybrid thua: RRF dìm đoạn chỉ một làn
  thấy (G006: vector hạng 1 → hợp nhất hạng 10). Đổi cấu hình ship là quyết định của người dùng, chưa làm.
- **"Rerank có cứu được không?"** Có cơ sở để thử: 23/26 câu trượt đã nằm trong top-30. Nhưng ai-rerank còn
  giả Jaccard — chưa có số thật.
- **"Câu không dấu thì sao?"** 6/14 — điểm yếu lớn nhất. Làn vector gần như mù với tiếng Việt không dấu;
  làn từ khoá cứu được vì so qua `f_unaccent`.
- **"Lượt 2 đạt 0,805 sao không báo đạt?"** Vì lượt 1 — lượt độc lập đầu — ra 0,797. Hai lượt lệch 0,75
  điểm, trong dung sai, nhưng nằm hai phía ngưỡng: con số này nằm GIỮA độ dao động của Gemini. Chọn lượt
  đẹp hơn để báo là đúng kiểu "chọn số" mà luật tái lập sinh ra để ngăn.
- **"Độ phủ trích dẫn 1,0 theo UC027 mà sao báo 0,797?"** Ba định nghĩa, ba câu hỏi. UC027 và §5.12 ra 1,0
  là do THIẾT KẾ (luật "0 trích dẫn ⇒ từ chối", hậu kiểm lọc số sai), không phải do mô hình giỏi. Định
  nghĩa theo câu mới đo được điều gì đó — và 31/31 câu thiếu nguồn là câu xã giao/câu "chưa có thông tin".
- **"38/38 từ chối đúng — có phải tập dễ?"** Có ca khó cố ý: "bình nóng lạnh 30 lít" (kho có "bình nóng
  lạnh" của máy lọc nước), "máy lọc nước cho bể cá". Nhưng AI vừa viết câu vừa viết luật — khai ở báo cáo.
- **"p95 ba service < 480 ms đạt chưa?"** Chưa kết luận: 1/3 service. Và phát hiện: ai-embed sau ~4,5 s
  nghỉ chậm từ ~22 ms lên ~180 ms — không phải do kết nối HTTP (mở kết nối mới vẫn 18 ms).

## 6. Số đo và ý nghĩa

| Số | Ý nghĩa |
|---|---|
| recall@5 0,740 · nDCG@5 0,631 · MRR@5 0,594 (hybrid) | trượt cổng 0,85; không đổi từ Ngày 6 |
| 300/300 top-k trùng hai lượt | truy hồi tái lập tuyệt đối |
| 23/26 câu trượt nằm trong top-30 | trần cho một bước xếp hạng lại |
| `khong_dau` 6/14 | lớp lỗi lớn nhất |
| độ phủ theo câu 122/153 = 0,797 | trượt đúng 1 câu; 31 câu thiếu nguồn đều là câu xã giao/"chưa có" |
| từ chối đúng 50/50 · nhầm 23/100 (22 do truy hồi trượt) | logic từ chối đúng; nút thắt là recall |
| 30/30 trả rỗng, 30/30 đúng lý do | UC025 giữ được trên lượt độc lập mới |
| tổng lượt p50 1.343 · p95 1.743 ms | xa ngưỡng 4.000 ms (chưa có tải) |
| embed 185 ms trong lượt thật vs 26 ms liền nhau | ai-embed nguội — việc của Ngày 15 |
| lượt 2 (14:21): độ phủ 0,805 · nhầm 22/100 · 50/50 · 30/30 | 13/13 ô LLM trong ±3 điểm %; 1/180 câu đổi kết quả (G108) — tái lập ĐẠT |
| độ phủ 0,797 ↔ 0,805 | hai lượt hai phía ngưỡng — 0,80 nằm trong độ dao động của LLM, không viết "đạt" |

## 7. Phần AI làm — khai trung thực

- AI viết harness, test, cấu hình, 50 ứng viên + phán quyết chọn 38 câu, báo cáo và ghi chú này.
- Định nghĩa cổng độ phủ trích dẫn, số câu mở rộng, cách ghi sổ hash, cách chứng minh tái lập phần LLM,
  cách xử lý classify và recall trượt: **người dùng chốt** trước khi đo (10/10).
- Phân loại 31 câu thiếu nguồn là phân loại tay của AI để giải thích.

## 8. Ba câu tự kiểm

1. Vì sao `tinh-lai` khớp 52/52 vẫn chưa đủ để nói "chạy hai lần ra cùng số"? Nó chứng minh điều gì,
   không chứng minh điều gì?
2. Một câu có đoạn đúng ở hạng 1 của làn vector nhưng không có trong làn từ khoá. Tính điểm RRF của nó và
   của một đoạn đứng hạng 15 ở CẢ hai làn (k = 60). Đoạn nào lên trước?
3. Nếu bỏ câu ≥ 4 âm tiết dạng câu mời khỏi mẫu số, độ phủ lượt 1 thành bao nhiêu? Vì sao không được tự
   đổi định nghĩa như vậy sau khi đã thấy số 0,797?
