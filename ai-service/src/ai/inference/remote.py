"""Backend ``remote`` + circuit breaker — Master Plan §3.8.

MA TRẬN SUY GIẢM — §3.8.1, kiểm đủ ba trường hợp ở Ngày 34
------------------------------------------------------------
Nguyên tắc: tầng suy luận chết thì **suy giảm**, không trả 5xx cho người dùng.

    ai-embed chết    → chuyển sang truy hồi CHỈ TỪ KHOÁ (sparse-only),
                       đánh cờ degraded=true. Vẫn trả lời được.
    ai-rerank chết   → bỏ bước rerank, vẫn trả lời bằng thứ hạng RRF.
    ai-classify chết → /ready trả 503, KHÔNG nhận yêu cầu mới.

``ai-classify`` là ngoại lệ vì nó chạy 100% lượt chat và là cửa vào của guardrails
— không có nó thì không còn lớp kiểm duyệt nào, nên fail-closed là đúng.

CIRCUIT BREAKER — ba trạng thái, cho cả ba client suy luận lẫn LLM API
----------------------------------------------------------------------
    closed → open → half-open → closed

    Retry:     429 · 5xx · timeout
    KHÔNG retry: 400 · 401 · 422   (hỏng ở phía mình, thử lại cũng hỏng)

Chuỗi timeout phải TĂNG DẦN từ trong ra ngoài (§3.10.2): client suy luận < tổng
ngân sách của ai-service < idle_timeout của ALB (120 s). Đặt ngược thì ALB cắt
kết nối trước khi ứng dụng kịp trả lỗi tử tế, và log không cho biết gì.

HIỆN CÓ (Ngày 5): ``RemoteEmbedClient`` — KHÔNG có circuit breaker, KHÔNG tự thử lại. Việc thử
lại của luồng nạp tài liệu nằm ở tầng job (``attempt_count``, ADR-0024): thử lại ở đây nữa là
nhân số lần thử lên, và một lô 32 đoạn treo 60 s × 3 lần ở client × 3 lượt job là 9 phút giữ
worker. Đường chat (Ngày 9) mới cần breaker — nó có ngân sách độ trễ, luồng nạp thì không.
TODO: ``CircuitBreaker`` ba trạng thái + đếm lỗi theo cửa sổ trượt.
TODO: ghi ``degraded=true`` vào telemetry mỗi lần suy giảm (UC039).

HỢP ĐỒNG ``POST /v1/embed/batch`` — [CẦN XÁC NHẬN] với Dev B (``inference/src/roles/embed.py``
còn là TODO, hai bên chưa khớp hình dạng)::

    → {"texts": ["…", …]}                                ≤ 32 phần tử
    ← {"model_id": "BAAI/bge-m3", "model_version": "int8-71e2aa91",
       "dim": 1024, "embeddings": [[…1024 số…], …]}      cùng thứ tự với texts

Thân yêu cầu CHỈ có văn bản — không ``tenant_id``, không ``document_id``, không định danh nào
(§3.6.3). Tầng suy luận không cần biết văn bản của ai; test
``test_than_yeu_cau_khong_mang_dinh_danh`` khoá điều này.
"""

from collections.abc import Sequence

import httpx

from src.ai.exceptions import (
    EmbeddingModelMismatchError,
    EmbeddingRejectedError,
    EmbeddingUnavailableError,
)
from src.ai.inference.clients import KetQuaNhung


class RemoteEmbedClient:
    """Gọi ``ai-embed`` qua HTTP. Phân loại lỗi theo "thử lại có ích không".

    Tạm thời (``EmbeddingUnavailableError``): mất kết nối, hết thời gian chờ, 429, 5xx.
    Vĩnh viễn: 400/401/403/404/422 (``EmbeddingRejectedError`` — hỏng ở phía mình), kết quả sai
    hình dạng, và ``model_id`` khác model đã ghim (``EmbeddingModelMismatchError`` — bất biến 1).
    """

    def __init__(
        self,
        base_url: str,
        *,
        model_id: str,
        dim: int,
        timeout_s: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model_id = model_id
        self.dim = dim
        # transport chỉ để test tiêm httpx.MockTransport; đường production để trống.
        self._http = httpx.AsyncClient(base_url=base_url, timeout=timeout_s, transport=transport)

    async def embed_batch(self, texts: Sequence[str]) -> KetQuaNhung:
        try:
            phan_hoi = await self._http.post("/v1/embed/batch", json={"texts": list(texts)})
        except httpx.TimeoutException as e:
            raise EmbeddingUnavailableError(f"ai-embed hết thời gian chờ: {e}") from e
        except httpx.TransportError as e:
            raise EmbeddingUnavailableError(f"Không kết nối được ai-embed: {e}") from e

        if phan_hoi.status_code == 429 or phan_hoi.status_code >= 500:
            raise EmbeddingUnavailableError(f"ai-embed trả {phan_hoi.status_code}")
        if phan_hoi.status_code != 200:
            raise EmbeddingRejectedError(
                f"ai-embed từ chối lô {len(texts)} đoạn: {phan_hoi.status_code}"
            )

        try:
            du_lieu = phan_hoi.json()
            model_id = str(du_lieu["model_id"])
            model_version = str(du_lieu.get("model_version") or "unknown")
            vectors = [[float(x) for x in v] for v in du_lieu["embeddings"]]
        except (ValueError, KeyError, TypeError) as e:
            raise EmbeddingRejectedError(f"Phản hồi ai-embed sai hình dạng: {e}") from e

        if model_id != self.model_id:
            raise EmbeddingModelMismatchError(
                f"ai-embed đang phục vụ {model_id!r}, kho đã ghim {self.model_id!r}"
            )
        if len(vectors) != len(texts):
            raise EmbeddingRejectedError(
                f"Gửi {len(texts)} đoạn, nhận {len(vectors)} vector"
            )
        if any(len(v) != self.dim for v in vectors):
            raise EmbeddingRejectedError(f"Vector không đủ {self.dim} chiều")
        return KetQuaNhung(model_id, model_version, vectors)

    async def aclose(self) -> None:
        await self._http.aclose()
