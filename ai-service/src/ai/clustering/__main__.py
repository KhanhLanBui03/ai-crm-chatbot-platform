"""Chạy tay một kỳ phân cụm chủ đề (UC038): ``python -m src.ai.clustering [--tenant <uuid>]``. [PRODUCTION]

Dành cho người vận hành (và demo) — không phải bề mặt API: không ai gửi ``tenant_id`` qua mạng vào đây.
Bỏ ``--tenant`` thì chạy cho mọi doanh nghiệp có hội thoại trong cửa sổ, như vòng nền hằng tuần.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID

import httpx

from src.ai.clustering import cong_viec
from src.ai.config import get_settings
from src.ai.inference.clients import tao_embed_client
from src.ai.integrations.llm import tao_llm_chiu_loi
from src.ai.telemetry.logging import setup_logging


async def _chay(tenant: str | None) -> list[dict]:
    s = get_settings()
    setup_logging(s.log_level)
    embed = tao_embed_client(s)
    llm = tao_llm_chiu_loi(s) if s.llm_mode == "remote" else None
    try:
        async with httpx.AsyncClient() as http:
            bay_gio = datetime.now(UTC)
            if tenant:
                kq = [await cong_viec.chay_ky(tenant, http=http, embed=embed, llm=llm, settings=s, bay_gio=bay_gio)]
            else:
                kq = await cong_viec.chay_moi_tenant(http=http, embed=embed, llm=llm, settings=s, bay_gio=bay_gio)
    finally:
        await embed.aclose()
        if llm is not None:
            await llm.aclose()
    return [asdict(k) for k in kq]


def main() -> None:
    p = argparse.ArgumentParser(description="UC038 — chạy một kỳ phân cụm chủ đề hội thoại")
    p.add_argument("--tenant", type=UUID, help="chỉ chạy cho doanh nghiệp này")
    a = p.parse_args()
    if sys.platform == "win32":   # psycopg async không chạy trên ProactorEventLoop
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    print(json.dumps(asyncio.run(_chay(str(a.tenant) if a.tenant else None)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
