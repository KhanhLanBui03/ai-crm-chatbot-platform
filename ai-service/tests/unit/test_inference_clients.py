"""Kiểm thử inference clients: Chế độ mock và rào chắn quyền riêng tư không rò rỉ PII."""

import asyncio
import pytest
from src.ai.inference.clients import (
    MockEmbedClient,
    MockClassifyClient,
    MockRerankClient,
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
    """Kiểm tra rào chắn bảo mật §4.10: Không bao giờ gửi tenant_id / contact_id sang tầng suy luận."""
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
