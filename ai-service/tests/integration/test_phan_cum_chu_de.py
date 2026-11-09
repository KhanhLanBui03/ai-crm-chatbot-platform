"""UC038 phần phân cụm — công việc một kỳ trên Postgres THẬT, role ``ai_app`` chịu RLS. [PRODUCTION]

Dịch vụ phân cụm (ai-inference) được thay bằng ``httpx.MockTransport`` gom cụm theo từ khoá — test
kiểm LUỒNG của công việc (ngưỡng, nguồn vector, đặt tên, ghi kỳ, cô lập doanh nghiệp), không kiểm
thuật toán; thuật toán có test riêng ở ``inference/tests/test_phan_cum.py``.

Câu hội đồng sẽ hỏi → test làm bằng chứng:
- Máy chạy vector giả có bị đem đi phân cụm không? → ``test_ai_mode_mock_khong_gui_vector_gia``.
- Doanh nghiệp B có thấy cụm của A không? → ``test_cum_chi_thuoc_doanh_nghiep_minh``.
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest

from src.ai.clustering import cong_viec, dat_ten, kho
from src.ai.config import get_settings
from src.ai.db import session as db_session
from src.ai.db.repositories import interaction_repository
from src.ai.orchestrator.ghi_luot import DbTurnRecorder
from src.ai.orchestrator.turn import TurnRecord

CAU = {
    "giao": ["giao hàng mấy ngày", "phí giao hàng bao nhiêu", "giao hàng tận nhà không"],
    "hoa_don": ["có xuất hoá đơn VAT không", "xuất hoá đơn công ty được không", "cần hoá đơn VAT gấp"],
    "bao_hanh": ["bảo hành máy giặt mấy năm", "bảo hành tủ lạnh ở đâu", "bảo hành tivi thế nào"],
}


@pytest.fixture
async def factory(pg_dsn_ai_app):
    engine = db_session.tao_engine(pg_dsn_ai_app.replace("postgresql://", "postgresql+psycopg://"))
    yield db_session.tao_session_factory(engine)
    await engine.dispose()


def _cai_dat(**thay):
    goc = {"chu_de_toi_thieu_hoi_thoai": 6, "ai_mode": "mock", "inference_classify_url": "http://ai-classify:8080"}
    goc.update(thay)
    return get_settings().model_copy(update=goc)


def _luot(tenant: str, cau: str, conv: str | None = None, **thay) -> TurnRecord:
    goc = dict(
        interaction_id=uuid4(), tenant_id=tenant, conversation_id=conv or str(uuid4()), branch="RAG",
        intent="KB_SEARCH", intent_confidence=0.9, user_query=cau, response_text="ok",
        retrieved_chunk_ids=[], is_answered=True, refusal_reason=None, model_name="template",
        model_version=None, cost_vnd=0.0, latency_ms=10, status="SUCCESS", error_message=None,
        safety_flag=None, llm_called=False, route_reason="TEST",
    )
    goc.update(thay)
    return TurnRecord(**goc)


async def _ghi(factory, *ds: TurnRecord) -> None:
    rec = DbTurnRecorder(factory)
    for r in ds:
        await rec.record(r)


async def _ghi_9_hoi_thoai(factory, tenant: str) -> None:
    await _ghi(factory, *[_luot(tenant, c) for nhom in CAU.values() for c in nhom])


class _DichVuGia:
    """Thay ai-inference: gom theo từ khoá, ghi lại thân request để test soi."""

    def __init__(self, ma: int = 200) -> None:
        self.ma = ma
        self.than: list[dict] = []

    def __call__(self, req: httpx.Request) -> httpx.Response:
        than = json.loads(req.content)
        self.than.append(than)
        if self.ma != 200:
            return httpx.Response(self.ma, json={"detail": "x"})
        texts = than["texts"]
        nhom = ["giao" if "giao" in t else "hoá đơn" if "hoá đơn" in t else "bảo" for t in texts]
        thu_tu = sorted(set(nhom))
        nhan = [thu_tu.index(n) for n in nhom]
        dai_dien = {str(c): [i for i, l in enumerate(nhan) if l == c][:10] for c in range(len(thu_tu))}
        return httpx.Response(200, json={
            "vector_source": "router-tfidf-ngram", "k": len(thu_tu), "silhouette": 0.42,
            "scores_by_k": {}, "labels": nhan, "representatives": dai_dien, "reduced_dims": 8,
        })


async def _chay(factory, tenant, dich_vu, **cai_dat):
    async with httpx.AsyncClient(transport=httpx.MockTransport(dich_vu)) as http:
        return await cong_viec.chay_ky(tenant, http=http, settings=_cai_dat(**cai_dat),
                                       bay_gio=datetime.now(UTC) + timedelta(minutes=1), factory=factory)


async def _ky(factory, tenant):
    async with db_session.get_tenant_session(tenant, factory) as phien:
        return await kho.ky_moi_nhat(phien, tenant)


async def test_du_hoi_thoai_thi_phan_cum_dat_ten_va_ghi_ky(factory):
    t = str(uuid4())
    await _ghi_9_hoi_thoai(factory, t)
    dv = _DichVuGia()
    kq = await _chay(factory, t, dv)
    assert kq.trang_thai == "DONE" and kq.k == 3 and kq.so_hoi_thoai == 9
    assert kq.nguon_vector == "router-tfidf-ngram" and kq.cach_dat_ten == "tu-khoa"

    ky = await _ky(factory, t)
    assert ky["status"] == "DONE" and ky["conversation_count"] == 9 and ky["min_conversations"] == 6
    nhan = {c["label"] for c in ky["clusters"]}
    assert any("giao hàng" in n.lower() for n in nhan)
    assert any("hoá đơn" in n.lower() for n in nhan)
    assert len(ky["assignments"]) == 9


async def test_chi_lay_cau_dau_moi_hoi_thoai(factory):
    t = str(uuid4())
    conv = str(uuid4())
    await _ghi_9_hoi_thoai(factory, t)
    # lượt thứ hai của MỘT hội thoại đã có — không thêm điểm nào vào phân cụm
    await _ghi(factory, _luot(t, "giao hàng mấy ngày", conv), _luot(t, "câu thứ hai không được tính", conv))
    dv = _DichVuGia()
    await _chay(factory, t, dv)
    assert len(dv.than[0]["texts"]) == 10
    assert "câu thứ hai không được tính" not in dv.than[0]["texts"]


async def test_duoi_nguong_bo_ky_khong_goi_dich_vu(factory):
    t = str(uuid4())
    await _ghi_9_hoi_thoai(factory, t)
    dv = _DichVuGia()
    kq = await _chay(factory, t, dv, chu_de_toi_thieu_hoi_thoai=200)
    assert (kq.trang_thai, kq.ly_do) == ("SKIPPED", "TOO_FEW_CONVERSATIONS")
    assert dv.than == []
    ky = await _ky(factory, t)
    assert ky["skip_reason"] == "TOO_FEW_CONVERSATIONS" and ky["clusters"] == []


async def test_ai_mode_mock_khong_gui_vector_gia(factory):
    """AI_MODE=mock: ai-service chỉ có vector mock-hash — KHÔNG được gửi đi phân cụm."""
    t = str(uuid4())
    await _ghi_9_hoi_thoai(factory, t)
    dv = _DichVuGia()
    await _chay(factory, t, dv)
    assert "vectors" not in dv.than[0] and "texts" in dv.than[0]


async def test_ky_moi_hong_khong_che_ky_cu(factory):
    t = str(uuid4())
    await _ghi_9_hoi_thoai(factory, t)
    await _chay(factory, t, _DichVuGia())
    kq = await _chay(factory, t, _DichVuGia(ma=503))
    assert (kq.trang_thai, kq.ly_do) == ("SKIPPED", "EMBED_UNAVAILABLE")
    ky = await _ky(factory, t)
    assert ky["status"] == "DONE" and len(ky["clusters"]) == 3      # giữ nguyên nhãn cũ (luồng phụ 2.1)


async def test_cum_chi_thuoc_doanh_nghiep_minh(factory):
    a, b = str(uuid4()), str(uuid4())
    await _ghi_9_hoi_thoai(factory, a)
    await _chay(factory, a, _DichVuGia())
    assert await _ky(factory, b) is None
    async with db_session.get_tenant_session(b, factory) as phien:
        assert await kho.cau_dau_moi_hoi_thoai(phien, b, datetime.now(UTC) - timedelta(days=1),
                                               datetime.now(UTC) + timedelta(days=1)) == []


async def test_xoa_du_lieu_ca_nhan_go_hoi_thoai_khoi_cum(factory):
    t = str(uuid4())
    conv = str(uuid4())
    await _ghi_9_hoi_thoai(factory, t)
    await _ghi(factory, _luot(t, "giao hàng chiều nay được không", conv))
    await _chay(factory, t, _DichVuGia())
    async with db_session.get_tenant_session(t, factory) as phien:
        await interaction_repository.xoa_theo_hoi_thoai(phien, [conv])
    ky = await _ky(factory, t)
    assert conv not in {str(g["conversation_id"]) for g in ky["assignments"]}
    assert len(ky["assignments"]) == 9


def test_dat_ten_theo_tu_khoa_uu_tien_cum_hai_tu():
    assert dat_ten.theo_tu_khoa(CAU["giao"]).lower().startswith("giao hàng")
    assert dat_ten.theo_tu_khoa(CAU["hoa_don"]).lower().startswith("hoá đơn")
    assert dat_ten.theo_tu_khoa([]) == "Chủ đề khác"
