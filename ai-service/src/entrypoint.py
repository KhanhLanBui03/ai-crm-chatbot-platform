"""Điểm vào duy nhất của image ``ai-service`` — chọn vai trò bằng biến ``RUN_MODE``.

Một image, hai vai trò (Master Plan §3.9.1):

    RUN_MODE=api     → FastAPI, nhận HTTP
    RUN_MODE=worker  → Kafka consumer

VÌ SAO ``workers=1`` — đây là ràng buộc kiến trúc, không phải tham số hiệu năng
--------------------------------------------------------------------------------
Master Plan §3.9.1 ghim đúng một tiến trình uvicorn. Ba lý do, không lý do nào
liên quan tới việc "chạy nhanh hơn":

1. **Scale bằng pod, không bằng tiến trình.** HPA ở §3.10.5 đếm pod. Mỗi pod có
   ``requests.cpu == limits.cpu`` để đạt QoS Guaranteed; nhân số tiến trình lên
   trong cùng một pod là phá vỡ phép tính đó và kéo theo CFS throttling.

2. **``OMP_NUM_THREADS`` là biến ở mức tiến trình.** Kỷ luật ghim luồng ở §5.4
   chỉ đúng khi mỗi container có đúng một tiến trình. Hai worker uvicorn trong
   một container thì mỗi cái tự nhận toàn bộ số luồng được cấp — tổng số luồng
   gấp đôi số vCPU, p95 xấu đi mà không có gì trong log chỉ ra nguyên nhân.

3. **Tài nguyên nền không nhân bản được.** ``lifespan`` khởi động consumer Kafka
   và đăng ký Eureka. Nhiều worker nghĩa là nhiều consumer trong cùng group và
   nhiều lần đăng ký cùng một ``instance_id`` — sai ở cả hai chỗ.

Suy ra: **không thêm ``--workers``, không dùng gunicorn ở đây.** Cần thêm năng lực
thì tăng ``replicas``, không tăng tiến trình.
"""

import os
import sys


def main() -> None:
    """Chọn vai trò theo ``RUN_MODE`` rồi chạy. Giá trị lạ thì thoát ngay, không đoán."""
    mode = os.getenv("RUN_MODE", "api")

    if mode == "api":
        import uvicorn

        uvicorn.run(
            "src.api.main:app",
            host="0.0.0.0",
            port=int(os.getenv("PORT", "8000")),
            workers=1,  # BẮT BUỘC — xem docstring đầu tệp (Master Plan §3.9.1)
        )

    elif mode == "worker":
        import asyncio

        from src.worker.main import run_worker

        asyncio.run(run_worker())

    else:
        raise SystemExit(
            f"RUN_MODE không hợp lệ: {mode!r}. Chỉ nhận 'api' hoặc 'worker' (§3.9.1)."
        )


if __name__ == "__main__":
    sys.exit(main())
