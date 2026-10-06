"""Điểm vào của image ``ai-inference`` — chọn vai trò bằng ``MODEL_ROLE`` (§3.9.1).

Một image, ba vai trò:

    MODEL_ROLE=embed     → /v1/embed, /v1/embed/batch     UC019, UC023
    MODEL_ROLE=rerank    → /v1/rerank                     UC023
    MODEL_ROLE=classify  → /v1/classify, /v1/lead-score   UC022, UC030

BA BẤT BIẾN KIỂM Ở ``/ready`` — FAIL-CLOSED, §3.4.2:
1. ``model_id`` khớp ``emb_model`` đã ghim trên chunk.
2. Thứ tự cột đặc trưng khớp ``lead_scorer.meta.json``.
3. ``OMP_NUM_THREADS`` khớp số vCPU được cấp.

Lệch bất kỳ bất biến nào thì ``/ready`` trả 503 và không nhận yêu cầu mới.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse

# Cấu hình logging JSON / chuẩn hóa
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("inference.entrypoint")

VALID_ROLES = ("embed", "rerank", "classify")


def get_current_role() -> str:
    role = os.getenv("MODEL_ROLE")
    if not role or role not in VALID_ROLES:
        logger.error("MODEL_ROLE không hợp lệ hoặc chưa đặt: %r. Phải là một trong: %s", role, " | ".join(VALID_ROLES))
        raise SystemExit(f"MODEL_ROLE không hợp lệ: {role!r}. Chỉ nhận {' | '.join(VALID_ROLES)} (§3.9.1).")
    return role


def create_app() -> FastAPI:
    """Khởi tạo ứng dụng FastAPI theo vai trò MODEL_ROLE."""
    role = get_current_role()
    app = FastAPI(
        title=f"ai-inference [{role}]",
        version="1.0.0",
        description=f"Tầng suy luận ML CPU tách biệt cho vai trò {role.upper()} theo Master Plan v8.0",
    )

    # Nạp module vai trò
    if role == "embed":
        from src.roles import embed
        app.include_router(embed.router)
        role_checker = embed.check_invariants
    elif role == "rerank":
        from src.roles import rerank
        app.include_router(rerank.router)
        role_checker = rerank.check_invariants
    elif role == "classify":
        from src.roles import classify
        app.include_router(classify.router)
        role_checker = classify.check_invariants
    else:
        raise ValueError(f"Vai trò không xác định: {role}")

    # Liveness probe
    @app.get("/health", tags=["probe"])
    async def health() -> dict[str, str]:
        return {"status": "UP", "role": role}

    # Readiness probe: Kiểm tra 3 BẤT BIẾN theo triết lý FAIL-CLOSED (§3.4.2)
    @app.get("/ready", tags=["probe"])
    async def ready() -> Response:
        from src import session

        violations: list[str] = []

        # Bất biến 1 & 2: Kiểm tra theo vai trò (model_id & feature column order)
        role_ok, role_msg = role_checker()
        if not role_ok:
            violations.append(role_msg)

        # Bất biến 3: Số luồng OMP_NUM_THREADS khớp số vCPU
        thread_ok, thread_msg = session.verify_thread_invariant()
        if not thread_ok:
            violations.append(thread_msg)

        # Cố tình nạp cờ ép lỗi fail-closed để test (dùng cho QA test kịch bản)
        if os.getenv("FORCE_READY_FAIL", "").lower() in ("true", "1"):
            violations.append("Cố tình kích hoạt lỗi qua biến môi trường FORCE_READY_FAIL=true")

        if violations:
            logger.warning("FAIL-CLOSED /ready trả về 503. Phát hiện %d vi phạm bất biến: %s", len(violations), violations)
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "ready": False,
                    "code": "INVARIANT_VIOLATION",
                    "role": role,
                    "violations": violations,
                },
            )

        allocated_threads = session.get_allocated_cpus()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "ready": True,
                "role": role,
                "threads": allocated_threads,
                "status": "READY",
            },
        )

    # Prometheus metrics probe
    @app.get("/metrics", tags=["probe"])
    async def metrics() -> Response:
        try:
            from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
        except ImportError:
            return Response(content="# prometheus_client not available\n", media_type="text/plain")

    logger.info("Dựng thành công app ai-inference cho vai trò MODEL_ROLE=%s", role)
    return app


app = create_app()


def main() -> None:
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info("Khởi động máy chủ uvicorn trên cổng %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
