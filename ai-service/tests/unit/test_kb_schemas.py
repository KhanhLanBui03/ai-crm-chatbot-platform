"""DTO tải tài liệu — ``KbDocumentCreate`` trong ``src/ai/schemas.py``.

Trọng tâm là ``title``: giữ ``varchar(255)`` của V202 nên DTO phải chặn đúng ở 255 — sau khi
đã chuẩn hoá NFC, vì cả Python lẫn Postgres đều đếm code point.
"""

import unicodedata

import pytest
from pydantic import ValidationError

from src.ai.schemas import KbDocumentCreate

HOP_LE = {"file_uri": "/data/kb/t/a.pdf", "file_name": "a.pdf", "title": "Bảng giá 2026"}


def _tao(**thay_doi) -> KbDocumentCreate:
    return KbDocumentCreate(**{**HOP_LE, **thay_doi})


def test_mac_dinh():
    doc = _tao()
    assert (doc.language, doc.description, doc.uploaded_by) == ("vi", None, None)


@pytest.mark.parametrize(("do_dai", "hop_le"), [(2, False), (3, True), (255, True), (256, False)])
def test_bien_do_dai_tieu_de(do_dai, hop_le):
    if hop_le:
        assert len(_tao(title="a" * do_dai).title) == do_dai
    else:
        with pytest.raises(ValidationError):
            _tao(title="a" * do_dai)


def test_tieu_de_nfd_duoc_dem_sau_khi_nfc():
    """100 chữ 'ệ': NFD là 300 code point (vượt 255), NFC là 100 — phải được nhận."""
    nfd = unicodedata.normalize("NFD", "ệ" * 100)
    assert len(nfd) == 300
    doc = _tao(title=nfd)
    assert doc.title == "ệ" * 100
    assert unicodedata.is_normalized("NFC", doc.title)


def test_tieu_de_strip_truoc_khi_dem():
    """'  ab  ' chỉ còn 2 ký tự sau strip → dưới mức tối thiểu 3."""
    with pytest.raises(ValidationError):
        _tao(title="  ab  ")
    assert _tao(title="  Bảng giá  ").title == "Bảng giá"


def test_mo_ta_toan_khoang_trang_thanh_none():
    assert _tao(description="   ").description is None


@pytest.mark.parametrize(("do_dai", "hop_le"), [(500, True), (501, False)])
def test_bien_do_dai_mo_ta(do_dai, hop_le):
    if hop_le:
        assert len(_tao(description="m" * do_dai).description) == do_dai
    else:
        with pytest.raises(ValidationError):
            _tao(description="m" * do_dai)


def test_ngon_ngu_ngoai_vi_en_bi_tu_choi():
    with pytest.raises(ValidationError):
        _tao(language="fr")


def test_gui_tenant_id_trong_body_bi_tu_choi():
    """Luật số một: tenant chỉ từ header. Gửi trong body phải lỗi ồn ào, không bị lờ đi."""
    with pytest.raises(ValidationError):
        _tao(tenant_id="22222222-2222-2222-2222-222222222222")
