"""Minh chứng UC020 trên hạ tầng thật: tải lên → nạp → nạp lại bằng bản bóng, hỏi kho. [R&D]

    docker compose up -d postgres rustfs-init
    docker compose -f inference/compose.inference.yml up -d ai-embed
    cd ai-service && source .venv/bin/activate
    AI_MODE=remote EMBED_URL=http://localhost:8091 python -m src.entrypoint        # cửa sổ khác
    AI_MODE=remote EMBED_URL=http://localhost:8091 python -m tests.eval.minh_chung_uc020

Khác test tích hợp (``tests/integration/test_quan_ly_kho.py``, nhúng mock) ở chỗ dùng ai-embed THẬT,
RustFS THẬT, và gọi API qua HTTP như java-core sẽ gọi. Tenant riêng ``dddddddd-…-d020`` — không đụng
kho đo của bộ vàng. Bộ quét và lượt nạp chạy trong tiến trình này thay cho worker (không cần Kafka).

In ra: số lần hỏi kho trong lúc nạp lại, số lần thấy 0 đoạn (phải là 0), số lần thấy CẢ hai bản
cùng lúc (phải là 0).
"""

import asyncio
import io
import time
from pathlib import Path
from uuid import UUID, uuid4

import httpx

from src.ai import service
from src.ai.config import get_settings
from src.ai.db import session as db_session
from src.ai.inference.clients import tao_embed_client
from src.ai.integrations import object_storage
from src.ai.rag.retrieve.hybrid import tim_kiem_lai
from src.ai.rag.tsquery import build_tsquery

TENANT = "dddddddd-0000-0000-0000-00000000d020"
TEP = Path(__file__).resolve().parents[3] / "data" / "kb_samples" / "chinh-sach-tra-gop.pdf"
CAU_HOI = "trả góp qua thẻ tín dụng mất phí chuyển đổi bao nhiêu"


async def chay(api: str) -> None:
    s = get_settings()
    h = {"X-Tenant-Id": TENANT}
    du_lieu = TEP.read_bytes()
    key = f"{TENANT}/{uuid4()}/{TEP.name}"
    kho = object_storage._client_mac_dinh()
    kho.put_object(s.s3_bucket, key, io.BytesIO(du_lieu), len(du_lieu))

    async with httpx.AsyncClient(base_url=api, timeout=60) as c:
        r = await c.post("/v1/ai/kb/documents", headers=h, json={
            "file_uri": f"s3://{s.s3_bucket}/{key}", "file_name": TEP.name,
            "title": "Chính sách trả góp 0% (minh chứng UC020)",
        })
        print("UC018 tải lên:", r.status_code, r.json()["status"], "version", r.json()["version"])
        cu = UUID(r.json()["document_id"])

        embed = tao_embed_client(s)
        try:
            kq = await service.nap_tai_lieu(TENANT, cu, embed=embed)
            print("nạp lần đầu:", kq.trang_thai, kq.so_doan, "đoạn")

            r = await c.post(f"/v1/documents/{cu}/reindex", headers=h)
            moi = UUID(r.json()["job_id"])
            print("nạp lại:", r.status_code, "bản bóng version", r.json()["version"])
            r2 = await c.post(f"/v1/documents/{cu}/reindex", headers=h)
            r3 = await c.delete(f"/v1/documents/{cu}", headers=h)
            print("nạp lại chồng:", r2.status_code, r2.json()["code"], "· gỡ giữa chừng:",
                  r3.status_code, r3.json()["code"])

            nhung = await embed.embed_batch([CAU_HOI])
            quan_sat: list[tuple[int, int]] = []

            async def hoi() -> None:
                async with db_session.get_tenant_session(TENANT) as phien:
                    ds = await tim_kiem_lai(
                        phien, vector=nhung.vectors[0], tsquery=build_tsquery(CAU_HOI),
                        embedding_model=nhung.model_id, embedding_version=nhung.model_version, k=10,
                    )
                quan_sat.append((sum(d.document_id == cu for d in ds),
                                 sum(d.document_id == moi for d in ds)))

            dung = asyncio.Event()

            async def lien_tuc() -> None:
                while not dung.is_set():
                    await hoi()
                    await asyncio.sleep(0.005)

            nen = asyncio.create_task(lien_tuc())
            bat_dau = time.perf_counter()
            nhat = [j for j in await service.quet_job_ket() if j.document_id == moi]
            kq = await service.nap_tai_lieu(TENANT, moi, embed=embed)
            dung.set()
            await nen
            await hoi()
            print(f"bộ quét nhặt bản bóng: {bool(nhat)} · nạp bản bóng: {kq.trang_thai}, "
                  f"{kq.so_doan} đoạn, {time.perf_counter() - bat_dau:.1f} s")
            print(f"hỏi kho {len(quan_sat)} lần · thấy 0 đoạn: "
                  f"{sum(a + b == 0 for a, b in quan_sat)} · thấy CẢ hai bản: "
                  f"{sum(a > 0 and b > 0 for a, b in quan_sat)} · chỉ bản cũ: "
                  f"{sum(a > 0 and b == 0 for a, b in quan_sat)} · chỉ bản mới: "
                  f"{sum(b > 0 and a == 0 for a, b in quan_sat)}")
        finally:
            await embed.aclose()

        for ten, x in (("bản cũ", cu), ("bản mới", moi)):
            d = (await c.get(f"/v1/documents/{x}", headers=h)).json()
            print(f"{ten}: {d['status']} · version {d['version']} · {d['chunk_count']} đoạn")


def main() -> None:
    import argparse

    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--api", default="http://localhost:8000")
    asyncio.run(chay(p.parse_args().api))


if __name__ == "__main__":
    main()
