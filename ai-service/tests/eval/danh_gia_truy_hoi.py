"""Harness truy hồi Ngày 6 — recall@5, nDCG@5, MRR@5, paired bootstrap KTC 95%. [R&D]

    cd ai-service && source .venv/bin/activate
    AI_MODE=remote EMBED_URL=http://localhost:<cổng ai-embed> \\
    python -m tests.eval.danh_gia_truy_hoi chay --nhan 1-tenant \\
        tests/eval/configs/e3_dense.yaml tests/eval/configs/e3_sparse.yaml \\
        tests/eval/configs/e3_hybrid.yaml
    python -m tests.eval.danh_gia_truy_hoi so-sanh \\
        tests/eval/reports/1-tenant_e3-hybrid.csv tests/eval/reports/20-tenant_e3-hybrid.csv

Cấu hình ĐẦU TIÊN của ``chay`` là baseline — mọi cấu hình sau được so theo cặp với nó. Kết quả
ghi vào ``tests/eval/reports/`` (không commit; cần giữ thì chép sang ``docs/report/``).

ĐỊNH NGHĨA — chép nguyên vào chương 5
-------------------------------------
Mỗi câu hỏi có ``can_cu`` là tập căn cứ TƯƠNG ĐƯƠNG (``bo_vang.py``). Một đoạn truy hồi được là
ĐÚNG khi ``file_name`` của tài liệu trùng tệp của một căn cứ VÀ nội dung đoạn (sau ``de_so``) chứa
câu trích của căn cứ đó.

- **recall@5** — tỉ lệ câu có ít nhất một đoạn đúng trong top-5. Các căn cứ tương đương nhau nên
  thấy một là thấy câu trả lời (về kỹ thuật là hit-rate@5; gọi recall@5 theo §1.6).
- **nDCG@5** — ``1 / log2(1 + hạng đoạn đúng đầu tiên)``, 0 nếu không có. IDCG = 1 vì mỗi câu chỉ có
  MỘT câu trả lời. Khác recall@5 ở chỗ phân biệt đứng hạng 1 với hạng 5.
- **MRR@5** — ``1 / hạng đoạn đúng đầu tiên``.
- Câu ``can_cu: []`` KHÔNG vào mẫu số (dành cho UC025).

PAIRED BOOTSTRAP
----------------
Hai cấu hình chạy trên CÙNG bộ câu → so theo cặp: rút có hoàn lại N câu, B = 10.000 lần, seed cố
định, mỗi lần tính trung bình hiệu (B − A) trên từng câu. KTC 95% là phân vị 2,5 / 97,5. KTC không
chứa 0 thì chênh lệch không phải nhiễu của việc chọn câu. So theo cặp chặt hơn so hai KTC riêng:
phần biến thiên do độ khó từng câu bị trừ đi. Với 100 câu, một câu = 1 điểm recall@5.

MỖI LƯỢT CHẠY GHI KÈM (``rag-eval.md``: số không kèm cấu hình là số không dùng được)
------------------------------------------------------------------------------------
Toàn bộ cấu hình · commit git · sha256 bộ vàng · số dòng của ``knowledge_chunks`` (MỌI tenant —
cách duy nhất ``ai_app`` thấy quy mô kho khi RLS che các tenant khác) · chỉ mục HNSW có tồn tại
không · tỉ lệ câu mà kế hoạch truy vấn dùng HNSW · p50/p95 thời gian SQL (không gồm nhúng câu hỏi).
Căn cứ nào không có trong kho của tenant đo thì in cảnh báo: câu đó không thể trúng, con số của
nó vô nghĩa.
"""

import argparse
import asyncio
import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import UUID

import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.ai.config import get_settings
from src.ai.db import session as db_session
from src.ai.inference.clients import EmbedClient, tao_embed_client
from src.ai.rag.retrieve import hybrid
from src.ai.rag.retrieve.hybrid import DoanTimDuoc
from src.ai.rag.tsquery import build_tsquery
from tests.eval.bo_vang import de_so

THU_MUC_BAO_CAO = Path(__file__).resolve().parent / "reports"
CHE_DO = ("dense", "sparse", "hybrid")
SO_LAN_BOOTSTRAP = 10_000
SEED = 42


# ── Cấu hình và bộ vàng ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class CauHinh:
    id: str
    mo_ta: str
    bo_vang: Path
    che_do: str
    tenant: UUID
    model: str
    version: str
    k: int = 5
    ung_vien: int = hybrid.UNG_VIEN_MOI_LAN
    ef_search: int = hybrid.EF_SEARCH
    quet_lap: str = "relaxed_order"
    nguon: Path = field(default=Path(), compare=False)


def doc_cau_hinh(duong_dan: Path) -> CauHinh:
    d = yaml.safe_load(duong_dan.read_text(encoding="utf-8"))
    if d.get("che_do") not in CHE_DO:
        raise ValueError(f"{duong_dan}: che_do phải thuộc {CHE_DO}, nhận {d.get('che_do')!r}")
    nhung = d.pop("nhung")
    return CauHinh(
        **{k: v for k, v in d.items() if k not in ("bo_vang", "tenant")},
        bo_vang=(duong_dan.parent / d["bo_vang"]).resolve(),
        tenant=UUID(str(d["tenant"])),
        model=nhung["model"],
        version=nhung["version"],
        nguon=duong_dan,
    )


@dataclass(frozen=True)
class CauVang:
    id: str
    question: str
    can_cu: tuple[tuple[str, str], ...]  # (tệp, câu trích đã de_so)


def doc_bo_vang(duong_dan: Path) -> tuple[list[CauVang], int, str]:
    """Các câu CÓ đáp án, số câu không có đáp án, sha256 của tệp."""
    cac_cau, khong_dap_an = [], 0
    for dong in duong_dan.read_text(encoding="utf-8").splitlines():
        if not dong.strip():
            continue
        m = json.loads(dong)
        if not m["can_cu"]:
            khong_dap_an += 1
            continue
        can_cu = tuple((cc["file"], de_so(cc["quote"])) for cc in m["can_cu"])
        cac_cau.append(CauVang(m["id"], m["question"], can_cu))
    return cac_cau, khong_dap_an, hashlib.sha256(duong_dan.read_bytes()).hexdigest()


# ── Chấm điểm ────────────────────────────────────────────────────────────────


def dung(doan: DoanTimDuoc, can_cu: tuple[tuple[str, str], ...]) -> bool:
    noi_dung = de_so(doan.content)
    return any(doan.file_name == tep and trich in noi_dung for tep, trich in can_cu)


def hang_dung_dau_tien(ket_qua: list[DoanTimDuoc], can_cu) -> int | None:
    return next((h for h, d in enumerate(ket_qua, 1) if dung(d, can_cu)), None)


def diem_cau(hang: int | None, k: int) -> dict[str, float]:
    if hang is None or hang > k:
        return {"trung": 0.0, "ndcg": 0.0, "rr": 0.0}
    return {"trung": 1.0, "ndcg": 1 / math.log2(1 + hang), "rr": 1 / hang}


def bootstrap_cap(
    a: list[float], b: list[float], *, so_lan: int = SO_LAN_BOOTSTRAP, seed: int = SEED
) -> tuple[float, float, float]:
    """``(hiệu trung bình B − A, cận dưới, cận trên)`` của KTC 95% — paired bootstrap."""
    hieu = [y - x for x, y in zip(a, b, strict=True)]
    n = len(hieu)
    rng = random.Random(seed)
    mau = sorted(sum(rng.choices(hieu, k=n)) / n for _ in range(so_lan))
    return sum(hieu) / n, mau[round(0.025 * (so_lan - 1))], mau[round(0.975 * (so_lan - 1))]


def _phan_vi(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(p * len(xs)) - 1)]


# ── Chạy ─────────────────────────────────────────────────────────────────────


@dataclass
class KetQuaCauHinh:
    cau_hinh: CauHinh
    dong: list[dict]  # một dòng CSV mỗi câu
    thieu_can_cu: list[str]  # id câu có căn cứ không nằm trong kho của tenant đo

    def trung_binh(self, cot: str) -> float:
        return statistics.fmean(float(d[cot]) for d in self.dong)


async def _nhung_cau_hoi(
    embed: EmbedClient, cac_cau: list[CauVang], model: str, version: str
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for dau in range(0, len(cac_cau), 32):
        kq = await embed.embed_batch([c.question for c in cac_cau[dau : dau + 32]])
        if (kq.model_id, kq.model_version) != (model, version):
            raise RuntimeError(
                f"ai-embed đang phục vụ {kq.model_id}/{kq.model_version}, cấu hình ghi "
                f"{model}/{version} — vector câu hỏi và vector kho sẽ thuộc hai không gian "
                "khác nhau"
            )
        vectors += kq.vectors
    return vectors


async def _kiem_can_cu_trong_kho(
    factory: async_sessionmaker, ch: CauHinh, cac_cau: list[CauVang]
) -> list[str]:
    async with db_session.get_tenant_session(str(ch.tenant), factory) as s:
        dong = await s.execute(
            text(
                "SELECT d.file_name, c.content FROM knowledge.knowledge_chunks c"
                " JOIN knowledge.knowledge_documents d ON d.id = c.document_id"
                " WHERE d.status = 'READY' AND c.embedding_model = :m"
                " AND c.embedding_version = :v"
            ),
            {"m": ch.model, "v": ch.version},
        )
        kho = [(r.file_name, de_so(r.content)) for r in dong]
    return [
        c.id
        for c in cac_cau
        if not all(any(t == tep and trich in nd for t, nd in kho) for tep, trich in c.can_cu)
    ]


async def chay_cau_hinh(
    factory: async_sessionmaker,
    ch: CauHinh,
    cac_cau: list[CauVang],
    vectors: list[list[float]] | None,
) -> KetQuaCauHinh:
    async def mot_cau(i: int) -> tuple[list[DoanTimDuoc], float, bool]:
        vector = vectors[i] if ch.che_do != "sparse" else None
        tsquery = build_tsquery(cac_cau[i].question) if ch.che_do != "dense" else None
        async with db_session.get_tenant_session(str(ch.tenant), factory) as s:
            dau = time.perf_counter()
            ket_qua = await hybrid.tim_kiem_lai(
                s,
                vector=vector,
                tsquery=tsquery,
                embedding_model=ch.model,
                embedding_version=ch.version,
                k=ch.k,
                ung_vien=ch.ung_vien,
                ef_search=ch.ef_search,
                quet_lap=ch.quet_lap,
            )
            ms = (time.perf_counter() - dau) * 1000
            # EXPLAIN trong CÙNG transaction, cùng tham số HNSW và cùng bind parameter.
            ke_hoach = await s.execute(
                text("EXPLAIN " + hybrid._SQL_TIM_LAI.text),
                hybrid.tham_so_cau_lenh(
                    vector, tsquery, ch.model, ch.version, ch.k, ch.ung_vien
                ),
            )
            dung_hnsw = any("ix_chunk_embedding" in r[0] for r in ke_hoach)
        return ket_qua, ms, dung_hnsw

    await mot_cau(0)  # làm nóng: kết nối, nạp thư viện pgvector, bộ đệm — không tính giờ
    dong = []
    for i, cau in enumerate(cac_cau):
        ket_qua, ms, dung_hnsw = await mot_cau(i)
        hang = hang_dung_dau_tien(ket_qua, cau.can_cu)
        doan_dung = ket_qua[hang - 1] if hang else None
        dong.append(
            {
                "id": cau.id,
                **diem_cau(hang, ch.k),
                "hang_dung": hang or "",
                "hang_vector": (doan_dung.hang_vector or "") if doan_dung else "",
                "hang_tu_khoa": (doan_dung.hang_tu_khoa or "") if doan_dung else "",
                "ms": round(ms, 2),
                "dung_hnsw": int(dung_hnsw),
                "top_k": json.dumps([f"{d.file_name}#{d.chunk_index}" for d in ket_qua]),
            }
        )
    return KetQuaCauHinh(ch, dong, await _kiem_can_cu_trong_kho(factory, ch, cac_cau))


async def _thong_tin_kho(factory: async_sessionmaker, tenant: UUID) -> dict[str, str]:
    async with db_session.get_tenant_session(str(tenant), factory) as s:
        so_dong = (
            await s.execute(
                text(
                    "SELECT n_live_tup FROM pg_stat_user_tables"
                    " WHERE relid = 'knowledge.knowledge_chunks'::regclass"
                )
            )
        ).scalar_one()
        chi_muc = (
            await s.execute(
                text(
                    "SELECT indexdef FROM pg_indexes WHERE schemaname = 'knowledge'"
                    " AND indexname = 'ix_chunk_embedding'"
                )
            )
        ).scalar_one_or_none()
    return {"so_dong_moi_tenant": str(so_dong), "chi_muc_hnsw": chi_muc or "KHÔNG CÓ"}


def _commit_git() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip() + (" (+ thay đổi chưa commit)" if _co_thay_doi() else "")
    except (OSError, subprocess.CalledProcessError):
        return "?"


def _co_thay_doi() -> bool:
    return bool(
        subprocess.run(["git", "status", "--porcelain", "--", "src", "tests/eval"],
                       capture_output=True, text=True).stdout.strip()
    )


# ── Báo cáo ──────────────────────────────────────────────────────────────────


def _ghi_csv(duong_dan: Path, dong: list[dict]) -> None:
    with duong_dan.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(dong[0]))
        w.writeheader()
        w.writerows(dong)


def _dong_so_sanh(ten: str, a: list[dict], b: list[dict]) -> str:
    theo_id = {d["id"]: d for d in b}
    chung = [d for d in a if d["id"] in theo_id]
    o = []
    for cot in ("trung", "ndcg"):
        x = [float(d[cot]) for d in chung]
        y = [float(theo_id[d["id"]][cot]) for d in chung]
        hieu, duoi, tren = bootstrap_cap(x, y)
        dau = "" if duoi <= 0 <= tren else " ✱"
        o.append(f"{hieu * 100:+.1f} [{duoi * 100:+.1f}; {tren * 100:+.1f}]{dau}")
    return f"| {ten} | {len(chung)} | {o[0]} | {o[1]} |"


def tong_hop(
    cac_ket_qua: list[KetQuaCauHinh], meta: dict[str, str], khong_dap_an: int
) -> str:
    k = cac_ket_qua[0].cau_hinh.k
    dong = [f"# Truy hồi — {meta['nhan']}", ""]
    dong += [f"- **{khoa}:** {gia_tri}" for khoa, gia_tri in meta.items() if khoa != "nhan"]
    dong += [
        f"- **Câu có đáp án (mẫu số):** {len(cac_ket_qua[0].dong)} · không đáp án: {khong_dap_an}",
        "",
        f"| Cấu hình | Chế độ | recall@{k} | nDCG@{k} | MRR@{k} | p50 ms | p95 ms | dùng HNSW |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for kq in cac_ket_qua:
        ch, ms = kq.cau_hinh, [float(d["ms"]) for d in kq.dong]
        dong.append(
            f"| `{ch.id}` | {ch.che_do} | {kq.trung_binh('trung'):.3f} | "
            f"{kq.trung_binh('ndcg'):.3f} | {kq.trung_binh('rr'):.3f} | "
            f"{_phan_vi(ms, 0.5):.1f} | {_phan_vi(ms, 0.95):.1f} | "
            f"{kq.trung_binh('dung_hnsw') * 100:.0f}% |"
        )
    if len(cac_ket_qua) > 1:
        goc = cac_ket_qua[0]
        dong += [
            "",
            f"So theo cặp với baseline `{goc.cau_hinh.id}` — hiệu (điểm %) [KTC 95%], "
            f"✱ = KTC không chứa 0 (paired bootstrap, B = {SO_LAN_BOOTSTRAP}, seed {SEED}):",
            "",
            f"| Cấu hình | N | Δ recall@{k} | Δ nDCG@{k} |",
            "|---|---|---|---|",
        ]
        dong += [_dong_so_sanh(f"`{kq.cau_hinh.id}`", goc.dong, kq.dong) for kq in cac_ket_qua[1:]]
    dong += ["", "Cấu hình đầy đủ:", ""]
    for kq in cac_ket_qua:
        ch = kq.cau_hinh
        dong.append(
            f"- `{ch.id}` ({ch.nguon.name}): {ch.mo_ta} — tenant `{ch.tenant}`, "
            f"{ch.model}/{ch.version}, k={ch.k}, ứng viên={ch.ung_vien}, "
            f"ef_search={ch.ef_search}, iterative_scan={ch.quet_lap}"
        )
        if kq.thieu_can_cu:
            dong.append(f"  - ⚠️ căn cứ KHÔNG có trong kho, không thể trúng: {kq.thieu_can_cu}")
    return "\n".join(dong) + "\n"


async def chay(
    cac_duong_dan: list[Path],
    *,
    nhan: str,
    factory: async_sessionmaker,
    embed: EmbedClient,
    thu_muc: Path = THU_MUC_BAO_CAO,
) -> tuple[list[KetQuaCauHinh], str]:
    cac_cau_hinh = [doc_cau_hinh(p) for p in cac_duong_dan]
    if len({ch.bo_vang for ch in cac_cau_hinh}) != 1:
        raise ValueError("Mọi cấu hình của một lượt phải dùng CÙNG bộ vàng — so theo cặp cần vậy.")
    cac_cau, khong_dap_an, sha = doc_bo_vang(cac_cau_hinh[0].bo_vang)
    if not cac_cau:
        raise ValueError(f"{cac_cau_hinh[0].bo_vang} chưa có câu nào có đáp án.")

    vector_theo_model: dict[tuple[str, str], list[list[float]]] = {}
    cac_ket_qua = []
    for ch in cac_cau_hinh:
        khoa = (ch.model, ch.version)
        if ch.che_do != "sparse" and khoa not in vector_theo_model:
            vector_theo_model[khoa] = await _nhung_cau_hoi(embed, cac_cau, *khoa)
        cac_ket_qua.append(
            await chay_cau_hinh(factory, ch, cac_cau, vector_theo_model.get(khoa))
        )

    meta = {
        "nhan": nhan,
        "thời điểm": datetime.now().isoformat(timespec="seconds"),
        "commit": _commit_git(),
        "bộ vàng": f"{cac_cau_hinh[0].bo_vang.name} · sha256 `{sha}`",
        **await _thong_tin_kho(factory, cac_cau_hinh[0].tenant),
    }
    bao_cao = tong_hop(cac_ket_qua, meta, khong_dap_an)
    thu_muc.mkdir(parents=True, exist_ok=True)
    for kq in cac_ket_qua:
        _ghi_csv(thu_muc / f"{nhan}_{kq.cau_hinh.id}.csv", kq.dong)
    (thu_muc / f"{nhan}_tong_hop.md").write_text(bao_cao, encoding="utf-8")
    return cac_ket_qua, bao_cao


def so_sanh(a: Path, b: Path) -> str:
    """Paired bootstrap giữa hai CSV — ví dụ cùng cấu hình ở kho 1 tenant và kho 20 tenant."""
    doc = [list(csv.DictReader(p.open(encoding="utf-8"))) for p in (a, b)]
    return "\n".join(
        [
            f"A = `{a.name}` · B = `{b.name}` — hiệu B − A (điểm %) [KTC 95%],"
            " ✱ = KTC không chứa 0",
            "",
            "| So sánh | N | Δ recall@5 | Δ nDCG@5 |",
            "|---|---|---|---|",
            _dong_so_sanh("B − A", *doc),
        ]
    )


async def _main(args: argparse.Namespace) -> None:
    engine = db_session.tao_engine(args.dsn)
    embed = tao_embed_client(get_settings())
    try:
        _, bao_cao = await chay(
            args.cau_hinh, nhan=args.nhan, factory=db_session.tao_session_factory(engine),
            embed=embed,
        )
        print(bao_cao)
    finally:
        await embed.aclose()
        await engine.dispose()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    lenh = ap.add_subparsers(dest="lenh", required=True)
    p_chay = lenh.add_parser("chay", help="chạy các cấu hình (cấu hình đầu là baseline)")
    p_chay.add_argument("cau_hinh", nargs="+", type=Path)
    p_chay.add_argument("--nhan", default=datetime.now().strftime("%Y%m%d-%H%M%S"))
    p_chay.add_argument("--dsn", help="DSN postgresql+psycopg:// của ai_app (mặc định: .env)")
    p_ss = lenh.add_parser("so-sanh", help="paired bootstrap giữa hai CSV kết quả")
    p_ss.add_argument("a", type=Path)
    p_ss.add_argument("b", type=Path)
    args = ap.parse_args()
    if args.lenh == "so-sanh":
        print(so_sanh(args.a, args.b))
    else:
        asyncio.run(_main(args))


if __name__ == "__main__":
    main()
