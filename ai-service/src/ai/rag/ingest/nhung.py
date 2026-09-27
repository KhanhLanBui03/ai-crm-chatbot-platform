"""Chặng EMBEDDING của UC019: nhúng theo lô và ghi ngay từng lô. [PRODUCTION]

VÌ SAO GHI TỪNG LÔ, KHÔNG GOM HẾT RỒI GHI MỘT LẦN
-------------------------------------------------
Một vector bge-m3 là 1024 số; ở Python mỗi số là một object ``float`` 24 byte cộng 8 byte con trỏ
trong list — ~32 KB một đoạn. Tài liệu 3.000 đoạn gom hết là ~100 MB RAM chỉ cho vector, trên một
pod worker có giới hạn bộ nhớ: OOM-kill giữa chừng, và lượt thử lại gom lại đúng chừng đó rồi chết
đúng chỗ đó. Nhúng lô nào ghi lô đó thì đỉnh bộ nhớ là MỘT lô (~1 MB với lô 32), bất kể tài liệu
dài bao nhiêu — ``tests/unit/test_nhung_theo_lo.py`` đo điều này bằng ``tracemalloc``.

Mỗi lần ghi lô cũng là một NHỊP TIM của job (ADR-0021) — bộ quét không nhầm một tài liệu dài đang
nhúng với một tiến trình đã chết.

Module này không chạm CSDL: việc ghi do ``ghi_lo`` (nơi gọi truyền vào) làm.
"""

from collections.abc import Awaitable, Callable, Sequence

from src.ai.inference.clients import EmbedClient, KetQuaNhung
from src.ai.rag.ingest.chia_doan import Doan

GhiLo = Callable[[Sequence[Doan], KetQuaNhung], Awaitable[None]]


def van_ban_de_nhung(doan: Doan) -> str:
    """Văn bản gửi sang ``ai-embed`` cho một đoạn — MỘT chỗ duy nhất quyết định điều này.

    Hiện là ``content`` nguyên văn, khớp làn từ khoá (``content_segmented`` cũng chỉ tính từ
    ``content``). Ghép thêm đường dẫn heading vào đầu là một thí nghiệm cần đo recall@5 bằng
    ai-embed THẬT trên bộ vàng (Ngày 6–7), không quyết bằng cảm tính — đổi ở đây thì phải nhúng
    lại toàn kho.
    """
    return doan.content


async def nhung_va_ghi_theo_lo(
    cac_doan: Sequence[Doan], embed: EmbedClient, ghi_lo: GhiLo, *, co_lo: int
) -> int:
    """Nhúng ``cac_doan`` theo lô ``co_lo`` đoạn, ghi xong lô này mới nhúng lô sau. Trả số đoạn.

    Tuần tự có chủ đích: chạy song song lô k+1 trong lúc ghi lô k nhanh hơn một chút nhưng giữ hai
    lô vector cùng lúc, và ``ai-embed`` trên CPU vốn đã bão hoà với một lô (§5.4) — song song chỉ
    làm hai lô cùng chậm.
    """
    for dau in range(0, len(cac_doan), co_lo):
        lo = cac_doan[dau : dau + co_lo]
        ket_qua = await embed.embed_batch([van_ban_de_nhung(d) for d in lo])
        await ghi_lo(lo, ket_qua)
        # Không giữ tham chiếu nào tới ket_qua sau vòng này — vector của lô được giải phóng.
    return len(cac_doan)
