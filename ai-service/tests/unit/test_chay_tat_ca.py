"""Harness một lệnh Ngày 13 (``tests/eval/chay_tat_ca.py``) — pha TÍNH, không CSDL, không LLM.

Câu hội đồng sẽ hỏi → test làm bằng chứng:

- Tập đo bị sửa sau khi khoá thì sao? → ``test_sha_lech_thi_dung``
- "Chạy lại ra cùng số" kiểm bằng gì? → ``test_tinh_lai_khop_tung_o``, ``test_tai_lap_*``
- Độ phủ trích dẫn 0,80 tính trên cái gì? → ``test_do_phu_theo_cau_tren_luot_tra_loi``
"""

import csv
import json
import shutil
from pathlib import Path

import pytest

from tests.eval import chay_tat_ca as h

CAU_HINH = h.THU_MUC / "configs" / "n13_nghiem_thu.yaml"


def _ghi_csv(duong: Path, dong: list[dict]) -> None:
    duong.parent.mkdir(parents=True, exist_ok=True)
    with duong.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dong[0]))
        w.writeheader()
        w.writerows(dong)


def _luot_tra_loi(tap: str, ma: str, *, refused=False, answer="", nen_tu_choi=False, **them):
    return {
        "id": ma, "tap": tap, "nen_tu_choi": nen_tu_choi, "ly_do_mong_doi": them.get("ly_do"),
        "question": f"câu {ma}", "refused": refused,
        "refusal_reason": them.get("reason", "NOT_COVERED" if refused else None),
        "handoff": False, "safety_flag": None, "llm_called": them.get("llm_called", True),
        "llm_khong_du_can_cu": False, "degraded": them.get("degraded", False),
        "retrieval_top": 0.6, "groundedness": them.get("g", 1.0 if not refused else None),
        "so_trich_dan": them.get("so_trich_dan", 0 if refused else 1),
        "truy_hoi_trung": them.get("truy_hoi_trung"), "trich_dung_can_cu": them.get("dung"),
        "answer": answer, "tong_ms": 2000, "generate_ms": 1800,
        "llm_raw": them.get("raw", answer or None), "cosine_top_k": [0.7, 0.6, 0.5, 0.1, 0.05],
        "latency_breakdown": {"embed_ms": 60, "retrieve_ms": 8, "generate_ms": 1800,
                              "postguard_ms": 1},
    }


@pytest.fixture
def luot(tmp_path: Path) -> Path:
    """Một lượt đo giả, đủ tệp thô để ``tinh_chi_so`` chạy trên ĐÚNG cấu hình và tập thật."""
    ch = h.doc_cau_hinh(CAU_HINH)
    vang = [d for d in h._jsonl(ch.tap["bo_vang"]) if d["can_cu"]]
    thu_muc = tmp_path / "n13_gia"
    for i, duong in enumerate(ch.truy_hoi):
        cid = h.dgth.doc_cau_hinh(duong).id
        dong = []
        for j, d in enumerate(vang):
            hang = (j + i) % 7 + 1  # 1..7 — hạng 6, 7 là trượt top-5
            hang = hang if hang <= 5 else None
            dong.append({"id": d["id"], **h.dgth.diem_cau(hang, 5), "hang_dung": hang or "",
                         "hang_vector": "", "hang_tu_khoa": "", "ms": 3.0 + j % 5,
                         "dung_hnsw": 0, "top_k": json.dumps([f"t#{n}" for n in range(5)])})
        _ghi_csv(thu_muc / "truy_hoi" / f"{h.NHAN_TRUY_HOI}_{cid}.csv", dong)
    _ghi_csv(thu_muc / "truot.csv", [{"id": vang[5]["id"], "hang_top30": 9, "hang_lan_vector": 3,
                                      "hang_lan_tu_khoa": "", "top5_e3-dense": 2,
                                      "top5_e3-sparse": ""}])
    _ghi_csv(thu_muc / "do_tre_embed.csv", [{"thu_tu": i, "ms": 50 + i} for i in range(100)])
    tra_loi = [
        # 2 lượt trả lời: 3/4 câu nội dung có nguồn ("Dạ." không tính)
        _luot_tra_loi("vang", "G002", answer="Dạ. Bảo hành 24 tháng [1]. Giao trong 10 km [2].",
                      truy_hoi_trung=True, dung=True),
        _luot_tra_loi("vang", "G003", answer="Đổi mới trong 30 ngày [1]. Anh chị cứ nhắn em nhé.",
                      truy_hoi_trung=True, dung=False,
                      raw="Đổi mới trong 30 ngày [1][9]. Nhắn em."),
        _luot_tra_loi("vang", "G005", refused=True, truy_hoi_trung=False),
        _luot_tra_loi("vang", "G004", refused=True, nen_tu_choi=True),
        _luot_tra_loi("mo_rong", "T001", refused=True, nen_tu_choi=True),
        _luot_tra_loi("mo_rong", "T002", answer="Shop có bán loa [1].", nen_tu_choi=True),
        _luot_tra_loi("ngoai_30", "N013", refused=True, nen_tu_choi=True, llm_called=False,
                      ly_do="OUT_OF_SCOPE_DATA", reason="OUT_OF_SCOPE_DATA"),
    ]
    (thu_muc / "tra_loi.jsonl").write_text(
        "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in tra_loi), encoding="utf-8"
    )
    meta = {
        "nhan": "gia", "thoi_diem": "2026-10-10T10:00:00", "commit": "abc",
        "cau_hinh": str(CAU_HINH.relative_to(h.THU_MUC)),
        "sha256": {ten: h._sha(p) for ten, p in ch.tap.items()},
        "kho": {"so_dong_moi_tenant": "3820", "chi_muc_hnsw": "có"},
        "nhung_ai_embed": "BAAI/bge-m3/int8-71e2aa91",
        "nhung_cau_hinh": "BAAI/bge-m3/int8-71e2aa91",
        "tenant": "eeeeeeee-0000-0000-0000-000000000001",
        "llm": {"model": "gemini-3.5-flash-lite", "reasoning_effort": "minimal", "temperature": 0.0,
                "han_chot_s": 30, "gian_s": 4.5},
        "rag": {"san_toan_tap": 0.0, "san_tung_doan": 0.15, "nguong_bam_nguon": 0.0,
                "so_doan_loi_nhac": 5, "rerank_enabled": False},
        "chi_truy_hoi": False, "gioi_han": None,
    }
    (thu_muc / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    h.ghi_bao_cao(thu_muc, h.tinh_chi_so(thu_muc))
    return thu_muc


def _o(thu_muc: Path, chi_so: str, cau_hinh: str = "") -> dict:
    return next(d for d in h._doc_csv(thu_muc / "chi_so.csv")
                if d["chi_so"] == chi_so and d["cau_hinh"] == cau_hinh)


def test_cau_hinh_doc_duoc_va_ba_tap_dung_khoa():
    ch = h.doc_cau_hinh(CAU_HINH)
    h.kiem_sha(ch)  # không ném
    assert ch.ship == "e3-hybrid" and ch.nguong["recall_at_5"] == 0.85
    assert len(h.cac_cau_tra_loi(ch)) == 112 + 38 + 30


def test_sha_lech_thi_dung(tmp_path: Path):
    sai = CAU_HINH.read_text(encoding="utf-8").replace("bf44948e", "00000000")
    (tmp_path / "x.yaml").write_text(
        sai.replace("../", f"{h.THU_MUC}/").replace("e3_", f"{h.THU_MUC / 'configs'}/e3_"),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="tu_choi_mo_rong"):
        h.kiem_sha(h.doc_cau_hinh(tmp_path / "x.yaml"))


def test_do_phu_theo_cau_tren_luot_tra_loi(luot: Path):
    o = _o(luot, "độ phủ trích dẫn — theo câu")
    # G002: 2/2 · G003: 1/2 (câu mời không nguồn) · T002: 1/1 ⇒ 4/5
    assert (o["tu_so"], o["mau_so"], o["gia_tri"], o["ket_luan"]) == ("4", "5", "0.8000", "đạt")
    assert _o(luot, "độ phủ trích dẫn — UC027 (lượt ≥ 1 trích dẫn)")["gia_tri"] == "1.0000"
    # §5.12 trên đầu ra thô: [9] trỏ ra ngoài 3 đoạn qua sàn 0,15 ⇒ 4 hợp lệ / 5
    tho = _o(luot, "độ phủ trích dẫn — Master Plan §5.12 (trích dẫn thô hợp lệ)")
    assert (tho["tu_so"], tho["mau_so"]) == ("4", "5")
    assert _o(luot, "trích đúng căn cứ")["gia_tri"] == "0.5000"


def test_tu_choi_dung_nham_va_30_cau(luot: Path):
    assert _o(luot, "từ chối đúng — gộp 50 câu")["tu_so"] == "2"
    assert _o(luot, "từ chối đúng — 38 câu mở rộng")["gia_tri"] == "0.5000"
    nham = _o(luot, "từ chối nhầm — câu có đáp án")
    assert (nham["tu_so"], nham["mau_so"]) == ("1", "3")
    assert nham["ghi_chu"].startswith("1/1")  # câu nhầm do truy hồi trượt
    assert _o(luot, "30 câu ngoài phạm vi — đúng lý do")["gia_tri"] == "1.0000"


def test_cong_ba_service_chua_ket_luan(luot: Path):
    o = _o(luot, "tổng p95 ba service (ms)")
    assert o["ket_luan"] == "chưa đo" and o["gia_tri"] == ""
    # xếp hạng gần nhất: phần tử thứ ⌈0,95 × 100⌉ = 95 của 50…149
    assert _o(luot, "p95 ai-embed (ms)")["gia_tri"] == "144.0"


def test_recall_ship_dung_ranx_va_so_cong(luot: Path):
    o = _o(luot, "recall@5", "e3-hybrid")
    assert o["nguong"] == "≥ 0.85" and o["tai_lap"] == "tuyet_doi"
    assert _o(luot, "recall@5", "e3-dense")["nguong"] == ""  # chỉ cấu hình ship so cổng


def test_tinh_lai_khop_tung_o(luot: Path):
    assert h.tinh_lai(luot) == 0


def test_tinh_lai_bat_o_bi_sua(luot: Path):
    dong = h._doc_csv(luot / "chi_so.csv")
    dong[0]["gia_tri"] = "0.9999"
    _ghi_csv(luot / "chi_so.csv", dong)
    assert h.tinh_lai(luot) == 1


def test_tai_lap_hai_luot_giong_nhau(luot: Path):
    b = luot.with_name("n13_gia2")
    shutil.copytree(luot, b)
    assert h.tai_lap(luot, b) == 0


def test_tai_lap_lech_top_k_la_hong(luot: Path):
    b = luot.with_name("n13_gia2")
    shutil.copytree(luot, b)
    tep = next((b / "truy_hoi").glob("*.csv"))
    dong = h._doc_csv(tep)
    dong[0]["top_k"] = json.dumps(["khac"])
    _ghi_csv(tep, dong)
    assert h.tai_lap(luot, b) == 1


def test_tai_lap_llm_lech_qua_dung_sai_la_hong(luot: Path):
    b = luot.with_name("n13_gia2")
    shutil.copytree(luot, b)
    dong = h._doc_csv(b / "chi_so.csv")
    o = next(d for d in dong if d["chi_so"] == "độ phủ trích dẫn — theo câu")
    o["gia_tri"] = "0.8250"  # +2,5 điểm — trong ±3
    _ghi_csv(b / "chi_so.csv", dong)
    assert h.tai_lap(luot, b) == 0
    o["gia_tri"] = "0.8400"  # +4 điểm — ngoài ±3
    _ghi_csv(b / "chi_so.csv", dong)
    assert h.tai_lap(luot, b) == 1
