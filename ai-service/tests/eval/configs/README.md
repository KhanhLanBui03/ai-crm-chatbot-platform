# Cấu hình thí nghiệm — mỗi thí nghiệm một file `.yaml`

Kế hoạch phần 8. Mười một thí nghiệm, **mỗi thí nghiệm có baseline để so** — không có baseline
thì không có kết luận khoa học, chỉ có mô tả tính năng.

| Mã | Thí nghiệm | Baseline | Biến thể so sánh | Chỉ số |
|---|---|---|---|---|
| E1 | Chiến lược chia đoạn | Cố định 512 token | Đệ quy theo tiêu đề; có/không ghép đường dẫn mục | Recall@5, MRR |
| E2 | Mô hình nhúng | multilingual-e5-base | bge-m3; mô hình tiếng Việt chuyên biệt | Recall@5, độ trễ, kích thước chỉ mục |
| E3 | Chế độ truy hồi | Vector thuần | BM25 thuần; hybrid RRF | Recall@5, nDCG@10 |
| E4 | Xếp hạng lại | Không xếp hạng lại | bge-reranker-v2-m3 top-20→top-5 | nDCG@10, Precision@3, độ trễ tăng thêm |
| E5 | Độ chính xác định tuyến | Luật từ khóa | Bộ định tuyến bằng mô hình trong LangGraph | Accuracy, F1 theo lớp |
| E6 | Tỉ lệ bịa đặt | RAG ngây thơ | Bắt buộc trích dẫn + xác minh bám nguồn | Tỉ lệ bịa đặt, tỉ lệ bám nguồn |
| E7 | Hành vi từ chối | Không có ngưỡng | Ngưỡng điểm hiệu chỉnh | Precision/Recall của từ chối |
| E8 | Chấm điểm Lead | Bảng điểm theo luật | Trích xuất bằng mô hình + học máy | AUC-ROC, Precision@20 |
| E9 | Phòng thủ tiêm chỉ thị | Không phòng thủ | Bật lần lượt từng lớp | Attack Success Rate theo nhóm |
| E10 | Chi phí và độ trễ | Một mô hình cho mọi nhánh | Mô hình rẻ cho định tuyến + đệm ngữ nghĩa | Đồng/hội thoại, p50/p95 theo chặng |
| E11 | Phân nhóm chủ đề | Gán nhãn thủ công 100 hội thoại | K-Means, k chọn bằng Elbow | Silhouette, độ trùng khớp nhãn tay |

E10 là thí nghiệm chung của **cả hai làn**; còn lại thuộc Track B.

## Khung file — một file MỘT cấu hình

Harness `tests/eval/danh_gia_truy_hoi.py` nhận nhiều file; file ĐẦU TIÊN là baseline, các file sau
được so theo cặp với nó (paired bootstrap KTC 95%).

```yaml
id: e3-hybrid
mo_ta: "Hai làn, hợp nhất RRF k=60 — cấu hình ship"
bo_vang: ../golden_set.jsonl   # tương đối với file cấu hình
che_do: hybrid                 # dense | sparse | hybrid — cùng MỘT câu SQL, tắt một làn
tenant: eeeeeeee-0000-0000-0000-000000000001   # tenant gốc của gieo_kho.py
k: 5
ung_vien: 30                   # mỗi làn
ef_search: 100
quet_lap: relaxed_order        # "off" PHẢI trong ngoặc kép — YAML đọc off trần thành False
nhung:                         # danh tính ai-embed trả về; lệch thì harness dừng
  model: BAAI/bge-m3
  version: int8-71e2aa91
```

Hiện có: `e3_dense` · `e3_sparse` · `e3_hybrid` · `e3_hybrid_khong_quet_lap` (đối chứng ngược cho
phép so 1 ↔ 20 tenant).

## Ba con số phải có bằng mọi giá (mục 8.2)

1. **Truy hồi:** Recall@5 ≥ **0,85** (§1.6 — không phải 0,80) nhờ tìm kiếm lai và xếp hạng lại — mốc **M5, hạn 26/10**.
2. **Độ tin cậy:** tỉ lệ bịa đặt giảm rõ rệt nhờ ràng buộc trích dẫn + bước xác minh.
3. **Giá trị nghiệp vụ:** mô hình chấm điểm Lead vượt baseline luật theo AUC-ROC
   **trên dữ liệu thật của doanh nghiệp pilot**.
