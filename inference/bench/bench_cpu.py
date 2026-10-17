"""``bench_cpu.py`` — độ trễ CPU của ai-embed, ai-rerank, ai-classify; ghim luồng và mặc định. [R&D]

Ngày 15 Khối B. Bench không phục vụ request nên KHÔNG nằm trong ``src/`` (Dockerfile
``COPY src/ src/`` sẽ chép nó vào image ship). Lúc đo thì mount vào ``ai-inference:dev`` — image duy
nhất có onnxruntime — nên vẫn chạy đúng onnxruntime và ``session.py`` của image ship; sửa bench
không phải build lại image (ADR-0034).

Đo trong container, cấp vCPU bằng ``--cpus`` (cùng cơ chế ``deploy.resources.limits.cpus``):

    cd <gốc repo>
    docker run --rm --cpus 2 -e OMP_NUM_THREADS=2 -e TZ=ICT-7 \\
        -e TAI_MAY_CHU="$(sysctl -n vm.loadavg)" \\
        -v "$PWD/artifacts:/app/artifacts:ro" -v "$PWD/ai-service/tests/eval:/app/eval:ro" \\
        -v "$PWD/inference/bench:/app/bench:ro" -v "$PWD/reports/eval:/app/reports/eval" \\
        ai-inference:dev python -m bench.bench_cpu chay --vai rerank --che-do ghim --nhan n15

    python3 inference/bench/bench_cpu.py bang --ra reports/eval/bench-n15.md \\
        reports/eval/bench-n15-*.json

``bang`` chạy trên máy, chỉ cần thư viện chuẩn. CHẠY TỪNG CẤU HÌNH MỘT, KHÔNG SONG SONG: ``--cpus``
là hạn mức thời gian CPU, không giữ riêng nhân nào — hai container đo cùng lúc tranh cùng các vCPU
của VM Docker và mọi con số đều chậm hơn thật một lượng không biết trước.

ĐO GÌ
-----
Gọi đúng hàm production — ``BoNhung.nhung`` (embed) và ``BoXepHang.cham`` (rerank), nạp qua
``lay_bo_nhung`` / ``lay_bo_xep_hang`` — trên session nạp trực tiếp, không qua HTTP. Router
(classify) không có hàm nào tách riêng tầng ONNX để gọi: bench dựng ``RouterEmbedder`` + session như
``_init_router_model`` và chép đúng tầng 2 của ``classify.py`` (xem ``_BoPhanLoai``). Chỉ thay hàm
dựng session, mọi tuỳ chọn khác giữ nguyên (``ORT_ENABLE_ALL``, ``ORT_SEQUENTIAL``):

    ghim      ``make_session`` của ``session.py``: intra_op = OMP_NUM_THREADS, inter_op = 1
    mac-dinh  ``SessionOptions`` không đặt số luồng — ONNX Runtime tự chọn

Một MẪU là một yêu cầu. Đầu vào thật, không PII, chỉ đọc:

    embed   ``--tai cau-hoi`` (mặc định): nhúng MỘT câu hỏi — mọi câu ``eval/golden_set.jsonl``
            (112 câu, tệp đóng băng, mount ``:ro``) × ``--vong`` vòng. Việc của UC023 lúc chat.
            ``--tai doan``: nhúng MỘT đoạn — các đoạn khác nhau trong ứng viên của ``--so-cau``
            dòng đầu ``rerank_cap_100x20.jsonl``. Đoạn thật của kho đo, việc của worker UC019.
    rerank  một câu hỏi × 20 ứng viên = 20 lượt ``run`` lô 1, cộng tách từ. ``--so-cau`` dòng đầu
            ``eval/rerank_cap_100x20.jsonl`` — 30 dòng đầu là G001–G033, đúng 30 câu lượt
            2 ↔ 4 vCPU của Khối A (``docs/report/rerank-ngay15-2026-10-11.md`` §3)
    classify  phân loại MỘT câu hỏi ``golden_set.jsonl`` × ``--vong`` vòng: băm n-gram (Python, một
            luồng) + một lượt ``run``. Ghi riêng thời gian băm để tách phần ONNX Runtime ra

Warm-up chạy trước, không vào số đo. Phân vị theo hạng gần nhất, cùng ``_phan_vi`` của harness
truy hồi (``ai-service/tests/eval/danh_gia_truy_hoi.py``) để so được với số Khối A.

GHI KÈM ĐIỀU KIỆN ĐO — thiếu thì bảng không đọc được
-----------------------------------------------------
- **Số luồng ONNX Runtime thật sự tạo** — đếm ``Threads`` của ``/proc/self/status`` trước và sau
  khi nạp session. Bằng chứng cho điều (2): để mặc định, ORT tạo luồng theo số CPU VM nhìn thấy,
  không theo hạn mức ``--cpus``.
- **``cpu.stat`` của cgroup** trước và sau vòng đo: tỉ lệ chu kỳ bị CFS chặn (``nr_throttled /
  nr_periods``) và số lõi dùng trung bình. Nhiều luồng hơn hạn mức thì hạn mức cạn giữa chu kỳ,
  cả tiến trình bị dừng tới chu kỳ sau — p95 xấu đi mà không log nào báo.
- **RSS** sau khi nạp và đỉnh (``VmHWM``) sau vòng đo.
- **Tải** của VM Docker (``os.getloadavg`` trong container) và của máy chủ (``TAI_MAY_CHU``, người
  chạy truyền vào). Docker Desktop chạy VM trên macOS: tiến trình khác của máy chủ tranh nhân
  với VM.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import platform
import statistics
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# Ngưỡng §5.3 — số KẾ HOẠCH, chưa áp dụng (người dùng chốt 11/10/2026: độ trễ chưa là cổng).
NGUONG_KE_HOACH_MS = {"embed": 120, "rerank": 300, "classify": 60}

TEN_MODEL = {
    "embed": "bge-m3 INT8",
    "rerank": "bge-reranker-v2-m3 INT8",
    "classify": "router LogisticRegression QUInt8",
}
TEN_TAI = {"cau-hoi": "câu hỏi", "doan": "đoạn"}

# Nhóm độ dài cặp rerank — biết lượt nào ăn thời gian trước khi bàn tới đòn bẩy ``max_length``.
NHOM_DO_DAI = ((0, 128), (129, 256), (257, 512))


def phan_vi(xs: list[float], p: float) -> float:
    """Phân vị theo hạng gần nhất — chép ``_phan_vi`` của harness truy hồi để số so được."""
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(p * len(xs)) - 1)]


# ── Đọc trạng thái tiến trình và cgroup ──────────────────────────────────────


def _trang_thai() -> dict[str, int]:
    """``Threads`` và ``VmRSS``/``VmHWM`` (kB) của chính tiến trình, từ ``/proc/self/status``."""
    ra: dict[str, int] = {}
    for dong in Path("/proc/self/status").read_text().splitlines():
        khoa, _, giatri = dong.partition(":")
        if khoa in ("Threads", "VmRSS", "VmHWM"):
            ra[khoa] = int(giatri.split()[0])
    return ra


def _cpu_stat() -> dict[str, int]:
    """``cpu.stat`` của cgroup v2; rỗng nếu không đọc được (Docker Desktop hiện là cgroup v2)."""
    tep = Path("/sys/fs/cgroup/cpu.stat")
    if not tep.is_file():
        return {}
    return {k: int(v) for k, v in (dong.split() for dong in tep.read_text().splitlines())}


# ── Dựng session theo chế độ ─────────────────────────────────────────────────


class _PhienDo:
    """Bọc ``InferenceSession``: bấm giờ từng lượt ``run`` kèm độ dài chuỗi, còn lại chuyển thẳng.

    Mã production (``nhung``/``cham``) gọi ``self.session.run`` — bọc ở đây thì đo được từng cặp
    mà không phải chép vòng lặp production vào bench.
    """

    def __init__(self, phien: Any) -> None:
        self._phien = phien
        self.luot: list[tuple[int, float]] = []

    def run(self, ten_ra: Any, dau_vao: dict[str, Any]) -> Any:
        t0 = time.perf_counter()
        ra = self._phien.run(ten_ra, dau_vao)
        ms = (time.perf_counter() - t0) * 1000
        # Router nhận vector cố định 1024 chiều, không có độ dài chuỗi — ghi 0.
        do_dai = int(dau_vao["input_ids"].shape[1]) if "input_ids" in dau_vao else 0
        self.luot.append((do_dai, ms))
        return ra

    def __getattr__(self, ten: str) -> Any:
        return getattr(self._phien, ten)


def _session_mac_dinh(duong: Path) -> Any:
    """Như ``make_session`` nhưng KHÔNG đặt ``intra_op``/``inter_op`` — để ONNX Runtime tự chọn."""
    import onnxruntime as ort

    tuy_chon = ort.SessionOptions()
    tuy_chon.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    tuy_chon.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    return ort.InferenceSession(
        str(duong), sess_options=tuy_chon, providers=["CPUExecutionProvider"]
    )


@contextlib.contextmanager
def _thay_ham_dung_session(che_do: str) -> Iterator[None]:
    """Thay ``src.session.make_session`` trong lúc nạp bộ production.

    ``BoNhung``/``BoXepHang`` import ``make_session`` NGAY TRONG ``__init__``, nên thay thuộc tính
    của module trước khi dựng là đủ — kiểm đầu vào/đầu ra của graph và tách từ vẫn chạy đúng mã
    production.
    """
    import src.session as phien

    goc = phien.make_session

    def dung(duong: Path, num_threads: int | None = None) -> _PhienDo:
        if che_do == "ghim":
            return _PhienDo(goc(duong, num_threads))
        return _PhienDo(_session_mac_dinh(Path(duong)))

    phien.make_session = dung  # type: ignore[assignment]
    try:
        yield
    finally:
        phien.make_session = goc


class _BoPhanLoai:
    """Tầng 2 của ``classify.py`` (dòng 257–262), dựng thẳng — không qua ``classify()``.

    Hai lý do không gọi được hàm production như embed/rerank: ``_init_router_model`` nạp
    ``session.py`` bằng ``_load_sibling`` thành module riêng và giữ session ở biến toàn cục,
    nên thay ``src.session.make_session`` không với tới; và tầng luật đứng trước ONNX — câu khớp
    từ khoá không chạm ONNX. Bench dựng embedder + session đúng như ``_init_router_model``
    (``make_session(tệp)``, không truyền số luồng ⇒ lấy ``OMP_NUM_THREADS``) và chép nguyên ba
    dòng băm → ``run`` → đọc kết quả.
    """

    def __init__(self) -> None:
        from src.roles.classify import INTENT_TAXONOMY, _find_path
        from src.roles.router_embedder import RouterEmbedder
        from src.session import make_session

        tep_onnx = _find_path("artifacts/router_model.onnx")
        tep_emb = _find_path("artifacts/router_embedder.json")
        if tep_onnx is None or tep_emb is None:
            raise SystemExit(f"Thiếu artifact router: onnx={tep_onnx}, embedder={tep_emb}")
        self.embedder = RouterEmbedder.from_json(tep_emb)
        if sorted(self.embedder.classes) != sorted(INTENT_TAXONOMY):
            raise SystemExit(f"Lớp embedder {self.embedder.classes} không khớp taxonomy 7 ý định")
        self.session = make_session(tep_onnx)
        self.model_version = "onnx-" + hashlib.sha256(tep_onnx.read_bytes()).hexdigest()[:8]
        self.bam_ms: list[float] = []

    def phan_loai(self, cau: str) -> tuple[str, dict[str, float]]:
        t = time.perf_counter()
        vec = self.embedder.transform_single(cau)
        self.bam_ms.append((time.perf_counter() - t) * 1000)
        ten_vao = self.session.get_inputs()[0].name
        ra = self.session.run(None, {ten_vao: vec.reshape(1, -1)})
        return str(ra[0][0]), {k: round(float(v), 4) for k, v in ra[1][0].items()}


# ── Đầu vào ──────────────────────────────────────────────────────────────────


def _doc_jsonl(duong: Path) -> list[dict[str, Any]]:
    with duong.open(encoding="utf-8") as f:
        return [json.loads(dong) for dong in f if dong.strip()]


def _yeu_cau(
    vai: str, tai: str, thu_muc_eval: Path, so_cau: int, so_ung_vien: int
) -> list[tuple[str, Any]]:
    """Danh sách (mã, đầu vào của một yêu cầu)."""
    if vai in ("embed", "classify") and tai == "cau-hoi":
        return [(d["id"], d["question"]) for d in _doc_jsonl(thu_muc_eval / "golden_set.jsonl")]
    dong = _doc_jsonl(thu_muc_eval / "rerank_cap_100x20.jsonl")[:so_cau]
    if vai == "embed":
        doan: dict[str, str] = {}
        for d in dong:
            for u in d["ung_vien"][:so_ung_vien]:
                doan.setdefault(u["ma"], u["text"])
        return list(doan.items())
    return [
        (d["id"], (d["question"], [u["text"] for u in d["ung_vien"][:so_ung_vien]])) for d in dong
    ]


# ── chay: đo một cấu hình, ghi JSON ──────────────────────────────────────────


def chay(args: argparse.Namespace) -> Path:
    import onnxruntime as ort

    from src.session import get_cgroup_cpus

    if args.vai == "embed":
        from src.roles.embed import lay_bo_nhung as nap
    elif args.vai == "rerank":
        from src.roles.rerank import lay_bo_xep_hang as nap
    else:
        # Import trước khi đếm luồng: classify.py kéo theo fastapi/pydantic, không phải của ORT.
        import src.roles.classify  # noqa: F401

        nap = _BoPhanLoai

    yeu_cau = _yeu_cau(args.vai, args.tai, Path(args.eval), args.so_cau, args.so_ung_vien)
    vcpu = get_cgroup_cpus()
    tai_vm = os.getloadavg()

    luong_truoc = _trang_thai()["Threads"]
    t0 = time.perf_counter()
    with _thay_ham_dung_session(args.che_do):
        bo = nap()
    giay_nap = time.perf_counter() - t0
    sau_nap = _trang_thai()
    phien: _PhienDo = bo.session  # type: ignore[assignment]

    def mot_yeu_cau(dau_vao: Any) -> None:
        if args.vai == "embed":
            bo.nhung([dau_vao])
        elif args.vai == "rerank":
            bo.cham(*dau_vao)
        else:
            bo.phan_loai(dau_vao)

    # Warm-up: lượt đầu cấp phát arena bộ nhớ và dựng kernel — không phải chi phí của yêu cầu thật.
    for _, dau_vao in yeu_cau[: args.warmup]:
        mot_yeu_cau(dau_vao)
    phien.luot.clear()

    cpu_truoc = _cpu_stat()
    mau: list[dict[str, Any]] = []
    t_do = time.perf_counter()
    for vong in range(args.vong):
        for ma, dau_vao in yeu_cau:
            so_luot = len(phien.luot)
            t = time.perf_counter()
            mot_yeu_cau(dau_vao)
            mau.append({
                "ma": ma,
                "vong": vong,
                "ms": (time.perf_counter() - t) * 1000,
                "run_ms": sum(ms for _, ms in phien.luot[so_luot:]),
            })
            if args.vai == "classify":
                mau[-1]["bam_ms"] = bo.bam_ms[-1]
    giay_do = time.perf_counter() - t_do
    cpu_sau = _cpu_stat()
    cuoi = _trang_thai()

    ms = [m["ms"] for m in mau]
    luot_ms = [ms_ for _, ms_ in phien.luot]
    cgroup: dict[str, Any] = {}
    if cpu_truoc and cpu_sau:
        chu_ky = cpu_sau["nr_periods"] - cpu_truoc["nr_periods"]
        bi_chan = cpu_sau["nr_throttled"] - cpu_truoc["nr_throttled"]
        cgroup = {
            "chu_ky": chu_ky,
            "chu_ky_bi_chan": bi_chan,
            "ti_le_bi_chan": bi_chan / chu_ky if chu_ky else None,
            "giay_bi_chan": (cpu_sau["throttled_usec"] - cpu_truoc["throttled_usec"]) / 1e6,
            "loi_dung_tb": (cpu_sau["usage_usec"] - cpu_truoc["usage_usec"]) / 1e6 / giay_do,
        }

    ket_qua = {
        "nhan": args.nhan,
        "vai": args.vai,
        "tai": args.tai,
        "model": TEN_MODEL[args.vai],
        "model_version": bo.model_version,
        "che_do": args.che_do,
        "vcpu_cgroup": vcpu,
        "omp_num_threads": os.getenv("OMP_NUM_THREADS"),
        "luong_ort_tao": sau_nap["Threads"] - luong_truoc,
        "luong_cuoi": cuoi["Threads"],
        "cpu_vm_nhin_thay": os.cpu_count(),
        "ort": ort.__version__,
        "kien_truc": platform.machine(),
        "thoi_diem": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tai_vm": [round(x, 2) for x in tai_vm],
        "tai_may_chu": os.getenv("TAI_MAY_CHU", "").strip("{} ") or None,
        "giay_nap": round(giay_nap, 2),
        "giay_do": round(giay_do, 1),
        "warmup": args.warmup,
        "vong": args.vong,
        "so_mau": len(ms),
        "p50_ms": phan_vi(ms, 0.50),
        "p95_ms": phan_vi(ms, 0.95),
        "max_ms": max(ms),
        "tb_ms": statistics.fmean(ms),
        "luot_run": {
            "so": len(luot_ms),
            "p50_ms": phan_vi(luot_ms, 0.5),
            "p95_ms": phan_vi(luot_ms, 0.95),
        },
        "rss_nap_mb": round(sau_nap["VmRSS"] / 1024),
        "rss_dinh_mb": round(cuoi["VmHWM"] / 1024),
        "cgroup": cgroup,
        "mau": mau,
        "luot": phien.luot,
    }
    if args.vai == "classify":
        bam = [m["bam_ms"] for m in mau]
        ket_qua["bam"] = {"p50_ms": phan_vi(bam, 0.5), "p95_ms": phan_vi(bam, 0.95)}
    vai_tai = args.vai if args.tai == "cau-hoi" else f"{args.vai}-{args.tai}"
    gio = time.strftime("%H%M%S")
    ra = Path(args.ra) / f"bench-{args.nhan}-{vai_tai}-{_so(vcpu)}vcpu-{args.che_do}-{gio}.json"
    ra.write_text(json.dumps(ket_qua, ensure_ascii=False, indent=1), encoding="utf-8")
    print(
        f"{vai_tai} {_so(vcpu)} vCPU {args.che_do}: luồng ORT +{ket_qua['luong_ort_tao']} "
        f"(cuối vòng {ket_qua['luong_cuoi']}) · p50 {_thoi_gian(ket_qua['p50_ms'])} · "
        f"p95 {_thoi_gian(ket_qua['p95_ms'])} · bị chặn {_phan_tram(cgroup.get('ti_le_bi_chan'))}"
        f" → {ra}"
    )
    return ra


# ── bang: gộp JSON thành Markdown ────────────────────────────────────────────


def _so(x: float | None, chu_so: int = 0) -> str:
    """Số kiểu Việt: phẩy thập phân."""
    if x is None:
        return "—"
    return f"{x:.{chu_so}f}".replace(".", ",")


def _thoi_gian(ms: float) -> str:
    """Router chạy dưới 1 ms — làm tròn tới ms thì mọi ô thành "0 ms"."""
    if ms < 1:
        return f"{_so(ms, 3)} ms"
    if ms < 10:
        return f"{_so(ms, 2)} ms"
    return f"{_so(ms)} ms" if ms < 1000 else f"{_so(ms / 1000, 1)} s"


def _phan_tram(x: float | None) -> str:
    return "—" if x is None else f"{_so(100 * x)}%"


def _ti_le(a: float, b: float) -> str:
    return f"× {_so(a / b, 2)}"


def _ten_dong(r: dict[str, Any]) -> str:
    """Tên dòng trong bảng: model kèm tải — embed câu hỏi và embed đoạn là hai việc khác cỡ."""
    if r["vai"] == "rerank":
        return f"{r['model']} — 20 cặp"
    return f"{r['model']} — {TEN_TAI[r.get('tai', 'cau-hoi')]}"


def _nguong(r: dict[str, Any]) -> str:
    """Ngưỡng §5.3 là của đường chat — nhúng đoạn lúc nạp kho (UC019) không có ngưỡng."""
    if r.get("tai") == "doan":
        return "— (nạp kho)"
    return f"{NGUONG_KE_HOACH_MS[r['vai']]} ms"


def _bang_chinh(lan: list[dict[str, Any]]) -> list[str]:
    dong = [
        "## Bảng chính",
        "",
        "| Model — tải | vCPU | Chế độ | `OMP_NUM_THREADS` | Luồng ORT tạo / cả tiến trình² | Mẫu "
        "| p50 | p95 | Lâu nhất | RSS nạp / đỉnh | Chu kỳ bị chặn | Lõi dùng TB | Ngưỡng¹ |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in lan:
        cg = r["cgroup"]
        dong.append(
            f"| {r['ten']} | {_so(r['vcpu_cgroup'])} | {r['che_do']} | {r['omp_num_threads']} "
            f"| +{r['luong_ort_tao']} / {r.get('luong_cuoi', '—')} | {r['so_mau']} "
            f"| {_thoi_gian(r['p50_ms'])} | **{_thoi_gian(r['p95_ms'])}** "
            f"| {_thoi_gian(r['max_ms'])} | {r['rss_nap_mb']} / {r['rss_dinh_mb']} MB "
            f"| {_phan_tram(cg.get('ti_le_bi_chan'))} | {_so(cg.get('loi_dung_tb'), 2)} "
            f"| {_nguong(r)} |"
        )
    return dong + [
        "",
        "¹ Ngưỡng p95 §5.3 — số kế hoạch, **chưa áp dụng** (người dùng chốt 11/10/2026: độ trễ "
        "chưa là cổng).",
        "² Luồng ORT tạo = chênh `Threads` trước/sau khi nạp session; cả tiến trình = `Threads` "
        "cuối vòng đo (gồm luồng chính, pool của `tokenizers`).",
        "",
    ]


def _bang_ghim(theo: dict[tuple[str, float, str], dict[str, Any]]) -> list[str]:
    dong = [
        "## Ghim luồng ↔ để mặc định",
        "",
        "| Model — tải | vCPU | Luồng ORT ghim / mặc định | p50 ghim / mặc định "
        "| p95 ghim / mặc định | p95 mặc định ÷ ghim | Chu kỳ bị chặn ghim / mặc định |",
        "|---|---|---|---|---|---|---|",
    ]
    for (ten, vcpu, che_do), g in theo.items():
        m = theo.get((ten, vcpu, "mac-dinh"))
        if che_do != "ghim" or m is None:
            continue
        dong.append(
            f"| {ten} | {_so(vcpu)} | +{g['luong_ort_tao']} / +{m['luong_ort_tao']} "
            f"| {_thoi_gian(g['p50_ms'])} / {_thoi_gian(m['p50_ms'])} "
            f"| {_thoi_gian(g['p95_ms'])} / {_thoi_gian(m['p95_ms'])} "
            f"| **{_ti_le(m['p95_ms'], g['p95_ms'])}** "
            f"| {_phan_tram(g['cgroup'].get('ti_le_bi_chan'))} / "
            f"{_phan_tram(m['cgroup'].get('ti_le_bi_chan'))} |"
        )
    return dong + [""]


def _bang_vcpu(theo: dict[tuple[str, float, str], dict[str, Any]]) -> list[str]:
    """So các mức vCPU trong cùng chế độ — embed/rerank đo 2 và 4, router đo thêm 1."""
    nhom: dict[tuple[str, str], dict[float, dict[str, Any]]] = {}
    for (ten, vcpu, che_do), r in theo.items():
        nhom.setdefault((ten, che_do), {})[vcpu] = r
    dong = [
        "## Theo mức vCPU (cùng chế độ)",
        "",
        "| Model — tải | Chế độ | vCPU | p50 | p95 | p95 ÷ mức thấp nhất | Lõi dùng TB |",
        "|---|---|---|---|---|---|---|",
    ]
    for (ten, che_do), muc in nhom.items():
        if len(muc) < 2:
            continue
        ds = [muc[v] for v in sorted(muc)]
        p95_thap = ds[0]["p95_ms"]
        dong.append(
            f"| {ten} | {che_do} | {' / '.join(_so(r['vcpu_cgroup']) for r in ds)} "
            f"| {' / '.join(_thoi_gian(r['p50_ms']) for r in ds)} "
            f"| {' / '.join(_thoi_gian(r['p95_ms']) for r in ds)} "
            f"| **{' / '.join(_ti_le(r['p95_ms'], p95_thap) for r in ds)}** "
            f"| {' / '.join(_so(r['cgroup'].get('loi_dung_tb'), 2) for r in ds)} |"
        )
    return dong + [""]


def _bang_lap(lan: list[dict[str, Any]]) -> list[str]:
    """Lượt đầu ↔ lượt lặp của cùng cấu hình — biên trôi theo tải máy, chênh nhỏ hơn là nhiễu."""
    theo: dict[tuple[str, float, str], list[dict[str, Any]]] = {}
    for r in lan:
        theo.setdefault((r["ten"], r["vcpu_cgroup"], r["che_do"]), []).append(r)
    dong = [
        "## Lượt đầu ↔ lượt lặp (biên trôi)",
        "",
        "| Model — tải | vCPU | Chế độ | p95 lượt đầu / lặp | Chênh p95 |",
        "|---|---|---|---|---|",
    ]
    co = False
    for (ten, vcpu, che_do), ds in theo.items():
        if len(ds) < 2:
            continue
        co = True
        chenh = [_so(100 * (r["p95_ms"] / ds[0]["p95_ms"] - 1), 1) + "%" for r in ds[1:]]
        dong.append(
            f"| {ten} | {_so(vcpu)} | {che_do} "
            f"| {' / '.join(_thoi_gian(r['p95_ms']) for r in ds)} | {' / '.join(chenh)} |"
        )
    return dong + [""] if co else []


def _bang_chang(router: list[dict[str, Any]]) -> list[str]:
    """Router: băm n-gram (Python, một luồng) ↔ ``run`` của ONNX Runtime trong cùng một mẫu."""
    dong = [
        "## Router — hai chặng của một mẫu",
        "",
        "| vCPU | Chế độ | Băm p50 / p95 | `run` p50 / p95 | Cả mẫu p95 "
        "| Phần thời gian của `run` |",
        "|---|---|---|---|---|---|",
    ]
    for r in router:
        tong = sum(m["ms"] for m in r["mau"])
        run = sum(m["run_ms"] for m in r["mau"])
        dong.append(
            f"| {_so(r['vcpu_cgroup'])} | {r['che_do']} "
            f"| {_thoi_gian(r['bam']['p50_ms'])} / {_thoi_gian(r['bam']['p95_ms'])} "
            f"| {_thoi_gian(r['luot_run']['p50_ms'])} / {_thoi_gian(r['luot_run']['p95_ms'])} "
            f"| {_thoi_gian(r['p95_ms'])} | {_phan_tram(run / tong)} |"
        )
    return dong + [""]


def _bang_do_dai(rerank: list[dict[str, Any]]) -> list[str]:
    nhom_cot = " | ".join(f"{a}–{b} token: số cặp · p50" for a, b in NHOM_DO_DAI)
    dong = [
        "## Rerank — một lượt `run` (một cặp) theo độ dài",
        "",
        f"| vCPU | Chế độ | {nhom_cot} | Phần thời gian của cặp > 256 token |",
        "|---|---|" + "---|" * len(NHOM_DO_DAI) + "---|",
    ]
    for r in rerank:
        o = []
        for a, b in NHOM_DO_DAI:
            nhom = [ms for n, ms in r["luot"] if a <= n <= b]
            o.append(f"{len(nhom)} · {_thoi_gian(phan_vi(nhom, 0.5))}" if nhom else "0 · —")
        tong = sum(ms for _, ms in r["luot"])
        dai = sum(ms for n, ms in r["luot"] if n > 256)
        dong.append(
            f"| {_so(r['vcpu_cgroup'])} | {r['che_do']} | {' | '.join(o)} "
            f"| {_phan_tram(dai / tong)} |"
        )
    return dong + [""]


def bang(args: argparse.Namespace) -> None:
    lan = [json.loads(Path(t).read_text(encoding="utf-8")) for t in args.tep]
    lan.sort(key=lambda r: r["thoi_diem"])
    for r in lan:
        r["ten"] = _ten_dong(r)

    dong = [
        f"# Benchmark CPU — {', '.join(sorted({r['nhan'] for r in lan}))}",
        "",
        "## Điều kiện đo",
        "",
        "| # | Đo xong lúc | Model — tải | vCPU | Chế độ | Tải VM lúc bắt đầu "
        "| Tải máy chủ lúc bắt đầu | Nạp | Đo |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(lan, 1):
        dong.append(
            f"| {i} | {r['thoi_diem']} | {r['ten']} | {_so(r['vcpu_cgroup'])} | {r['che_do']} "
            f"| {' / '.join(_so(x, 2) for x in r['tai_vm'])} | {r['tai_may_chu'] or '—'} "
            f"| {_so(r['giay_nap'], 1)} s | {_so(r['giay_do'])} s |"
        )
    r0 = lan[0]
    dong += [
        "",
        f"ONNX Runtime {r0['ort']} · {r0['kien_truc']} · VM nhìn thấy {r0['cpu_vm_nhin_thay']} CPU."
        " Mẫu = một yêu cầu (embed: một câu hỏi hoặc một đoạn; rerank: một câu hỏi × 20 cặp,"
        " lô 1; router: một câu, băm + một lượt `run`). Phân vị theo hạng gần nhất.",
        "",
    ]
    dong += _bang_chinh(lan)
    dong += _bang_lap(lan)

    # Lượt ĐẦU của mỗi (dòng, vCPU, chế độ) là lượt dùng để so. Lượt chạy lặp lại cuối buổi để
    # kiểm số có trôi theo tải máy hay không — chỉ ghi ở bảng chính, không chọn lượt đẹp hơn.
    theo: dict[tuple[str, float, str], dict[str, Any]] = {}
    for r in lan:
        theo.setdefault((r["ten"], r["vcpu_cgroup"], r["che_do"]), r)
    dong += _bang_ghim(theo)
    dong += _bang_vcpu(theo)
    rerank = [r for r in theo.values() if r["vai"] == "rerank"]
    if rerank:
        dong += _bang_do_dai(rerank)
    router = [r for r in theo.values() if r["vai"] == "classify"]
    if router:
        dong += _bang_chang(router)

    noi_dung = "\n".join(dong)
    if args.ra:
        Path(args.ra).write_text(noi_dung, encoding="utf-8")
        print(f"Đã ghi {args.ra}")
    else:
        sys.stdout.write(noi_dung)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    con = p.add_subparsers(dest="lenh", required=True)

    c = con.add_parser("chay", help="đo một cấu hình (trong container ai-inference)")
    c.add_argument("--vai", choices=["embed", "rerank", "classify"], required=True)
    c.add_argument("--che-do", choices=["ghim", "mac-dinh"], required=True)
    c.add_argument("--tai", choices=["cau-hoi", "doan"], default="cau-hoi", help="chỉ cho embed")
    c.add_argument("--nhan", required=True, help="tiền tố tên tệp kết quả, vd. n15")
    c.add_argument("--eval", default="eval", help="thư mục có golden_set + rerank_cap_100x20")
    c.add_argument("--ra", default="reports/eval")
    c.add_argument("--so-cau", type=int, default=30, help="số dòng đầu rerank_cap_100x20.jsonl")
    c.add_argument("--so-ung-vien", type=int, default=20)
    c.add_argument(
        "--warmup", type=int, default=None, help="mặc định: embed 10, rerank 2, classify 20"
    )
    c.add_argument(
        "--vong", type=int, default=None,
        help="mặc định: embed câu hỏi 3, classify 10, còn lại 1",
    )

    b = con.add_parser("bang", help="gộp các tệp JSON thành bảng Markdown (chạy trên máy)")
    b.add_argument("tep", nargs="+")
    b.add_argument("--ra", help="tệp .md; bỏ trống thì in ra màn hình")

    args = p.parse_args()
    if args.lenh == "bang":
        bang(args)
        return
    if args.vai != "embed" and args.tai != "cau-hoi":
        p.error("--tai chỉ dùng cho embed")
    if args.warmup is None:
        args.warmup = {"embed": 10, "rerank": 2, "classify": 20}[args.vai]
    if args.vong is None:
        # Router: một mẫu dưới 1 ms — 10 vòng (1.120 mẫu) gần như không tốn thời gian (§9.1).
        vong = {("embed", "cau-hoi"): 3, ("classify", "cau-hoi"): 10}
        args.vong = vong.get((args.vai, args.tai), 1)
    chay(args)


if __name__ == "__main__":
    main()
