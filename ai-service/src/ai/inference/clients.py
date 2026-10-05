"""Ba backend hoán đổi được cho tầng suy luận — Master Plan §3.4.1.

Chọn bằng biến môi trường ``AI_MODE``:

    remote   gọi sang tầng suy luận qua HTTP. MẶC ĐỊNH ở mọi môi trường vận hành.
    mock     trả dữ liệu giả có seed cố định. Dùng cho CI và khi Frontend/Backend
             cần một bản giả lập ổn định để làm song song.
    offline  nạp logic nhẹ ngay trong tiến trình. CHỈ dùng khi lập trình viên không có mạng.

BA BẤT BIẾN KIỂM Ở ``/ready``, FAIL-CLOSED NẾU LỆCH — §3.4.2:
1. ``model_id`` đang phục vụ phải khớp ``emb_model`` đã ghim trên từng chunk.
2. Thứ tự cột đặc trưng phải khớp ``lead_scorer.meta.json``.
3. ``OMP_NUM_THREADS`` phải khớp số vCPU được cấp.

BẢO MẬT DỮ LIỆU: Payload gửi sang tầng suy luận KHÔNG ĐƯỢC CHỨA ``tenant_id``,
``contact_id`` hay bất kỳ định danh nào (§4.10, §3.6.3).
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Protocol, runtime_checkable

import httpx

logger = logging.getLogger("ai_service.inference.clients")

FORBIDDEN_PAYLOAD_KEYS = {"tenant_id", "contact_id", "user_id", "customer_id", "phone", "email"}
VECTOR_DIM = 1024


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
# PROTOCOLS / INTERFACES
# ══════════════════════════════════════════════════════════════════════════════

@runtime_checkable
class EmbedClient(Protocol):
    async def embed(self, text: str) -> list[float]:
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...


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


# ══════════════════════════════════════════════════════════════════════════════
# 1. REMOTE INFERENCE CLIENT (HTTP sang container inference)
# ══════════════════════════════════════════════════════════════════════════════

# MỘT httpx.AsyncClient dùng chung cho mỗi (event loop, base_url) — KHÔNG tạo mới mỗi lần gọi.
# Đo 05/10: tạo AsyncClient tốn ~200 ms (nạp chứng chỉ SSL) và chiếm event loop, nên client
# tạo-mỗi-lần cho p95 phân loại 205–265 ms (ngân sách 60 ms) và 5 request đồng thời mất ~1 s;
# giữ kết nối thì p95 còn ~3,6 ms. Gắn theo event loop vì connection pool của httpx không
# dùng được sang loop khác (test chạy nhiều asyncio.run).
_HTTP_CLIENTS: dict[tuple[int, str], httpx.AsyncClient] = {}


def _http(base_url: str) -> httpx.AsyncClient:
    import asyncio

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


class RemoteEmbedClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url or os.getenv("INFERENCE_EMBED_URL", "http://ai-embed:8080")

    async def embed(self, text: str) -> list[float]:
        return (await _post(self.base_url, "/v1/embed", {"text": text}, 10.0))["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return (await _post(self.base_url, "/v1/embed/batch", {"texts": texts}, 30.0))["embeddings"]


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


# ══════════════════════════════════════════════════════════════════════════════
# 2. MOCK INFERENCE CLIENT (Trả kết quả giả lập với Seed cố định 42)
# ══════════════════════════════════════════════════════════════════════════════

class MockEmbedClient:
    """Mock client tạo vector giả lập ổn định bằng hash SHA-256 (phục vụ CI và Track A)."""

    async def embed(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        # Sử dụng LCG đơn giản để không phụ thuộc vào numpy trong ai-service (§3.2 sạch ML runtime)
        vec: list[float] = []
        cur = seed
        for _ in range(VECTOR_DIM):
            cur = (1103515245 * cur + 12345) % (2**31)
            vec.append((cur / (2**31)) - 0.5)
        # Chuẩn hóa L2
        norm = sum(x * x for x in vec) ** 0.5
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


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


# ══════════════════════════════════════════════════════════════════════════════
# FACTORY SELECTION (remote | mock | offline)
# ══════════════════════════════════════════════════════════════════════════════

def get_ai_mode() -> str:
    return os.getenv("AI_MODE", "remote").lower()


def get_embed_client() -> EmbedClient:
    mode = get_ai_mode()
    if mode == "mock":
        return MockEmbedClient()
    return RemoteEmbedClient()


def get_rerank_client() -> RerankClient:
    mode = get_ai_mode()
    if mode == "mock":
        return MockRerankClient()
    return RemoteRerankClient()


def get_classify_client() -> ClassifyClient:
    mode = get_ai_mode()
    if mode == "mock":
        return MockClassifyClient()
    return RemoteClassifyClient()
