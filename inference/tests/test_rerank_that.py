"""ai-rerank chạy cross-encoder bge-reranker-v2-m3 INT8 thật — tự bỏ qua khi máy không có artifact.
[PRODUCTION]

Khoá những tính chất mà ``ai-service`` (``rag/rerank/quyet_dinh.xep_lai``) dựa vào mà không tự kiểm
được: đoạn đúng xếp trên đoạn lạc đề trên một ví dụ chấm tay, kết quả gồm đủ ứng viên kèm
``chunk_id`` gốc, ``score`` ∈ (0, 1) giảm dần theo ``rank``, và điểm của một cặp là hàm của RIÊNG cặp
đó — không phụ thuộc đoạn nào đi cùng request (lý do ở docstring ``src/roles/rerank.py``).
"""

import sys
from pathlib import Path

import pytest

_INFERENCE = Path(__file__).resolve().parents[1]
_MODELS = _INFERENCE.parent / "artifacts" / "models"

pytestmark = pytest.mark.skipif(
    not (
        (_MODELS / "bge-reranker-v2-m3-int8.onnx").is_file()
        and (_MODELS / "bge-reranker-v2-m3-tokenizer.json").is_file()
    ),
    reason="thiếu artifacts/models/bge-reranker-v2-m3-int8.onnx + bge-reranker-v2-m3-tokenizer.json",
)

CAU_HOI = "máy lọc nước bao lâu thì phải thay lõi"
# Chấm tay: đúng > cùng chủ đề nhưng không trả lời > lạc đề hẳn.
DUNG = "Lõi PP 5 micron cần thay sau 3 tháng sử dụng để nước đạt chất lượng và tránh hỏng màng RO."
CUNG_CHU_DE = "Máy lọc nước Ngân Hà được bảo hành 24 tháng kể từ ngày lắp đặt."
LAC_DE = "Cửa hàng mở cửa từ 8 giờ sáng đến 21 giờ tối, kể cả thứ Bảy và Chủ nhật."


def _nap_rerank():
    if sys.path[0] != str(_INFERENCE):
        sys.path.insert(0, str(_INFERENCE))
    for ten in [m for m in sys.modules if m == "src" or m.startswith("src.")]:
        del sys.modules[ten]
    from src.roles import rerank

    return rerank


@pytest.fixture(scope="module")
def rerank():
    return _nap_rerank()


@pytest.fixture(scope="module")
def bo(rerank):
    return rerank.lay_bo_xep_hang()


def test_model_version_la_hash_cua_graph(bo):
    bien_the, ma = bo.model_version.split("-")
    assert bien_the == "int8" and len(ma) == 8 and int(ma, 16) >= 0


def test_khoa_thu_tu_tren_vi_du_cham_tay(rerank):
    req = rerank.RerankRequest(
        query=CAU_HOI,
        candidates=[
            rerank.Candidate(chunk_id="lac-de", text=LAC_DE),
            rerank.Candidate(chunk_id="cung-chu-de", text=CUNG_CHU_DE),
            rerank.Candidate(chunk_id="dung", text=DUNG),
        ],
    )
    ra = rerank.rerank(req)
    assert [r["chunk_id"] for r in ra["results"]] == ["dung", "cung-chu-de", "lac-de"]
    assert [r["rank"] for r in ra["results"]] == [1, 2, 3]
    diem = [r["score"] for r in ra["results"]]
    assert all(0.0 < d < 1.0 for d in diem) and diem == sorted(diem, reverse=True)
    assert ra["model_id"] == "BAAI/bge-reranker-v2-m3"


def test_diem_khong_phu_thuoc_doan_di_cung(bo):
    """Đổi sang ghép lô là test này đỏ: INT8 động tính thang lượng tử hoá trên cả lô."""
    rieng = bo.cham(CAU_HOI, [DUNG])[0]
    chung = bo.cham(CAU_HOI, ["Quy định bảo hành " * 100, DUNG, "ok"])[1]
    assert rieng == chung


def test_giu_dung_thu_tu_dau_vao(bo):
    doan = [LAC_DE, DUNG, CUNG_CHU_DE]
    gop = bo.cham(CAU_HOI, doan)
    tung_cap = [bo.cham(CAU_HOI, [d])[0] for d in doan]
    assert gop == tung_cap


def test_doan_dai_bi_cat_o_512_khong_loi(bo):
    ma = bo.tokenizer.encode(CAU_HOI, "từ " * 3000)
    assert len(ma.ids) == 512
    assert ma.tokens[:3] == ["<s>", "▁máy", "▁lọc"]  # câu hỏi giữ nguyên, đoạn bị cắt
    assert len(bo.cham(CAU_HOI, ["từ " * 3000])) == 1


def test_danh_sach_rong_tra_rong(rerank):
    ra = rerank.rerank(rerank.RerankRequest(query=CAU_HOI, candidates=[]))
    assert ra["results"] == []
