"""UC038 bước 3–5 — thuật toán phân cụm thuần numpy (``src/roles/phan_cum.py``). [PRODUCTION]

Dữ liệu tổng hợp có cấu trúc biết trước (các nhóm tách xa nhau) để kiểm thuật toán TÌM LẠI được cấu
trúc đó. Đây là test thuật toán, không phải số đo chất lượng phân cụm trên hội thoại thật.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

_P = Path(__file__).resolve().parents[1] / "src" / "roles" / "phan_cum.py"
_spec = importlib.util.spec_from_file_location("inference_phan_cum_test", _P)
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)


def _nhom(so_nhom: int, moi_nhom: int, chieu: int = 64, hat: int = 0) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(hat)
    tam = rng.normal(size=(so_nhom, chieu)) * 10
    x = np.concatenate([t + rng.normal(scale=0.3, size=(moi_nhom, chieu)) for t in tam])
    that = np.repeat(np.arange(so_nhom), moi_nhom)
    return x, that


def _cung_phan_hoach(a: list[int], b: np.ndarray) -> bool:
    """Hai cách gán nhãn mô tả cùng một phân hoạch (tên cụm có thể hoán vị)."""
    return len(set(zip(a, b.tolist()))) == len(set(a)) == len(set(b.tolist()))


def test_tim_lai_dung_so_nhom_va_dung_phan_hoach():
    x, that = _nhom(6, 15)
    kq = pc.phan_cum(x)
    assert kq.k == 6
    assert _cung_phan_hoach(kq.nhan, that)
    assert kq.silhouette > 0.5
    assert set(kq.diem_theo_k) == set(range(5, 26))


def test_chay_lai_cung_du_lieu_cho_cung_ket_qua():
    """Hạt giống ghim — báo cáo không 'nhảy múa' giữa hai kỳ trên cùng dữ liệu (hậu điều kiện UC038)."""
    x, _ = _nhom(7, 12, hat=3)
    a, b = pc.phan_cum(x), pc.phan_cum(x)
    assert a.nhan == b.nhan and a.k == b.k and a.dai_dien == b.dai_dien


def test_khong_co_dinh_ro_thi_chon_k_nho_nhat_trong_vung_tot():
    assert pc.chon_k({5: 0.300, 6: 0.305, 7: 0.31, 8: 0.20}) == 5     # 0,300 cách đỉnh 0,31 đúng 0,01
    assert pc.chon_k({5: 0.10, 6: 0.40, 7: 0.20}) == 6


def test_dai_dien_toi_da_10_mau_va_thuoc_dung_cum():
    x, _ = _nhom(5, 30, hat=1)
    kq = pc.phan_cum(x)
    for c, chi_so in kq.dai_dien.items():
        assert 1 <= len(chi_so) <= 10
        assert all(kq.nhan[i] == c for i in chi_so)


def test_giam_ve_50_chieu_va_khong_vuot_so_diem():
    x, _ = _nhom(5, 30, chieu=1024, hat=2)
    assert pc.phan_cum(x).so_chieu_da_giam == 50
    nho, _ = _nhom(5, 3, chieu=1024, hat=2)     # 15 điểm → tối đa 14 chiều
    assert pc.phan_cum(nho).so_chieu_da_giam == 14


def test_qua_it_diem_bao_loi_khong_doan():
    x, _ = _nhom(1, 5)
    with pytest.raises(ValueError):
        pc.phan_cum(x)


def test_silhouette_khop_dinh_nghia_tren_vi_du_tay():
    # Hai cụm trên trục số: {0, 1} và {10, 11}
    x = np.array([[0.0], [1.0], [10.0], [11.0]])
    nhan = np.array([0, 0, 1, 1])
    # điểm 0: a = 1, b = (10 + 11) / 2 = 10,5 → (10,5 − 1) / 10,5
    s0 = (10.5 - 1) / 10.5
    s1 = (9.5 - 1) / 9.5        # điểm 1: a = 1, b = (9 + 10) / 2
    # điểm 10 và 11 đối xứng với điểm 1 và 0
    assert pc.silhouette(x, nhan) == pytest.approx((s0 + s1 + s1 + s0) / 4, rel=1e-9)
