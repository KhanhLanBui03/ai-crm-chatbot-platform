"""Ba backend hoán đổi được cho tầng suy luận — Master Plan §3.4.1.

Chọn bằng biến môi trường ``AI_MODE``:

    remote   gọi sang tầng suy luận. MẶC ĐỊNH ở mọi môi trường vận hành.
    mock     trả dữ liệu giả có seed cố định. Dùng cho CI và khi Frontend/Backend
             cần một bản giả lập ổn định để làm song song.
    offline  nạp model nhẹ ngay trong tiến trình. CHỈ dùng khi lập trình viên không
             có mạng. KHÔNG BAO GIỜ bật ở môi trường (D) AWS EKS.

Cùng một interface ở cả ba chế độ — đó là điều làm cho số đo ở môi trường (C)
chuyển được sang (D) mà không phải sửa lời gọi.

BA BẤT BIẾN KIỂM Ở ``/ready``, FAIL-CLOSED NẾU LỆCH — §3.4.2
-------------------------------------------------------------
1. ``model_id`` đang phục vụ phải khớp ``emb_model`` đã ghim trên từng chunk.
   Lệch nghĩa là vector câu hỏi và vector chỉ mục thuộc hai không gian khác nhau —
   truy hồi vẫn chạy, vẫn trả kết quả, nhưng kết quả vô nghĩa. Đây là kiểu hỏng
   im lặng nguy hiểm nhất của RAG (mã lỗi ``EMBEDDING_MODEL_MISMATCH``).
2. Thứ tự cột đặc trưng phải khớp ``lead_scorer.meta.json``. **Thứ tự cột là hợp
   đồng**, không phải chi tiết hiện thực (§5.10.4).
3. ``OMP_NUM_THREADS`` phải khớp số vCPU được cấp (§5.4).

[CẦN XÁC NHẬN] Payload gửi sang tầng suy luận **không được chứa** ``tenant_id``,
``contact_id`` hay bất kỳ định danh nào — kế hoạch Ngày 41 yêu cầu assert điều này
trên body request trong CI (§4.10, §3.6.3).

HIỆN CÓ (Ngày 5): ``EmbedClient`` với hai hiện thực ``mock`` (tệp này) và ``remote``
(``remote.py``). ``offline`` KHÔNG hiện thực ở ai-service: nạp model trong tiến trình cần
``onnxruntime``, mà cổng chặn CI cấm gói đó ở image này — ``offline`` thuộc về ``inference/``.
TODO: ``RerankClient`` (Ngày 8) · ``ClassifyClient`` (Ngày 6/9) theo cùng khuôn.
"""

import hashlib
import math
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from src.ai.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class KetQuaNhung:
    """Kết quả một lô: vector theo ĐÚNG thứ tự văn bản gửi đi, kèm danh tính model đã sinh ra chúng.

    ``model_id`` + ``model_version`` đi thẳng vào ``knowledge_chunks.embedding_model`` /
    ``embedding_version`` của từng dòng (V203) — lấy từ phía ĐÃ SINH vector, không lấy từ cấu hình
    của phía gọi, để cột đó luôn nói thật.
    """

    model_id: str
    model_version: str
    vectors: list[list[float]]


class EmbedClient(Protocol):
    """Giao diện chung của ba backend. Phía gọi không biết mình đang nói với backend nào."""

    async def embed_batch(self, texts: Sequence[str]) -> KetQuaNhung:
        """Nhúng một lô. Ném ``EmbeddingUnavailableError`` (tạm thời) hoặc
        ``EmbeddingRejectedError`` / ``EmbeddingModelMismatchError`` (vĩnh viễn)."""
        ...

    async def aclose(self) -> None:
        """Trả tài nguyên (kết nối HTTP). Gọi một lần lúc tắt."""
        ...


class MockEmbedClient:
    """Vector giả, SEED CỐ ĐỊNH theo nội dung: cùng văn bản → cùng vector, ở mọi tiến trình, mọi
    máy.

    Sinh bằng ``shake_256`` của văn bản chứ không bằng ``random`` + ``hash()``: ``hash()`` của
    chuỗi bị ngẫu nhiên hoá theo từng tiến trình (``PYTHONHASHSEED``), hai lần chạy CI sẽ cho hai
    bộ vector khác nhau và test so vector sẽ chập chờn.

    Vector đã chuẩn hoá L2 — cùng tính chất với bge-m3 thật, để truy vấn cosine của Ngày 6 chạy
    được trên dữ liệu giả mà không đổi câu SQL.

    ⚠️ ``model_id`` là ``mock-hash-1024``, KHÔNG giả danh ``BAAI/bge-m3``. Đoạn nạp bằng mock vì
    thế mang nhãn riêng trên từng dòng: đổi sang ai-embed thật thì truy hồi (lọc theo
    ``embedding_model``) không trộn hai không gian vector, và biết chính xác dòng nào phải nhúng
    lại.
    Vector giả KHÔNG mang nghĩa — mọi số đo recall trên chúng là vô nghĩa.
    """

    MODEL_ID = "mock-hash-1024"
    MODEL_VERSION = "shake256-v1"

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        so_nguyen = struct.unpack(
            f"<{self.dim}h", hashlib.shake_256(text.encode("utf-8")).digest(self.dim * 2)
        )
        do_dai = math.sqrt(sum(x * x for x in so_nguyen)) or 1.0
        return [x / do_dai for x in so_nguyen]

    async def embed_batch(self, texts: Sequence[str]) -> KetQuaNhung:
        return KetQuaNhung(self.MODEL_ID, self.MODEL_VERSION, [self._vector(t) for t in texts])

    async def aclose(self) -> None:
        return None


def tao_embed_client(settings: Settings | None = None) -> EmbedClient:
    """Chọn backend theo ``AI_MODE``. Giá trị không hỗ trợ thì ném ngay lúc khởi động."""
    settings = settings or get_settings()
    if settings.ai_mode == "mock":
        return MockEmbedClient(settings.embedding_dim)
    if settings.ai_mode == "remote":
        from src.ai.inference.remote import RemoteEmbedClient

        return RemoteEmbedClient(
            settings.embed_url,
            model_id=settings.embedding_model,
            dim=settings.embedding_dim,
            timeout_s=settings.embed_timeout_s,
        )
    raise ValueError(
        f"AI_MODE={settings.ai_mode!r} không chạy được ở ai-service: nạp model trong tiến trình "
        "cần onnxruntime, mà cổng chặn CI cấm gói đó ở image này (§3.2). Dùng remote hoặc mock."
    )
