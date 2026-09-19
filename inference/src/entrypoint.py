"""Điểm vào của image ``ai-inference`` — chọn vai trò bằng ``MODEL_ROLE`` (§3.9.1).

Một image, ba vai trò:

    MODEL_ROLE=embed     → /v1/embed, /v1/embed/batch     UC019, UC023
    MODEL_ROLE=rerank    → /v1/rerank                     UC023
    MODEL_ROLE=classify  → /v1/classify, /v1/lead-score   UC022, UC030

VÌ SAO BA SERVICE CHỨ KHÔNG MỘT — §3.2.2
------------------------------------------
``OMP_NUM_THREADS`` là biến ở **mức tiến trình**. Một container không thể vừa cấp
8 luồng cho encoder cấp L vừa cấp 2 luồng cho router cấp S. Gộp chung là phá vỡ
toàn bộ kỷ luật ghim luồng §5.4 — và kỷ luật đó mới là thứ giữ tổng p95 < 480 ms.

Ba service cũng cho phép cập nhật model mà không deploy lại tầng orchestration.

BA BẤT BIẾN KIỂM Ở ``/ready`` — FAIL-CLOSED, §3.4.2
----------------------------------------------------
1. ``model_id`` khớp ``emb_model`` đã ghim trên chunk.
2. Thứ tự cột đặc trưng khớp ``lead_scorer.meta.json`` — thứ tự cột là HỢP ĐỒNG.
3. ``OMP_NUM_THREADS`` khớp số vCPU được cấp.

Lệch bất kỳ bất biến nào thì ``/ready`` trả 503 và **không nhận yêu cầu mới**. Chạy
tiếp với model sai còn tệ hơn dừng: nó trả về vector đúng số chiều nhưng sai nội
dung, và lỗi chỉ lộ ra ở Tuần 7 dưới dạng "recall tự nhiên tụt".

TODO: ``build_app(routes)`` + ba module trong ``roles/``.
TODO: ``_warn_if_thread_mismatch()`` — cảnh báo khi số luồng không khớp CPU được cấp.
"""

import os
import sys

ROUTES = ("embed", "rerank", "classify")


def main() -> None:
    """Đọc ``MODEL_ROLE``, dựng app tương ứng. Vai trò lạ thì thoát ngay."""
    role = os.getenv("MODEL_ROLE")
    if role not in ROUTES:
        raise SystemExit(
            f"MODEL_ROLE không hợp lệ: {role!r}. Chỉ nhận {' | '.join(ROUTES)} (§3.9.1)."
        )
    raise NotImplementedError("Tầng suy luận — kế hoạch 49 ngày, Ngày 5 và Ngày 8")


if __name__ == "__main__":
    sys.exit(main())
