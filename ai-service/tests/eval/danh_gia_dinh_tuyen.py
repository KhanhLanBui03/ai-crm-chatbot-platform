"""So các luật định tuyến câu dưới ngưỡng τ trên CÙNG đầu ra của ai-classify. [R&D]

    docker compose -f inference/compose.inference.yml up -d ai-classify
    cd ai-service && source .venv/bin/activate
    python -m tests.eval.danh_gia_dinh_tuyen

Cách đo và tiêu chí chọn chốt TRƯỚC khi chạy:
``docs/report/dinh-tuyen-duoi-nguong-2026-10-15.md`` §1.
Không tạo lượt chat, không gọi LLM, không ghi CSDL. Mọi tệp dữ liệu chỉ đọc.

Mỗi câu gọi ai-classify ĐÚNG MỘT lần; mọi phương án chấm trên cùng bảy xác suất đó, nên chênh
lệch giữa các phương án chỉ đến từ luật chọn nhánh. Phương án A là luật CŨ của ``decide_route``
(trước ADR-0035), chép nguyên ở đây làm mốc so; script kiểm thêm rằng ``decide_route`` production
cho đúng kết quả của D trên mọi câu.
Ghi JSON từng câu vào ``tests/eval/reports/dinh_tuyen_<ngày>.json`` (không commit).
"""

from __future__ import annotations

import asyncio
import collections
import json
import time
from collections.abc import Callable
from pathlib import Path

from src.ai.config import get_settings
from src.ai.inference.clients import RemoteClassifyClient, aclose_http_clients
from src.ai.orchestrator.router import Branch, Classification, decide_route

_EVAL = Path(__file__).resolve().parent
_REPO = _EVAL.parents[2]

# ── Ba ô của bản đồ luồng (báo cáo §1.1) ─────────────────────────────────────
Y_DINH_THEO_O: dict[str, tuple[str, ...]] = {
    "giua": ("KB_SEARCH", "PRICING_POLICY", "COMPLAINT_SUPPORT", "TECH_ERROR"),
    "phai": ("HANDOFF_HUMAN", "BUYING_INTENT"),
    "trai": ("GREETING",),
}
O_CUA_Y_DINH = {yd: o for o, ds in Y_DINH_THEO_O.items() for yd in ds}
O_CUA_NHANH = {
    Branch.RAG: "giua",
    Branch.HANDOFF: "phai",
    Branch.TOOL_CALL: "phai",
    Branch.SMALL_TALK: "trai",
    Branch.CLARIFY: "hoi_lai",
}

# ── Các phương án (báo cáo §1.2) — thuần hàm: (kết quả ai-classify, τ, ngưỡng đi nhanh) → nhánh ──
LuatDinhTuyen = Callable[[dict, float, float], Branch]


def _r0(_c: dict, _tau: float, _nhanh: float) -> Branch:
    return Branch.RAG


def _a(c: dict, tau: float, nhanh: float) -> Branch:
    """Luật CŨ của ``decide_route`` (tới 15/10/2026, trước ADR-0035): ngưỡng trên ý định đầu."""
    yd, conf = c["intent"], float(c["confidence"])
    if yd == "HANDOFF_HUMAN" and conf >= tau:
        return Branch.HANDOFF
    if conf < tau:
        return Branch.CLARIFY
    if yd == "GREETING" and conf >= nhanh:
        return Branch.SMALL_TALK
    if yd == "BUYING_INTENT":
        return Branch.TOOL_CALL
    return Branch.RAG


def _production(c: dict, tau: float, nhanh: float) -> Branch:
    return decide_route(
        Classification(c["intent"], float(c["confidence"]), c.get("model_id"),
                       probabilities=c.get("probabilities")),
        fast_path_threshold=nhanh,
        abstention_threshold=tau,
    ).branch


def _b(c: dict, tau: float, nhanh: float) -> Branch:
    nhanh_a = _a(c, tau, nhanh)
    return Branch.RAG if nhanh_a is Branch.CLARIFY else nhanh_a


def _cong_theo_o(c: dict, tau: float, nhanh: float, *, khong_o_nao: Branch) -> Branch:
    p = c["probabilities"]
    g = {o: sum(p.get(yd, 0.0) for yd in ds) for o, ds in Y_DINH_THEO_O.items()}
    if g["phai"] >= tau:
        xin_nguoi = p.get("HANDOFF_HUMAN", 0.0) >= p.get("BUYING_INTENT", 0.0)
        return Branch.HANDOFF if xin_nguoi else Branch.TOOL_CALL
    if g["trai"] >= nhanh:
        return Branch.SMALL_TALK
    if g["giua"] >= tau:
        return Branch.RAG
    # Giữ đúng hành vi A: câu chào từ τ tới dưới ngưỡng đi nhanh rơi xuống RAG (router.py:127).
    if g["trai"] >= tau:
        return Branch.RAG
    return khong_o_nao


def _d(c: dict, tau: float, nhanh: float) -> Branch:
    return _cong_theo_o(c, tau, nhanh, khong_o_nao=Branch.CLARIFY)


def _e(c: dict, tau: float, nhanh: float) -> Branch:
    return _cong_theo_o(c, tau, nhanh, khong_o_nao=Branch.RAG)


def _f(c: dict, tau: float, nhanh: float) -> Branch:
    """THÊM SAU KHI THẤY SỐ (báo cáo §3) — số của F trên H và G+ là số LẠC QUAN.

    Như D; không ô nào đạt τ thì xem ô lớn nhất: ô phải ⇒ hỏi lại (khách có thể đang xin người hay
    muốn mua — hỏi lại rẻ hơn bỏ qua họ), còn lại ⇒ RAG (lối từ chối UC025 làm lưới). Không thêm
    tham số nào ngoài τ đã chốt.
    """
    nhanh_d = _d(c, tau, nhanh)
    if nhanh_d is not Branch.CLARIFY:
        return nhanh_d
    p = c["probabilities"]
    g = {o: sum(p.get(yd, 0.0) for yd in ds) for o, ds in Y_DINH_THEO_O.items()}
    return Branch.CLARIFY if max(g, key=g.get) == "phai" else Branch.RAG


PHUONG_AN: dict[str, LuatDinhTuyen] = {
    "R0": _r0, "A": _a, "B": _b, "D": _d, "E": _e,
    "F*": _f,  # * = thêm sau khi thấy số
}


# ── Dữ liệu (báo cáo §1.3) ───────────────────────────────────────────────────


def _doc(path: Path) -> list[dict]:
    return [json.loads(dong) for dong in path.open(encoding="utf-8") if dong.strip()]


def nap_du_lieu() -> dict[str, list[dict]]:
    """Mỗi tập: danh sách {id, text, o_dung} — ``o_dung`` None nghĩa là không có nhãn ô."""
    h = [
        {"id": r["id"], "text": r["text"], "o_dung": O_CUA_Y_DINH[r["intent"]],
         "intent": r["intent"], "variant": r["variant"]}
        for r in _doc(_REPO / "data" / "intent_test_human.jsonl")
    ]
    vang = _doc(_EVAL / "golden_set.jsonl")
    return {
        "H": h,
        "G+": [{"id": r["id"], "text": r["question"], "o_dung": "giua"}
               for r in vang if r["can_cu"]],
        "G0": [{"id": r["id"], "text": r["question"], "o_dung": None}
               for r in vang if not r["can_cu"]],
        "N": [{"id": r["id"], "text": r["question"], "o_dung": None, "nhom": r["nhom"]}
              for r in _doc(_EVAL / "ngoai_pham_vi.jsonl")],
        "T": [{"id": r["id"], "text": r["question"], "o_dung": None, "nhom": r["nhom"]}
              for r in _doc(_EVAL / "tu_choi_mo_rong.jsonl")],
    }


async def phan_loai_tat_ca(cau: list[str]) -> dict[str, dict]:
    client = RemoteClassifyClient()
    ket_qua: dict[str, dict] = {}
    for text in dict.fromkeys(cau):  # bỏ trùng, giữ thứ tự
        ket_qua[text] = await client.classify(text)
    await aclose_http_clients()
    return ket_qua


# ── Chấm (báo cáo §1.4) ──────────────────────────────────────────────────────


def cham_tap(rows: list[dict], kq: dict[str, dict], luat: LuatDinhTuyen, tau: float,
             nhanh: float) -> dict:
    o_du_doan = [O_CUA_NHANH[luat(kq[r["text"]], tau, nhanh)] for r in rows]
    n = len(rows)
    phan_bo = collections.Counter(o_du_doan)
    out: dict = {"n": n, "phan_bo": dict(phan_bo)}
    if rows and rows[0]["o_dung"] is not None:
        dung = sum(1 for r, o in zip(rows, o_du_doan, strict=True) if o == r["o_dung"])
        hoi_lai = phan_bo.get("hoi_lai", 0)
        sai = n - dung - hoi_lai
        out |= {"dung": dung, "sai": sai, "hoi_lai": hoi_lai,
                "chinh_xac_khi_khong_hoi_lai": dung / (dung + sai) if dung + sai else None,
                "khong_goi_llm": 1 - phan_bo.get("giua", 0) / n}
        if "intent" in rows[0]:
            xin_nguoi = [o for r, o in zip(rows, o_du_doan, strict=True)
                         if r["intent"] == "HANDOFF_HUMAN"]
            out["xin_nguoi_bot_tu_tra_loi"] = sum(1 for o in xin_nguoi if o in ("giua", "trai"))
            out["xin_nguoi_hoi_lai"] = xin_nguoi.count("hoi_lai")
            out["tri_thuc_day_cho_nhan_vien"] = sum(
                1 for r, o in zip(rows, o_du_doan, strict=True)
                if r["o_dung"] == "giua" and o == "phai")
            out["sai_theo_y_dinh"] = dict(collections.Counter(
                f"{r['intent']}->{o}" for r, o in zip(rows, o_du_doan, strict=True)
                if o not in (r["o_dung"], "hoi_lai")))
    return out


def _pct(x: int, n: int) -> str:
    return f"{x} ({x / n:.0%})"


def in_bang(du_lieu: dict[str, list[dict]], kq: dict[str, dict], tau: float, nhanh: float) -> dict:
    tong: dict = {}
    print(f"\n## Tập H — {len(du_lieu['H'])} câu người thật, τ = {tau}\n")
    print("| Phương án | Đúng ô | Sai ô | Hỏi lại | Chính xác khi không hỏi lại "
          "| Xin người → bot tự trả lời | Xin người → hỏi lại | Tri thức → nhân viên "
          "| Ước tính không gọi LLM |")
    print("|---|---|---|---|---|---|---|---|---|")
    for ma, luat in PHUONG_AN.items():
        m = cham_tap(du_lieu["H"], kq, luat, tau, nhanh)
        tong.setdefault(ma, {})["H"] = m
        n = m["n"]
        cx = m["chinh_xac_khi_khong_hoi_lai"]
        print(f"| {ma} | {_pct(m['dung'], n)} | {_pct(m['sai'], n)} | {_pct(m['hoi_lai'], n)} "
              f"| {cx:.3f} | {m['xin_nguoi_bot_tu_tra_loi']}/28 | {m['xin_nguoi_hoi_lai']}/28 "
              f"| {m['tri_thuc_day_cho_nhan_vien']}/116 | {m['khong_goi_llm']:.0%} |")

    print("\n## Tập G+ — 100 câu bộ vàng có đáp án (ô đúng: giữa)\n")
    print("| Phương án | Tới RAG | Hỏi lại | Sai ô |")
    print("|---|---|---|---|")
    for ma, luat in PHUONG_AN.items():
        m = cham_tap(du_lieu["G+"], kq, luat, tau, nhanh)
        tong[ma]["G+"] = m
        n = m["n"]
        print(f"| {ma} | {_pct(m['dung'], n)} | {_pct(m['hoi_lai'], n)} | {_pct(m['sai'], n)} |")

    print("\n## Tập không có đáp án — phân bố ô (giữa · phải · trái · hỏi lại)\n")
    print("| Phương án | G0 (12) | N (30) | T (38) |")
    print("|---|---|---|---|")
    for ma, luat in PHUONG_AN.items():
        o_tap = []
        for tap in ("G0", "N", "T"):
            m = cham_tap(du_lieu[tap], kq, luat, tau, nhanh)
            tong[ma][tap] = m
            pb = m["phan_bo"]
            o_tap.append(" · ".join(str(pb.get(o, 0)) for o in ("giua", "phai", "trai", "hoi_lai")))
        print(f"| {ma} | " + " | ".join(o_tap) + " |")
    return tong


def in_sai_theo_y_dinh(tong: dict) -> None:
    print("\n## Tập H — câu đi SAI ô, theo nhãn người gán → ô đã đi\n")
    for ma in PHUONG_AN:
        sai = tong[ma]["H"]["sai_theo_y_dinh"]
        print(f"- **{ma}**: " + (", ".join(f"{k} {v}" for k, v in sorted(sai.items())) or "không"))


def in_do_nhay(du_lieu: dict[str, list[dict]], kq: dict[str, dict], nhanh: float) -> dict:
    """Chỉ để xem kết luận có đổi khi τ đổi — KHÔNG dùng để chọn τ (báo cáo §1.5)."""
    print("\n## Độ nhạy theo τ — H: đúng · sai · hỏi lại | G+: tới RAG\n")
    print("| τ | " + " | ".join(ma for ma in PHUONG_AN if ma != "R0") + " |")
    print("|---|" + "---|" * (len(PHUONG_AN) - 1))
    do_nhay: dict = {}
    for tau in (0.50, 0.55, 0.60, 0.65, 0.70, 0.80, 0.90):
        o = []
        for ma, luat in PHUONG_AN.items():
            if ma == "R0":
                continue
            h = cham_tap(du_lieu["H"], kq, luat, tau, nhanh)
            g = cham_tap(du_lieu["G+"], kq, luat, tau, nhanh)
            do_nhay.setdefault(str(tau), {})[ma] = {"H": h, "G+": g}
            o.append(f"{h['dung']} · {h['sai']} · {h['hoi_lai']} \\| {g['dung']}")
        print(f"| {tau:.2f} | " + " | ".join(o) + " |")
    return do_nhay


def kiem_dau_ra(kq: dict[str, dict]) -> None:
    """Kiểm giả định của phương án D/E: bảy xác suất cộng ≈ 1 và nhãn = xác suất lớn nhất."""
    lech_tong = [t for t, c in kq.items() if abs(sum(c["probabilities"].values()) - 1) > 0.01]
    lech_nhan = [t for t, c in kq.items()
                 if max(c["probabilities"], key=c["probabilities"].get) != c["intent"]]
    tang = collections.Counter(c.get("tier_used") for c in kq.values())
    # ADR-0035: production phải là D — và D chỉ được đổi những câu mà luật cũ (A) hỏi lại.
    lech_d = [t for t, c in kq.items() if _production(c, 0.65, 0.85) is not _d(c, 0.65, 0.85)]
    a_doi = [t for t, c in kq.items()
             if _a(c, 0.65, 0.85) is not Branch.CLARIFY
             and _d(c, 0.65, 0.85) is not _a(c, 0.65, 0.85)]
    print(f"decide_route production khác D: {len(lech_d)} câu · D đổi quyết định A đã đưa ra: "
          f"{len(a_doi)} câu (cả hai phải là 0)")
    print(f"\nĐầu ra ai-classify: {len(kq)} câu khác nhau · tầng {dict(tang)} · "
          f"tổng xác suất lệch 1 quá 0,01: {len(lech_tong)} · nhãn khác xác suất lớn nhất: "
          f"{len(lech_nhan)}")


async def main() -> None:
    s = get_settings()
    tau, nhanh = s.router_abstention_threshold, s.fast_path_threshold
    du_lieu = nap_du_lieu()
    t0 = time.perf_counter()
    kq = await phan_loai_tat_ca([r["text"] for rows in du_lieu.values() for r in rows])
    print(f"ai-classify {RemoteClassifyClient().base_url} · {time.perf_counter() - t0:.1f} s")
    kiem_dau_ra(kq)
    tong = in_bang(du_lieu, kq, tau, nhanh)
    in_sai_theo_y_dinh(tong)
    do_nhay = in_do_nhay(du_lieu, kq, nhanh)

    ra = _EVAL / "reports" / f"dinh_tuyen_{time.strftime('%Y-%m-%d')}.json"
    ra.parent.mkdir(exist_ok=True)
    ra.write_text(json.dumps(
        {"tau": tau, "nguong_di_nhanh": nhanh, "ket_qua": tong, "do_nhay": do_nhay,
         "phan_loai": {t: kq[t] for t in kq}},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nJSON: {ra.relative_to(_REPO)}")


if __name__ == "__main__":
    asyncio.run(main())
