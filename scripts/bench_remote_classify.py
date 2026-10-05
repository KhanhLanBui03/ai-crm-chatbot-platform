#!/usr/bin/env python3
"""[R&D] Đo p95 bước phân loại qua đường REMOTE ai-service -> ai-classify (Ngày 7, Dev B).

Ngân sách §5.3: p95 bước phân loại ≤ 60 ms, tính cả đi về trên mạng.

Trước khi chạy:
    docker compose -f inference/compose.inference.yml up -d --build ai-classify
    curl http://localhost:8083/ready        # phải 200, router đã nạp

    python scripts/bench_remote_classify.py [--url http://localhost:8083] [--rounds 3]

Đo ba chế độ, 200 câu test người thật mỗi vòng, warmup 10:
- ``seq_client_hien_tai``: tuần tự qua ``RemoteClassifyClient`` của ai-service — ĐÚNG đường
  production đang dùng (client mở kết nối HTTP mới cho mỗi lần gọi).
- ``seq_giu_ket_noi``: tuần tự, một ``httpx.AsyncClient`` dùng lại — tách phần chi phí mở kết nối.
- ``conc5_client_hien_tai``: 5 request đồng thời qua client hiện tại — tải nhẹ.

Kết quả: ``reports/eval/remote_classify_latency.json``. Số đo là của môi trường chạy script
(vd Docker Desktop trên Windows có lớp mạng ảo) — ghi kèm khi trích dẫn.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import sys
import time
from pathlib import Path

import httpx
import numpy as np

sys.path.insert(0, str(Path("ai-service").resolve()))
from src.ai.inference.clients import RemoteClassifyClient  # noqa: E402

BUDGET_MS = 60.0
OUT = Path("reports/eval/remote_classify_latency.json")


def _stats(ms: list[float]) -> dict:
    a = np.array(ms)
    return {
        "n": len(ms),
        "p50_ms": round(float(np.percentile(a, 50)), 2),
        "p95_ms": round(float(np.percentile(a, 95)), 2),
        "p99_ms": round(float(np.percentile(a, 99)), 2),
        "max_ms": round(float(a.max()), 2),
        "within_budget_60ms": bool(np.percentile(a, 95) <= BUDGET_MS),
    }


async def _timed(coro) -> tuple[float, dict]:
    t0 = time.perf_counter()
    res = await coro
    return (time.perf_counter() - t0) * 1000, res


async def run(url: str, texts: list[str], rounds: int) -> dict:
    client = RemoteClassifyClient(base_url=url)
    tiers: dict[str, int] = {}

    for t in texts[:10]:  # warmup
        await client.classify(t)

    seq = []
    for _ in range(rounds):
        for t in texts:
            ms, res = await _timed(client.classify(t))
            seq.append(ms)
            tiers[res["tier_used"]] = tiers.get(res["tier_used"], 0) + 1

    keep = []
    async with httpx.AsyncClient(base_url=url, timeout=5.0) as http:
        for t in texts[:10]:
            await http.post("/v1/classify", json={"text": t})
        for _ in range(rounds):
            for t in texts:
                t0 = time.perf_counter()
                (await http.post("/v1/classify", json={"text": t})).raise_for_status()
                keep.append((time.perf_counter() - t0) * 1000)

    conc = []
    sem = asyncio.Semaphore(5)

    async def one(t: str) -> None:
        async with sem:
            ms, _ = await _timed(client.classify(t))
            conc.append(ms)

    for _ in range(rounds):
        await asyncio.gather(*(one(t) for t in texts))

    return {
        "seq_client_hien_tai": _stats(seq),
        "seq_giu_ket_noi": _stats(keep),
        "conc5_client_hien_tai": _stats(conc),
        "tier_breakdown_seq": {k: v // rounds for k, v in tiers.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8083")
    ap.add_argument("--rounds", type=int, default=3)
    args = ap.parse_args()

    ready = httpx.get(f"{args.url}/ready", timeout=5.0)
    if ready.status_code != 200:
        print(f"ai-classify chưa sẵn sàng ({ready.status_code}): {ready.text}", file=sys.stderr)
        return 1

    texts = [json.loads(line)["text"] for line in Path("data/intent_test_human.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    result = asyncio.run(run(args.url, texts, args.rounds))
    report = {
        "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target": args.url,
        "ready": ready.json(),
        "environment": f"{platform.system()} {platform.release()} · {platform.processor() or platform.machine()} · client chạy trên host, ai-classify trong Docker (cpus=2, OMP_NUM_THREADS=2)",
        "budget_p95_ms": BUDGET_MS,
        "texts": len(texts),
        "rounds": args.rounds,
        **result,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'Chế độ':26} {'n':>5} {'p50':>8} {'p95':>8} {'p99':>8}  ≤60ms?")
    for k in ("seq_client_hien_tai", "seq_giu_ket_noi", "conc5_client_hien_tai"):
        s = report[k]
        print(f"{k:26} {s['n']:>5} {s['p50_ms']:>8} {s['p95_ms']:>8} {s['p99_ms']:>8}  {'ĐẠT' if s['within_budget_60ms'] else 'KHÔNG'}")
    print(f"Tầng xử lý (mỗi vòng 200 câu): {report['tier_breakdown_seq']}")
    print(f"-> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
