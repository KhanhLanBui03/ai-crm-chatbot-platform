"""ai-embed chạy model bge-m3 INT8 thật — tự bỏ qua khi máy không có artifact. [PRODUCTION]

Khoá bốn tính chất mà ``ai-service`` dựa vào mà không tự kiểm được: 1024 chiều, đã chuẩn hoá L2
(cosine = tích vô hướng, khớp ``vector_cosine_ops``), đúng thứ tự, và vector là hàm của RIÊNG văn
bản đó — không phụ thuộc văn bản nào đi cùng request (lý do ở docstring ``src/roles/embed.py``).
"""

import sys
from pathlib import Path

import numpy as np
import pytest

_INFERENCE = Path(__file__).resolve().parents[1]
_MODELS = _INFERENCE.parent / "artifacts" / "models"

pytestmark = pytest.mark.skipif(
    not ((_MODELS / "bge-m3-int8.onnx").is_file() and (_MODELS / "tokenizer.json").is_file()),
    reason="thiếu artifacts/models/bge-m3-int8.onnx + tokenizer.json",
)


@pytest.fixture(scope="module")
def bo():
    if sys.path[0] != str(_INFERENCE):
        sys.path.insert(0, str(_INFERENCE))
    for ten in [m for m in sys.modules if m == "src" or m.startswith("src.")]:
        del sys.modules[ten]
    from src.roles import embed

    return embed.lay_bo_nhung()


def test_model_version_la_hash_cua_graph(bo):
    # 71e2aa91 = sha256 của bge-m3-int8.onnx trong ADR-0021; e3_*.yaml ghim đúng chuỗi này.
    assert bo.model_version == "int8-71e2aa91"


def test_1024_chieu_va_da_chuan_hoa_l2(bo):
    v = bo.nhung(["Chính sách đổi trả hàng trong 7 ngày", "a"])
    assert v.shape == (2, 1024)
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, atol=1e-3)


def test_cau_dong_nghia_gan_hon_cau_lac_de(bo):
    hoi, dong_nghia, lac_de = bo.nhung(
        [
            "Tôi muốn trả lại sản phẩm đã mua",
            "Chính sách đổi trả hàng",
            "Giờ mở cửa chi nhánh Quận 1",
        ]
    )
    assert hoi @ dong_nghia > hoi @ lac_de + 0.1


def test_vector_khong_phu_thuoc_van_ban_di_cung(bo):
    """Đổi sang ghép lô là test này đỏ: INT8 động tính thang lượng tử hoá trên cả lô."""
    cau = "bảo hành máy nén tủ lạnh inverter bao lâu"
    rieng = bo.nhung([cau])[0]
    chung = bo.nhung(["Quy định bảo hành " * 100, cau, "ok"])[1]
    assert np.array_equal(rieng, chung)


def test_giu_dung_thu_tu_dau_vao(bo):
    cau = ["một câu rất ngắn", "Quy định vận chuyển và lắp đặt " * 20, "câu thứ ba"]
    gop = bo.nhung(cau)
    tung_cau = np.vstack([bo.nhung([c]) for c in cau])
    assert np.array_equal(gop, tung_cau)


def test_cat_o_512_token_khong_loi(bo):
    assert bo.nhung(["từ " * 3000]).shape == (1, 1024)
