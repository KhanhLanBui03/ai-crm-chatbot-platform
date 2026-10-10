"""Eval harness MỘT LỆNH — Ngày 13: toàn bộ bảng số của báo cáo từ một tệp cấu hình. [R&D]

    cd ai-service && source .venv/bin/activate          # Postgres + ai-embed :8091 đang chạy
    AI_MODE=remote EMBED_URL=http://localhost:8091 \\
    python -m tests.eval.chay_tat_ca chay tests/eval/configs/n13_nghiem_thu.yaml --nhan lan1
    python -m tests.eval.chay_tat_ca tai-lap tests/eval/reports/n13_lan1 tests/eval/reports/n13_lan2
    python -m tests.eval.chay_tat_ca tinh-lai tests/eval/reports/n13_lan1

``--chi-truy-hoi`` bỏ lượt LLM (0 lượt Gemini) · ``--gioi-han N`` chỉ N câu đầu mỗi tập ở lượt LLM
(thử khói). Lượt LLM đủ tốn ~165 lượt Gemini (18 câu luật chặn trước, không gọi).

HAI PHA: ĐO RỒI MỚI TÍNH
-----------------------
``chay`` chỉ GHI ĐẦU RA THÔ vào ``reports/n13_<nhan>/``:

- ``truy_hoi/n13_<cấu hình>.csv`` — từng câu, từng cấu hình (``danh_gia_truy_hoi.chay``);
- ``truot.csv`` — câu trượt top-5 ở cấu hình ship, tìm lại trong top-30;
- ``do_tre_embed.csv`` — nhúng TỪNG câu một như production;
- ``tra_loi.jsonl`` — đúng ``RagAnswerer`` production, LLM thật
  (``hieu_chinh_tu_choi.hoi_mot_cau``);
- ``meta.json`` — commit, sha256 ba tập, danh tính nhúng, cấu hình LLM và ngưỡng ship.

Mọi con số rồi được ``tinh_chi_so`` tính THUẦN từ các tệp đó. ``tinh-lai`` chạy lại đúng hàm đó
trên đúng tệp đó và phải ra ``chi_so.csv`` y hệt từng ô — chứng minh phần TÍNH là tất định. Phần ĐO
thì ``tai-lap`` so hai lượt độc lập.

ĐỊNH NGHĨA — chép nguyên vào chương 5
------------------------------------
**Truy hồi** — recall@5 · nDCG@5 · MRR@5 của ``danh_gia_truy_hoi`` (``ranx``, lớp tương đương), trên
100 câu có đáp án. Cổng §1.6 xét trên cấu hình ship.

**Lượt trả lời** = lượt KHÔNG từ chối và KHÔNG suy giảm, gộp mọi tập (câu nên từ chối mà hệ thống
vẫn trả lời cũng là một câu trả lời đã gửi cho khách).

**Độ phủ trích dẫn** — bốn định nghĩa, bốn câu hỏi khác nhau:

| Tên | Tử / mẫu |
|---|---|
| theo câu (CỔNG, chốt 10/10) | Σ câu có trích dẫn / Σ câu ≥ 4 âm tiết, trên lượt trả lời |
| theo câu, bỏ "chưa có thông tin" | như trên, bỏ câu mà lời nhắc CẤM gắn nguồn |
| UC027 (``/v1/ai/quality``) | lượt có ≥ 1 trích dẫn / lượt trả lời — luôn 1,0 (ADR-0029 (c)) |
| Master Plan §5.12 | trích dẫn thô trỏ vào đoạn đã cấp / trích dẫn thô — gần 1,0 |
| trích đúng căn cứ | lượt có trích đoạn chứa căn cứ / lượt trả lời câu có đáp án — độ ĐÚNG |

**Từ chối** — đúng: bị từ chối / câu nên từ chối (12 cũ · 38 mới · gộp 50); nhầm: bị từ chối / 100
câu có đáp án (kèm số câu nhầm mà đoạn đúng không có trong top-5); 30 câu ngoài phạm vi: trả rỗng
(``refused`` và 0 trích dẫn) và đúng lý do. Tỉ lệ không gọi LLM tính trên TẬP ĐO — không đại diện
lưu lượng thật (tập đo gần như toàn câu hỏi tri thức).

**Độ trễ** — p50/p95 xếp hạng gần nhất (``danh_gia_truy_hoi._phan_vi``). Tầng lấy từ
``latency_breakdown`` của lượt LLM; ai-embed đo riêng, từng câu, bỏ ``khoi_dong`` lượt đầu.

TÁI LẬP — ba loại ô trong ``chi_so.csv``
--------------------------------------
``tuyet_doi`` (truy hồi: ai-embed tất định, cùng chỉ mục HNSW + cùng ``ef_search`` ⇒ cùng
top-k) phải khớp từng chữ số · ``dung_sai`` (chỉ số cần LLM — Gemini không nhận seed, ADR-0032)
phải lệch ≤ ``nguong.dung_sai_llm`` · ``khong_xet`` (độ trễ) in cả hai, không xét.
"""

import argparse
import asyncio
import csv
import hashlib
import json
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from src.ai.config import Settings, get_settings
from src.ai.db import session as db_session
from src.ai.inference.clients import tao_embed_client
from src.ai.rag.chuan_hoa import normalize_vi
from src.ai.rag.generate.hau_kiem import dem_cau_co_trich_dan, dem_trich_dan_tho
from src.ai.rag.retrieve import hybrid
from src.ai.rag.tsquery import build_tsquery
from tests.eval import danh_gia_truy_hoi as dgth
from tests.eval import hieu_chinh_tu_choi as hctc

THU_MUC = Path(__file__).resolve().parent
BAO_CAO = THU_MUC / "reports"
NHAN_TRUY_HOI = "n13"
TANG = ("embed_ms", "retrieve_ms", "generate_ms", "postguard_ms")
COT = ("nhom", "chi_so", "cau_hinh", "gia_tri", "tu_so", "mau_so", "nguong", "ket_luan", "tai_lap",
       "ghi_chu")


# ── Cấu hình ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CauHinhN13:
    id: str
    mo_ta: str
    nguon: Path
    truy_hoi: tuple[Path, ...]
    ship: str
    tap: dict[str, Path]
    sha256: dict[str, str]
    seed: int
    gian_s: float
    han_chot_s: float
    khoi_dong: int
    nguong: dict[str, float]


def doc_cau_hinh(duong: Path) -> CauHinhN13:
    d = yaml.safe_load(duong.read_text(encoding="utf-8"))
    goc = duong.resolve().parent
    if set(d["tap"]) != set(d["sha256"]):
        raise ValueError(f"{duong}: mỗi tập phải có đúng một sha256 đã khoá")
    return CauHinhN13(
        id=d["id"], mo_ta=d["mo_ta"], nguon=duong.resolve(),
        truy_hoi=tuple((goc / p).resolve() for p in d["truy_hoi"]),
        ship=d["ship"],
        tap={ten: (goc / p).resolve() for ten, p in d["tap"].items()},
        sha256=dict(d["sha256"]), seed=int(d["seed"]),
        gian_s=float(d["tra_loi"]["gian_s"]), han_chot_s=float(d["tra_loi"]["han_chot_s"]),
        khoi_dong=int(d["do_tre"]["khoi_dong"]),
        nguong={k: float(v) for k, v in d["nguong"].items()},
    )


def _sha(duong: Path) -> str:
    return hashlib.sha256(duong.read_bytes()).hexdigest()


def kiem_sha(ch: CauHinhN13) -> None:
    """Tập đo lệch khoá ⇒ DỪNG, không cảnh báo rồi chạy tiếp."""
    lech = [f"{ten}: {_sha(p)[:12]}… ≠ {ch.sha256[ten][:12]}…" for ten, p in ch.tap.items()
            if _sha(p) != ch.sha256[ten]]
    if lech:
        raise SystemExit("Tập đo lệch sha256 đã khoá — " + "; ".join(lech))


def _jsonl(duong: Path) -> list[dict]:
    return [json.loads(x) for x in duong.read_text(encoding="utf-8").splitlines() if x.strip()]


def cac_cau_tra_loi(ch: CauHinhN13, gioi_han: int | None = None) -> list[dict]:
    """Ba tập theo thứ tự cố định (thứ tự tệp) — thứ tự câu là một phần của cấu hình."""
    vang = [{**d, "tap": "vang", "nen_tu_choi": not d["can_cu"]} for d in _jsonl(ch.tap["bo_vang"])]
    mo_rong = [{**d, "tap": "mo_rong", "nen_tu_choi": True}
               for d in _jsonl(ch.tap["tu_choi_mo_rong"])]
    ngoai = [{**d, "can_cu": [], "tap": "ngoai_30", "nen_tu_choi": True}
             for d in _jsonl(ch.tap["ngoai_pham_vi"])]
    return [c for tap in (vang, mo_rong, ngoai) for c in tap[:gioi_han]]


# ── Pha 1: đo, ghi đầu ra thô ────────────────────────────────────────────────


def _ghi_csv(duong: Path, dong: list[dict], cot: tuple[str, ...] | None = None) -> None:
    with duong.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(cot or dong[0]))
        w.writeheader()
        w.writerows(dong)


def _doc_csv(duong: Path) -> list[dict]:
    with duong.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


async def _phan_tich_truot(
    factory, embed, ket_qua: list[dgth.KetQuaCauHinh], ship: str
) -> list[dict]:
    """Câu trượt top-5 ở cấu hình ship: tìm lại đoạn đúng trong top-30 cùng cấu hình.

    Hạng 6–30 = đoạn đúng đã có trong tập ứng viên, xếp lại (rerank) cứu được. Ngoài top-30 = tập
    ứng viên không có nó, xếp lại không cứu được — phải sửa từ phía nhúng / từ khoá / chia đoạn.
    """
    theo_id = {kq.cau_hinh.id: {d["id"]: d for d in kq.dong} for kq in ket_qua}
    kq_ship = next(kq for kq in ket_qua if kq.cau_hinh.id == ship)
    ch = kq_ship.cau_hinh
    cac_cau, _, _ = dgth.doc_bo_vang(ch.bo_vang)
    truot = [c for c in cac_cau if not float(theo_id[ship][c.id]["trung"])]
    if not truot:
        return []
    vectors = await dgth._nhung_cau_hoi(embed, truot, ch.model, ch.version)
    dong = []
    for cau, vector in zip(truot, vectors, strict=True):
        async with db_session.get_tenant_session(str(ch.tenant), factory) as s:
            top30 = await hybrid.tim_kiem_lai(
                s, vector=vector if ch.che_do != "sparse" else None,
                tsquery=build_tsquery(cau.question) if ch.che_do != "dense" else None,
                embedding_model=ch.model, embedding_version=ch.version,
                k=ch.ung_vien, ung_vien=ch.ung_vien, ef_search=ch.ef_search, quet_lap=ch.quet_lap,
            )
        hang = dgth.hang_dung_dau_tien(top30, cau.can_cu)
        doan = top30[hang - 1] if hang else None
        dong.append({
            "id": cau.id,
            "hang_top30": hang or "",
            "hang_lan_vector": (doan.hang_vector or "") if doan else "",
            "hang_lan_tu_khoa": (doan.hang_tu_khoa or "") if doan else "",
            **{f"top5_{cid}": theo_id[cid][cau.id]["hang_dung"]
               for cid in theo_id if cid != ship},
        })
    return dong


async def _do_tre_embed(embed, cau_hoi: list[str], khoi_dong: int) -> tuple[list[dict], str]:
    """Nhúng TỪNG câu một (đúng như một lượt chat), bỏ ``khoi_dong`` lượt đầu."""
    for cau in cau_hoi[:khoi_dong]:
        await embed.embed_batch([normalize_vi(cau)])
    dong, danh_tinh = [], ""
    for i, cau in enumerate(cau_hoi):
        dau = time.perf_counter()
        kq = await embed.embed_batch([normalize_vi(cau)])
        dong.append({"thu_tu": i, "ms": round((time.perf_counter() - dau) * 1000, 2)})
        danh_tinh = f"{kq.model_id}/{kq.model_version}"
    return dong, danh_tinh


async def _tra_loi(ch: CauHinhN13, thu_muc: Path, gioi_han: int | None) -> None:
    settings = Settings(llm_mode="remote")
    cac_cau = cac_cau_tra_loi(ch, gioi_han)
    tra_loi, llm, lan_cuoi = hctc.dung_answerer(settings, ch.han_chot_s)
    try:
        with (thu_muc / "tra_loi.jsonl").open("w", encoding="utf-8") as f:
            for i, cau in enumerate(cac_cau):
                dong = await hctc.hoi_mot_cau(tra_loi, llm, lan_cuoi, cau)
                f.write(json.dumps(dong, ensure_ascii=False) + "\n")
                f.flush()
                trang_thai = dong["refusal_reason"] or (
                    "suy giảm" if dong["degraded"] else "trả lời"
                )
                print(f"[{i + 1}/{len(cac_cau)}] {cau['tap']}/{cau['id']} → {trang_thai}")
                if dong["llm_called"] and ch.gian_s:
                    await asyncio.sleep(ch.gian_s)
    finally:
        await tra_loi.aclose()


async def chay(duong: Path, nhan: str, *, chi_truy_hoi: bool, gioi_han: int | None) -> Path:
    ch = doc_cau_hinh(duong)
    kiem_sha(ch)
    thu_muc = BAO_CAO / f"n13_{nhan}"
    if thu_muc.exists() and any(thu_muc.iterdir()):
        raise SystemExit(f"{thu_muc} đã có kết quả — chọn --nhan khác, không ghi đè lượt đo cũ")
    thu_muc.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    settings_llm = Settings(llm_mode="remote")
    engine = db_session.tao_engine()
    factory = db_session.tao_session_factory(engine)
    embed = tao_embed_client(settings)
    try:
        ket_qua, _ = await dgth.chay(
            list(ch.truy_hoi), nhan=NHAN_TRUY_HOI, factory=factory, embed=embed,
            thu_muc=thu_muc / "truy_hoi",
        )
        ship = next(kq.cau_hinh for kq in ket_qua if kq.cau_hinh.id == ch.ship)
        if str(ship.tenant) != hctc.TENANT:
            raise SystemExit(f"Tenant ship {ship.tenant} ≠ tenant lượt trả lời {hctc.TENANT}")
        truot = await _phan_tich_truot(factory, embed, ket_qua, ch.ship)
        if truot:
            _ghi_csv(thu_muc / "truot.csv", truot)
        cau_hoi = [c["question"] for c in cac_cau_tra_loi(ch) if c["tap"] != "ngoai_30"]
        do_tre, danh_tinh = await _do_tre_embed(embed, cau_hoi, ch.khoi_dong)
        _ghi_csv(thu_muc / "do_tre_embed.csv", do_tre)
        kho = await dgth._thong_tin_kho(factory, ship.tenant)
    finally:
        await embed.aclose()
        await engine.dispose()

    meta = {
        "nhan": nhan,
        "thoi_diem": datetime.now().isoformat(timespec="seconds"),
        "commit": dgth._commit_git(),
        "cau_hinh": str(ch.nguon.relative_to(THU_MUC)),
        "sha256": {ten: _sha(p) for ten, p in ch.tap.items()},
        "kho": kho,
        "nhung_ai_embed": danh_tinh,
        "nhung_cau_hinh": f"{ship.model}/{ship.version}",
        "tenant": str(ship.tenant),
        "llm": {"model": settings_llm.llm_model,
                "reasoning_effort": settings_llm.llm_reasoning_effort,
                "temperature": settings_llm.llm_temperature, "han_chot_s": ch.han_chot_s,
                "gian_s": ch.gian_s},
        "rag": {"san_toan_tap": settings_llm.rag_san_toan_tap,
                "san_tung_doan": settings_llm.rag_san_tung_doan,
                "nguong_bam_nguon": settings_llm.rag_nguong_bam_nguon,
                "so_doan_loi_nhac": settings_llm.rag_so_doan_loi_nhac,
                "rerank_enabled": settings_llm.rerank_enabled},
        "chi_truy_hoi": chi_truy_hoi,
        "gioi_han": gioi_han,
    }
    (thu_muc / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), "utf-8")

    if not chi_truy_hoi:
        await _tra_loi(ch, thu_muc, gioi_han)
    cac_dong = tinh_chi_so(thu_muc)
    ghi_bao_cao(thu_muc, cac_dong)
    return thu_muc


# ── Pha 2: tính — THUẦN từ đầu ra thô ───────────────────────────────────────


def _ty_le(tu: int, mau: int) -> float | None:
    return tu / mau if mau else None


def _p(xs: list[float], p: float) -> float | None:
    return dgth._phan_vi(xs, p) if xs else None


def _o(nhom: str, chi_so: str, gia_tri: float | int | None, *, cau_hinh: str = "",
       tu_so: int | str = "", mau_so: int | str = "", nguong: float | None = None,
       nho_hon: bool = False, tai_lap: str = "khong_xet", ghi_chu: str = "",
       dang: str = "{:.4f}") -> dict:
    """Một ô của ``chi_so.csv``. Định dạng cố định để ``tinh-lai`` so được từng chữ số."""
    if gia_tri is None:
        ket_luan = "chưa đo" if nguong is not None else ""
    elif nguong is None:
        ket_luan = ""
    else:
        ket_luan = "đạt" if (gia_tri < nguong if nho_hon else gia_tri >= nguong) else "trượt"
    return {
        "nhom": nhom, "chi_so": chi_so, "cau_hinh": cau_hinh,
        "gia_tri": "" if gia_tri is None else dang.format(gia_tri),
        "tu_so": tu_so, "mau_so": mau_so,
        "nguong": "" if nguong is None else f"{'<' if nho_hon else '≥'} {nguong:g}",
        "ket_luan": ket_luan, "tai_lap": tai_lap, "ghi_chu": ghi_chu,
    }


def _chi_so_truy_hoi(thu_muc: Path, ch: CauHinhN13) -> tuple[list[dict], float | None]:
    o = []
    for duong in ch.truy_hoi:
        cid = dgth.doc_cau_hinh(duong).id
        dong = _doc_csv(thu_muc / "truy_hoi" / f"{NHAN_TRUY_HOI}_{cid}.csv")
        r = dgth.chi_so_ranx(dong, 5)
        tu = int(sum(float(d["trung"]) for d in dong))
        if cid == ch.ship:
            so_cau_ship = len(dong)
        o.append(_o("truy_hoi", "recall@5", r["trung"], cau_hinh=cid, tu_so=tu, mau_so=len(dong),
                    nguong=ch.nguong["recall_at_5"] if cid == ch.ship else None,
                    tai_lap="tuyet_doi",
                    ghi_chu="cấu hình ship — số đem so cổng §1.6" if cid == ch.ship else ""))
        o.append(_o("truy_hoi", "nDCG@5", r["ndcg"], cau_hinh=cid, mau_so=len(dong),
                    tai_lap="tuyet_doi"))
        o.append(_o("truy_hoi", "MRR@5", r["rr"], cau_hinh=cid, mau_so=len(dong),
                    tai_lap="tuyet_doi"))
        ms = [float(d["ms"]) for d in dong]
        for p in (0.5, 0.95):
            o.append(_o("do_tre", f"p{int(p * 100)} SQL truy hồi (ms)", _p(ms, p), cau_hinh=cid,
                        mau_so=len(ms), dang="{:.1f}"))
    truot_duong = thu_muc / "truot.csv"
    truot = _doc_csv(truot_duong) if truot_duong.exists() else []
    trong_30 = sum(1 for d in truot if d["hang_top30"])
    cot_lan = [c for c in (truot[0] if truot else {}) if c.startswith("top5_")]
    o.append(_o("truy_hoi", "câu trượt top-5", len(truot), cau_hinh=ch.ship, mau_so=so_cau_ship,
                tai_lap="tuyet_doi", dang="{}"))
    o.append(_o("truy_hoi", "  trong đó đoạn đúng ở hạng 6–30", trong_30, cau_hinh=ch.ship,
                mau_so=len(truot), tai_lap="tuyet_doi", dang="{}",
                ghi_chu="xếp lại (rerank) cứu được"))
    o.append(_o("truy_hoi", "  trong đó ngoài top-30", len(truot) - trong_30, cau_hinh=ch.ship,
                mau_so=len(truot), tai_lap="tuyet_doi", dang="{}",
                ghi_chu="tập ứng viên không có đoạn đúng"))
    for cot in cot_lan:
        bat = sum(1 for d in truot if d[cot])
        o.append(_o("truy_hoi", f"  trong đó {cot[5:]} trúng top-5", bat, cau_hinh=ch.ship,
                    mau_so=len(truot), tai_lap="tuyet_doi", dang="{}"))
    recall_ship = next(float(x["gia_tri"]) for x in o
                       if x["chi_so"] == "recall@5" and x["cau_hinh"] == ch.ship)
    return o, recall_ship


def _chi_so_tra_loi(dong: list[dict], meta: dict, ch: CauHinhN13) -> list[dict]:
    o = []
    dung_sai = "dung_sai"  # loại ô: chỉ số cần LLM — so hai lượt theo dung sai
    tra_loi = [d for d in dong if not d["refused"] and not d["degraded"]]
    # Độ phủ trích dẫn — bốn định nghĩa (đầu tệp).
    co, nd = map(sum, zip(*(dem_cau_co_trich_dan(d["answer"]) for d in tra_loi), strict=True)) \
        if tra_loi else (0, 0)
    o.append(_o("tra_loi", "độ phủ trích dẫn — theo câu", _ty_le(co, nd), tu_so=co, mau_so=nd,
                nguong=ch.nguong["do_phu_trich_dan"], tai_lap=dung_sai,
                ghi_chu=f"cổng §1.6, trên {len(tra_loi)} lượt trả lời"))
    co2, nd2 = map(sum, zip(*(dem_cau_co_trich_dan(d["answer"], bo_cau_chua_co=True)
                              for d in tra_loi), strict=True)) if tra_loi else (0, 0)
    o.append(_o("tra_loi", "độ phủ trích dẫn — theo câu, bỏ câu “chưa có thông tin”",
                _ty_le(co2, nd2), tu_so=co2, mau_so=nd2, tai_lap=dung_sai))
    uc027 = sum(1 for d in tra_loi if d["so_trich_dan"] > 0)
    o.append(_o("tra_loi", "độ phủ trích dẫn — UC027 (lượt ≥ 1 trích dẫn)",
                _ty_le(uc027, len(tra_loi)), tu_so=uc027, mau_so=len(tra_loi), tai_lap=dung_sai,
                ghi_chu="luôn 1,0 do luật (c) ADR-0029"))
    san, k = meta["rag"]["san_tung_doan"], meta["rag"]["so_doan_loi_nhac"]
    hop_le = tong = 0
    for d in dong:
        if d["llm_raw"] is None or d["degraded"]:
            continue
        so_doan = sum(1 for c in d["cosine_top_k"][:k] if c is not None and c >= san)
        h, t = dem_trich_dan_tho(d["llm_raw"], so_doan)
        hop_le, tong = hop_le + h, tong + t
    o.append(_o("tra_loi", "độ phủ trích dẫn — Master Plan §5.12 (trích dẫn thô hợp lệ)",
                _ty_le(hop_le, tong), tu_so=hop_le, mau_so=tong, tai_lap=dung_sai,
                ghi_chu="đếm trước khi hậu kiểm lọc"))
    co_dap_an = [d for d in tra_loi if d["tap"] == "vang" and not d["nen_tu_choi"]]
    dung = sum(1 for d in co_dap_an if d["trich_dung_can_cu"])
    o.append(_o("tra_loi", "trích đúng căn cứ", _ty_le(dung, len(co_dap_an)), tu_so=dung,
                mau_so=len(co_dap_an), tai_lap=dung_sai, ghi_chu="câu có đáp án được trả lời"))
    g = [d["groundedness"] for d in tra_loi if d["groundedness"] is not None]
    o.append(_o("tra_loi", "groundedness trung bình", statistics.fmean(g) if g else None,
                mau_so=len(g), tai_lap=dung_sai))

    # Từ chối.
    def tu_choi(cac: list[dict]) -> tuple[int, int]:
        return sum(1 for d in cac if d["refused"]), len(cac)

    nhom = {
        "từ chối đúng — 12 câu bộ vàng": [d for d in dong
                                          if d["tap"] == "vang" and d["nen_tu_choi"]],
        "từ chối đúng — 38 câu mở rộng": [d for d in dong if d["tap"] == "mo_rong"],
        "từ chối đúng — gộp 50 câu": [d for d in dong
                                      if d["tap"] in ("vang", "mo_rong") and d["nen_tu_choi"]],
        "từ chối nhầm — câu có đáp án": [d for d in dong
                                         if d["tap"] == "vang" and not d["nen_tu_choi"]],
    }
    for ten, cac in nhom.items():
        tu, mau = tu_choi(cac)
        ghi = ""
        if ten.startswith("từ chối nhầm"):
            truot = sum(1 for d in cac if d["refused"] and not d["truy_hoi_trung"])
            ghi = f"{truot}/{tu} câu nhầm có đoạn đúng KHÔNG trong top-5"
        o.append(_o("tu_choi", ten, _ty_le(tu, mau), tu_so=tu, mau_so=mau, tai_lap=dung_sai,
                    ghi_chu=ghi))
    ngoai = [d for d in dong if d["tap"] == "ngoai_30"]
    rong = sum(1 for d in ngoai if d["refused"] and d["so_trich_dan"] == 0)
    dung_ly_do = sum(1 for d in ngoai if d["refusal_reason"] == d["ly_do_mong_doi"])
    o.append(_o("tu_choi", "30 câu ngoài phạm vi — trả rỗng đúng", _ty_le(rong, len(ngoai)),
                tu_so=rong, mau_so=len(ngoai), tai_lap=dung_sai))
    o.append(_o("tu_choi", "30 câu ngoài phạm vi — đúng lý do", _ty_le(dung_ly_do, len(ngoai)),
                tu_so=dung_ly_do, mau_so=len(ngoai), tai_lap=dung_sai))
    for ly_do in sorted({d["refusal_reason"] for d in dong if d["refusal_reason"]}):
        so = sum(1 for d in dong if d["refusal_reason"] == ly_do)
        o.append(_o("tu_choi", f"lý do {ly_do}", so, mau_so=len(dong), tai_lap="khong_xet",
                    dang="{}"))
    khong_llm = sum(1 for d in dong if not d["llm_called"])
    o.append(_o("tu_choi", "lượt không gọi LLM (trên tập đo)", _ty_le(khong_llm, len(dong)),
                tu_so=khong_llm, mau_so=len(dong), tai_lap=dung_sai,
                ghi_chu="KHÔNG đại diện lưu lượng thật — KPI ≥ 55% đo trên telemetry"))
    suy = sum(1 for d in dong if d["degraded"])
    o.append(_o("tu_choi", "lượt suy giảm", suy, mau_so=len(dong), dang="{}"))

    # Độ trễ từng tầng (lượt LLM).
    for tang in (*TANG, "tong_ms"):
        xs = [float(d["latency_breakdown"][tang]) for d in dong
              if tang in (d.get("latency_breakdown") or {})] if tang != "tong_ms" \
            else [float(d["tong_ms"]) for d in dong]
        ten = "tổng lượt" if tang == "tong_ms" else tang.removesuffix("_ms")
        for p in (0.5, 0.95):
            o.append(_o("do_tre", f"p{int(p * 100)} tầng {ten} (ms)", _p(xs, p), mau_so=len(xs),
                        dang="{:.1f}"))
    return o


def tinh_chi_so(thu_muc: Path) -> list[dict]:
    """Toàn bộ ``chi_so.csv`` từ đầu ra thô — KHÔNG gọi mạng, không đọc đồng hồ."""
    meta = json.loads((thu_muc / "meta.json").read_text(encoding="utf-8"))
    ch = doc_cau_hinh(THU_MUC / meta["cau_hinh"])
    for ten, sha in meta["sha256"].items():
        if _sha(ch.tap[ten]) != sha:
            raise SystemExit(f"{ten} đã đổi so với lúc đo ({sha[:12]}…) — số tính lại vô nghĩa")
    cac_dong, _ = _chi_so_truy_hoi(thu_muc, ch)

    embed = [float(d["ms"]) for d in _doc_csv(thu_muc / "do_tre_embed.csv")]
    p95_embed = _p(embed, 0.95)
    cac_dong += [
        _o("do_tre", "p50 ai-embed, đo riêng (ms)", _p(embed, 0.5), mau_so=len(embed),
           dang="{:.1f}"),
        _o("ba_service", "p95 ai-classify (ms)", None,
           ghi_chu="chưa đo — thiếu artifacts/router_model.onnx, chờ Dev B (N15)"),
        _o("ba_service", "p95 ai-embed (ms)", p95_embed, mau_so=len(embed), dang="{:.1f}",
           ghi_chu=f"gọi LIỀN NHAU (ấm), bỏ {ch.khoi_dong} lượt khởi động. Lượt thật có khoảng nghỉ"
                   " ⇒ xem p95 tầng embed: ai-embed nguội sau ~4,5 s nghỉ (đo 10/10)"),
        _o("ba_service", "p95 ai-rerank (ms)", None,
           ghi_chu="chưa đo — RERANK_ENABLED tắt, ai-rerank còn giả Jaccard"),
        _o("ba_service", "tổng p95 ba service (ms)", None, nguong=ch.nguong["p95_ba_service_ms"],
           nho_hon=True, ghi_chu="chưa kết luận — 1/3 service đo được"),
    ]
    duong = thu_muc / "tra_loi.jsonl"
    if duong.exists():
        cac_dong += _chi_so_tra_loi(_jsonl(duong), meta, ch)
    else:
        cac_dong += [
            _o("tra_loi", "độ phủ trích dẫn — theo câu", None,
               nguong=ch.nguong["do_phu_trich_dan"], ghi_chu="chưa chạy lượt LLM (--chi-truy-hoi)"),
        ]
    return cac_dong


# ── Báo cáo ──────────────────────────────────────────────────────────────────


def _tim(cac_dong: list[dict], chi_so: str, cau_hinh: str = "") -> dict | None:
    return next((d for d in cac_dong if d["chi_so"] == chi_so and d["cau_hinh"] == cau_hinh), None)


def _so(o: dict | None) -> float | None:
    return float(o["gia_tri"]) if o and o["gia_tri"] != "" else None


def _bang_truot(thu_muc: Path, ch: CauHinhN13) -> list[str]:
    """recall@5 của cấu hình ship theo loại câu và kiểu gõ + danh sách câu trượt."""
    vang = {d["id"]: d for d in _jsonl(ch.tap["bo_vang"]) if d["can_cu"]}
    ship = {d["id"]: d for d in _doc_csv(thu_muc / "truy_hoi" / f"{NHAN_TRUY_HOI}_{ch.ship}.csv")}
    ra = []
    for truong in ("loai", "kieu_go"):
        ra += ["", f"| {truong} | trúng / số câu | recall@5 |", "|---|---|---|"]
        for gia_tri in sorted({d[truong] for d in vang.values()}):
            ids = [i for i, d in vang.items() if d[truong] == gia_tri]
            trung = sum(int(float(ship[i]["trung"])) for i in ids)
            ra.append(f"| `{gia_tri}` | {trung} / {len(ids)} | {trung / len(ids):.3f} |")
    duong = thu_muc / "truot.csv"
    if duong.exists():
        truot = _doc_csv(duong)
        cot_lan = [c for c in truot[0] if c.startswith("top5_")]
        ra += ["", "Câu trượt top-5 ở cấu hình ship — hạng đoạn đúng đầu tiên khi lấy top-30:", "",
               "| id | loại | kiểu gõ | hạng top-30 | hạng làn vector | hạng làn từ khoá | "
               + " | ".join(f"top-5 {c[5:]}" for c in cot_lan) + " | câu hỏi |",
               "|---" * (6 + len(cot_lan)) + "|---|"]
        for d in truot:
            v = vang[d["id"]]
            ra.append(f"| {d['id']} | {v['loai']} | {v['kieu_go']} | {d['hang_top30'] or '—'} | "
                      f"{d['hang_lan_vector'] or '—'} | {d['hang_lan_tu_khoa'] or '—'} | "
                      + " | ".join(d[c] or "—" for c in cot_lan) + f" | {v['question']} |")
    return ra


def ghi_bao_cao(thu_muc: Path, cac_dong: list[dict]) -> None:
    meta = json.loads((thu_muc / "meta.json").read_text(encoding="utf-8"))
    ch = doc_cau_hinh(THU_MUC / meta["cau_hinh"])
    _ghi_csv(thu_muc / "chi_so.csv", cac_dong, COT)
    cong = [
        _tim(cac_dong, "recall@5", ch.ship),
        _tim(cac_dong, "độ phủ trích dẫn — theo câu"),
        _tim(cac_dong, "tổng p95 ba service (ms)"),
    ]
    md = [
        f"# Bảng số nghiệm thu — `{ch.id}` · lượt `{meta['nhan']}`", "",
        f"- **thời điểm:** {meta['thoi_diem']} · **commit:** {meta['commit']}",
        f"- **cấu hình:** `tests/eval/{meta['cau_hinh']}` — {ch.mo_ta}",
        *(f"- **{ten}:** `{p.name}` sha256 `{meta['sha256'][ten][:16]}…`"
          for ten, p in ch.tap.items()),
        f"- **kho:** tenant `{meta['tenant']}` · {meta['kho']['so_dong_moi_tenant']} đoạn"
        f" (mọi tenant) · nhúng `{meta['nhung_ai_embed']}`",
        f"- **LLM:** `{meta['llm']['model']}` · reasoning `{meta['llm']['reasoning_effort']}` · "
        f"temperature {meta['llm']['temperature']} · hạn chót {meta['llm']['han_chot_s']} s",
        f"- **ngưỡng ship:** sàn toàn tập {meta['rag']['san_toan_tap']} · sàn từng đoạn "
        f"{meta['rag']['san_tung_doan']} · bám nguồn {meta['rag']['nguong_bam_nguon']} · "
        f"rerank {meta['rag']['rerank_enabled']}",
        "", "## Ba cổng §1.6", "",
        "| Chỉ số | Giá trị | Tử / mẫu | Ngưỡng | Kết luận | Ghi chú |",
        "|---|---|---|---|---|---|",
        *(f"| {o['chi_so']} {('`' + o['cau_hinh'] + '`') if o['cau_hinh'] else ''} | "
          f"{o['gia_tri'] or '—'} | {o['tu_so']} / {o['mau_so']} | {o['nguong']} | "
          f"**{o['ket_luan']}** | {o['ghi_chu']} |" for o in cong if o),
        "", "## Toàn bộ chỉ số", "",
        "| Nhóm | Chỉ số | Cấu hình | Giá trị | Tử / mẫu | Ngưỡng | Kết luận | Tái lập | Ghi chú |",
        "|---|---|---|---|---|---|---|---|---|",
        *(f"| {o['nhom']} | {o['chi_so']} | {o['cau_hinh']} | {o['gia_tri'] or '—'} | "
          f"{o['tu_so']} / {o['mau_so']} | {o['nguong']} | {o['ket_luan']} | {o['tai_lap']} | "
          f"{o['ghi_chu']} |" for o in cac_dong),
        "", "## Phân tích câu trượt (cấu hình ship)", *_bang_truot(thu_muc, ch),
        "", "Biểu đồ: `truy_hoi.png` · `tu_choi.png` · `do_tre.png`. Bảng đầy đủ: `chi_so.csv`.",
    ]
    (thu_muc / "tong_hop.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    _ve(thu_muc, cac_dong, ch)


# Ba ô đầu của bảng màu tham chiếu (dataviz/palette.md) — qua kiểm mọi cặp kể cả mù màu.
MAU = ("#2a78d6", "#eb6834", "#1baf7a")
MUC_CHU, MUC_PHU, MUC_LUOI, NEN = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"


def _so_vn(x: float, so_le: int) -> str:
    """Định dạng số kiểu Việt: phẩy thập phân, chấm ngăn nghìn."""
    return f"{x:,.{so_le}f}".replace(",", "\0").replace(".", ",").replace("\0", ".")


def _truc(ax, so_le: int = 1, truc: str = "y") -> None:
    from matplotlib.ticker import FuncFormatter

    (ax.yaxis if truc == "y" else ax.xaxis).set_major_formatter(
        FuncFormatter(lambda x, _: _so_vn(x, so_le))
    )
    ax.set_facecolor(NEN)
    for canh in ("top", "right", "left"):
        ax.spines[canh].set_visible(False)
    ax.spines["bottom"].set_color(MUC_PHU)
    ax.tick_params(colors=MUC_PHU, labelsize=8, length=0)
    ax.yaxis.grid(True, color=MUC_LUOI, linewidth=0.8)
    ax.set_axisbelow(True)


def _ve(thu_muc: Path, cac_dong: list[dict], ch: CauHinhN13) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "text.color": MUC_CHU, "axes.labelcolor": MUC_PHU})
    ids = [dgth.doc_cau_hinh(p).id for p in ch.truy_hoi]

    # 1. Truy hồi: ba chỉ số × ba cấu hình, vạch cổng chỉ trên nhóm recall@5.
    fig, ax = plt.subplots(figsize=(7.2, 3.6), facecolor=NEN)
    _truc(ax)
    chi_so, rong = ("recall@5", "nDCG@5", "MRR@5"), 0.26
    for j, cid in enumerate(ids):
        ys = [_so(_tim(cac_dong, c, cid)) or 0.0 for c in chi_so]
        xs = [i + (j - 1) * rong for i in range(len(chi_so))]
        nhan_chuoi = cid + (" (ship)" if cid == ch.ship else "")
        cot = ax.bar(xs, ys, rong - 0.03, color=MAU[j], label=nhan_chuoi)
        ax.bar_label(cot, labels=[_so_vn(y, 3) for y in ys], fontsize=7,
                     color=MUC_CHU, padding=2)
    ax.hlines(ch.nguong["recall_at_5"], -0.45, 0.45, colors=MUC_CHU, linestyles="--", linewidth=1)
    ax.text(0.47, ch.nguong["recall_at_5"], f"cổng {ch.nguong['recall_at_5']:g}".replace(".", ","),
            va="center", fontsize=7, color=MUC_CHU)
    ax.set_xticks(range(len(chi_so)), chi_so)
    ax.set_ylim(0, 1.05)
    ax.set_title("Truy hồi trên 100 câu có đáp án", loc="left", fontsize=10, color=MUC_CHU)
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncols=3)
    fig.tight_layout()
    fig.savefig(thu_muc / "truy_hoi.png", dpi=150, facecolor=NEN)
    plt.close(fig)

    # 2. Từ chối: một chuỗi, mỗi tập một thanh — không cần chú giải.
    ten = ["từ chối đúng — 12 câu bộ vàng", "từ chối đúng — 38 câu mở rộng",
           "30 câu ngoài phạm vi — trả rỗng đúng", "từ chối nhầm — câu có đáp án"]
    nhan = ["Nên từ chối — 12 câu bộ vàng", "Nên từ chối — 38 câu mở rộng",
            "Ngoài phạm vi — 30 câu", "Có đáp án — 100 câu (từ chối nhầm)"]
    o_tc = [_tim(cac_dong, t) for t in ten]
    if all(o and o["gia_tri"] for o in o_tc):
        fig, ax = plt.subplots(figsize=(7.2, 2.8), facecolor=NEN)
        _truc(ax, truc="x")
        ax.yaxis.grid(False)
        ax.xaxis.grid(True, color=MUC_LUOI, linewidth=0.8)
        ys = [float(o["gia_tri"]) for o in o_tc]
        cot = ax.barh(range(len(ys))[::-1], ys, 0.6, color=MAU[0])
        nhan_thanh = [f"{y:.0%} ({o['tu_so']}/{o['mau_so']})"
                      for y, o in zip(ys, o_tc, strict=True)]
        ax.bar_label(cot, labels=nhan_thanh, fontsize=8, color=MUC_CHU, padding=3)
        ax.set_yticks(range(len(ys))[::-1], nhan)
        ax.set_xlim(0, 1.25)
        ax.set_title("Tỉ lệ bị từ chối theo tập (lượt LLM thật)", loc="left", fontsize=10,
                     color=MUC_CHU)
        fig.tight_layout()
        fig.savefig(thu_muc / "tu_choi.png", dpi=150, facecolor=NEN)
        plt.close(fig)

    # 3. Độ trễ: hai panel (tầng CPU · tầng có LLM) thay vì trục log — mỗi panel một thang.
    panel = [("Tầng không gọi LLM", ["embed", "retrieve", "postguard"]),
             ("Tầng có LLM", ["generate", "tổng lượt"])]
    if _so(_tim(cac_dong, "p95 tầng generate (ms)")) is not None:
        fig, cac_ax = plt.subplots(1, 2, figsize=(7.2, 3.2), facecolor=NEN,
                                   gridspec_kw={"width_ratios": [3, 2]})
        for ax, (tieu_de, cac_tang) in zip(cac_ax, panel, strict=True):
            _truc(ax, so_le=0)
            for j, p in enumerate((50, 95)):
                ys = [_so(_tim(cac_dong, f"p{p} tầng {t} (ms)")) or 0.0 for t in cac_tang]
                xs = [i + (j - 0.5) * 0.36 for i in range(len(cac_tang))]
                cot = ax.bar(xs, ys, 0.33, color=MAU[j], label=f"p{p}")
                ax.bar_label(cot, labels=[_so_vn(y, 0) for y in ys], fontsize=7,
                             color=MUC_CHU, padding=2)
            ax.set_xticks(range(len(cac_tang)), cac_tang)
            ax.set_title(tieu_de + " (ms)", loc="left", fontsize=9, color=MUC_CHU)
            ax.margins(y=0.15)
        cac_ax[0].legend(frameon=False, fontsize=8)
        fig.tight_layout()
        fig.savefig(thu_muc / "do_tre.png", dpi=150, facecolor=NEN)
        plt.close(fig)


# ── Tái lập ─────────────────────────────────────────────────────────────────


def tinh_lai(thu_muc: Path) -> int:
    """Tính lại từ đầu ra thô, so từng ô với ``chi_so.csv`` đã ghi. 0 = khớp tuyệt đối."""
    cu = _doc_csv(thu_muc / "chi_so.csv")
    moi = [{k: str(v) for k, v in d.items()} for d in tinh_chi_so(thu_muc)]
    lech = [(a, b) for a, b in zip(cu, moi, strict=False) if a != b]
    print(f"{len(moi)} ô · lệch {len(lech) + abs(len(cu) - len(moi))}")
    for a, b in lech:
        print(f"  {a['chi_so']} {a['cau_hinh']}: {a['gia_tri']} → {b['gia_tri']}")
    return 0 if not lech and len(cu) == len(moi) else 1


def tai_lap(a: Path, b: Path) -> int:
    """So hai lượt đo độc lập. 0 = mọi ô ``tuyet_doi`` khớp, mọi ô ``dung_sai`` trong ngưỡng."""
    meta = json.loads((a / "meta.json").read_text(encoding="utf-8"))
    dung_sai = doc_cau_hinh(THU_MUC / meta["cau_hinh"]).nguong["dung_sai_llm"]
    ra = [f"# Tái lập — `{a.name}` ↔ `{b.name}`", "", "## Top-k từng câu (truy hồi)", "",
          "| Cấu hình | Số câu | Câu lệch top-k |", "|---|---|---|"]
    hong = 0
    for tep in sorted((a / "truy_hoi").glob("*.csv")):
        x = {d["id"]: d["top_k"] for d in _doc_csv(tep)}
        y = {d["id"]: d["top_k"] for d in _doc_csv(b / "truy_hoi" / tep.name)}
        lech = sorted(i for i in x if x[i] != y.get(i))
        hong += bool(lech)
        ra.append(f"| `{tep.stem}` | {len(x)} | {len(lech)} {lech[:10] if lech else ''} |")
    ra += ["", f"## Từng ô (`dung_sai` ≤ {dung_sai:g})", "",
           "| Chỉ số | Cấu hình | Lượt A | Lượt B | Δ | Loại | Kết luận |",
           "|---|---|---|---|---|---|---|"]
    o_b = {(d["chi_so"], d["cau_hinh"]): d for d in _doc_csv(b / "chi_so.csv")}
    for o in _doc_csv(a / "chi_so.csv"):
        p = o_b.get((o["chi_so"], o["cau_hinh"]))
        if p is None or (o["gia_tri"] == "" and p["gia_tri"] == ""):
            continue
        if o["tai_lap"] == "tuyet_doi":
            kl = "khớp" if o["gia_tri"] == p["gia_tri"] else "LỆCH"
        elif o["tai_lap"] == "dung_sai" and o["gia_tri"] and p["gia_tri"]:
            kl = "trong ngưỡng" if abs(float(o["gia_tri"]) - float(p["gia_tri"])) <= dung_sai \
                else "NGOÀI NGƯỠNG"
        else:
            kl = "—"
        hong += kl in ("LỆCH", "NGOÀI NGƯỠNG")
        delta = (f"{float(p['gia_tri']) - float(o['gia_tri']):+.4f}"
                 if o["gia_tri"] and p["gia_tri"] else "")
        ra.append(f"| {o['chi_so']} | {o['cau_hinh']} | {o['gia_tri'] or '—'} | "
                  f"{p['gia_tri'] or '—'} | {delta} | {o['tai_lap']} | {kl} |")
    if (a / "tra_loi.jsonl").exists() and (b / "tra_loi.jsonl").exists():
        x = {(d["tap"], d["id"]): d for d in _jsonl(a / "tra_loi.jsonl")}
        y = {(d["tap"], d["id"]): d for d in _jsonl(b / "tra_loi.jsonl")}
        doi = [k for k in x if k in y and x[k]["refused"] != y[k]["refused"]]
        ra += ["", f"## Câu đổi kết quả từ chối ↔ trả lời: {len(doi)} / {len(x)}", ""]
        ra += [f"- `{t}/{i}`: {x[(t, i)]['refusal_reason'] or 'trả lời'} → "
               f"{y[(t, i)]['refusal_reason'] or 'trả lời'} — {x[(t, i)]['question']}"
               for t, i in doi]
    ra += ["", "**TÁI LẬP ĐẠT**" if not hong else f"**TÁI LẬP KHÔNG ĐẠT — {hong} chỗ hỏng**"]
    (a.parent / f"tai_lap_{a.name}_{b.name}.md").write_text("\n".join(ra) + "\n", encoding="utf-8")
    print("\n".join(ra))
    return 0 if not hong else 1


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    lenh = ap.add_subparsers(dest="lenh", required=True)
    p = lenh.add_parser("chay", help="đo toàn bộ, ghi đầu ra thô rồi tính bảng số")
    p.add_argument("cau_hinh", type=Path)
    p.add_argument("--nhan", default=datetime.now().strftime("%Y%m%d-%H%M%S"))
    p.add_argument("--chi-truy-hoi", action="store_true", help="bỏ lượt LLM (0 lượt Gemini)")
    p.add_argument("--gioi-han", type=int, help="chỉ N câu đầu mỗi tập ở lượt LLM (thử khói)")
    t = lenh.add_parser("tai-lap", help="so hai lượt đo độc lập")
    t.add_argument("a", type=Path)
    t.add_argument("b", type=Path)
    r = lenh.add_parser("tinh-lai", help="tính lại từ đầu ra thô, so từng ô với chi_so.csv")
    r.add_argument("thu_muc", type=Path)
    args = ap.parse_args()
    if args.lenh == "chay":
        thu_muc = asyncio.run(chay(args.cau_hinh, args.nhan, chi_truy_hoi=args.chi_truy_hoi,
                                   gioi_han=args.gioi_han))
        print((thu_muc / "tong_hop.md").read_text(encoding="utf-8").split("## Toàn bộ")[0])
        print(f"Kết quả: {thu_muc}")
    elif args.lenh == "tai-lap":
        raise SystemExit(tai_lap(args.a, args.b))
    else:
        raise SystemExit(tinh_lai(args.thu_muc))


if __name__ == "__main__":
    main()
