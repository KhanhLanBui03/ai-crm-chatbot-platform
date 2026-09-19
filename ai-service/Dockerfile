# syntax=docker/dockerfile:1
#
# Image "ai-service" — TẦNG ORCHESTRATION, KHÔNG có ML runtime (Master Plan §3.9.1).
# Một image, hai vai trò, chọn bằng RUN_MODE:
#     RUN_MODE=api     → FastAPI          (mặc định)
#     RUN_MODE=worker  → Kafka consumer
#
# Ngưỡng: < 400 MB, pod sẵn sàng 2–5 giây (§3.2.3).
# Cổng chặn CI §3.2 kiểm image này KHÔNG có onnxruntime/torch/xgboost/scikit-learn.

FROM python:3.11-slim

# WORKDIR là /app nhưng mã nguồn nằm ở /app/src — nhờ vậy "src.api.main:app" trong
# src/entrypoint.py (§3.9.1) import đúng. Đừng đổi thành /app/src: làm thế thì `src`
# không còn là package và entrypoint gãy.
WORKDIR /app

# curl cho healthcheck. KHÔNG cài build-essential: base.txt thuần orchestration,
# mọi gói đều có wheel dựng sẵn — thêm toolchain là cộng ~200 MB vô ích.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Chỉ base.txt. dev.txt (pytest, ruff, testcontainers) KHÔNG vào image production.
COPY requirements/base.txt requirements/base.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements/base.txt

COPY src/ src/

RUN useradd -m app && chown -R app:app /app
USER app

EXPOSE 8000
ENV RUN_MODE=api \
    PORT=8000 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Gọi qua entrypoint.py chứ không gọi thẳng uvicorn: workers=1 và việc chọn vai trò
# đều được ghim trong đó (§3.9.1).
CMD ["python", "-m", "src.entrypoint"]
