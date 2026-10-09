"""Lược đồ ``ConversationClosed`` — ``src/ai/events/su_kien_hoi_thoai_dong.py``. Không Kafka."""

import json
from uuid import uuid4

import pytest

from src.ai.events.su_kien_hoi_thoai_dong import giai_ma
from src.ai.exceptions import EventSchemaInvalidError, EventUnsupportedError

TENANT = "11111111-1111-1111-1111-111111111111"
CONV = str(uuid4())


def _vo(**thay) -> dict:
    vo = {
        "event_id": 77, "event_version": 1, "event_type": "ConversationClosed",
        "tenant_id": TENANT, "aggregate_id": CONV, "occurred_at": "2026-10-09T08:00:00Z",
        "payload": {"conversation_id": CONV, "closed_by": str(uuid4()),
                    "closed_at": "2026-10-09T08:00:00Z", "close_reason": "RESOLVED"},
    }
    vo.update(thay)
    return vo


def test_vo_hop_le():
    sk = giai_ma(json.dumps(_vo()).encode())
    assert (sk.event_id, sk.tenant_id, str(sk.conversation_id)) == (77, TENANT, CONV)


def test_he_thong_tu_dong_khong_co_closed_by_van_nhan():
    """Hội thoại hệ thống tự đóng không có người đóng — worker không cần ``closed_by``."""
    vo = _vo()
    del vo["payload"]["closed_by"]
    assert giai_ma(json.dumps(vo).encode()).conversation_id


def test_khong_co_aggregate_id_van_nhan():
    vo = _vo()
    del vo["aggregate_id"]
    assert str(giai_ma(json.dumps(vo).encode()).conversation_id) == CONV


@pytest.mark.parametrize("gia_tri", [
    None, b"", b"khong-phai-json", b"[1]",
    json.dumps(_vo(event_id="77")).encode(),
    json.dumps(_vo(event_id=0)).encode(),
    json.dumps(_vo(aggregate_id=str(uuid4()))).encode(),
    json.dumps(_vo(payload={"closed_at": "2026-10-09T08:00:00Z"})).encode(),
    json.dumps(_vo(tenant_id="khong-phai-uuid")).encode(),
])
def test_vo_hong_luoc_do(gia_tri):
    with pytest.raises(EventSchemaInvalidError):
        giai_ma(gia_tri)


@pytest.mark.parametrize("thay", [{"event_type": "DocumentUploaded"}, {"event_version": 2}])
def test_loai_hoac_phien_ban_chua_ho_tro(thay):
    with pytest.raises(EventUnsupportedError):
        giai_ma(json.dumps(_vo(**thay)).encode())


def test_thong_diep_loi_khong_lap_lai_noi_dung():
    bi_mat = "Khách Nguyễn Văn A 0912345678"
    with pytest.raises(EventSchemaInvalidError) as loi:
        giai_ma(json.dumps(_vo(event_id=bi_mat)).encode())
    assert bi_mat not in str(loi.value)
