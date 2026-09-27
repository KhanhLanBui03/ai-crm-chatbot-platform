"""Sáu bước tiến độ nạp — SCR033, UC019. [PRODUCTION]

    QUEUED → EXTRACTING → CHUNKING → EMBEDDING → INDEXING → DONE

Tên bước lấy nguyên văn từ enum ``TrangThaiCongViecNap`` của ``docs/openapi/dashboard-api.yaml``
(bỏ ``FAILED``/``PAUSED`` — đó là KẾT CỤC, không phải bước). ``PAUSED`` (vượt hạn mức token giữa
chừng) chưa có nguồn: luồng nạp hiện không tiêu token tính tiền nào.

Hai bước đầu-cuối suy ra từ ``status``, bốn bước giữa đọc từ ``ingest_step`` (V211):

    status      ingest_step     bước hiện tại
    PENDING     NULL            QUEUED
    PROCESSING  EXTRACTING…     chính nó
    READY       NULL            DONE
    FAILED      bước đã hỏng    bước đó (FAILED), các bước sau SKIPPED
"""

from typing import Literal

CAC_BUOC: tuple[str, ...] = ("QUEUED", "EXTRACTING", "CHUNKING", "EMBEDDING", "INDEXING", "DONE")

TrangThaiBuoc = Literal["DONE", "RUNNING", "PENDING", "FAILED", "SKIPPED"]


def buoc_hien_tai(status: str, ingest_step: str | None) -> str:
    """Giá trị ``state`` của SCR033: một trong sáu bước, hoặc ``FAILED``."""
    if status == "FAILED":
        return "FAILED"
    if status in ("READY", "ARCHIVED"):
        return "DONE"
    if status == "PROCESSING":
        # PROCESSING mà chưa có ingest_step: dòng nhận xử lý trước V211 (Ngày 4). Đang ở bước
        # đầu tiên sau hàng đợi là cách đọc duy nhất không bịa thêm tiến độ.
        return ingest_step or "EXTRACTING"
    return "QUEUED"


def dung_cac_buoc(status: str, ingest_step: str | None) -> list[tuple[str, TrangThaiBuoc]]:
    """Trạng thái của từng bước trong sáu bước, theo thứ tự."""
    if status in ("READY", "ARCHIVED"):
        return [(b, "DONE") for b in CAC_BUOC]

    if status == "FAILED":
        # Bước hỏng không rõ (dòng FAILED trước V211) thì không tô bước nào đỏ — không đoán.
        if ingest_step not in CAC_BUOC:
            return [(b, "SKIPPED") for b in CAC_BUOC]
        hong = CAC_BUOC.index(ingest_step)
        return [
            (b, "DONE" if i < hong else "FAILED" if i == hong else "SKIPPED")
            for i, b in enumerate(CAC_BUOC)
        ]

    dang = CAC_BUOC.index(buoc_hien_tai(status, ingest_step))
    return [
        (b, "DONE" if i < dang else "RUNNING" if i == dang else "PENDING")
        for i, b in enumerate(CAC_BUOC)
    ]
