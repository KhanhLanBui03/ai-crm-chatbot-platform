"""Quyết định COMMIT hay DLQ của consumer tóm tắt — ``src/worker/consumers/tom_tat.py``.

``service.summarize`` được thay bằng kịch bản giả; không Kafka, không CSDL, không LLM.
"""

import json
from uuid import uuid4

import pytest

from src.ai import service
from src.ai.exceptions import JavaCoreUnavailableError, SummaryLlmError
from src.worker.consumers.tom_tat import XuLyTomTat

TENANT = "11111111-1111-1111-1111-111111111111"


def _ban_tin(event_id: int = 9) -> bytes:
    conv = str(uuid4())
    return json.dumps({
        "event_id": event_id, "event_version": 1, "event_type": "ConversationClosed",
        "tenant_id": TENANT, "aggregate_id": conv, "occurred_at": "2026-10-09T08:00:00Z",
        "payload": {"conversation_id": conv, "closed_by": str(uuid4()),
                    "closed_at": "2026-10-09T08:00:00Z"},
    }).encode()


@pytest.fixture
def goi(monkeypatch):
    lan_goi: list[dict] = []
    kich_ban: list = []

    async def tom_tat_gia(tenant_id, conversation_id, *, trigger, su_kien, java_core,
                          bo_tom_tat, factory):
        lan_goi.append({"tenant": tenant_id, "trigger": trigger, "su_kien": su_kien})
        buoc = kich_ban.pop(0)
        if isinstance(buoc, Exception):
            raise buoc
        return buoc

    monkeypatch.setattr(service, "summarize", tom_tat_gia)
    return lan_goi, kich_ban


@pytest.fixture
def xu_ly():
    da_ngu: list[float] = []

    async def ngu(s):
        da_ngu.append(s)

    x = XuLyTomTat(consumer_group="summarizer-cg", cho_thu_lai_s=(10.0, 60.0), ngu=ngu)
    x.da_ngu = da_ngu
    return x


@pytest.mark.parametrize("ket_cuc", ["DA_GHI", "BO_QUA_NGAN", "TRUNG", "SAI_DINH_DANG"])
async def test_moi_ket_cuc_cua_service_deu_commit(goi, xu_ly, ket_cuc):
    """SAI_DINH_DANG cũng COMMIT: ở nhiệt độ 0 thử lại chỉ ra lại đúng đầu ra hỏng đó."""
    lan_goi, kich_ban = goi
    kich_ban.append(service.KetQuaTomTatHoiThoai(ket_cuc))
    kq = await xu_ly.xu_ly_ban_tin(_ban_tin(9), [("X-Trace-Id", b"t-9")])
    assert kq.hanh_dong == "COMMIT" and kq.ket_qua_tom_tat.trang_thai == ket_cuc
    assert lan_goi == [{
        "tenant": TENANT, "trigger": "CLOSING",
        "su_kien": service.SuKienNap("summarizer-cg", 9),
    }]


async def test_sai_luoc_do_vao_dlq_ngay_khong_goi_service(goi, xu_ly):
    lan_goi, _ = goi
    kq = await xu_ly.xu_ly_ban_tin(b'{"event_id": "hong"}', None)
    assert (kq.hanh_dong, kq.ma_loi) == ("DLQ", "EVENT_SCHEMA_INVALID") and lan_goi == []


async def test_loi_tam_thoi_thu_lai_roi_qua(goi, xu_ly):
    _, kich_ban = goi
    kich_ban += [SummaryLlmError("503"), JavaCoreUnavailableError("sập"),
                 service.KetQuaTomTatHoiThoai("DA_GHI")]
    kq = await xu_ly.xu_ly_ban_tin(_ban_tin(), None)
    assert kq.hanh_dong == "COMMIT"
    assert xu_ly.da_ngu == [10.0, 60.0]


async def test_het_luot_thu_thi_dlq_khong_lo_chi_tiet(goi, xu_ly):
    _, kich_ban = goi
    kich_ban += [SummaryLlmError("khach 0912345678")] * 3
    kq = await xu_ly.xu_ly_ban_tin(_ban_tin(), None)
    assert (kq.hanh_dong, kq.ma_loi) == ("DLQ", "RETRY_EXHAUSTED")
    assert "LLM_ERROR" in kq.thong_diep and "0912345678" not in kq.thong_diep
