"""Client tầng suy luận — ``src/ai/inference/{clients,remote}.py``.

Nhúng (UC019, Ngày 5): mock seed cố định + remote kiểm hình dạng và model đã ghim.
Phân loại (UC022): mock + client remote dùng chung một ``AsyncClient`` + rào chắn không gửi định
danh sang tầng suy luận (§4.10).
"""

import asyncio
import json
import math

import httpx
import pytest

from src.ai.config import Settings
from src.ai.exceptions import (
    EmbeddingModelMismatchError,
    EmbeddingRejectedError,
    EmbeddingUnavailableError,
)
from src.ai.inference import clients
from src.ai.inference.clients import (
    MockClassifyClient,
    MockEmbedClient,
    _assert_no_pii_keys,
    tao_embed_client,
)
from src.ai.inference.remote import RemoteEmbedClient

DIM = 1024


# ── mock ─────────────────────────────────────────────────────────────────────


async def test_mock_cung_van_ban_cung_vector_va_da_chuan_hoa_l2():
    a = await MockEmbedClient(DIM).embed_batch(["Chính sách đổi trả", "Bảng giá"])
    b = await MockEmbedClient(DIM).embed_batch(["Chính sách đổi trả"])
    assert a.vectors[0] == b.vectors[0]
    assert a.vectors[0] != a.vectors[1]
    assert all(len(v) == DIM for v in a.vectors)
    assert math.isclose(math.sqrt(sum(x * x for x in a.vectors[0])), 1.0, rel_tol=1e-9)


async def test_mock_khong_gia_danh_bge_m3():
    """Đoạn nạp bằng mock phải mang nhãn riêng, nếu không đổi sang ai-embed thật là trộn hai
    không gian vector mà không ai biết dòng nào phải nhúng lại."""
    ket_qua = await MockEmbedClient(DIM).embed_batch(["x"])
    assert ket_qua.model_id == "mock-hash-1024"
    assert "bge" not in ket_qua.model_id.lower()


def test_factory_chon_theo_ai_mode_va_tu_choi_offline():
    assert isinstance(tao_embed_client(Settings(ai_mode="mock")), MockEmbedClient)
    assert isinstance(tao_embed_client(Settings(ai_mode="remote")), RemoteEmbedClient)
    with pytest.raises(ValueError, match="onnxruntime"):
        tao_embed_client(Settings(ai_mode="offline"))


# ── remote ───────────────────────────────────────────────────────────────────


def _client(xu_ly) -> RemoteEmbedClient:
    return RemoteEmbedClient(
        "http://ai-embed", model_id="BAAI/bge-m3", dim=DIM, timeout_s=1,
        transport=httpx.MockTransport(xu_ly),
    )


def _tra_loi(n: int, *, model_id="BAAI/bge-m3", dim=DIM) -> dict:
    return {"model_id": model_id, "model_version": "int8-test", "dim": dim,
            "embeddings": [[0.0] * dim for _ in range(n)]}


async def test_than_yeu_cau_khong_mang_dinh_danh():
    """§3.6.3: tầng suy luận chỉ nhận văn bản — không tenant, không tài liệu, không định danh."""
    da_gui: list[dict] = []

    def xu_ly(req: httpx.Request) -> httpx.Response:
        da_gui.append(json.loads(req.content))
        return httpx.Response(200, json=_tra_loi(2))

    ket_qua = await _client(xu_ly).embed_batch(["một", "hai"])

    assert da_gui == [{"texts": ["một", "hai"]}]
    assert (ket_qua.model_id, ket_qua.model_version, len(ket_qua.vectors)) == (
        "BAAI/bge-m3", "int8-test", 2,
    )


@pytest.mark.parametrize("ma", [429, 500, 502, 503])
async def test_429_va_5xx_la_tam_thoi(ma):
    with pytest.raises(EmbeddingUnavailableError):
        await _client(lambda req: httpx.Response(ma)).embed_batch(["x"])


async def test_mat_ket_noi_la_tam_thoi():
    def xu_ly(req):
        raise httpx.ConnectError("refused", request=req)

    with pytest.raises(EmbeddingUnavailableError):
        await _client(xu_ly).embed_batch(["x"])


@pytest.mark.parametrize("ma", [400, 404, 422])
async def test_4xx_la_vinh_vien(ma):
    with pytest.raises(EmbeddingRejectedError):
        await _client(lambda req: httpx.Response(ma)).embed_batch(["x"])


async def test_sai_so_vector_hoac_so_chieu_la_vinh_vien():
    with pytest.raises(EmbeddingRejectedError, match="nhận 1 vector"):
        await _client(lambda req: httpx.Response(200, json=_tra_loi(1))).embed_batch(["a", "b"])
    with pytest.raises(EmbeddingRejectedError, match="1024 chiều"):
        await _client(lambda req: httpx.Response(200, json=_tra_loi(1, dim=768))).embed_batch(["a"])


async def test_model_khac_model_da_ghim_thi_dung():
    """Bất biến 1 §3.4.2 — vector của một không gian khác không được vào kho."""
    with pytest.raises(EmbeddingModelMismatchError):
        await _client(
            lambda req: httpx.Response(200, json=_tra_loi(1, model_id="intfloat/e5-base"))
        ).embed_batch(["a"])


# ── phân loại (UC022) ─────────────────────────────────────────────────────────


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
