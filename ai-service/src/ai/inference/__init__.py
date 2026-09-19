"""Client gọi sang TẦNG SUY LUẬN — Master Plan §3.4.

Thư mục này **không nạp model**. Nó chỉ gọi HTTP sang ba service của image
``ai-inference``: ``ai-embed`` · ``ai-rerank`` · ``ai-classify``.

Đây là điểm cốt lõi của kiến trúc hai tầng v8.0: image ``ai-service`` không có
``onnxruntime``, ``torch``, ``xgboost``, ``scikit-learn`` hay ``transformers``.
Cổng chặn CI §3.2 kiểm điều này mỗi build:

    docker run --rm ai-service:ci pip list --format=freeze \\
        | grep -Eiq "^(onnxruntime|torch|xgboost|transformers|scikit-learn)" && exit 1

Ngưỡng phải giữ:
- Tổng p95 của ba service < **480 ms** (§1.6) — đo qua ``latency_breakdown``.
- p95 bước phân loại ý định ≤ **60 ms** (§5.3 dòng 2).
- Dung lượng image: ``ai-service`` < **400 MB** · ``ai-inference`` < **900 MB**.
"""
