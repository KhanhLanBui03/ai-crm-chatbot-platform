"""Chặng EMBEDDING — ``src/ai/rag/ingest/nhung.py``. Cổng Ngày 5: lô 32, RSS không phình.

Tài liệu 3.000 đoạn phải chạy được mà bộ nhớ không phình theo số đoạn: đỉnh bộ nhớ đo bằng
``tracemalloc`` phải ở cỡ MỘT lô vector, không phải cỡ cả tài liệu.
"""

import tracemalloc

from src.ai.inference.clients import KetQuaNhung, MockEmbedClient
from src.ai.rag.ingest.chia_doan import Doan
from src.ai.rag.ingest.nhung import nhung_va_ghi_theo_lo

DIM = 1024


def _doan(n: int) -> list[Doan]:
    return [Doan(i, f"Đoạn số {i} nói về chính sách đổi trả.", None, None, 8) for i in range(n)]


class _EmbedGhiLai(MockEmbedClient):
    def __init__(self, nhat_ky: list[str]) -> None:
        super().__init__(DIM)
        self.nhat_ky = nhat_ky

    async def embed_batch(self, texts):
        self.nhat_ky.append(f"nhung:{len(texts)}")
        return await super().embed_batch(texts)


async def test_lo_32_va_ghi_xong_lo_nay_moi_nhung_lo_sau():
    nhat_ky: list[str] = []

    async def ghi_lo(lo, kq: KetQuaNhung):
        assert len(lo) == len(kq.vectors)
        nhat_ky.append(f"ghi:{lo[0].chunk_index}-{lo[-1].chunk_index}")

    so = await nhung_va_ghi_theo_lo(_doan(70), _EmbedGhiLai(nhat_ky), ghi_lo, co_lo=32)

    assert so == 70
    assert nhat_ky == [
        "nhung:32", "ghi:0-31",
        "nhung:32", "ghi:32-63",
        "nhung:6", "ghi:64-69",
    ]


async def test_3000_doan_dinh_bo_nho_co_mot_lo_khong_phai_ca_tai_lieu():
    """Một vector 1024 số ở Python ~32 KB ⇒ gom 3.000 vector ~100 MB, một lô 32 ~1 MB.

    Trần 10 MB rộng gấp ~10 lần một lô nhưng hẹp gấp ~10 lần gom cả tài liệu — kiểm ngược: đổi
    ``ghi_lo`` thành gom vào một list thì test này đỏ.
    """
    cac_doan = _doan(3000)
    da_ghi = 0

    async def ghi_lo(lo, kq):
        nonlocal da_ghi
        da_ghi += len(kq.vectors)

    tracemalloc.start()
    try:
        await nhung_va_ghi_theo_lo(cac_doan, MockEmbedClient(DIM), ghi_lo, co_lo=32)
        _, dinh = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert da_ghi == 3000
    assert dinh < 10 * 1024 * 1024, f"đỉnh bộ nhớ {dinh / 1e6:.1f} MB — vector đang bị gom lại"


async def test_kiem_nguoc_gom_het_vector_thi_vuot_tran():
    """Chứng minh trần 10 MB ở test trên có sức phân biệt: gom hết thì vượt."""
    gom: list = []

    async def ghi_lo(lo, kq):
        gom.extend(kq.vectors)

    tracemalloc.start()
    try:
        await nhung_va_ghi_theo_lo(_doan(3000), MockEmbedClient(DIM), ghi_lo, co_lo=32)
        _, dinh = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert dinh > 10 * 1024 * 1024
