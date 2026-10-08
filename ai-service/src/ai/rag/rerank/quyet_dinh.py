"""[PRODUCTION] Khi nào xếp hạng lại — ``needs_rerank`` / ``AMBIGUITY_GAP``. Kế hoạch Ngày 8.

Rerank cross-encoder là chặng đắt nhất của đường ống (rag-eval.md). Gọi nó cho MỌI câu là trả
giá độ trễ cả ở những câu truy hồi đã chắc chắn. Nên chỉ gọi khi top đầu MƠ HỒ:

    mơ hồ  ⇔  cosine(hạng 1) − cosine(hạng 3) < AMBIGUITY_GAP

VÌ SAO SO HẠNG 1 VỚI HẠNG 3, KHÔNG PHẢI HẠNG 2
--------------------------------------------
Tài liệu doanh nghiệp hay có hai đoạn gần trùng nhau (cùng chính sách ở hai phiên bản, bảng giá
và trang khuyến mãi nhắc cùng sản phẩm). Hạng 1 sát hạng 2 là chuyện thường và cả hai thường cùng
đúng — so với hạng 2 thì gần như câu nào cũng "mơ hồ". Hạng 3 vẫn sát hạng 1 mới là dấu hiệu cả
cụm đầu không phân định được, đúng chỗ cross-encoder đáng tiền.

VÌ SAO COSINE, KHÔNG PHẢI ĐIỂM RRF
--------------------------------
Kế hoạch ghi "chênh điểm RRF < 0,15", nhưng điểm RRF với k = 60 chỉ nằm trong ~0,016–0,033 — chênh
giữa hai hạng bất kỳ luôn dưới 0,02, nên điều kiện đó đúng với 100% câu và cổng mất ý nghĩa.
Cosine là thang tuyệt đối duy nhất ``hybrid.py`` trả về. 0,15 giữ nguyên làm điểm xuất phát;
hiệu chỉnh ở Khối 2 (rerank thật) cho tỉ lệ mơ hồ về vùng kỳ vọng 30–40%.

Ứng viên đưa vào cross-encoder: **12, không phải 30** — chi phí cross-encoder tuyến tính theo số
cặp, và đoạn đúng nằm ngoài top-12 của RRF thì gần như không bao giờ được rerank kéo về top-5.
"""

from collections.abc import Sequence

from src.ai.inference.clients import RerankClient
from src.ai.rag.retrieve.hybrid import DoanTimDuoc

AMBIGUITY_GAP = 0.15
SO_UNG_VIEN_RERANK = 12


def needs_rerank(cac_doan: Sequence[DoanTimDuoc], gap: float = AMBIGUITY_GAP) -> bool:
    if len(cac_doan) < 3:
        return False
    dau, ba = cac_doan[0].do_tuong_dong, cac_doan[2].do_tuong_dong
    if dau is None or ba is None:
        return False
    return dau - ba < gap


async def xep_lai(
    client: RerankClient, cau_hoi: str, cac_doan: Sequence[DoanTimDuoc]
) -> list[DoanTimDuoc]:
    """Xếp lại tối đa ``SO_UNG_VIEN_RERANK`` đoạn theo điểm cross-encoder.

    Chỉ gửi ``chunk_id`` + nội dung — không ``tenant_id`` (``_assert_no_pii_keys`` chặn ở tầng gửi).
    Đoạn mà ai-rerank không trả điểm thì xuống cuối, giữ thứ tự RRF giữa chúng.
    """
    ung_vien = list(cac_doan[:SO_UNG_VIEN_RERANK])
    ket_qua = await client.rerank(
        cau_hoi, [{"chunk_id": str(d.chunk_id), "text": d.content} for d in ung_vien]
    )
    diem = {str(r["chunk_id"]): float(r["score"]) for r in ket_qua}

    def khoa(i: int) -> tuple[bool, float, int]:
        ma = str(ung_vien[i].chunk_id)
        return (ma not in diem, -diem.get(ma, 0.0), i)

    return [ung_vien[i] for i in sorted(range(len(ung_vien)), key=khoa)]
