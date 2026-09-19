# notebooks/ — R&D trên Kaggle

Nghiên cứu, fine-tune, export ONNX và lượng tử hoá. **Chạy trên Kaggle GPU T4**, không
chạy ở máy dev và không nằm trong image nào.

## Bốn điều kiện tái lập cho mọi notebook (§5.8)

1. Ghim seed cho mọi nguồn ngẫu nhiên (`random_state`, `torch.manual_seed`).
2. Ghim phiên bản thư viện, ghi vào Model Card.
3. Ghi `sha256` của cả dữ liệu vào lẫn artifact ra.
4. Ghép cặp `.ipynb` ↔ `.py` bằng **jupytext** — notebook không diff được thì không
   review được, và hội đồng không kiểm chứng được.

## Notebook dự kiến

| Notebook | Việc | UC | Chạy trên |
|---|---|---|---|
| `03_train_lead_scoring` | XGBoost + CalibratedClassifierCV → ONNX | UC030 | **CPU** — vài chục nghìn dòng, vài chục giây |
| `06_export_onnx` | Export encoder → ONNX → INT8 per-channel | UC019, UC023 | **CPU** — export và quantize là tác vụ CPU |
| Router 3 nhánh | TF-IDF / XLM-R / embedding+kNN | UC022 | GPU cho nhánh B |
| K-Means + PCA | Phân cụm chủ đề | UC038 | CPU |

Hai notebook đầu **không bật GPU** — bật GPU cho tác vụ CPU chỉ làm chậm hàng đợi Kaggle.

## Hai cổng chặn, không phải báo cáo

- **Parity encoder:** `cosine(fp32, int8) >= 0,995` trên 500 mẫu (§5.8).
- **Parity lead scorer:** lệch `< 1e-4` so với sklearn (§5.10.4).

Không đạt thì artifact **không được lên S3**. Lượng tử hoá INT8 khi hỏng thì hỏng âm
thầm — model vẫn trả vector đúng số chiều, chỉ là vector sai.

## Ranh giới trung thực phải ghi trong báo cáo

UC030 huấn luyện trên dữ liệu công khai hoặc tổng hợp. Đây là **model tham chiếu về
đường ống**, không phải model dự báo chuyển đổi cho một doanh nghiệp cụ thể. Nói rõ
điều này trong báo cáo (kế hoạch Ngày 29).
