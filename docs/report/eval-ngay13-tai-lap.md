# Tái lập — `n13_lan1` ↔ `n13_lan2`

## Top-k từng câu (truy hồi)

| Cấu hình | Số câu | Câu lệch top-k |
|---|---|---|
| `n13_e3-dense` | 100 | 0  |
| `n13_e3-hybrid` | 100 | 0  |
| `n13_e3-sparse` | 100 | 0  |

## Từng ô (`dung_sai` ≤ 0.03)

| Chỉ số | Cấu hình | Lượt A | Lượt B | Δ | Loại | Kết luận |
|---|---|---|---|---|---|---|
| recall@5 | e3-dense | 0.8000 | 0.8000 | +0.0000 | tuyet_doi | khớp |
| nDCG@5 | e3-dense | 0.6776 | 0.6776 | +0.0000 | tuyet_doi | khớp |
| MRR@5 | e3-dense | 0.6365 | 0.6365 | +0.0000 | tuyet_doi | khớp |
| p50 SQL truy hồi (ms) | e3-dense | 3.7 | 3.5 | -0.2000 | khong_xet | — |
| p95 SQL truy hồi (ms) | e3-dense | 5.1 | 6.5 | +1.4000 | khong_xet | — |
| recall@5 | e3-sparse | 0.5300 | 0.5300 | +0.0000 | tuyet_doi | khớp |
| nDCG@5 | e3-sparse | 0.4103 | 0.4103 | +0.0000 | tuyet_doi | khớp |
| MRR@5 | e3-sparse | 0.3707 | 0.3707 | +0.0000 | tuyet_doi | khớp |
| p50 SQL truy hồi (ms) | e3-sparse | 2.4 | 2.3 | -0.1000 | khong_xet | — |
| p95 SQL truy hồi (ms) | e3-sparse | 3.2 | 3.0 | -0.2000 | khong_xet | — |
| recall@5 | e3-hybrid | 0.7400 | 0.7400 | +0.0000 | tuyet_doi | khớp |
| nDCG@5 | e3-hybrid | 0.6306 | 0.6306 | +0.0000 | tuyet_doi | khớp |
| MRR@5 | e3-hybrid | 0.5935 | 0.5935 | +0.0000 | tuyet_doi | khớp |
| p50 SQL truy hồi (ms) | e3-hybrid | 4.0 | 4.3 | +0.3000 | khong_xet | — |
| p95 SQL truy hồi (ms) | e3-hybrid | 6.1 | 5.5 | -0.6000 | khong_xet | — |
| câu trượt top-5 | e3-hybrid | 26 | 26 | +0.0000 | tuyet_doi | khớp |
|   trong đó đoạn đúng ở hạng 6–30 | e3-hybrid | 23 | 23 | +0.0000 | tuyet_doi | khớp |
|   trong đó ngoài top-30 | e3-hybrid | 3 | 3 | +0.0000 | tuyet_doi | khớp |
|   trong đó e3-dense trúng top-5 | e3-hybrid | 10 | 10 | +0.0000 | tuyet_doi | khớp |
|   trong đó e3-sparse trúng top-5 | e3-hybrid | 2 | 2 | +0.0000 | tuyet_doi | khớp |
| p50 ai-embed, đo riêng (ms) |  | 25.8 | 22.4 | -3.4000 | khong_xet | — |
| p95 ai-embed (ms) |  | 55.1 | 43.1 | -12.0000 | khong_xet | — |
| độ phủ trích dẫn — theo câu |  | 0.7974 | 0.8049 | +0.0075 | dung_sai | trong ngưỡng |
| độ phủ trích dẫn — theo câu, bỏ câu “chưa có thông tin” |  | 0.8133 | 0.8137 | +0.0004 | dung_sai | trong ngưỡng |
| độ phủ trích dẫn — UC027 (lượt ≥ 1 trích dẫn) |  | 1.0000 | 1.0000 | +0.0000 | dung_sai | trong ngưỡng |
| độ phủ trích dẫn — Master Plan §5.12 (trích dẫn thô hợp lệ) |  | 1.0000 | 1.0000 | +0.0000 | dung_sai | trong ngưỡng |
| trích đúng căn cứ |  | 0.9481 | 0.9359 | -0.0122 | dung_sai | trong ngưỡng |
| groundedness trung bình |  | 0.7673 | 0.7832 | +0.0159 | dung_sai | trong ngưỡng |
| từ chối đúng — 12 câu bộ vàng |  | 1.0000 | 1.0000 | +0.0000 | dung_sai | trong ngưỡng |
| từ chối đúng — 38 câu mở rộng |  | 1.0000 | 1.0000 | +0.0000 | dung_sai | trong ngưỡng |
| từ chối đúng — gộp 50 câu |  | 1.0000 | 1.0000 | +0.0000 | dung_sai | trong ngưỡng |
| từ chối nhầm — câu có đáp án |  | 0.2300 | 0.2200 | -0.0100 | dung_sai | trong ngưỡng |
| 30 câu ngoài phạm vi — trả rỗng đúng |  | 1.0000 | 1.0000 | +0.0000 | dung_sai | trong ngưỡng |
| 30 câu ngoài phạm vi — đúng lý do |  | 1.0000 | 1.0000 | +0.0000 | dung_sai | trong ngưỡng |
| lý do NOT_COVERED |  | 85 | 84 | -1.0000 | khong_xet | — |
| lý do OUT_OF_SCOPE_DATA |  | 9 | 9 | +0.0000 | khong_xet | — |
| lý do SAFETY_PROBE |  | 9 | 9 | +0.0000 | khong_xet | — |
| lượt không gọi LLM (trên tập đo) |  | 0.1000 | 0.1000 | +0.0000 | dung_sai | trong ngưỡng |
| lượt suy giảm |  | 0 | 0 | +0.0000 | khong_xet | — |
| p50 tầng embed (ms) |  | 185.0 | 190.0 | +5.0000 | khong_xet | — |
| p95 tầng embed (ms) |  | 259.0 | 299.0 | +40.0000 | khong_xet | — |
| p50 tầng retrieve (ms) |  | 23.0 | 21.0 | -2.0000 | khong_xet | — |
| p95 tầng retrieve (ms) |  | 33.0 | 35.0 | +2.0000 | khong_xet | — |
| p50 tầng generate (ms) |  | 1158.0 | 1072.0 | -86.0000 | khong_xet | — |
| p95 tầng generate (ms) |  | 1531.0 | 1451.0 | -80.0000 | khong_xet | — |
| p50 tầng postguard (ms) |  | 1.0 | 1.0 | +0.0000 | khong_xet | — |
| p95 tầng postguard (ms) |  | 3.0 | 4.0 | +1.0000 | khong_xet | — |
| p50 tầng tổng lượt (ms) |  | 1343.0 | 1258.0 | -85.0000 | khong_xet | — |
| p95 tầng tổng lượt (ms) |  | 1743.0 | 1673.0 | -70.0000 | khong_xet | — |

## Câu đổi kết quả từ chối ↔ trả lời: 1 / 180

- `vang/G108`: NOT_COVERED → trả lời — máy lạnh inverter dòng nào tiết kiệm điện nhất

**TÁI LẬP ĐẠT**
