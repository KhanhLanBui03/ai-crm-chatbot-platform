"""Phép chấm và paired bootstrap của harness truy hồi (``tests/eval/danh_gia_truy_hoi.py``)."""

import json
import math
from uuid import uuid4

import pytest

from src.ai.rag.retrieve.hybrid import DoanTimDuoc
from tests.eval.bo_vang import de_so
from tests.eval.danh_gia_truy_hoi import (
    bootstrap_cap,
    chi_so_ranx,
    diem_cau,
    hang_dung_dau_tien,
)


def _doan(tep: str, noi_dung: str) -> DoanTimDuoc:
    return DoanTimDuoc(uuid4(), uuid4(), "t", tep, 1, 0, None, None, noi_dung, 0.0, None, None)


@pytest.mark.parametrize(
    ("hang", "trung", "ndcg", "rr"),
    [(1, 1, 1, 1), (2, 1, 1 / math.log2(3), 1 / 2), (5, 1, 1 / math.log2(6), 1 / 5),
     (6, 0, 0, 0), (None, 0, 0, 0)],
)
def test_diem_mot_cau(hang, trung, ndcg, rr):
    assert diem_cau(hang, 5) == pytest.approx({"trung": trung, "ndcg": ndcg, "rr": rr})


def test_dung_can_ca_tep_lan_cau_trich_va_mot_can_cu_la_du():
    can_cu = (
        ("chinh-sach-bao-hanh.pdf", de_so("máy nén của tủ lạnh inverter")),
        ("faq-bao-hanh.html", de_so("riêng máy nén được bảo hành đến 10 năm")),
    )
    ket_qua = [
        _doan("bang-gia-2026.pdf", "Máy nén của tủ lạnh inverter 10 năm"),  # đúng chữ, sai tệp
        _doan("faq-bao-hanh.html", "Thân tủ 2 năm, riêng  máy nén được BẢO HÀNH đến 10 năm."),
        _doan("chinh-sach-bao-hanh.pdf", "máy nén của tủ lạnh inverter"),
    ]
    assert hang_dung_dau_tien(ket_qua, can_cu) == 2  # căn cứ thứ hai, khoảng trắng + hoa thường
    assert hang_dung_dau_tien(ket_qua[:1], can_cu) is None


def test_bootstrap_hai_day_giong_nhau_ra_khong():
    a = [1.0, 0.0, 1.0, 1.0, 0.0] * 20
    assert bootstrap_cap(a, a) == (0.0, 0.0, 0.0)


def test_bootstrap_hon_han_thi_ktc_khong_chua_khong():
    a = [0.0] * 60 + [1.0] * 40
    b = [1.0] * 60 + [1.0] * 40  # b đúng thêm 60 câu
    hieu, duoi, tren = bootstrap_cap(a, b)
    assert hieu == pytest.approx(0.6)
    assert 0 < duoi <= hieu <= tren


def test_bootstrap_chenh_mot_cau_tren_tram_la_nhieu():
    """Một câu trên 100 (1 điểm) — KTC phải chứa 0: không đủ bằng chứng để nói B hơn A."""
    a = [1.0] * 80 + [0.0] * 20
    b = [1.0] * 81 + [0.0] * 19
    _, duoi, tren = bootstrap_cap(a, b)
    assert duoi <= 0 <= tren


def test_bootstrap_tai_lap_theo_seed():
    a = [float(i % 3 == 0) for i in range(100)]
    b = [float(i % 2 == 0) for i in range(100)]
    assert bootstrap_cap(a, b) == bootstrap_cap(a, b)


# ── ranx (Ngày 13) — thư viện ra đúng số của định nghĩa đã dùng từ Ngày 6 ─────


def _dong(ma: str, hang: int | None, so_doan: int = 5) -> dict:
    return {"id": ma, "hang_dung": hang or "",
            "top_k": json.dumps([f"t#{i}" for i in range(so_doan)])}


def test_ranx_khop_cong_thuc_tu_cai():
    cac_hang = [1, 2, 5, None, 3, None, 1, 4]
    dong = [_dong(f"G{i}", h) for i, h in enumerate(cac_hang)]
    ra = chi_so_ranx(dong, 5)
    for cot in ("trung", "ndcg", "rr"):
        assert ra[cot] == pytest.approx(sum(diem_cau(h, 5)[cot] for h in cac_hang) / len(cac_hang))


def test_ranx_doc_lai_tu_csv_cung_so():
    """Dòng đọc lại từ CSV mang chuỗi — ``tinh-lai`` dựa vào việc hai đường cho cùng số."""
    trong_bo_nho = [_dong("G1", 2), _dong("G2", None)]
    tu_csv = [{k: str(v) for k, v in d.items()} for d in trong_bo_nho]
    assert chi_so_ranx(trong_bo_nho, 5) == chi_so_ranx(tu_csv, 5)


def test_ranx_kho_it_doan_hon_k():
    assert chi_so_ranx([_dong("G1", 2, so_doan=3)], 5) == pytest.approx(
        {"trung": 1.0, "ndcg": 1 / math.log2(3), "rr": 0.5}
    )
