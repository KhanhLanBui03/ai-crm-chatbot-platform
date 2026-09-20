"""Client gọi sang TẦNG SUY LUẬN — Master Plan §3.4.

Thư mục này **không nạp model**. Nó chỉ gọi HTTP sang ba service của image
``ai-inference``: ``ai-embed`` · ``ai-rerank`` · ``ai-classify``.

Đây là điểm cốt lõi của kiến trúc hai tầng v8.0: image ``ai-service`` không có
``onnxruntime``, ``torch`` hay ``xgboost``. Cổng chặn CI §3.2 kiểm mỗi build, ĐÚNG BA GÓI
(ADR-0015 mục 4 — bản 5 gói của §3.2 mâu thuẫn với chính §4.6 và đã bị thay):

    docker run --rm ai-service:ci pip list --format=freeze \\
        | grep -Eiq "^(onnxruntime|torch|xgboost)" && exit 1

``scikit-learn`` CÓ trong image như phụ thuộc gián tiếp của ``pyvi`` và điều đó được chấp
nhận có chủ đích. Luật đi kèm: cấm ``import sklearn`` trong ``src/`` — suy luận thuộc về
``inference/``, huấn luyện thuộc về ``notebooks/``. CI kiểm luật này bằng grep riêng.

Ngưỡng phải giữ:
- Tổng p95 của ba service < **480 ms** (§1.6) — đo qua ``latency_breakdown``.
- p95 bước phân loại ý định ≤ **60 ms** (§5.3 dòng 2).
- Dung lượng image: ``ai-service`` < **400 MB** · ``ai-inference`` < **900 MB**.
"""
