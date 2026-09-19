"""``MODEL_ROLE=classify`` — router ý định (UC022) + lead scorer (UC030).

Endpoint: ``POST /v1/classify`` · ``POST /v1/lead-score`` · ``GET /ready`` · ``GET /v1/model``

Gom chung một service vì cả hai đều là model cấp S, cùng hồ sơ scale.

UC022 — ROUTER. Chạy 100% lượt chat
------------------------------------
Ngân sách p95 **60 ms** (§5.3 dòng 2). Ba nhánh đối chứng (§5.9), đánh giá trên
CÙNG tập test người thật đã đóng băng Ngày 7:

    A  TF-IDF word(1,2) + char_wb(2,5) + LinearSVC hiệu chuẩn
    B  fine-tune XLM-R base
    C  embedding từ ai-embed + k-NN/logistic

Chốt: macro-F1 >= **0,90** thì ship nhánh A; vùng 0,82-0,90 chọn nhánh có p95 thấp
nhất. Báo cáo phải đưa **cả ba** nhánh kèm khoảng tin cậy bootstrap và so sánh theo
cặp, không chỉ nhánh thắng.

Đường nhanh: ``confidence >= 0,85`` VÀ intent thuộc danh sách đi nhanh → trả mẫu câu,
KHÔNG gọi LLM. Chỉ số nghiệm thu: tỉ lệ lượt không gọi LLM >= **55%** (§1.6), tỉ lệ
đường nhanh >= **35%** ở Tuần 4.

UC030 — LEAD SCORER
-------------------
XGBoost bọc ``CalibratedClassifierCV`` → ONNX qua skl2onnx. Trả điểm 0-100, ba mức
tin cậy, ba mã lý do từ SHAP. p95 < **1.000 ms** (thực tế vài ms).

BẤT BIẾN 2 — thứ tự cột đặc trưng khớp ``lead_scorer.meta.json``, assert ở ``/ready``.
**Thứ tự cột là hợp đồng.** Convert sai thứ tự thì model vẫn chạy, vẫn trả điểm, và
điểm đó sai hoàn toàn — parity test là thứ bắt được.

Parity ONNX vs sklearn: lệch < **1e-4** (Ngày 30).

Image này có onnxruntime + tokenizers + numpy. KHÔNG có torch, KHÔNG có xgboost —
xgboost chỉ dùng lúc huấn luyện trên Kaggle (§5.10.5).
"""
