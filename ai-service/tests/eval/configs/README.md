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

## Khung file

```yaml
id: E3
name: "Chế độ truy hồi"
dataset: ../golden_set.jsonl
repeats: 3            # mục 8.1 — một lần chạy duy nhất không đủ để kết luận
seed: 42
llm:
  temperature: 0      # bắt buộc, để tái lập
  model: claude-sonnet-5
metrics: [recall@5, ndcg@10]
baseline:
  retrieval: vector_only
variants:
  - { retrieval: bm25_only }
  - { retrieval: hybrid_rrf, rrf_k: 60 }
report:
  formats: [csv, html]
  out_dir: ../reports
```

## Ba con số phải có bằng mọi giá (mục 8.2)

1. **Truy hồi:** Recall@5 ≥ **0,80** nhờ tìm kiếm lai và xếp hạng lại — mốc **M5, hạn 26/10**.
2. **Độ tin cậy:** tỉ lệ bịa đặt giảm rõ rệt nhờ ràng buộc trích dẫn + bước xác minh.
3. **Giá trị nghiệp vụ:** mô hình chấm điểm Lead vượt baseline luật theo AUC-ROC
   **trên dữ liệu thật của doanh nghiệp pilot**.
