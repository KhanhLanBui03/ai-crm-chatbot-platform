"""Gieo kho đo Ngày 6 — 19 tệp mẫu vào tenant gốc, rồi nhân bản sang tối đa 19 tenant nữa. [R&D]

    cd ai-service && source .venv/bin/activate
    # 1. Tenant gốc: phân tích + nhúng THẬT qua ai-embed
    AI_MODE=remote EMBED_URL=http://localhost:<cổng ai-embed> python -m tests.eval.gieo_kho nap
    # 2. Đo cấu hình "1 tenant", rồi nhân bản thành 20 tenant và DỰNG LẠI HNSW
    python -m tests.eval.gieo_kho nhan-ban --den 20
    # 3. Dọn toàn bộ tenant đo
    python -m tests.eval.gieo_kho xoa

Chạy bằng ``ai_app`` (role chịu RLS) theo ``DB_*`` trong ``.env`` — hoặc ``--dsn``. Mọi tenant đo có
UUID cố định ``eeeeeeee-0000-0000-0000-0000000000NN`` (NN = 01…20), không đụng tenant thật nào.

BỐN QUYẾT ĐỊNH
--------------
1. **Bỏ qua S3 và Kafka, KHÔNG bỏ qua chặng nào của đường ống.** Đoạn đi qua đúng các hàm của
   worker: ``phan_tich_tep`` → ``normalize_vi`` → ``chia_doan`` → ``nhung_va_ghi_theo_lo`` →
   ``chunk_repository.them_lo``. Chỉ khác đường vận chuyển tệp — thứ không ảnh hưởng nội dung đoạn
   hay vector. Đường Kafka có minh chứng riêng (``docs/report/uc019-ngay5-*.md``).
2. **Nhân bản bằng CHÉP vector, không nhúng lại.** bge-m3 là hàm tất định: cùng nội dung ra cùng
   vector, nhúng lại 19 lần chỉ tốn 19 lần thời gian CPU để ra đúng các dòng đó.
3. **19 tenant còn lại có nội dung GIỐNG HỆT tenant gốc** — ca khó nhất cho cả cô lập lẫn HNSW:
   láng giềng gần nhất của mọi câu hỏi có 95% là đoạn của tenant khác, nên HNSW (lọc tenant SAU khi
   quét) sẽ hụt nếu không có ``iterative_scan``. Kho thật của 20 SME khác nhau dễ hơn ca này.
4. **Bản 1 của chính sách đổi trả vào kho ở trạng thái ``ARCHIVED``** (version 1), bản 2 ``READY``
   (version 2) — đúng trạng thái kho sau khi UC020 lưu trữ bản cũ. Bộ vàng không bao giờ trỏ vào
   bản 1; nó ở đây để điều kiện ``status = 'READY'`` có việc để làm trong phép đo.

SAU KHI NHÂN BẢN PHẢI DỰNG LẠI HNSW (bằng ``crm_owner``) — chèn thêm 19× dòng vào một đồ thị đã
dựng cho đồ thị kém hơn dựng một lần trên tập đủ (``scripts/create_hnsw_index.sql``). Lệnh in ra ở
cuối ``nhan-ban``.
"""

import argparse
import asyncio
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.ai.config import Settings, get_settings
from src.ai.db import session as db_session
from src.ai.db.repositories import chunk_repository
from src.ai.inference.clients import EmbedClient, KetQuaNhung, tao_embed_client
from src.ai.rag.ingest.chia_doan import Doan
from src.ai.rag.ingest.nhung import nhung_va_ghi_theo_lo
from tests.eval.bo_vang import TEP_BI_THAY, KhoMau

SO_TENANT_TOI_DA = 20


def tenant_do(so: int) -> UUID:
    """Tenant đo thứ ``so`` (1 = tenant gốc, nơi bộ vàng được đo)."""
    if not 1 <= so <= SO_TENANT_TOI_DA:
        raise ValueError(f"tenant đo phải trong 1..{SO_TENANT_TOI_DA}, nhận {so}")
    return UUID(f"eeeeeeee-0000-0000-0000-{so:012d}")


TENANT_GOC = tenant_do(1)

_SQL_THEM_TAI_LIEU = text(
    """
    INSERT INTO knowledge.knowledge_documents (tenant_id, title, source_type, file_name, file_path,
        language, status, chunk_count, version, indexed_at)
    VALUES (ai.current_tenant(), :title, :source_type, :file_name, :file_path, :language, :status,
        :chunk_count, :version, now())
    RETURNING id
    """
)


async def _them_tai_lieu(session: AsyncSession, tenant: UUID, **cot) -> UUID:
    cot.setdefault("file_path", f"eval/{tenant}/{cot['file_name']}")
    return (await session.execute(_SQL_THEM_TAI_LIEU, cot)).scalar_one()


async def _so_tai_lieu(factory: async_sessionmaker, tenant: UUID) -> int:
    async with db_session.get_tenant_session(str(tenant), factory) as s:
        return (
            await s.execute(text("SELECT count(*) FROM knowledge.knowledge_documents"))
        ).scalar_one()


async def nap_tenant_goc(
    factory: async_sessionmaker, embed: EmbedClient, kho: KhoMau, *, co_lo: int = 32
) -> tuple[str, str, int]:
    """Nạp mọi tệp của ``kho`` vào tenant gốc. Trả ``(model_id, model_version, số đoạn)``.

    Mỗi tệp một transaction: tài liệu + mọi đoạn của nó cùng commit, hỏng giữa chừng thì không để
    lại tài liệu ``READY`` thiếu đoạn.
    """
    if await _so_tai_lieu(factory, TENANT_GOC):
        raise RuntimeError("Tenant gốc đã có tài liệu — chạy `xoa` trước nếu muốn nạp lại.")
    danh_tinh: set[tuple[str, str]] = set()
    tong = 0
    for tep, cac_doan in kho.doan.items():
        bi_thay = tep in TEP_BI_THAY
        async with db_session.get_tenant_session(str(TENANT_GOC), factory) as s:
            doc = await _them_tai_lieu(
                s,
                TENANT_GOC,
                title=kho.tieu_de[tep],
                source_type=kho.dinh_dang[tep],
                file_name=tep,
                language=kho.ngon_ngu[tep],
                status="ARCHIVED" if bi_thay else "READY",
                chunk_count=len(cac_doan),
                version=2 if tep == "chinh-sach-doi-tra-v2.md" else 1,
            )

            async def ghi_lo(lo, ket_qua: KetQuaNhung, s=s, doc=doc) -> None:
                danh_tinh.add((ket_qua.model_id, ket_qua.model_version))
                await chunk_repository.them_lo(
                    s,
                    doc,
                    lo,
                    ket_qua.vectors,
                    embedding_model=ket_qua.model_id,
                    embedding_version=ket_qua.model_version,
                )

            tong += await nhung_va_ghi_theo_lo(cac_doan, embed, ghi_lo, co_lo=co_lo)
        print(f"  {tep}: {len(cac_doan)} đoạn", flush=True)
    if len(danh_tinh) != 1:
        raise RuntimeError(f"ai-embed đổi danh tính giữa chừng: {sorted(danh_tinh)}")
    model_id, model_version = danh_tinh.pop()
    return model_id, model_version, tong


_SQL_DOC_KHO_GOC = text(
    """
    SELECT d.id, d.title, d.source_type, d.file_name, d.language, d.status, d.chunk_count,
           d.version, c.chunk_index, c.content, c.heading, c.page_number, c.token_count,
           c.embedding::text AS embedding, c.embedding_model, c.embedding_version
      FROM knowledge.knowledge_documents d
      JOIN knowledge.knowledge_chunks c ON c.document_id = d.id
     ORDER BY d.file_name, c.chunk_index
    """
)


async def nhan_ban(factory: async_sessionmaker, den: int) -> list[UUID]:
    """Chép tenant gốc sang tenant 2..``den`` còn trống. Trả các tenant vừa gieo."""
    async with db_session.get_tenant_session(str(TENANT_GOC), factory) as s:
        dong = (await s.execute(_SQL_DOC_KHO_GOC)).all()
    if not dong:
        raise RuntimeError("Tenant gốc chưa có đoạn nào — chạy `nap` trước.")
    theo_tai_lieu: dict[UUID, list] = {}
    for r in dong:
        theo_tai_lieu.setdefault(r.id, []).append(r)

    moi: list[UUID] = []
    for so in range(2, den + 1):
        tenant = tenant_do(so)
        if await _so_tai_lieu(factory, tenant):
            continue
        async with db_session.get_tenant_session(str(tenant), factory) as s:
            for cac_dong in theo_tai_lieu.values():
                r0 = cac_dong[0]
                doc = await _them_tai_lieu(
                    s,
                    tenant,
                    title=r0.title,
                    source_type=r0.source_type,
                    file_name=r0.file_name,
                    language=r0.language,
                    status=r0.status,
                    chunk_count=r0.chunk_count,
                    version=r0.version,
                )
                await chunk_repository.them_lo(
                    s,
                    doc,
                    [
                        Doan(r.chunk_index, r.content, r.heading, r.page_number, r.token_count)
                        for r in cac_dong
                    ],
                    [[float(x) for x in r.embedding.strip("[]").split(",")] for r in cac_dong],
                    embedding_model=r0.embedding_model,
                    embedding_version=r0.embedding_version,
                )
        moi.append(tenant)
    return moi


async def xoa(factory: async_sessionmaker) -> int:
    """Xoá tài liệu (đoạn đi theo ``ON DELETE CASCADE``) của mọi tenant đo. Trả số tài liệu."""
    tong = 0
    for so in range(1, SO_TENANT_TOI_DA + 1):
        async with db_session.get_tenant_session(str(tenant_do(so)), factory) as s:
            tong += (await s.execute(text("DELETE FROM knowledge.knowledge_documents"))).rowcount
    return tong


_DUNG_LAI_HNSW = """
Dựng lại HNSW trên tập đủ (bằng crm_owner):
  docker compose exec -T postgres psql -U crm_owner -d thesis_crm \\
      -c "DROP INDEX CONCURRENTLY IF EXISTS knowledge.ix_chunk_embedding"
  docker compose exec -T postgres psql -U crm_owner -d thesis_crm \\
      < ai-service/scripts/create_hnsw_index.sql
"""


async def _main(args: argparse.Namespace) -> None:
    cau_hinh: Settings = get_settings()
    engine = db_session.tao_engine(args.dsn)
    factory = db_session.tao_session_factory(engine)
    try:
        if args.lenh == "nap":
            kho = KhoMau()
            embed = tao_embed_client(cau_hinh)
            try:
                model_id, version, tong = await nap_tenant_goc(
                    factory, embed, kho, co_lo=cau_hinh.kb_embed_batch
                )
            finally:
                await embed.aclose()
            print(f"\nTenant gốc {TENANT_GOC}: {len(kho.doan)} tài liệu, {tong} đoạn")
            print(f"embedding_model = {model_id!r} · embedding_version = {version!r}")
            print("→ ghi hai giá trị này vào `nhung:` của các file trong tests/eval/configs/")
            print(_DUNG_LAI_HNSW)
        elif args.lenh == "nhan-ban":
            moi = await nhan_ban(factory, args.den)
            print(f"Đã gieo {len(moi)} tenant mới (tổng {args.den} tenant đo).")
            print(_DUNG_LAI_HNSW)
        else:
            print(f"Đã xoá {await xoa(factory)} tài liệu của các tenant đo.")
    finally:
        await engine.dispose()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dsn", help="DSN postgresql+psycopg:// của ai_app (mặc định: .env)")
    lenh = ap.add_subparsers(dest="lenh", required=True)
    lenh.add_parser("nap", help="phân tích + nhúng 19 tệp mẫu vào tenant gốc")
    p_nb = lenh.add_parser("nhan-ban", help="chép tenant gốc sang tenant 2..N")
    p_nb.add_argument("--den", type=int, default=SO_TENANT_TOI_DA)
    lenh.add_parser("xoa", help="xoá mọi tenant đo")
    asyncio.run(_main(ap.parse_args()))


if __name__ == "__main__":
    main()
