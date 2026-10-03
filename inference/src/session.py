"""``make_session`` — ghim số luồng cho ONNX Runtime (Master Plan §5.4).

BẪY LỚN NHẤT KHI CHẠY ONNX TRÊN KUBERNETES
-------------------------------------------
ONNX Runtime đọc **số CPU của NODE**, không đọc ``limits.cpu`` của container. Trên
một node 16 vCPU, pod được cấp 2 vCPU vẫn tạo 16 luồng. Kết quả: 16 luồng tranh nhau
2 vCPU, context-switch liên tục, p95 xấu hơn hẳn so với chạy 2 luồng — và không có
gì trong log chỉ ra nguyên nhân.

Vì vậy **luôn đặt tường minh**, không bao giờ để mặc định::

    sess_options.intra_op_num_threads = <đúng limits.cpu>
    sess_options.inter_op_num_threads = 1

``inter_op = 1`` vì các model ở đây chạy tuần tự một đồ thị; song song ở mức
inter-op chỉ thêm chi phí điều phối mà không có nhánh nào để chạy song song.

CẤU HÌNH ĐỘNG THEO CẤP MODEL — §5.4, bảng bắt buộc áp dụng
-----------------------------------------------------------
    requests.cpu == limits.cpu      → QoS Guaranteed, tránh CFS throttling
    OMP_NUM_THREADS == limits.cpu   → bất biến 3 kiểm ở /ready

Fix cứng một con số là sai theo cả hai hướng: model nhỏ thì thừa luồng (overhead),
model lớn thì thiếu luồng (vượt ngân sách p95). Cấp S/M/L chốt ở Ngày 21 dựa trên
bảng benchmark ``bench_cpu.py``, không chốt bằng cảm tính.

Bằng chứng phải có trong báo cáo: chạy ``bench_cpu.py`` HAI LẦN trong pod
— một lần ghim đúng số luồng, một lần để mặc định — rồi đưa bảng chênh lệch p95 vào.
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import onnxruntime as ort

logger = logging.getLogger("inference.session")


def get_cgroup_cpus() -> float | None:
    """Đọc hạn mức CPU cấp cho container từ cgroup (v1 hoặc v2) thay vì đọc node CPU.

    Returns:
        Số vCPU (float) nếu đọc được, ngược lại trả về None.
    """
    # 1. Thử cgroup v2: /sys/fs/cgroup/cpu.max (chứa: "<quota> <period>")
    cgroup_v2 = Path("/sys/fs/cgroup/cpu.max")
    if cgroup_v2.exists():
        try:
            parts = cgroup_v2.read_text().strip().split()
            if len(parts) >= 2 and parts[0] != "max":
                quota = float(parts[0])
                period = float(parts[1])
                if period > 0:
                    return quota / period
        except Exception as exc:
            logger.debug("Không thể đọc cgroup v2 cpu.max: %s", exc)

    # 2. Thử cgroup v1: /sys/fs/cgroup/cpu/cpu.cfs_quota_us và cpu.cfs_period_us
    quota_file = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    period_file = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    if quota_file.exists() and period_file.exists():
        try:
            quota = float(quota_file.read_text().strip())
            period = float(period_file.read_text().strip())
            if quota > 0 and period > 0:
                return quota / period
        except Exception as exc:
            logger.debug("Không thể đọc cgroup v1 CFS quota: %s", exc)

    return None


def get_allocated_cpus() -> int:
    """Xác định số luồng CPU cần ghim cho tiến trình suy luận.

    Thứ tự ưu tiên:
    1. Biến môi trường OMP_NUM_THREADS (quy ước bất biến 3 §3.4.2).
    2. Hạn mức từ cgroup của container (requests/limits cpu).
    3. os.cpu_count() fallback cuối cùng.

    Returns:
        Số nguyên vCPU hợp lệ >= 1.
    """
    env_threads = os.getenv("OMP_NUM_THREADS")
    if env_threads and env_threads.isdigit():
        return max(1, int(env_threads))

    cgroup_cpus = get_cgroup_cpus()
    if cgroup_cpus is not None and cgroup_cpus > 0:
        return max(1, math.ceil(cgroup_cpus))

    return max(1, os.cpu_count() or 1)


def verify_thread_invariant() -> tuple[bool, str]:
    """Kiểm tra bất biến 3 (§3.4.2): OMP_NUM_THREADS phải khớp với CPU được cấp.

    Returns:
        (True, message) nếu khớp hoặc không có cảnh báo nghiêm trọng.
        (False, error_reason) nếu phát hiện sai lệch luồng.
    """
    env_threads = os.getenv("OMP_NUM_THREADS")
    cgroup_cpus = get_cgroup_cpus()

    if env_threads is None:
        return False, "Thiếu biến môi trường OMP_NUM_THREADS bắt buộc (§3.4.2 bất biến 3)"

    try:
        threads = int(env_threads)
    except ValueError:
        return False, f"OMP_NUM_THREADS={env_threads!r} không phải số nguyên hợp lệ"

    if cgroup_cpus is not None:
        expected = math.ceil(cgroup_cpus)
        if threads != expected:
            return False, (
                f"Lệch số luồng: OMP_NUM_THREADS={threads} nhưng container cgroup cấp {cgroup_cpus} CPU "
                f"(kỳ vọng {expected} luồng). Sẽ gây CFS throttling hoặc tranh chấp CPU."
            )

    return True, f"Số luồng CPU hợp lệ: {threads}"


def make_session(model_path: str | Path, num_threads: int | None = None) -> ort.InferenceSession:
    """Tạo InferenceSession của ONNX Runtime với kỷ luật ghim luồng tường minh.

    Quy tắc bắt buộc (Master Plan §5.4):
    - intra_op_num_threads: Ghim chặt bằng số vCPU container (OMP_NUM_THREADS).
    - inter_op_num_threads: Luôn bằng 1 (tránh overhead điều phối đồ thị tuần tự).
    - graph_optimization_level: ORT_ENABLE_ALL.
    - execution_mode: ORT_SEQUENTIAL.

    Args:
        model_path: Đường dẫn tới file model ONNX (.onnx).
        num_threads: Số luồng chỉ định (nếu None sẽ lấy từ get_allocated_cpus()).

    Returns:
        InferenceSession sẵn sàng suy luận trên CPU.
    """
    import onnxruntime as ort

    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy model ONNX tại đường dẫn: {path}")

    threads = num_threads if num_threads is not None else get_allocated_cpus()

    sess_options = ort.SessionOptions()
    sess_options.intra_op_num_threads = threads
    sess_options.inter_op_num_threads = 1
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

    logger.info(
        "Khởi tạo ONNX Session: model=%s, intra_op=%d, inter_op=1",
        path.name,
        threads,
    )

    return ort.InferenceSession(
        str(path),
        sess_options=sess_options,
        providers=["CPUExecutionProvider"],
    )
