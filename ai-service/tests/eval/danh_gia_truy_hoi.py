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

TÍNH BẰNG ``ranx`` (Ngày 13), CÔNG THỨC TỰ CÀI GIỮ LÀM KIỂM CHÉO
----------------------------------------------------------------
Số in ra là của ``ranx`` (``hit_rate@k`` · ``ndcg@k`` · ``mrr@k``). Mã hoá theo LỚP TƯƠNG ĐƯƠNG: mỗi
câu có đúng MỘT tài liệu liên quan tên ``DUNG``, đặt ở hạng của đoạn đúng đầu tiên; các đoạn còn lại
mang mã riêng không liên quan. Cách này khớp định nghĩa "trúng một căn cứ là đủ, IDCG = 1" ở trên.
Đưa MỌI đoạn khớp căn cứ vào qrels thì ``ranx`` sẽ tính IDCG trên nhiều tài liệu liên quan — nDCG
khác định nghĩa đã dùng từ Ngày 6 và không còn so được với số cũ. ``diem_cau`` vẫn chạy song song:
lệch quá ``SAI_SO_KIEM_CHEO`` là dừng — hai cách tính khác nhau ra hai số khác nhau là lỗi, không
phải chọn số đẹp hơn.

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

XẾP LẠI — NGÀY 15
-----------------
Cấu hình có khối ``rerank:`` thì lấy ``ung_vien`` đoạn đầu của RRF, gửi ai-rerank xếp lại rồi mới
cắt top-k — ``khi: moi_cau`` xếp lại mọi câu, ``khi: mo_ho`` chỉ khi ``needs_rerank`` (đúng đường
production). Danh tính ai-rerank (``/v1/model``) phải khớp ``rerank.model``/``rerank.version``, lệch
là dừng. Báo cáo thêm: tỉ lệ lượt mơ hồ · p50/p95 thời gian một lượt xếp lại (gồm HTTP) · trần
recall@k khi xếp hoàn hảo · số câu trần mà cổng mơ hồ bỏ qua · số câu cứu được / bị đẩy ra.

    AI_MODE=remote EMBED_URL=http://localhost:8091 INFERENCE_RERANK_URL=http://localhost:8082 \\
    python -m tests.eval.danh_gia_truy_hoi chay --nhan n15 tests/eval/configs/e3_hybrid.yaml \\
        tests/eval/configs/n15_rerank_12_moi_cau.yaml ...

``xuat-cap`` ghi tệp cặp cho cổng parity của cross-encoder (notebook 07): mỗi câu có đáp án một
dòng, ``--ung-vien`` đoạn đầu của RRF đúng thứ tự kèm nhãn ``dung``.

    python -m tests.eval.danh_gia_truy_hoi xuat-cap tests/eval/configs/e3_hybrid.yaml \\
        --ung-vien 20 --ra tests/eval/rerank_cap_100x20.jsonl
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

import httpx
import yaml
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.ai.config import get_settings
from src.ai.db import session as db_session
from src.ai.inference.clients import (
    EmbedClient,
    RemoteRerankClient,
    RerankClient,
    tao_embed_client,
)
from src.ai.rag.rerank import quyet_dinh
from src.ai.rag.retrieve import hybrid
from src.ai.rag.retrieve.hybrid import DoanTimDuoc
from src.ai.rag.tsquery import build_tsquery
from tests.eval.bo_vang import de_so

THU_MUC_BAO_CAO = Path(__file__).resolve().parent / "reports"
CHE_DO = ("dense", "sparse", "hybrid")
KHI_XEP_LAI = ("moi_cau", "mo_ho")
SO_LAN_BOOTSTRAP = 10_000
SEED = 42
DUNG = "DUNG"  # tài liệu liên quan duy nhất của mỗi câu trong qrels của ranx
SAI_SO_KIEM_CHEO = 1e-9


# ── Cấu hình và bộ vàng ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class XepLai:
    """Khối ``rerank:`` — ``ung_vien`` đoạn đầu của RRF đưa vào ai-rerank, ``khi`` thuộc
    ``KHI_XEP_LAI``. ``model``/``version`` là danh tính ai-rerank phải trả ở ``/v1/model``."""

    ung_vien: int
    khi: str
    model: str
    version: str


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
    xep_lai: XepLai | None = None
    nguon: Path = field(default=Path(), compare=False)


def doc_cau_hinh(duong_dan: Path) -> CauHinh:
    d = yaml.safe_load(duong_dan.read_text(encoding="utf-8"))
    if d.get("che_do") not in CHE_DO:
        raise ValueError(f"{duong_dan}: che_do phải thuộc {CHE_DO}, nhận {d.get('che_do')!r}")
    nhung = d.pop("nhung")
    xl = d.pop("rerank", None)
    return CauHinh(
        **{k: v for k, v in d.items() if k not in ("bo_vang", "tenant")},
        bo_vang=(duong_dan.parent / d["bo_vang"]).resolve(),
        tenant=UUID(str(d["tenant"])),
        model=nhung["model"],
        version=nhung["version"],
        xep_lai=_doc_xep_lai(duong_dan, xl, d.get("k", 5)) if xl else None,
        nguon=duong_dan,
    )


def _doc_xep_lai(duong_dan: Path, xl: dict, k: int) -> XepLai:
    if xl.get("khi") not in KHI_XEP_LAI:
        raise ValueError(
            f"{duong_dan}: rerank.khi phải thuộc {KHI_XEP_LAI}, nhận {xl.get('khi')!r}"
        )
    if int(xl["ung_vien"]) <= k:
        raise ValueError(f"{duong_dan}: rerank.ung_vien ({xl['ung_vien']}) phải lớn hơn k ({k})")
    return XepLai(int(xl["ung_vien"]), xl["khi"], xl["model"], str(xl["version"]))


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


def _hang(gia_tri: object) -> int | None:
    """``hang_dung`` của một dòng — ``int`` khi còn trong bộ nhớ, chuỗi khi đọc lại từ CSV."""
    return int(gia_tri) if str(gia_tri) else None


def chi_so_ranx(dong: list[dict], k: int) -> dict[str, float]:
    """``{"trung", "ndcg", "rr"}`` trung bình các câu — tính bằng ``ranx``, kiểm chéo ``diem_cau``.

    ``dong`` là các dòng CSV từng câu (trong bộ nhớ hoặc đọc lại từ tệp — cùng kết quả).
    """
    import warnings

    from ranx import Qrels, Run, evaluate

    run: dict[str, dict[str, float]] = {}
    for d in dong:
        so_doan, hang = len(json.loads(d["top_k"])), _hang(d["hang_dung"])
        # Điểm giảm dần theo hạng ⇒ ranx xếp lại đúng thứ tự đã truy hồi.
        run[d["id"]] = {
            (DUNG if h == hang else f"{d['id']}#{h}"): float(so_doan + 1 - h)
            for h in range(1, so_doan + 1)
        }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # numba: ép kiểu uint64→int64 ở hit_rate, vô hại
        m = evaluate(
            Qrels({d["id"]: {DUNG: 1} for d in dong}),
            Run(run),
            [f"hit_rate@{k}", f"ndcg@{k}", f"mrr@{k}"],
            make_comparable=True,
        )
    ra = {"trung": m[f"hit_rate@{k}"], "ndcg": m[f"ndcg@{k}"], "rr": m[f"mrr@{k}"]}
    for cot, gia_tri in ra.items():
        tu_cai = statistics.fmean(diem_cau(_hang(d["hang_dung"]), k)[cot] for d in dong)
        if abs(float(gia_tri) - tu_cai) > SAI_SO_KIEM_CHEO:
            raise RuntimeError(f"ranx {cot}={gia_tri} lệch công thức tự cài {tu_cai}")
    return {cot: float(v) for cot, v in ra.items()}


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

    def ranx(self) -> dict[str, float]:
        return chi_so_ranx(self.dong, self.cau_hinh.k)


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


def _vector_tsquery(
    ch: CauHinh, cau_hoi: str, vector: list[float] | None
) -> tuple[list[float] | None, str | None]:
    """Đầu vào của hai làn theo ``che_do`` — tắt một làn bằng cách truyền ``None``."""
    return (
        vector if ch.che_do != "sparse" else None,
        build_tsquery(cau_hoi) if ch.che_do != "dense" else None,
    )


async def chay_cau_hinh(
    factory: async_sessionmaker,
    ch: CauHinh,
    cac_cau: list[CauVang],
    vectors: list[list[float]] | None,
    rerank: RerankClient | None = None,
) -> KetQuaCauHinh:
    xl = ch.xep_lai
    if xl and rerank is None:
        raise ValueError(f"{ch.id} có khối rerank nhưng không có client ai-rerank")
    # Có xếp lại thì lấy đủ ứng viên cho cross-encoder; top-k cắt SAU khi xếp lại.
    so_lay = xl.ung_vien if xl else ch.k

    async def mot_cau(i: int) -> tuple[list[DoanTimDuoc], float, bool]:
        vector, tsquery = _vector_tsquery(
            ch, cac_cau[i].question, vectors[i] if vectors else None
        )
        async with db_session.get_tenant_session(str(ch.tenant), factory) as s:
            dau = time.perf_counter()
            ket_qua = await hybrid.tim_kiem_lai(
                s,
                vector=vector,
                tsquery=tsquery,
                embedding_model=ch.model,
                embedding_version=ch.version,
                k=so_lay,
                ung_vien=ch.ung_vien,
                ef_search=ch.ef_search,
                quet_lap=ch.quet_lap,
            )
            ms = (time.perf_counter() - dau) * 1000
            # EXPLAIN trong CÙNG transaction, cùng tham số HNSW và cùng bind parameter.
            ke_hoach = await s.execute(
                text("EXPLAIN " + hybrid._SQL_TIM_LAI.text),
                hybrid.tham_so_cau_lenh(
                    vector, tsquery, ch.model, ch.version, so_lay, ch.ung_vien
                ),
            )
            dung_hnsw = any("ix_chunk_embedding" in r[0] for r in ke_hoach)
        return ket_qua, ms, dung_hnsw

    # Làm nóng: kết nối, nạp thư viện pgvector, bộ đệm — không tính giờ. Có xếp lại thì làm nóng
    # cả ai-rerank: lượt đầu của nó gồm thời gian nạp model.
    lam_nong, _, _ = await mot_cau(0)
    if xl:
        await quyet_dinh.xep_lai(rerank, cac_cau[0].question, lam_nong, xl.ung_vien)
    dong = []
    for i, cau in enumerate(cac_cau):
        ket_qua, ms, dung_hnsw = await mot_cau(i)
        them: dict = {}
        if xl:
            hang_truoc = hang_dung_dau_tien(ket_qua, cau.can_cu)
            mo_ho = quyet_dinh.needs_rerank(ket_qua)
            rerank_ms = None
            if xl.khi == "moi_cau" or mo_ho:
                dau = time.perf_counter()
                ket_qua = await quyet_dinh.xep_lai(rerank, cau.question, ket_qua, xl.ung_vien)
                rerank_ms = (time.perf_counter() - dau) * 1000
            ket_qua = ket_qua[: ch.k]
            them = {
                "hang_truoc_rerank": hang_truoc or "",
                "mo_ho": int(mo_ho),
                "da_rerank": int(rerank_ms is not None),
                "rerank_ms": "" if rerank_ms is None else round(rerank_ms, 2),
            }
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
                **them,
            }
        )
    return KetQuaCauHinh(ch, dong, await _kiem_can_cu_trong_kho(factory, ch, cac_cau))


def thong_ke_xep_lai(kq: KetQuaCauHinh) -> dict[str, float | int | None]:
    """Các con số Ngày 15 của một cấu hình có xếp lại — đọc được cả dòng trong bộ nhớ lẫn CSV.

    ``tran`` = số câu có đoạn đúng ở hạng k+1..``ung_vien`` TRƯỚC khi xếp lại: xếp hoàn hảo thì cứu
    được, nên ``tran_recall`` = (đã trúng sẵn + ``tran``) / N là trần recall@k của cấu hình.
    ``tran_bo_qua`` = trong số đó, bao nhiêu câu cổng mơ hồ không cho xếp lại.
    """
    xl, k = kq.cau_hinh.xep_lai, kq.cau_hinh.k
    if xl is None:
        raise ValueError(f"{kq.cau_hinh.id} không có khối rerank")
    truoc = [_hang(d["hang_truoc_rerank"]) for d in kq.dong]
    trung_truoc = [h is not None and h <= k for h in truoc]
    tran = [i for i, h in enumerate(truoc) if h is not None and k < h <= xl.ung_vien]
    ms = [float(d["rerank_ms"]) for d in kq.dong if str(d["rerank_ms"])]
    return {
        "ti_le_mo_ho": statistics.fmean(int(d["mo_ho"]) for d in kq.dong),
        "so_da_xep_lai": len(ms),
        "p50_ms": _phan_vi(ms, 0.5) if ms else None,
        "p95_ms": _phan_vi(ms, 0.95) if ms else None,
        "tran": len(tran),
        "tran_recall": (sum(trung_truoc) + len(tran)) / len(kq.dong),
        "tran_bo_qua": sum(1 for i in tran if not int(kq.dong[i]["da_rerank"])),
        "cuu_duoc": sum(
            1 for d, t in zip(kq.dong, trung_truoc, strict=True) if not t and float(d["trung"])
        ),
        "bi_day_ra": sum(
            1 for d, t in zip(kq.dong, trung_truoc, strict=True) if t and not float(d["trung"])
        ),
    }


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
        ch, ms, r = kq.cau_hinh, [float(d["ms"]) for d in kq.dong], kq.ranx()
        dong.append(
            f"| `{ch.id}` | {ch.che_do} | {r['trung']:.3f} | "
            f"{r['ndcg']:.3f} | {r['rr']:.3f} | "
            f"{_phan_vi(ms, 0.5):.1f} | {_phan_vi(ms, 0.95):.1f} | "
            f"{kq.trung_binh('dung_hnsw') * 100:.0f}% |"
        )
    dong += ["", f"recall@{k} · nDCG@{k} · MRR@{k} tính bằng `ranx`, kiểm chéo công thức tự cài."]
    co_xep_lai = [kq for kq in cac_ket_qua if kq.cau_hinh.xep_lai]
    if co_xep_lai:
        dong += [
            "",
            "Xếp lại — p50/p95 là thời gian một lượt gọi ai-rerank (gồm HTTP), chỉ tính lượt "
            f"đã xếp lại; trần = câu có đoạn đúng ở hạng {k + 1}..N trước khi xếp lại:",
            "",
            "| Cấu hình | N | khi | mơ hồ | đã xếp lại | p50 ms | p95 ms | trần (câu) "
            f"| trần recall@{k} | trần bị cổng bỏ qua | cứu được | bị đẩy ra |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for kq in co_xep_lai:
            xl, t = kq.cau_hinh.xep_lai, thong_ke_xep_lai(kq)
            p50 = "—" if t["p50_ms"] is None else f"{t['p50_ms']:.0f}"
            p95 = "—" if t["p95_ms"] is None else f"{t['p95_ms']:.0f}"
            dong.append(
                f"| `{kq.cau_hinh.id}` | {xl.ung_vien} | {xl.khi} | {t['ti_le_mo_ho'] * 100:.0f}% "
                f"| {t['so_da_xep_lai']} | {p50} | {p95} | {t['tran']} | {t['tran_recall']:.2f} "
                f"| {t['tran_bo_qua']} | {t['cuu_duoc']} | {t['bi_day_ra']} |"
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
        xl = ch.xep_lai
        dong.append(
            f"- `{ch.id}` ({ch.nguon.name}): {ch.mo_ta} — tenant `{ch.tenant}`, "
            f"{ch.model}/{ch.version}, k={ch.k}, ứng viên={ch.ung_vien}, "
            f"ef_search={ch.ef_search}, iterative_scan={ch.quet_lap}"
            + (
                f", xếp lại {xl.ung_vien} ứng viên khi={xl.khi} bằng {xl.model}/{xl.version}"
                if xl
                else ""
            )
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
    rerank: RerankClient | None = None,
    gioi_han: int | None = None,
) -> tuple[list[KetQuaCauHinh], str]:
    cac_cau_hinh = [doc_cau_hinh(p) for p in cac_duong_dan]
    if len({ch.bo_vang for ch in cac_cau_hinh}) != 1:
        raise ValueError("Mọi cấu hình của một lượt phải dùng CÙNG bộ vàng — so theo cặp cần vậy.")
    cac_cau, khong_dap_an, sha = doc_bo_vang(cac_cau_hinh[0].bo_vang)
    if not cac_cau:
        raise ValueError(f"{cac_cau_hinh[0].bo_vang} chưa có câu nào có đáp án.")
    # N câu ĐẦU theo thứ tự tệp — cố định, chạy lại ra đúng tập đó. Chỉ dùng cho phép đo độ trễ
    # rút gọn (Ngày 15, 2 vCPU); số chất lượng báo cáo luôn lấy từ lượt đủ câu.
    if gioi_han is not None:
        cac_cau = cac_cau[:gioi_han]

    vector_theo_model: dict[tuple[str, str], list[list[float]]] = {}
    cac_ket_qua = []
    for ch in cac_cau_hinh:
        khoa = (ch.model, ch.version)
        if ch.che_do != "sparse" and khoa not in vector_theo_model:
            vector_theo_model[khoa] = await _nhung_cau_hoi(embed, cac_cau, *khoa)
        cac_ket_qua.append(
            await chay_cau_hinh(factory, ch, cac_cau, vector_theo_model.get(khoa), rerank)
        )

    meta = {
        "nhan": nhan,
        "thời điểm": datetime.now().isoformat(timespec="seconds"),
        "commit": _commit_git(),
        "bộ vàng": f"{cac_cau_hinh[0].bo_vang.name} · sha256 `{sha}`"
        + (f" · RÚT GỌN {len(cac_cau)} câu đầu" if gioi_han is not None else ""),
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


async def xuat_cap(
    factory: async_sessionmaker, embed: EmbedClient, ch: CauHinh, ung_vien: int
) -> list[dict]:
    """Tệp cặp cho cổng parity của cross-encoder (notebook 07). [R&D]

    Mỗi câu CÓ đáp án một dòng: ``ung_vien`` đoạn đầu của RRF đúng thứ tự cấu hình ``ch`` trả về,
    nhãn ``dung`` theo đúng ``dung()`` của harness, ``mo_ho`` theo ``needs_rerank``. Chữ của đoạn là
    ``content`` trong kho — đúng chuỗi production gửi ai-rerank — nên chỉ có chữ của ``kb_samples``.
    """
    cac_cau, _, _ = doc_bo_vang(ch.bo_vang)
    vectors = await _nhung_cau_hoi(embed, cac_cau, ch.model, ch.version)
    ra = []
    for cau, v in zip(cac_cau, vectors, strict=True):
        vector, tsquery = _vector_tsquery(ch, cau.question, v)
        async with db_session.get_tenant_session(str(ch.tenant), factory) as s:
            ket_qua = await hybrid.tim_kiem_lai(
                s,
                vector=vector,
                tsquery=tsquery,
                embedding_model=ch.model,
                embedding_version=ch.version,
                k=ung_vien,
                ung_vien=ch.ung_vien,
                ef_search=ch.ef_search,
                quet_lap=ch.quet_lap,
            )
        ra.append(
            {
                "id": cau.id,
                "question": cau.question,
                "hang_dung_rrf": hang_dung_dau_tien(ket_qua, cau.can_cu),
                "mo_ho": quyet_dinh.needs_rerank(ket_qua),
                "ung_vien": [
                    {
                        "ma": f"{d.file_name}#{d.chunk_index}",
                        "text": d.content,
                        "dung": dung(d, cau.can_cu),
                    }
                    for d in ket_qua
                ],
            }
        )
    return ra


async def kiem_danh_tinh_rerank(base_url: str, cac_cau_hinh: list[CauHinh]) -> str:
    """``model_id/model_version`` ai-rerank đang phục vụ phải khớp MỌI khối ``rerank:`` — lệch là
    đang đo một model khác cái cấu hình ghi, con số không gắn được vào model nào."""
    async with httpx.AsyncClient(base_url=base_url) as c:
        # Lượt đầu có thể gồm thời gian nạp model (~vài giây) — nới hạn chờ.
        tt = (await c.get("/v1/model", timeout=120.0)).raise_for_status().json()
    dang_chay = (tt.get("model_id"), tt.get("model_version"))
    for ch in cac_cau_hinh:
        xl = ch.xep_lai
        if xl and dang_chay != (xl.model, xl.version):
            raise RuntimeError(
                f"ai-rerank đang phục vụ {dang_chay[0]}/{dang_chay[1]}, cấu hình {ch.id} ghi "
                f"{xl.model}/{xl.version}"
            )
    return f"{dang_chay[0]}/{dang_chay[1]}"


async def _main(args: argparse.Namespace) -> None:
    engine = db_session.tao_engine(args.dsn)
    embed = tao_embed_client(get_settings())
    try:
        factory = db_session.tao_session_factory(engine)
        if args.lenh == "xuat-cap":
            await _main_xuat_cap(args, factory, embed)
            return
        rerank = None
        if any(doc_cau_hinh(p).xep_lai for p in args.cau_hinh):
            # Hạn chờ rộng: đây là phép ĐO độ trễ — cắt ở 15 s như production là mất đuôi phân bố.
            rerank = RemoteRerankClient(timeout_s=300.0)
            print("ai-rerank:", await kiem_danh_tinh_rerank(
                rerank.base_url, [doc_cau_hinh(p) for p in args.cau_hinh]
            ))
        _, bao_cao = await chay(
            args.cau_hinh, nhan=args.nhan, factory=factory, embed=embed, rerank=rerank,
            gioi_han=args.gioi_han,
        )
        print(bao_cao)
    finally:
        await embed.aclose()
        await engine.dispose()


async def _main_xuat_cap(args: argparse.Namespace, factory, embed) -> None:
    ch = doc_cau_hinh(args.cau_hinh)
    ra = await xuat_cap(factory, embed, ch, args.ung_vien)
    noi_dung = "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in ra)
    args.ra.write_text(noi_dung, encoding="utf-8")
    so_cap = sum(len(d["ung_vien"]) for d in ra)
    print(
        f"{args.ra}: {len(ra)} câu · {so_cap} cặp · "
        f"có đoạn đúng trong {args.ung_vien} ứng viên: "
        f"{sum(1 for d in ra if d['hang_dung_rrf'])} câu · "
        f"mơ hồ: {sum(1 for d in ra if d['mo_ho'])} câu\n"
        f"cấu hình {ch.id} ({ch.nguon.name}) · {ch.model}/{ch.version} · tenant {ch.tenant}\n"
        f"commit {_commit_git()} · sha256 {hashlib.sha256(noi_dung.encode()).hexdigest()}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    lenh = ap.add_subparsers(dest="lenh", required=True)
    p_chay = lenh.add_parser("chay", help="chạy các cấu hình (cấu hình đầu là baseline)")
    p_chay.add_argument("cau_hinh", nargs="+", type=Path)
    p_chay.add_argument("--nhan", default=datetime.now().strftime("%Y%m%d-%H%M%S"))
    p_chay.add_argument("--dsn", help="DSN postgresql+psycopg:// của ai_app (mặc định: .env)")
    p_chay.add_argument("--gioi-han", type=int, help="chỉ chạy N câu có đáp án đầu tiên")
    p_ss = lenh.add_parser("so-sanh", help="paired bootstrap giữa hai CSV kết quả")
    p_ss.add_argument("a", type=Path)
    p_ss.add_argument("b", type=Path)
    p_cap = lenh.add_parser("xuat-cap", help="tệp cặp cho parity cross-encoder (notebook 07)")
    p_cap.add_argument("cau_hinh", type=Path)
    p_cap.add_argument("--ung-vien", type=int, default=20)
    p_cap.add_argument("--ra", type=Path, required=True)
    p_cap.add_argument("--dsn", help="DSN postgresql+psycopg:// của ai_app (mặc định: .env)")
    args = ap.parse_args()
    if args.lenh == "so-sanh":
        print(so_sanh(args.a, args.b))
    else:
        asyncio.run(_main(args))


if __name__ == "__main__":
    main()
