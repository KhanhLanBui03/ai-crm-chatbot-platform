"""UC039 — sự kiện ``ai.turn.completed``: đúng hợp đồng, không chở nội dung chat, Kafka hỏng không làm
hỏng lượt chat. [PRODUCTION]"""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.ai.events import su_kien_luot_xong as mod
from src.ai.events.su_kien_luot_xong import Y_DINH, TurnEventPublisher, dung_su_kien
from src.ai.orchestrator.turn import TurnRecord

LUOC_DO = json.loads(
    (Path(__file__).resolve().parents[3] / "docs" / "events" / "ai.turn.completed.v1.json").read_text(
        encoding="utf-8"
    )
)


def _luot(**ghi_de) -> TurnRecord:
    goc = dict(
        interaction_id=uuid4(),
        tenant_id="11111111-1111-1111-1111-111111111111",
        conversation_id="22222222-2222-2222-2222-222222222222",
        branch="RAG",
        intent="KB_SEARCH",
        intent_confidence=0.91,
        user_query="Số điện thoại của tôi là 0912345678, gói Pro giá bao nhiêu?",
        response_text="Gói Pro 3.990.000đ/tháng.",
        retrieved_chunk_ids=["c-1"],
        is_answered=True,
        refusal_reason=None,
        model_name="gemini-2.5-flash",
        model_version="2025-06",
        cost_vnd=12.345678,
        latency_ms=1834,
        status="SUCCESS",
        error_message=None,
        safety_flag=None,
        llm_called=True,
        route_reason="ABOVE_THRESHOLD",
        prompt_tokens=812,
        completion_tokens=64,
        groundedness_score=0.88,
        latency_breakdown={"guard_ms": 1, "classify_ms": 6, "retrieve_ms": 120, "generate_ms": 1650, "total_ms": 1834},
    )
    goc.update(ghi_de)
    return TurnRecord(**goc)


def _kiem_theo_luoc_do(su_kien: dict) -> None:
    """Đối chiếu tối thiểu với lược đồ JSON (dự án không kéo thư viện jsonschema)."""
    assert set(LUOC_DO["required"]) <= su_kien.keys()
    assert su_kien.keys() <= LUOC_DO["properties"].keys()  # additionalProperties: false
    p_luoc = LUOC_DO["properties"]["payload"]
    assert set(p_luoc["required"]) <= su_kien["payload"].keys()
    assert su_kien["payload"].keys() <= p_luoc["properties"].keys()
    assert su_kien["payload"]["branch"] in p_luoc["properties"]["branch"]["enum"]
    assert su_kien["payload"]["status"] in p_luoc["properties"]["status"]["enum"]
    assert su_kien["event_type"] in LUOC_DO["properties"]["event_type"]["enum"]


def test_vo_su_kien_dung_luoc_do_va_dung_khoa():
    rec = _luot()
    sk = dung_su_kien(rec, occurred_at=datetime(2026, 11, 7, 3, 0, tzinfo=UTC))
    _kiem_theo_luoc_do(sk)
    assert sk["event_id"] == str(rec.interaction_id)
    assert sk["tenant_id"] == rec.tenant_id
    assert sk["aggregate_id"] == rec.conversation_id
    assert sk["occurred_at"] == "2026-11-07T03:00:00Z"
    assert sk["payload"]["cost_vnd"] == 12.3457          # 4 chữ số thập phân, không sớm hơn
    assert sk["payload"]["latency_breakdown"] == {"guard_ms": 1, "classify_ms": 6, "retrieve_ms": 120, "generate_ms": 1650}


def test_khong_cho_noi_dung_chat_hay_du_lieu_ca_nhan():
    text = json.dumps(dung_su_kien(_luot()), ensure_ascii=False)
    assert "0912345678" not in text
    assert "gói Pro giá" not in text
    assert "Gói Pro 3.990.000" not in text


@pytest.mark.parametrize("branch", ["SMALL_TALK", "CLARIFY", "HANDOFF", "TOOL_CALL"])
def test_luot_mau_cau_va_tu_choi_van_dung_luoc_do(branch):
    rec = _luot(branch=branch, is_answered=False, refusal_reason="LOW_CONFIDENCE", llm_called=False,
                model_name="template", model_version=None, cost_vnd=0.0, prompt_tokens=None,
                completion_tokens=None, groundedness_score=None, latency_breakdown={})
    sk = dung_su_kien(rec)
    _kiem_theo_luoc_do(sk)
    assert sk["payload"]["prompt_tokens"] == 0
    assert sk["payload"]["latency_breakdown"] == {}


def test_mang_y_dinh_cho_thong_ke_chu_de():
    """UC038 lớp 1 — ý định đi kèm sự kiện; nhãn lạ hoặc bộ phân loại hỏng thì null, không gửi chuỗi lạ."""
    enum = LUOC_DO["properties"]["payload"]["properties"]["intent"]["enum"]
    assert dung_su_kien(_luot())["payload"]["intent"] == "KB_SEARCH"
    assert dung_su_kien(_luot(intent="NHAN_LA"))["payload"]["intent"] is None
    assert dung_su_kien(_luot(intent=None))["payload"]["intent"] is None
    assert set(enum) - {None} == Y_DINH  # hai nơi khai báo bảy nhãn phải khớp nhau


class _ProducerHong:
    async def start(self):
        raise ConnectionError("không có broker")

    async def stop(self):
        pass


async def test_kafka_hong_khong_nem_loi_va_dem_that_bai(monkeypatch):
    monkeypatch.setattr(mod, "AIOKafkaProducer", lambda **kw: _ProducerHong())
    truoc = mod.turn_event_failures._value.get()
    pub = TurnEventPublisher("khong-co:9092")

    pub.phat_nen(_luot())                 # không ném, không chờ
    await asyncio.sleep(0.05)
    await pub.aclose()

    assert mod.turn_event_failures._value.get() == truoc + 1


class _ProducerGhi:
    def __init__(self):
        self.da_gui = []

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send_and_wait(self, topic, value, key, headers):
        self.da_gui.append((topic, json.loads(value), key, dict(headers)))


async def test_gui_dung_topic_khoa_tenant_va_header_trace(monkeypatch):
    p = _ProducerGhi()
    monkeypatch.setattr(mod, "AIOKafkaProducer", lambda **kw: p)
    pub = TurnEventPublisher("kafka:9092")
    rec = _luot()

    await pub.phat(rec)

    topic, value, key, headers = p.da_gui[0]
    assert topic == "ai.turn.completed"
    assert key == rec.tenant_id.encode()
    assert "X-Trace-Id" in headers
    assert value["event_id"] == str(rec.interaction_id)
