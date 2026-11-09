"""[PRODUCTION] Phân cụm chủ đề hội thoại — UC038 bước 3–5. Chạy trong image ai-inference.

Đặc tả UC038: "Công việc phân cụm chạy bằng ảnh chứa thư viện học máy chứ không phải ảnh của
ai-service". Image này đã có numpy, nên thuật toán viết thẳng bằng numpy thay vì kéo thêm
scikit-learn (~40 MB) cho ba hàm.

Các bước, đúng tham số của đặc tả:

1. Chuẩn hoá L2 từng vector (so theo hướng — câu dài hay ngắn không làm lệch khoảng cách).
2. Giảm chiều bằng PCA xuống **50 chiều** (SVD). Phân cụm trên vector hàng trăm chiều kém do
   lời nguyền số chiều.
3. Thử k-means với **k từ 5 đến 25**, khởi tạo k-means++, **hạt giống ghim cố định** — chạy lại trên
   cùng dữ liệu cho cùng kết quả, báo cáo không "nhảy múa" giữa hai kỳ.
4. Chọn k theo **hệ số silhouette**. Không có đỉnh rõ (luồng phụ 4.1) thì chọn k NHỎ NHẤT trong vùng
   tốt nhất (cách đỉnh không quá ``DUNG_SAI_DINH``) — ít cụm thì dễ đọc hơn khi điểm như nhau.
5. Lấy tối đa **10 mẫu gần tâm nhất** mỗi cụm để đặt tên.

Thuần hàm, không I/O — test được không cần model.
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

SO_CHIEU = 50
K_MIN = 5
K_MAX = 25
HAT_GIONG = 42
SO_MAU_DAI_DIEN = 10
# Silhouette chênh dưới mức này coi như bằng nhau — "không có đỉnh rõ" (UC038 4.1)
DUNG_SAI_DINH = 0.01
# Silhouette tính trên tối đa chừng này điểm: ma trận khoảng cách n×n, 2.000 điểm ≈ 32 MB
MAU_SILHOUETTE = 2000
SO_LAN_KHOI_TAO = 4
SO_VONG_TOI_DA = 100


class KetQuaPhanCum(NamedTuple):
    # NamedTuple chứ không dataclass: classify.py nạp file này theo đường dẫn, không qua sys.modules
    k: int
    silhouette: float
    diem_theo_k: dict[int, float]
    nhan: list[int]
    dai_dien: dict[int, list[int]]
    so_chieu_da_giam: int


def chuan_hoa(x: np.ndarray) -> np.ndarray:
    chuan = np.linalg.norm(x, axis=1, keepdims=True)
    chuan[chuan == 0] = 1.0
    return x / chuan


def giam_chieu(x: np.ndarray, so_chieu: int = SO_CHIEU) -> np.ndarray:
    """PCA bằng SVD. Số chiều đích không vượt quá (số điểm − 1) và số chiều gốc."""
    tam = x - x.mean(axis=0, keepdims=True)
    d = max(1, min(so_chieu, x.shape[0] - 1, x.shape[1]))
    _, _, vt = np.linalg.svd(tam, full_matrices=False)
    return tam @ vt[:d].T


def _kmeans_pp(x: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    tam = [x[rng.integers(len(x))]]
    d2 = ((x - tam[0]) ** 2).sum(-1)
    for _ in range(1, k):
        tong = d2.sum()
        if tong <= 0:   # mọi điểm trùng các tâm đã chọn
            tam.append(x[rng.integers(len(x))])
        else:
            tam.append(x[rng.choice(len(x), p=d2 / tong)])
        d2 = np.minimum(d2, ((x - tam[-1]) ** 2).sum(-1))
    return np.asarray(tam)


def kmeans(x: np.ndarray, k: int, hat_giong: int = HAT_GIONG) -> tuple[np.ndarray, np.ndarray]:
    """k-means Lloyd, chạy ``SO_LAN_KHOI_TAO`` lần từ cùng một hạt giống, giữ lần có quán tính nhỏ nhất."""
    rng = np.random.default_rng(hat_giong)
    tot_nhan, tot_tam, tot_qt = None, None, np.inf
    for _ in range(SO_LAN_KHOI_TAO):
        tam = _kmeans_pp(x, k, rng)
        nhan = np.zeros(len(x), dtype=int)
        for _ in range(SO_VONG_TOI_DA):
            kc = ((x[:, None, :] - tam[None, :, :]) ** 2).sum(-1)
            nhan_moi = kc.argmin(axis=1)
            tam_moi = tam.copy()
            for c in range(k):
                thanh_vien = x[nhan_moi == c]
                if len(thanh_vien):
                    tam_moi[c] = thanh_vien.mean(axis=0)
                else:  # cụm rỗng: lấy điểm xa tâm của nó nhất làm tâm mới
                    tam_moi[c] = x[kc.min(axis=1).argmax()]
            hoi_tu = np.array_equal(nhan_moi, nhan) and np.allclose(tam_moi, tam)
            nhan, tam = nhan_moi, tam_moi
            if hoi_tu:
                break
        qt = float(((x - tam[nhan]) ** 2).sum())
        if qt < tot_qt:
            tot_nhan, tot_tam, tot_qt = nhan, tam, qt
    return tot_nhan, tot_tam


def silhouette(x: np.ndarray, nhan: np.ndarray, hat_giong: int = HAT_GIONG) -> float:
    """Hệ số silhouette trung bình (khoảng cách Euclid). Một cụm duy nhất thì không xác định → -1."""
    if len(set(nhan.tolist())) < 2:
        return -1.0
    if len(x) > MAU_SILHOUETTE:
        chon = np.random.default_rng(hat_giong).choice(len(x), MAU_SILHOUETTE, replace=False)
        x, nhan = x[chon], nhan[chon]
    # |a−b|² = |a|² + |b|² − 2a·b — ma trận n×n, không dựng mảng n×n×d (2.000 điểm × 50 chiều sẽ là 1,6 GB)
    bp = (x * x).sum(1)
    kc = np.sqrt(np.maximum(bp[:, None] + bp[None, :] - 2.0 * (x @ x.T), 0.0))
    cac_cum = sorted(set(nhan.tolist()))
    # Trung bình khoảng cách từ mỗi điểm tới từng cụm: n × số cụm
    tb = np.stack([kc[:, nhan == c].mean(axis=1) for c in cac_cum], axis=1)
    co = np.array([(nhan == c).sum() for c in cac_cum])
    diem = np.zeros(len(x))
    for i in range(len(x)):
        j = cac_cum.index(int(nhan[i]))
        if co[j] < 2:               # điểm đứng một mình trong cụm: quy ước silhouette = 0
            continue
        a = tb[i, j] * co[j] / (co[j] - 1)   # bỏ khoảng cách 0 tới chính nó
        b = np.min(np.delete(tb[i], j))
        diem[i] = (b - a) / max(a, b) if max(a, b) > 0 else 0.0
    return float(diem.mean())


def chon_k(diem_theo_k: dict[int, float]) -> int:
    """k nhỏ nhất trong vùng cách đỉnh không quá ``DUNG_SAI_DINH`` (UC038 luồng phụ 4.1)."""
    dinh = max(diem_theo_k.values())
    return min(k for k, d in diem_theo_k.items() if d >= dinh - DUNG_SAI_DINH)


def phan_cum(
    vectors: np.ndarray,
    *,
    k_min: int = K_MIN,
    k_max: int = K_MAX,
    so_chieu: int = SO_CHIEU,
    hat_giong: int = HAT_GIONG,
    so_mau: int = SO_MAU_DAI_DIEN,
) -> KetQuaPhanCum:
    x = np.asarray(vectors, dtype=np.float64)
    if x.ndim != 2 or len(x) < k_min + 1:
        raise ValueError(f"Cần ít nhất {k_min + 1} điểm để thử từ {k_min} cụm; có {len(x)}.")
    x = giam_chieu(chuan_hoa(x), so_chieu)
    tren = min(k_max, len(x) - 1)

    diem_theo_k: dict[int, float] = {}
    cac_lan: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for k in range(k_min, tren + 1):
        nhan, tam = kmeans(x, k, hat_giong)
        cac_lan[k] = (nhan, tam)
        diem_theo_k[k] = round(silhouette(x, nhan, hat_giong), 4)

    k = chon_k(diem_theo_k)
    nhan, tam = cac_lan[k]
    dai_dien: dict[int, list[int]] = {}
    for c in range(k):
        chi_so = np.flatnonzero(nhan == c)
        if len(chi_so) == 0:
            continue
        kc = ((x[chi_so] - tam[c]) ** 2).sum(-1)
        dai_dien[c] = chi_so[np.argsort(kc, kind="stable")[:so_mau]].tolist()
    return KetQuaPhanCum(
        k=k,
        silhouette=diem_theo_k[k],
        diem_theo_k=diem_theo_k,
        nhan=nhan.tolist(),
        dai_dien=dai_dien,
        so_chieu_da_giam=x.shape[1],
    )
