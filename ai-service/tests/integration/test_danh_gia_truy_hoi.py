"""Gieo kho đo + harness truy hồi trên Postgres THẬT, nhúng mock. [R&D]

Vector mock không mang nghĩa — test này KHÔNG đo chất lượng truy hồi, chỉ khoá đường ống đo:
gieo đúng, nhân bản đúng, chấm đúng, bản ghi ``ARCHIVED`` không bao giờ được tính trúng, báo cáo
đủ thông tin để tái lập.
"""

import json
import re
from pathlib import Path
from uuid import UUID

import pytest
import yaml
from sqlalchemy import text

from src.ai.db import session as db_session
from src.ai.inference.clients import MockEmbedClient
from tests.eval import danh_gia_truy_hoi as harness
from tests.eval import gieo_kho
from tests.eval.bo_vang import KhoMau, de_so
from tests.eval.gieo_kho import TENANT_GOC, tenant_do

CAC_TEP = {
    "faq-thanh-toan.txt",
    "gio-mo-cua-chi-nhanh.txt",
    "chinh-sach-doi-tra.docx",  # bản 1 → ARCHIVED
    "chinh-sach-doi-tra-v2.md",
}


@pytest.fixture(scope="module")
def kho_mau() -> KhoMau:
    return KhoMau(CAC_TEP)


@pytest.fixture
async def factory(pg_dsn_ai_app):
    engine = db_session.tao_engine(pg_dsn_ai_app.replace("postgresql://", "postgresql+psycopg://"))
    factory = db_session.tao_session_factory(engine)
    await gieo_kho.xoa(factory)
    yield factory
    await gieo_kho.xoa(factory)
    await engine.dispose()


async def _dem(factory, tenant: UUID) -> dict:
    async with db_session.get_tenant_session(str(tenant), factory) as s:
        r = (
            await s.execute(
                text(
                    "SELECT count(*) FILTER (WHERE d.status = 'READY') AS ready,"
                    " count(*) FILTER (WHERE d.status = 'ARCHIVED') AS archived,"
                    " md5(string_agg(c.content || c.embedding::text, '|'"
                    "     ORDER BY d.file_name, c.chunk_index)) AS dau_van"
                    " FROM knowledge.knowledge_chunks c"
                    " JOIN knowledge.knowledge_documents d ON d.id = c.document_id"
                )
            )
        ).one()
    return {"ready": r.ready, "archived": r.archived, "dau_van": r.dau_van}


async def test_gieo_roi_nhan_ban_giong_het_tenant_goc(factory, kho_mau):
    model, version, tong = await gieo_kho.nap_tenant_goc(
        factory, MockEmbedClient(1024), kho_mau, co_lo=8
    )
    assert (model, version) == (MockEmbedClient.MODEL_ID, MockEmbedClient.MODEL_VERSION)
    assert tong == sum(len(ds) for ds in kho_mau.doan.values())

    assert await gieo_kho.nhan_ban(factory, 3) == [tenant_do(2), tenant_do(3)]
    assert await gieo_kho.nhan_ban(factory, 3) == []  # chạy lại không nhân đôi

    goc = await _dem(factory, TENANT_GOC)
    assert goc["archived"] == len(kho_mau.doan["chinh-sach-doi-tra.docx"])
    assert goc["ready"] + goc["archived"] == tong
    for so in (2, 3):
        assert await _dem(factory, tenant_do(so)) == goc  # từng ký tự nội dung, từng số vector

    with pytest.raises(RuntimeError, match="đã có tài liệu"):
        await gieo_kho.nap_tenant_goc(factory, MockEmbedClient(1024), kho_mau)


def _cau_trich(noi_dung: str, so_tu: int = 7, tru: tuple[str, ...] = ()) -> str:
    """Cửa sổ ``so_tu`` từ đầu tiên của ``noi_dung`` KHÔNG xuất hiện trong ``tru``."""
    tu = noi_dung.split()
    for dau in range(len(tu) - so_tu + 1):
        cua_so = " ".join(tu[dau : dau + so_tu])
        if re.search(r"\w", cua_so) and not any(de_so(cua_so) in de_so(t) for t in tru):
            return cua_so
    raise AssertionError("không tìm được câu trích riêng")


def _cau_hinh(tmp_path, che_do: str, **them) -> Path:
    duong_dan = tmp_path / f"{che_do}{them.get('id', '')}.yaml"
    duong_dan.write_text(
        yaml.safe_dump(
            {
                "id": f"test-{che_do}",
                "mo_ta": "test",
                "bo_vang": "golden_set.jsonl",
                "che_do": che_do,
                "tenant": str(TENANT_GOC),
                "nhung": {
                    "model": MockEmbedClient.MODEL_ID,
                    "version": MockEmbedClient.MODEL_VERSION,
                },
                **them,
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return duong_dan


async def test_harness_cham_dung_bo_qua_ban_luu_tru_va_ghi_bao_cao(factory, kho_mau, tmp_path):
    await gieo_kho.nap_tenant_goc(factory, MockEmbedClient(1024), kho_mau, co_lo=8)
    await gieo_kho.nhan_ban(factory, 3)

    v1 = [d.content for d in kho_mau.doan["chinh-sach-doi-tra.docx"]]
    v2 = [d.content for d in kho_mau.doan["chinh-sach-doi-tra-v2.md"]]
    thanh_toan = kho_mau.doan["faq-thanh-toan.txt"][1].content
    gio = kho_mau.doan["gio-mo-cua-chi-nhanh.txt"][2].content
    chi_ban_1 = next(_cau_trich(c, tru=tuple(v2)) for c in v1 if len(c.split()) > 20)
    dong = [
        {"id": "G1", "question": _cau_trich(thanh_toan),
         "can_cu": [{"file": "faq-thanh-toan.txt", "quote": _cau_trich(thanh_toan)}]},
        {"id": "G2", "question": _cau_trich(gio),
         "can_cu": [{"file": "gio-mo-cua-chi-nhanh.txt", "quote": _cau_trich(gio)}]},
        # Đáp án CHỈ có ở bản 1 (ARCHIVED) — không bao giờ được tính trúng.
        {"id": "G3", "question": chi_ban_1,
         "can_cu": [{"file": "chinh-sach-doi-tra.docx", "quote": chi_ban_1}]},
        {"id": "G4", "question": "cửa hàng có bán vé máy bay không", "can_cu": []},
    ]
    (tmp_path / "golden_set.jsonl").write_text(
        "\n".join(json.dumps(d, ensure_ascii=False) for d in dong), encoding="utf-8"
    )

    cac_ket_qua, bao_cao = await harness.chay(
        [_cau_hinh(tmp_path, "sparse"), _cau_hinh(tmp_path, "hybrid"),
         _cau_hinh(tmp_path, "dense")],
        nhan="test",
        factory=factory,
        embed=MockEmbedClient(1024),
        thu_muc=tmp_path / "reports",
    )
    sparse, hybrid, dense = cac_ket_qua
    # Câu hỏi = nguyên câu trích ⇒ làn từ khoá chắc chắn trúng G1, G2; G3 thì không bao giờ.
    assert [d["trung"] for d in sparse.dong] == [1.0, 1.0, 0.0]
    assert [d["trung"] for d in hybrid.dong] == [1.0, 1.0, 0.0]
    assert sparse.thieu_can_cu == ["G3"]
    assert all(0 <= d["ndcg"] <= 1 for d in dense.dong)
    assert all("chinh-sach-doi-tra.docx" not in d["top_k"] for kq in cac_ket_qua for d in kq.dong)

    assert "không đáp án: 1" in bao_cao
    assert "so_dong_moi_tenant" in bao_cao and "sha256" in bao_cao
    assert "So theo cặp với baseline `test-sparse`" in bao_cao
    for ten in ("test_test-sparse.csv", "test_test-hybrid.csv", "test_tong_hop.md"):
        assert (tmp_path / "reports" / ten).exists()
    assert "B − A" in harness.so_sanh(
        tmp_path / "reports" / "test_test-sparse.csv",
        tmp_path / "reports" / "test_test-hybrid.csv",
    )


async def test_harness_tu_choi_khi_ai_embed_lech_danh_tinh(factory, kho_mau, tmp_path):
    """Cấu hình ghi model/version khác cái ai-embed đang phục vụ ⇒ dừng ồn ào, không đo."""
    await gieo_kho.nap_tenant_goc(factory, MockEmbedClient(1024), kho_mau, co_lo=8)
    (tmp_path / "golden_set.jsonl").write_text(
        '{"id":"G1","question":"x","can_cu":[{"file":"a","quote":"một hai ba bốn năm"}]}',
        encoding="utf-8",
    )
    cau_hinh = _cau_hinh(tmp_path, "dense", nhung={"model": "BAAI/bge-m3", "version": "int8-x"})
    with pytest.raises(RuntimeError, match="hai không gian khác nhau"):
        await harness.chay(
            [cau_hinh], nhan="t", factory=factory, embed=MockEmbedClient(1024),
            thu_muc=tmp_path,
        )
