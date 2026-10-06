"""Chia đoạn giữ heading và số trang — ``src/ai/rag/ingest/chia_doan.py``.

Dựng ``Khoi`` bằng tay, không đọc tệp: mỗi test kiểm đúng một luật chia.
"""

from src.ai.rag.ingest.chia_doan import chia_doan, dem_token, duong_dan_heading
from src.ai.rag.ingest.phan_tich import Khoi


def _h(cap: int, chu: str, trang: int | None = None) -> Khoi:
    return Khoi("heading", chu, cap, trang)


def _d(chu: str, trang: int | None = None) -> Khoi:
    return Khoi("doan", chu, trang=trang)


# ── Đường dẫn heading ────────────────────────────────────────────────────────


def test_duong_dan_heading_tu_goc_toi_la():
    doan = chia_doan(
        [
            _h(1, "Bảng giá 2026"),
            _h(2, "3. Máy lạnh"),
            _d("Máy lạnh 1 HP giá 5.990.000đ."),
        ]
    )
    assert [d.heading for d in doan] == ["Bảng giá 2026 > 3. Máy lạnh"]


def test_heading_cung_cap_thay_the_heading_truoc():
    doan = chia_doan(
        [
            _h(1, "Bảng giá 2026"),
            _h(2, "3. Máy lạnh"),
            _h(3, "3.1. Inverter"),
            _d("A."),
            _h(2, "4. Tivi"),  # đóng cả "3. Máy lạnh" lẫn "3.1. Inverter"
            _d("B."),
        ]
    )
    assert [d.heading for d in doan] == [
        "Bảng giá 2026 > 3. Máy lạnh > 3.1. Inverter",
        "Bảng giá 2026 > 4. Tivi",
    ]


def test_khong_co_heading_thi_none():
    assert chia_doan([_d("Chỉ có một đoạn.")])[0].heading is None


def test_duong_dan_qua_255_bo_goc_giu_la():
    goc = "G" * 200
    la = "3.1. Máy lạnh inverter"
    ket_qua = duong_dan_heading([goc, "Mục giữa", la])
    assert len(ket_qua) <= 255
    assert ket_qua.endswith(la)  # phần gần đoạn nhất — thứ trích dẫn cần


def test_heading_la_qua_255_bi_cat():
    ket_qua = duong_dan_heading(["x" * 400])
    assert len(ket_qua) == 255 and ket_qua.endswith("…")


# ── Ranh giới đoạn ───────────────────────────────────────────────────────────


def test_heading_moi_dong_doan_ke_ca_khi_con_ngan():
    doan = chia_doan([_h(1, "A"), _d("ngắn."), _h(1, "B"), _d("cũng ngắn.")])
    assert [d.content for d in doan] == ["ngắn.", "cũng ngắn."]


def test_gom_nhieu_khoi_cung_muc_vao_mot_doan():
    doan = chia_doan([_h(1, "A"), _d("Câu một."), _d("Câu hai.")])
    assert len(doan) == 1
    assert doan[0].content == "Câu một.\n\nCâu hai."


def test_muc_dai_tach_theo_cau_khong_vuot_tran():
    cau = "Đây là một câu mười một từ ước lượng thôi ạ."
    assert dem_token(cau) == 12  # 11 từ + dấu chấm
    doan = chia_doan([_h(1, "Dài"), _d(" ".join([cau] * 30))], tran_token=50)
    assert len(doan) > 1
    assert all(d.token_count <= 50 for d in doan)
    assert all(d.content.endswith(".") for d in doan)  # cắt ở ranh giới câu
    assert all(d.heading == "Dài" for d in doan)


def test_cau_don_qua_dai_tach_theo_tu():
    doan = chia_doan([_d(" ".join(["từ"] * 120))], tran_token=50)
    assert len(doan) == 3
    assert all(d.token_count <= 50 for d in doan)


def test_chunk_index_lien_tuc_tu_0():
    doan = chia_doan([_h(1, "A"), _d("a."), _h(1, "B"), _d("b."), _h(1, "C"), _d("c.")])
    assert [d.chunk_index for d in doan] == [0, 1, 2]


def test_bo_khoi_rong():
    assert chia_doan([_h(1, "A"), _d("   "), _d("")]) == []


# ── Số trang ─────────────────────────────────────────────────────────────────


def test_so_trang_la_trang_cua_khoi_dau():
    doan = chia_doan([_h(1, "A", 1), _d("trang 2.", 2), _d("trang 3.", 3)])
    assert [(d.page_number, d.content) for d in doan] == [(2, "trang 2.\n\ntrang 3.")]


# ── Bảng ─────────────────────────────────────────────────────────────────────


def _bang(so_dong: int) -> Khoi:
    tieu_de = "Mã | Mô tả | Giá niêm yết"
    dong = [f"NH-ML{i:02d} | Máy lạnh inverter dòng {i} | {i}.490.000đ" for i in range(so_dong)]
    return Khoi("bang", "\n".join([tieu_de, *dong]), trang=2)


def test_bang_vua_thi_giu_nguyen():
    doan = chia_doan([_h(1, "Máy lạnh"), _bang(3)], tran_token=500)
    assert len(doan) == 1 and doan[0].content.count("\n") == 3


def test_bang_dai_tach_theo_dong_va_lap_tieu_de():
    doan = chia_doan([_h(1, "Máy lạnh"), _bang(40)], tran_token=80)
    assert len(doan) > 1
    for d in doan:
        dong = d.content.split("\n")
        assert dong[0] == "Mã | Mô tả | Giá niêm yết"  # mọi phần đều mang tên cột
        assert len(dong) >= 2  # không có phần chỉ có tiêu đề
        assert d.page_number == 2
    # Không mất, không lặp dòng dữ liệu nào.
    du_lieu = [x for d in doan for x in d.content.split("\n")[1:]]
    assert du_lieu == _bang(40).text.split("\n")[1:]


def test_doan_sau_bang_noi_tiep_phan_cuoi_cua_bang():
    doan = chia_doan([_h(1, "Máy lạnh"), _bang(40), _d("Ghi chú: giá chưa gồm lắp đặt.")], 80)
    assert doan[-1].content.endswith("Ghi chú: giá chưa gồm lắp đặt.")
