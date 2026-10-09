"""Hiệu chỉnh ngưỡng từ chối UC025 bằng đường cong, rồi kiểm 30 câu ngoài phạm vi. [R&D]

    cd ai-service && source .venv/bin/activate
    AI_MODE=remote EMBED_URL=http://localhost:8091 python -m tests.eval.hieu_chinh_tu_choi chay
    python -m tests.eval.hieu_chinh_tu_choi quet tests/eval/reports/hieu-chinh_<nhan>.jsonl
    AI_MODE=remote EMBED_URL=http://localhost:8091 python -m tests.eval.hieu_chinh_tu_choi \\
        kiem-30 --san 0.45 --bam-nguon 0.5

BA BƯỚC, HAI TẬP — tách tập chọn ngưỡng khỏi tập nghiệm thu
----------------------------------------------------------
1. ``chay`` — đưa 112 câu bộ vàng (100 có đáp án + 12 ngoài kho) VÀ 30 câu ngoài phạm vi qua đúng
   đường production ``RagAnswerer`` với LLM thật, HAI NGƯỠNG TẮT (sàn toàn tập = 0, bám nguồn = 0)
   — đó là baseline "không ngưỡng": chỉ còn luật trước truy hồi và LLM tự nói ``KHONG_DU_CAN_CU``.
   Ghi điểm thô của từng câu: cosine cao nhất, LLM có từ chối không, groundedness, trích đúng chưa.
2. ``quet`` — quét lưới (sàn × ngưỡng bám nguồn) OFFLINE trên điểm thô của BỘ VÀNG, không gọi lại
   LLM. Hai ngưỡng chỉ quyết "dừng trước LLM" và "huỷ sau LLM", không đổi những gì LLM đã sinh —
   nên áp ngưỡng lên điểm thô cho đúng kết quả như chạy lại, trừ độ ngẫu nhiên của LLM.
3. ``kiem-30`` — chạy THẬT 30 câu ngoài phạm vi với ngưỡng đã chọn. 30 câu này KHÔNG dùng để chọn
   ngưỡng: chọn trên bộ vàng, nghiệm thu trên tập khác (khoá sha256 lúc 23:19 08/10, trước khi viết
   dòng luật nào — ``a1b6fd97…``).

LUẬT CHỌN NGƯỠNG — chốt TRƯỚC khi chạy, không đổi sau khi thấy đường cong
-----------------------------------------------------------------------
Lớp dương = "nên từ chối" (câu bộ vàng có ``can_cu: []``). Trên bộ vàng:

    chọn (sàn, bám nguồn) có F1 của hành vi từ chối CAO NHẤT;
    hoà thì chọn bộ làm MẤT ÍT câu trả lời đúng nhất (câu có đáp án, baseline trả lời và trích
    đúng căn cứ, nay bị từ chối); vẫn hoà thì sàn nhỏ hơn, rồi ngưỡng bám nguồn nhỏ hơn.

Báo cáo cả baseline cạnh bộ đã chọn: độ chính xác + độ phủ của chính hành vi từ chối (đặc tả
UC025, "Ngưỡng chọn từ đường cong hiệu chỉnh, có baseline không ngưỡng để so"). Ba dòng:

- **không ngưỡng** — đúng hệ thống Ngày 9: sàn 0, không cổng bám nguồn, không luật trích dẫn;
- **chỉ luật trích dẫn** — thêm luật cấu trúc "0 trích dẫn ⇒ NOT_COVERED" (thêm giữa phép đo
  08/10, sau khi câu đầu G001 lộ lớp lỗi G004), chưa có ngưỡng nào;
- **hai luật cấu trúc** — thêm "không phải câu trả lời ⇒ NOT_COVERED"
  (``hau_kiem.khong_phai_tra_loi``, thêm 09/10 sau khi ``kiem-30`` trượt N005, N012, N003; mỗi lần
  sửa đều kiểm trên điểm thô của bộ vàng TRƯỚC khi chạy lại 30 câu);
- **đã chọn** — hai luật cấu trúc + hai ngưỡng theo luật chọn ở trên.

Hạn mức: Flash-Lite bậc miễn phí 500 lượt/ngày. ``chay`` ~124 lượt (18 câu luật chặn không gọi),
``kiem-30`` ≤ 12 lượt.
"""

import argparse
import asyncio
import csv
import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.ai.config import Settings
from src.ai.guardrails import normalize_vietnamese_text
from src.ai.inference.clients import KetQuaNhung, tao_embed_client
from src.ai.integrations.llm import CircuitBreaker, LLMChiuLoi, tao_llm_client
from src.ai.rag.answerer import RagAnswerer, truy_hoi_csdl
from src.ai.rag.generate.hau_kiem import khong_phai_tra_loi
from src.ai.rag.generate.loi_nhac import KHONG_DU_CAN_CU
from src.ai.rag.retrieve.hybrid import DoanTimDuoc
from src.ai.schemas import ChatRequest
from tests.eval.bo_vang import de_so

THU_MUC = Path(__file__).resolve().parent
BO_VANG = THU_MUC / "golden_set.jsonl"
NGOAI_PHAM_VI = THU_MUC / "ngoai_pham_vi.jsonl"
BAO_CAO = THU_MUC / "reports"
TENANT = "eeeeeeee-0000-0000-0000-000000000001"  # tenant gốc của gieo_kho.py

LUOI_SAN = [0.0, 0.25, 0.30, 0.35, 0.40, 0.42, 0.44, 0.46, 0.48, 0.50, 0.55, 0.60]
LUOI_BAM_NGUON = [round(x * 0.1, 1) for x in range(11)]


def _jsonl(duong: Path) -> list[dict]:
    return [json.loads(x) for x in duong.read_text(encoding="utf-8").splitlines() if x.strip()]


def _sha(duong: Path) -> str:
    return hashlib.sha256(duong.read_bytes()).hexdigest()


def _dung(doan: DoanTimDuoc, can_cu: list[dict]) -> bool:
    noi_dung = de_so(doan.content)
    return any(doan.file_name == c["file"] and de_so(c["quote"]) in noi_dung for c in can_cu)


def _cac_cau() -> list[dict]:
    cau = []
    for d in _jsonl(BO_VANG):
        cau.append({**d, "tap": "vang", "nen_tu_choi": not d["can_cu"]})
    for d in _jsonl(NGOAI_PHAM_VI):
        cau.append({**d, "can_cu": [], "tap": "ngoai_30", "nen_tu_choi": True})
    return cau


# ── 1. chạy baseline, ghi điểm thô ───────────────────────────────────────────


class _LLMGhiLai:
    """Bọc client LLM để giữ nguyên văn đầu ra — biết LLM có nói KHONG_DU_CAN_CU không."""

    def __init__(self, ben_trong) -> None:
        self._b = ben_trong
        self.model = getattr(ben_trong, "model", "?")
        self.lan_cuoi: str | None = None

    async def chat(self, messages, *, timeout_s: float):
        kq = await self._b.chat(messages, timeout_s=timeout_s)
        self.lan_cuoi = kq.noi_dung
        return kq

    async def aclose(self) -> None:
        await self._b.aclose()


def _dung_answerer(settings: Settings, han_chot_s: float = 10.0):
    lan_cuoi: list[DoanTimDuoc] = []

    async def truy_hoi_ghi_lai(tenant_id: str, cau_hoi: str, nhung: KetQuaNhung, k: int):
        ket_qua = await truy_hoi_csdl(tenant_id, cau_hoi, nhung, k)
        lan_cuoi[:] = ket_qua
        return ket_qua

    async def chua_tu_choi_lan_nao(tenant_id: str, conversation_id: str) -> int:
        return 0  # mỗi câu là một hội thoại mới — đo ngưỡng, không đo chuỗi từ chối

    llm = _LLMGhiLai(tao_llm_client(settings))
    tra_loi = RagAnswerer(
        embed=tao_embed_client(settings),
        # Mạch rộng tay + hạn chót rộng: muốn thấy từng câu, không muốn câu chậm thành suy giảm.
        # Phép đo này đo NỘI DUNG (ngưỡng), không đo độ trễ — độ trễ đo ở thu_llm.py và Ngày 13.
        llm=LLMChiuLoi(llm, CircuitBreaker(nguong_hong=100), han_chot_s=han_chot_s),
        settings=settings,
        truy_hoi=truy_hoi_ghi_lai,
        dem_tu_choi=chua_tu_choi_lan_nao,
    )
    return tra_loi, llm, lan_cuoi


async def _hoi_mot_cau(tra_loi, llm, lan_cuoi, cau: dict, so_lan_thu: int = 3) -> dict:
    for lan in range(so_lan_thu):
        llm.lan_cuoi = None
        lan_cuoi.clear()
        req = ChatRequest(conversation_id=uuid.uuid4(), message=cau["question"])
        bat_dau = time.perf_counter()
        kq = await tra_loi.answer(
            tenant_id=TENANT, question=normalize_vietnamese_text(cau["question"]), request=req
        )
        tong_ms = int((time.perf_counter() - bat_dau) * 1000)
        if not kq.degraded:
            break
        print(f"   suy giảm (lần {lan + 1}) — chờ 30 s rồi thử lại")
        await asyncio.sleep(30)
    theo_id = {d.chunk_id: d for d in lan_cuoi}
    trich = [theo_id[c.chunk_id] for c in kq.citations if c.chunk_id in theo_id]
    return {
        "id": cau["id"],
        "tap": cau["tap"],
        "nen_tu_choi": cau["nen_tu_choi"],
        "ly_do_mong_doi": cau.get("ly_do"),
        "question": cau["question"],
        "refused": kq.refused,
        "refusal_reason": kq.refusal_reason,
        "handoff": kq.handoff,
        "safety_flag": kq.safety_flag,
        "llm_called": kq.llm_called,
        "llm_khong_du_can_cu": bool(
            llm.lan_cuoi and llm.lan_cuoi.strip().startswith(KHONG_DU_CAN_CU)
        ),
        "degraded": kq.degraded,
        "retrieval_top": kq.retrieval_top_score,
        "groundedness": kq.groundedness_score,
        "so_trich_dan": len(kq.citations),
        "truy_hoi_trung": any(_dung(d, cau["can_cu"]) for d in lan_cuoi) if cau["can_cu"] else None,
        "trich_dung_can_cu": any(_dung(d, cau["can_cu"]) for d in trich) if cau["can_cu"] else None,
        "answer": kq.answer,
        "tong_ms": tong_ms,
        "generate_ms": kq.latency_breakdown.get("generate_ms"),
    }


async def chay(
    gian_s: float, chi_tap: str | None, san: float, bam_nguon: float, han_chot_s: float
) -> Path:
    settings = Settings(llm_mode="remote", rag_san_toan_tap=san, rag_nguong_bam_nguon=bam_nguon)
    cac_cau = [c for c in _cac_cau() if chi_tap is None or c["tap"] == chi_tap]
    tra_loi, llm, lan_cuoi = _dung_answerer(settings, han_chot_s)
    BAO_CAO.mkdir(exist_ok=True)
    nhan = datetime.now().strftime("%Y%m%d-%H%M%S")
    ten = "kiem-30" if chi_tap == "ngoai_30" else "hieu-chinh"
    duong = BAO_CAO / f"{ten}_san{san}_bn{bam_nguon}_{nhan}.jsonl"
    meta = {
        "_meta": True, "thoi_diem": datetime.now().isoformat(timespec="seconds"),
        "model": settings.llm_model, "reasoning_effort": settings.llm_reasoning_effort,
        "tenant": TENANT, "san_toan_tap": san, "san_tung_doan": settings.rag_san_tung_doan,
        "nguong_bam_nguon": bam_nguon, "rerank": settings.rerank_enabled, "han_chot_s": han_chot_s,
        "sha_bo_vang": _sha(BO_VANG), "sha_ngoai_pham_vi": _sha(NGOAI_PHAM_VI),
    }
    try:
        with duong.open("w", encoding="utf-8") as f:
            f.write(json.dumps(meta, ensure_ascii=False) + "\n")
            for i, cau in enumerate(cac_cau):
                dong = await _hoi_mot_cau(tra_loi, llm, lan_cuoi, cau)
                f.write(json.dumps(dong, ensure_ascii=False) + "\n")
                f.flush()
                trang_thai = dong["refusal_reason"] or (
                    "suy giảm" if dong["degraded"] else "trả lời"
                )
                print(f"[{i + 1}/{len(cac_cau)}] {cau['id']} top={dong['retrieval_top']} "
                      f"g={dong['groundedness']} → {trang_thai}")
                if dong["llm_called"] and gian_s:
                    await asyncio.sleep(gian_s)
    finally:
        await tra_loi.aclose()
    return duong


# ── 2. quét lưới offline ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class Diem:
    san: float
    bam_nguon: float
    tp: int
    fp: int
    fn: int
    tn: int
    mat_cau_dung: int
    goi_llm: int
    tong: int

    @property
    def chinh_xac(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def do_phu(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        p, r = self.chinh_xac, self.do_phu
        return 2 * p * r / (p + r) if p + r else 0.0


def tu_choi_mo_phong(
    d: dict, san: float, bam_nguon: float, luat_trich_dan: bool = True,
    luat_khong_thong_tin: bool = True,
) -> tuple[bool, bool]:
    """(từ chối?, có gọi LLM?) của một câu khi áp hai ngưỡng lên điểm thô của lượt baseline."""
    if d["refusal_reason"] in ("SAFETY_PROBE", "OUT_OF_SCOPE_DATA"):
        return True, False  # luật trước truy hồi — không phụ thuộc ngưỡng
    top = d["retrieval_top"]
    if top is None or top < san or (d["refusal_reason"] == "NOT_COVERED" and not d["llm_called"]):
        return True, False
    if d["llm_khong_du_can_cu"]:
        return True, True
    if d["degraded"]:
        return False, d["llm_called"]
    if d["refused"]:
        return True, True  # lượt chạy với code đã có luật trích dẫn (kiem-30)
    if luat_trich_dan and d["so_trich_dan"] == 0:
        return True, True
    if luat_khong_thong_tin and khong_phai_tra_loi(d["answer"], d["groundedness"] or 0.0):
        return True, True
    return (d["groundedness"] or 0.0) < bam_nguon, True


def _diem(
    cac_dong: list[dict], san: float, bn: float, luat_trich_dan: bool,
    luat_khong_thong_tin: bool = True,
) -> "Diem":
    tp = fp = fn = tn = mat = goi = 0
    for d in cac_dong:
        tu_choi, goi_llm = tu_choi_mo_phong(d, san, bn, luat_trich_dan, luat_khong_thong_tin)
        goi += goi_llm
        if d["nen_tu_choi"]:
            tp += tu_choi
            fn += not tu_choi
        else:
            fp += tu_choi
            tn += not tu_choi
            # câu trả lời ĐÚNG ở baseline mà nay bị từ chối
            mat += tu_choi and not d["refused"] and bool(d["trich_dung_can_cu"])
    return Diem(san, bn, tp, fp, fn, tn, mat, goi, len(cac_dong))


def quet_luoi(cac_dong: list[dict]) -> list[Diem]:
    return [_diem(cac_dong, san, bn, True) for san in LUOI_SAN for bn in LUOI_BAM_NGUON]


def chon(cac_diem: list[Diem]) -> Diem:
    """Luật chọn đã chốt ở đầu tệp."""
    return min(cac_diem, key=lambda x: (-round(x.f1, 6), x.mat_cau_dung, x.san, x.bam_nguon))


def quet(duong: Path) -> Path:
    dong = [d for d in _jsonl(duong) if not d.get("_meta")]
    meta = next(d for d in _jsonl(duong) if d.get("_meta"))
    vang = [d for d in dong if d["tap"] == "vang"]
    ngoai = [d for d in dong if d["tap"] == "ngoai_30"]
    cac_diem = quet_luoi(vang)
    goc = _diem(vang, 0.0, 0.0, luat_trich_dan=False, luat_khong_thong_tin=False)
    chi_trich_dan = _diem(vang, 0.0, 0.0, luat_trich_dan=True, luat_khong_thong_tin=False)
    hai_luat = _diem(vang, 0.0, 0.0, luat_trich_dan=True, luat_khong_thong_tin=True)
    tot = chon(cac_diem)

    with (duong.with_suffix(".csv")).open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["san", "bam_nguon", "tp", "fp", "fn", "tn", "chinh_xac", "do_phu", "f1",
                    "mat_cau_dung", "ty_le_goi_llm"])
        for x in cac_diem:
            w.writerow([x.san, x.bam_nguon, x.tp, x.fp, x.fn, x.tn, f"{x.chinh_xac:.3f}",
                        f"{x.do_phu:.3f}", f"{x.f1:.3f}", x.mat_cau_dung,
                        f"{x.goi_llm / x.tong:.3f}"])
    _ve(cac_diem, goc, tot, duong.with_suffix(".png"))

    def dong_bang(x: Diem, nhan: str) -> str:
        return (f"| {nhan} | {x.san} | {x.bam_nguon} | {x.tp}/{x.fp}/{x.fn}/{x.tn} | "
                f"{x.chinh_xac:.3f} | {x.do_phu:.3f} | {x.f1:.3f} | {x.mat_cau_dung} | "
                f"{x.goi_llm}/{x.tong} |")

    ngoai_tot = [tu_choi_mo_phong(d, tot.san, tot.bam_nguon)[0] for d in ngoai]
    ngoai_goc = [
        tu_choi_mo_phong(d, 0.0, 0.0, luat_trich_dan=False, luat_khong_thong_tin=False)[0]
        for d in ngoai
    ]
    phan_bo = sorted(
        ((d["retrieval_top"] or 0.0, d["nen_tu_choi"], d["id"]) for d in vang
         if d["refusal_reason"] not in ("SAFETY_PROBE", "OUT_OF_SCOPE_DATA")), reverse=True
    )
    bao_cao = [
        f"# Hiệu chỉnh ngưỡng từ chối UC025 — {duong.stem}",
        "",
        f"- model `{meta['model']}` · reasoning `{meta['reasoning_effort']}` · "
        f"tenant `{meta['tenant']}`",
        f"- bộ vàng sha256 `{meta['sha_bo_vang'][:16]}…` · 30 câu sha256 "
        f"`{meta['sha_ngoai_pham_vi'][:16]}…`",
        f"- sàn từng đoạn {meta['san_tung_doan']} (cố định) · rerank {meta['rerank']}",
        "",
        "## Baseline \"không ngưỡng\" và bộ đã chọn — trên bộ vàng (112 câu, 12 nên từ chối)",
        "",
        "| | sàn | bám nguồn | TP/FP/FN/TN | chính xác | độ phủ | F1 | mất câu đúng | gọi LLM |",
        "|---|---|---|---|---|---|---|---|---|",
        dong_bang(goc, "không ngưỡng (Ngày 9)"),
        dong_bang(chi_trich_dan, "chỉ luật trích dẫn"),
        dong_bang(hai_luat, "hai luật cấu trúc"),
        dong_bang(tot, "**đã chọn**"),
        "",
        f"30 câu ngoài phạm vi (mô phỏng trên điểm thô): baseline từ chối {sum(ngoai_goc)}/30 · "
        f"bộ đã chọn {sum(ngoai_tot)}/30. Số nghiệm thu là `kiem-30` chạy thật.",
        "",
        "## Phân bố cosine cao nhất (bộ vàng, trừ câu luật đã chặn)",
        "",
        "| cosine | nên từ chối | id |",
        "|---|---|---|",
        *[f"| {c:.3f} | {'✓' if n else ''} | {i} |" for c, n, i in phan_bo],
        "",
        f"Bảng lưới đầy đủ: `{duong.with_suffix('.csv').name}` · đường cong: "
        f"`{duong.with_suffix('.png').name}`",
    ]
    ra = duong.with_suffix(".md")
    ra.write_text("\n".join(bao_cao), encoding="utf-8")
    print("\n".join(bao_cao[:14]))
    return ra


def _ve(cac_diem: list[Diem], goc: Diem, tot: Diem, duong: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2))
    for bn in sorted({0.0, tot.bam_nguon}):
        hang = [x for x in cac_diem if x.bam_nguon == bn]
        a.plot([x.san for x in hang], [x.chinh_xac for x in hang], marker="o",
               label=f"chính xác (bám nguồn {bn})")
        a.plot([x.san for x in hang], [x.do_phu for x in hang], marker="s", linestyle="--",
               label=f"độ phủ (bám nguồn {bn})")
    a.axvline(tot.san, color="grey", linewidth=0.8)
    a.set_xlabel("sàn cosine toàn tập")
    a.set_ylabel("hành vi từ chối")
    a.set_ylim(0, 1.05)
    a.legend(fontsize=7)
    a.set_title("Theo sàn cosine")
    for san in sorted({0.0, tot.san}):
        hang = [x for x in cac_diem if x.san == san]
        b.plot([x.bam_nguon for x in hang], [x.f1 for x in hang], marker="o",
               label=f"F1 (sàn {san})")
        b.plot([x.bam_nguon for x in hang], [x.mat_cau_dung / 100 for x in hang], linestyle=":",
               label=f"mất câu đúng /100 (sàn {san})")
    b.axvline(tot.bam_nguon, color="grey", linewidth=0.8)
    b.scatter([goc.bam_nguon], [goc.f1], color="black", zorder=3, label="không ngưỡng")
    b.set_xlabel("ngưỡng bám nguồn")
    b.set_ylim(0, 1.05)
    b.legend(fontsize=7)
    b.set_title("Theo ngưỡng bám nguồn")
    fig.tight_layout()
    fig.savefig(duong, dpi=130)


# ── 3. nghiệm thu 30 câu ─────────────────────────────────────────────────────


def tong_ket_30(duong: Path) -> None:
    dong = [d for d in _jsonl(duong) if not d.get("_meta")]
    rong = [d for d in dong if d["refused"] and d["so_trich_dan"] == 0]
    dung_ly_do = [d for d in dong if d["refusal_reason"] == d["ly_do_mong_doi"]]
    print(f"\nTrả rỗng đúng: {len(rong)}/{len(dong)} · đúng lý do: {len(dung_ly_do)}/{len(dong)} · "
          f"gọi LLM: {sum(d['llm_called'] for d in dong)}")
    for d in dong:
        if d not in rong or d not in dung_ly_do:
            print(f"  {d['id']} mong {d['ly_do_mong_doi']} → {d['refusal_reason']} "
                  f"(trích {d['so_trich_dan']}) | {d['question']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="lenh", required=True)
    c = sub.add_parser("chay", help="baseline không ngưỡng trên bộ vàng + 30 câu, LLM thật")
    c.add_argument("--gian-s", type=float, default=4.5)
    c.add_argument("--han-chot-s", type=float, default=10.0)
    q = sub.add_parser("quet", help="quét lưới ngưỡng offline")
    q.add_argument("jsonl", type=Path)
    k = sub.add_parser("kiem-30", help="chạy thật 30 câu với ngưỡng đã chọn")
    k.add_argument("--san", type=float, required=True)
    k.add_argument("--bam-nguon", type=float, required=True)
    k.add_argument("--gian-s", type=float, default=4.5)
    k.add_argument("--han-chot-s", type=float, default=10.0)
    a = p.parse_args()
    if a.lenh == "chay":
        print(f"Kết quả: {asyncio.run(chay(a.gian_s, None, 0.0, 0.0, a.han_chot_s))}")
    elif a.lenh == "quet":
        print(f"\nBáo cáo: {quet(a.jsonl)}")
    else:
        duong = asyncio.run(chay(a.gian_s, "ngoai_30", a.san, a.bam_nguon, a.han_chot_s))
        tong_ket_30(duong)
        print(f"Kết quả: {duong}")


if __name__ == "__main__":
    main()
