# syntax=docker/dockerfile:1
#
# Image "ai-inference" — TẦNG SUY LUẬN (Master Plan §3.9.1).
# Một image, ba vai trò, chọn bằng MODEL_ROLE:
#     MODEL_ROLE=embed     → /v1/embed, /v1/embed/batch
#     MODEL_ROLE=rerank    → /v1/rerank
#     MODEL_ROLE=classify  → /v1/classify, /v1/lead-score
#
# Đây là image DUY NHẤT trong repo được phép có onnxruntime. Ngưỡng: < 900 MB.
#
# MỘT IMAGE DUY NHẤT cho suy luận: image chạy ở môi trường (C) Ephemeral Cloud CPU
# chính là image đẩy lên ECR cho (D) AWS EKS. Khác biệt duy nhất là biến môi trường
# và resources — nếu khác nữa thì benchmark Tuần 3 không dự báo được gì cho Tuần 7.

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt requirements/base.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements/base.txt

COPY src/ src/

RUN useradd -m app && chown -R app:app /app
USER app

EXPOSE 8080

# OMP_NUM_THREADS KHÔNG đặt mặc định ở đây — nó phải bằng đúng limits.cpu của từng
# vai trò, và cấp S/M/L khác nhau cho embed/rerank/classify (§5.4). Đặt sẵn một con
# số ở Dockerfile là ghim nhầm cho hai vai trò còn lại.
#
# Bất biến 3 ở §3.4.2 kiểm điều này lúc khởi động: OMP_NUM_THREADS phải khớp số vCPU
# được cấp, lệch thì /ready trả 503.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "src.entrypoint"]
