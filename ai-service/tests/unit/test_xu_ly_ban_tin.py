"""Quyết định COMMIT hay DLQ — ``src/worker/consumers/tai_lieu.py``. Không cần Kafka, không CSDL.

``service.nap_tai_lieu`` được thay bằng kịch bản giả để đi đủ mọi nhánh: đây là nơi kiểm "phân
biệt lỗi tạm thời (thử lại) và lỗi vĩnh viễn (DLQ) — đừng đẩy hết vào DLQ" của kế hoạch Ngày 5.
"""

import json
from uuid import uuid4

import pytest

from src.ai import service
from src.ai.inference.clients import MockEmbedClient
from src.worker.consumers.tai_lieu import XuLyTaiLieu

TENANT = "11111111-1111-1111-1111-111111111111"


def _ban_tin(event_id: int = 7) -> bytes:
    doc = str(uuid4())
    return json.dumps({
        "event_id": event_id, "event_version": 1, "event_type": "DocumentUploaded",
        "tenant_id": TENANT, "aggregate_id": doc, "occurred_at": "2026-09-27T08:00:00Z",
        "payload": {"document_id": doc},
    }).encode()


@pytest.fixture
def goi(monkeypatch):
    """Thay ``service.nap_tai_lieu`` bằng một hàng kết cục định sẵn; ghi lại mọi lần gọi."""
    lan_goi: list[dict] = []
    kich_ban: list = []

    async def nap_gia(tenant_id, document_id, *, embed, su_kien=None, factory=None):
        lan_goi.append({"tenant": tenant_id, "su_kien": su_kien})
        buoc = kich_ban.pop(0)
        if isinstance(buoc, Exception):
            raise buoc
        return buoc

    monkeypatch.setattr(service, "nap_tai_lieu", nap_gia)
    return lan_goi, kich_ban


@pytest.fixture
def xu_ly():
    da_ngu: list[float] = []

    async def ngu(s):
        da_ngu.append(s)

    x = XuLyTaiLieu(
        embed=MockEmbedClient(1024), consumer_group="ingestion-cg",
        so_luot_toi_da=3, cho_thu_lai_s=(5.0, 30.0), ngu=ngu,
    )
    x.da_ngu = da_ngu
    return x


async def test_ready_thi_commit_va_kem_dinh_danh_su_kien(goi, xu_ly):
    lan_goi, kich_ban = goi
    kich_ban.append(service.KetQuaNap("READY", 1, so_doan=12))

    kq = await xu_ly.xu_ly_ban_tin(_ban_tin(7), [("X-Trace-Id", b"t-1")])

    assert kq.hanh_dong == "COMMIT"
    assert lan_goi == [{"tenant": TENANT, "su_kien": service.SuKienNap("ingestion-cg", 7)}]


@pytest.mark.parametrize("ket_cuc", ["FAILED", "TRUNG", "BO_QUA", "MAT_QUYEN"])
async def test_ket_cuc_cua_tai_lieu_khong_vao_dlq(goi, xu_ly, ket_cuc):
    """PDF scan (FAILED) đã hiện lý do trên SCR033 — đẩy thêm vào DLQ là báo lỗi ở hai nơi."""
    _, kich_ban = goi
    kich_ban.append(service.KetQuaNap(ket_cuc, 1, loi="PARSE_NO_TEXT_EXTRACTED"))
    assert (await xu_ly.xu_ly_ban_tin(_ban_tin(), None)).hanh_dong == "COMMIT"


async def test_sai_luoc_do_vao_dlq_ngay_khong_cham_csdl(goi, xu_ly):
    lan_goi, _ = goi
    kq = await xu_ly.xu_ly_ban_tin(b'{"event_id": "hong"}', None)
    assert (kq.hanh_dong, kq.ma_loi) == ("DLQ", "EVENT_SCHEMA_INVALID")
    assert lan_goi == []


async def test_thu_lai_chi_kem_su_kien_o_luot_dau(goi, xu_ly):
    """THU_LAI: bước nhận việc đã commit cùng processed_events — lượt sau gửi lại sự kiện sẽ bị
    coi là trùng và tài liệu nằm PENDING mãi."""
    lan_goi, kich_ban = goi
    kich_ban += [
        service.KetQuaNap("THU_LAI", 1, loi="STORAGE_UNAVAILABLE"),
        service.KetQuaNap("THU_LAI", 2, loi="STORAGE_UNAVAILABLE"),
        service.KetQuaNap("READY", 3, so_doan=4),
    ]

    kq = await xu_ly.xu_ly_ban_tin(_ban_tin(9), None)

    assert kq.hanh_dong == "COMMIT" and kq.ket_qua_nap.trang_thai == "READY"
    assert [g["su_kien"] for g in lan_goi] == [service.SuKienNap("ingestion-cg", 9), None, None]
    assert xu_ly.da_ngu == [5.0, 30.0]


async def test_csdl_chet_het_luot_thi_dlq_khong_lo_chi_tiet(goi, xu_ly):
    _, kich_ban = goi
    loi = RuntimeError("SELECT … password=hunter2")
    kich_ban += [loi, loi, loi]

    kq = await xu_ly.xu_ly_ban_tin(_ban_tin(), None)

    assert (kq.hanh_dong, kq.ma_loi) == ("DLQ", "RETRY_EXHAUSTED")
    assert "hunter2" not in kq.thong_diep
    assert xu_ly.da_ngu == [5.0, 30.0]  # ngủ giữa các lần, không ngủ sau lần cuối


async def test_csdl_chet_roi_song_lai_thi_commit(goi, xu_ly):
    _, kich_ban = goi
    kich_ban += [RuntimeError("mất kết nối"), service.KetQuaNap("READY", 1, so_doan=1)]
    assert (await xu_ly.xu_ly_ban_tin(_ban_tin(), None)).hanh_dong == "COMMIT"
