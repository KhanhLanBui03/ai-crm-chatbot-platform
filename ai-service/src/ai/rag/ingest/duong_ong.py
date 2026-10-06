"""Đường ống UC019: tệp → khối → chuẩn hoá → đoạn → vector. [PRODUCTION]

    tai_ve (S3)  →  phan_tich (tiến trình con)  →  normalize_vi  →  chia_doan  →  nhúng theo lô
     EXTRACTING      EXTRACTING                     CHUNKING         CHUNKING      EMBEDDING

Tách thành từng hàm theo CHẶNG của SCR033 để ``service.nap_tai_lieu`` ghi được chặng vào CSDL
giữa hai bước (ADR-0024). Chặng nhúng ở ``nhung.py``.

Module này KHÔNG chạm CSDL — trạng thái tài liệu do ``service.nap_tai_lieu`` quản, để đường ống
chạy lại được y hệt trong ``tests/eval/`` mà không cần Postgres.
"""

import asyncio
import tempfile
from dataclasses import replace
from pathlib import Path

from src.ai.exceptions import NoTextExtractedError
from src.ai.integrations import object_storage
from src.ai.rag.chuan_hoa import normalize_vi
from src.ai.rag.ingest.chia_doan import Doan, chia_doan
from src.ai.rag.ingest.phan_tich import Khoi
from src.ai.rag.ingest.tien_trinh import bo_phan_tich


def chuan_hoa_khoi(cac_khoi: list[Khoi]) -> list[Khoi]:
    """``normalize_vi`` cho từng khối — cùng hàm mà câu hỏi sẽ đi qua lúc truy vấn."""
    return [replace(k, text=normalize_vi(k.text)) for k in cac_khoi]


def chia_doan_tu_khoi(cac_khoi: list[Khoi], source_type: str, tran_token: int) -> list[Doan]:
    """Chặng CHUNKING: chuẩn hoá rồi chia đoạn. Ném ``PARSE_NO_TEXT_EXTRACTED`` nếu không còn gì."""
    cac_doan = chia_doan(chuan_hoa_khoi(cac_khoi), tran_token)
    if not cac_doan:
        # Có khối nhưng chuẩn hoá xong chỉ còn khoảng trắng / ký tự vô hình.
        raise NoTextExtractedError(f"Tệp {source_type} không còn nội dung sau khi chuẩn hoá")
    return cac_doan


async def trich_khoi_tu_s3(
    bucket: str, key: str, source_type: str, *, gioi_han_byte: int, timeout_s: float
) -> list[Khoi]:
    """Chặng EXTRACTING: tải object về tệp tạm rồi phân tích ở tiến trình con. Tệp tạm bị xoá khi
    xong.

    Tải qua ``object_storage.tai_ve`` (không gọi thư viện S3 trực tiếp): cùng giới hạn byte và
    cùng cách dịch lỗi với UC018 — object biến mất thành ``FILE_NOT_FOUND``, kho S3 chết thành
    ``STORAGE_UNAVAILABLE``.
    """
    with tempfile.TemporaryDirectory(prefix="kb-nap-") as thu_muc:
        tep = Path(thu_muc) / "tep"
        await asyncio.to_thread(object_storage.tai_ve, bucket, key, tep, gioi_han_byte)
        return await bo_phan_tich.phan_tich(tep, source_type, timeout_s)


async def trich_doan_tu_tep(
    tep: Path, source_type: str, *, timeout_s: float, tran_token: int
) -> list[Doan]:
    """Tệp cục bộ → danh sách ``Doan`` (EXTRACTING + CHUNKING liền một mạch) — cho ``tests/eval/``.
    Ném ``PARSE_*`` khi không lấy được nội dung."""
    cac_khoi = await bo_phan_tich.phan_tich(tep, source_type, timeout_s)
    return chia_doan_tu_khoi(cac_khoi, source_type, tran_token)
