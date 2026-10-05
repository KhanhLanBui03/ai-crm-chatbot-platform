"""Kiểm thử inference clients: Chế độ mock và rào chắn quyền riêng tư không rò rỉ PII."""

import asyncio

import httpx
import pytest

from src.ai.inference import clients
from src.ai.inference.clients import (
    MockClassifyClient,
    MockEmbedClient,
    _assert_no_pii_keys,
)


def test_mock_embed_client_deterministic():
    async def _run():
        client = MockEmbedClient()
        text = "Gói cước bên mình có những tính năng gì?"
        vec1 = await client.embed(text)
        vec2 = await client.embed(text)

        # 1. Đúng số chiều 1024
        assert len(vec1) == 1024
        assert len(vec2) == 1024

        # 2. Cùng text ra cùng vector (deterministic)
        assert vec1 == vec2

        # 3. Text khác nhau ra vector khác nhau
        vec_other = await client.embed("Khác hoàn toàn")
        assert vec1 != vec_other

    asyncio.run(_run())


def test_mock_classify_client():
    async def _run():
        client = MockClassifyClient()

        # Phân loại intent
        res_cls = await client.classify("Báo giá gói Pro giúp em")
        assert res_cls["intent"] == "PRICING_POLICY"
        assert res_cls["confidence"] >= 0.9

        # Lead scoring
        res_score = await client.score_lead({"buying_intent_detected": 1.0})
        assert res_score["score"] >= 75
        assert res_score["confidence_level"] == "HIGH"

    asyncio.run(_run())


def test_pii_security_assertion():
    """Kiểm tra rào chắn bảo mật §4.10: Không gửi định danh sang tầng suy luận."""
    # Payload sạch: Hợp lệ
    clean_payload = {"text": "Xin chào", "context": {"topic": "support"}}
    _assert_no_pii_keys(clean_payload)

    # Payload chứa tenant_id: BẮT BUỘC ném ValueError
    leaky_payload = {"text": "Xin chào", "tenant_id": "123e4567-e89b-12d3-a456-426614174000"}
    with pytest.raises(ValueError, match="VI PHẠM BẢO MẬT"):
        _assert_no_pii_keys(leaky_payload)

    # Payload chứa contact_id lồng bên trong: BẮT BUỘC ném ValueError
    nested_leaky = {"data": [{"contact_id": "456", "text": "Hỏi giá"}]}
    with pytest.raises(ValueError, match="VI PHẠM BẢO MẬT"):
        _assert_no_pii_keys(nested_leaky)


# ══════════════════════════════════════════════════════════════════════════════
# Client remote dùng CHUNG một AsyncClient — tạo mới mỗi lần gọi tốn ~200 ms (đo 05/10)
# ══════════════════════════════════════════════════════════════════════════════

URL = "http://ai-classify.test"


def _install_fake(calls: list[str]) -> None:
    """Đặt sẵn một AsyncClient có transport giả vào cache, cho loop đang chạy."""
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json={"intent": "KB_SEARCH", "confidence": 0.9, "model_id": "m"})

    key = (id(asyncio.get_running_loop()), URL)
    clients._HTTP_CLIENTS[key] = httpx.AsyncClient(
        base_url=URL, transport=httpx.MockTransport(handler)
    )


def test_remote_classify_dung_chung_mot_client():
    async def _run():
        calls: list[str] = []
        _install_fake(calls)
        c = clients.RemoteClassifyClient(base_url=URL)
        first = clients._http(URL)
        for _ in range(3):
            res = await c.classify("giá gói pro")
            assert res["intent"] == "KB_SEARCH"
        assert calls == ["/v1/classify"] * 3
        assert clients._http(URL) is first  # không tạo client mới giữa các lần gọi
        await clients.aclose_http_clients()
        assert clients._HTTP_CLIENTS == {}

    asyncio.run(_run())


def test_remote_client_chan_dinh_danh_truoc_khi_goi_mang():
    async def _run():
        calls: list[str] = []
        _install_fake(calls)
        with pytest.raises(ValueError, match="VI PHẠM BẢO MẬT"):
            await clients.RemoteClassifyClient(base_url=URL).score_lead({"tenant_id": 1.0})
        assert calls == []  # chặn trước, không request nào đi ra
        await clients.aclose_http_clients()

    asyncio.run(_run())


def test_moi_event_loop_mot_client_rieng():
    seen = []

    async def _grab():
        seen.append(clients._http(URL))
        await clients.aclose_http_clients()

    asyncio.run(_grab())
    asyncio.run(_grab())
    assert seen[0] is not seen[1]
