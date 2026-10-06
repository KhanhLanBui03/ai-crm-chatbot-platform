"""Ba backend hoán đổi được cho tầng suy luận — Master Plan §3.4.1.

Chọn bằng biến môi trường ``AI_MODE``:

    remote   gọi sang tầng suy luận qua HTTP. MẶC ĐỊNH ở mọi môi trường vận hành.
    mock     trả dữ liệu giả có seed cố định. Dùng cho CI và khi Frontend/Backend
             cần một bản giả lập ổn định để làm song song.
    offline  nạp logic nhẹ ngay trong tiến trình. CHỈ dùng khi lập trình viên không có mạng.

BA BẤT BIẾN KIỂM Ở ``/ready``, FAIL-CLOSED NẾU LỆCH — §3.4.2:
1. ``model_id`` đang phục vụ phải khớp ``emb_model`` đã ghim trên từng chunk.
   Lệch nghĩa là vector câu hỏi và vector chỉ mục thuộc hai không gian khác nhau —
   truy hồi vẫn chạy, vẫn trả kết quả, nhưng kết quả vô nghĩa. Đây là kiểu hỏng
   im lặng nguy hiểm nhất của RAG (mã lỗi ``EMBEDDING_MODEL_MISMATCH``).
2. Thứ tự cột đặc trưng phải khớp ``lead_scorer.meta.json``. **Thứ tự cột là hợp
   đồng**, không phải chi tiết hiện thực (§5.10.4).
3. ``OMP_NUM_THREADS`` phải khớp số vCPU được cấp (§5.4).

BẢO MẬT DỮ LIỆU: payload gửi sang tầng suy luận KHÔNG ĐƯỢC CHỨA ``tenant_id``,
``contact_id`` hay bất kỳ định danh nào (§4.10, §3.6.3). ``_post`` chặn bằng
``_assert_no_pii_keys`` trước khi request rời tiến trình.

HIỆN CÓ:
- Nhúng (UC019): ``EmbedClient`` với hai hiện thực ``mock`` (tệp này) và ``remote``
  (``remote.py`` — kiểm ``model_id``, số chiều, số vector). Trả ``KetQuaNhung`` kèm danh tính
  model để ghim lên từng chunk.
- Phân loại ý định + chấm điểm lead (UC022, UC030): ``ClassifyClient``.
- Xếp hạng lại (UC023): ``RerankClient``.
``offline`` KHÔNG hiện thực ở ai-service: nạp model trong tiến trình cần ``onnxruntime``, mà cổng
chặn CI cấm gói đó ở image này — ``offline`` thuộc về ``inference/``.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import struct
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import httpx

from src.ai.config import Settings, get_settings

logger = logging.getLogger("ai_service.inference.clients")

FORBIDDEN_PAYLOAD_KEYS = {"tenant_id", "contact_id", "user_id", "customer_id", "phone", "email"}


def _assert_no_pii_keys(data: Any) -> None:
    """Bảo vệ quyền riêng tư (§4.10): Đảm bảo payload không rò rỉ định danh."""
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() in FORBIDDEN_PAYLOAD_KEYS:
                msg = f"VI PHẠM BẢO MẬT §4.10: Payload suy luận chứa định danh nhạy cảm {k!r}!"
                raise ValueError(msg)
            _assert_no_pii_keys(v)
    elif isinstance(data, list):
        for item in data:
            _assert_no_pii_keys(item)


# ══════════════════════════════════════════════════════════════════════════════
# NHÚNG — UC019
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# XẾP HẠNG LẠI VÀ PHÂN LOẠI — UC022, UC023, UC030
# ══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class RerankClient(Protocol):
    async def rerank(self, query: str, candidates: list[dict[str, str]]) -> list[dict[str, Any]]:
        ...


@runtime_checkable
class ClassifyClient(Protocol):
    async def classify(self, text: str) -> dict[str, Any]:
        ...

    async def score_lead(self, features: dict[str, float]) -> dict[str, Any]:
        ...


# MỘT httpx.AsyncClient dùng chung cho mỗi (event loop, base_url) — KHÔNG tạo mới mỗi lần gọi.
# Đo 05/10: tạo AsyncClient tốn ~200 ms (nạp chứng chỉ SSL) và chiếm event loop, nên client
# tạo-mỗi-lần cho p95 phân loại 205–265 ms (ngân sách 60 ms) và 5 request đồng thời mất ~1 s;
# giữ kết nối thì p95 còn ~3,6 ms. Gắn theo event loop vì connection pool của httpx không
# dùng được sang loop khác (test chạy nhiều asyncio.run).
_HTTP_CLIENTS: dict[tuple[int, str], httpx.AsyncClient] = {}


def _http(base_url: str) -> httpx.AsyncClient:
    key = (id(asyncio.get_running_loop()), base_url)
    client = _HTTP_CLIENTS.get(key)
    if client is None or client.is_closed:
        client = httpx.AsyncClient(base_url=base_url)
        _HTTP_CLIENTS[key] = client
    return client


async def aclose_http_clients() -> None:
    """Đóng mọi kết nối — gọi trong lifespan lúc tắt."""
    clients = list(_HTTP_CLIENTS.values())
    _HTTP_CLIENTS.clear()
    for c in clients:
        await c.aclose()


async def _post(
    base_url: str, path: str, payload: dict[str, Any], timeout: float
) -> dict[str, Any]:
    _assert_no_pii_keys(payload)
    resp = await _http(base_url).post(path, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


class RemoteRerankClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("INFERENCE_RERANK_URL", "http://ai-rerank:8080")

    async def rerank(self, query: str, candidates: list[dict[str, str]]) -> list[dict[str, Any]]:
        payload = {"query": query, "candidates": candidates}
        return (await _post(self.base_url, "/v1/rerank", payload, 15.0))["results"]


class RemoteClassifyClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("INFERENCE_CLASSIFY_URL", "http://ai-classify:8080")

    async def classify(self, text: str) -> dict[str, Any]:
        return await _post(self.base_url, "/v1/classify", {"text": text}, 5.0)

    async def score_lead(self, features: dict[str, float]) -> dict[str, Any]:
        return await _post(self.base_url, "/v1/lead-score", {"features": features}, 5.0)


class MockRerankClient:
    async def rerank(self, query: str, candidates: list[dict[str, str]]) -> list[dict[str, Any]]:
        results = []
        for idx, cand in enumerate(candidates):
            results.append({
                "chunk_id": cand.get("chunk_id", f"mock-{idx}"),
                "score": round(0.95 - (idx * 0.05), 4),
                "rank": idx + 1,
            })
        return results


class MockClassifyClient:
    async def classify(self, text: str) -> dict[str, Any]:
        t = text.lower()
        if any(w in t for w in ["chào", "hi", "hello"]):
            intent = "GREETING"
            conf = 0.95
        elif any(w in t for w in ["mua", "đặt", "đăng ký", "chốt"]):
            intent = "BUYING_INTENT"
            conf = 0.92
        elif any(w in t for w in ["giá", "báo giá", "gói"]):
            intent = "PRICING_POLICY"
            conf = 0.91
        elif any(w in t for w in ["người", "nhân viên", "tổng đài"]):
            intent = "HANDOFF_HUMAN"
            conf = 0.94
        else:
            intent = "KB_SEARCH"
            conf = 0.86

        return {
            "intent": intent,
            "confidence": conf,
            "probabilities": {intent: conf},
            "model_id": "mock-router-v1",
        }

    async def score_lead(self, features: dict[str, float]) -> dict[str, Any]:
        buying = features.get("buying_intent_detected", 0.0)
        score = int(80 if buying > 0 else 45)
        return {
            "score": score,
            "model_version": "mock-lead-scorer-v1",
            "confidence_level": "HIGH" if score >= 75 else "MEDIUM",
            "reasons": [
                "Mock: Tín hiệu mua hàng tích cực" if score >= 75 else "Mock: Nhu cầu trung bình"
            ],
        }


def get_ai_mode() -> str:
    return os.getenv("AI_MODE", "remote").lower()


def get_rerank_client() -> RerankClient:
    if get_ai_mode() == "mock":
        return MockRerankClient()
    return RemoteRerankClient()


def get_classify_client() -> ClassifyClient:
    if get_ai_mode() == "mock":
        return MockClassifyClient()
    return RemoteClassifyClient()
