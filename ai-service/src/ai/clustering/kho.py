"""UC038 — truy vấn của công việc phân cụm chủ đề (bảng V215). [PRODUCTION]

Mọi hàm nhận một session ĐÃ GẮN tenant (``get_tenant_session``) — RLS FORCE chặn doanh nghiệp khác,
và câu SQL vẫn lọc ``tenant_id`` tường minh (phòng thủ hai lớp như truy vấn vector, ADR-0007).
Riêng ``tenant_co_hoi_thoai`` chạy trong phiên hệ thống, qua hàm SECURITY DEFINER.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class CauDau:
    conversation_id: UUID
    cau_hoi: str


@dataclass(frozen=True)
class CumDaDatTen:
    nhan: str
    conversation_ids: list[UUID]


async def tenant_co_hoi_thoai(session: AsyncSession, tu: datetime) -> list[tuple[str, int]]:
    rs = await session.execute(text("SELECT tenant_id, so_hoi_thoai FROM ai.tenant_co_hoi_thoai(:tu)"), {"tu": tu})
    return [(str(r.tenant_id), int(r.so_hoi_thoai)) for r in rs]


async def cau_dau_moi_hoi_thoai(
    session: AsyncSession, tenant_id: str, tu: datetime, den: datetime
) -> list[CauDau]:
    """Câu hỏi của lượt ĐẦU mỗi hội thoại trong cửa sổ (đặc tả bước 2). ``user_query`` đã che dữ liệu
    cá nhân ở tầng ghi (UC040), nên số điện thoại hay email không đi sang tầng suy luận."""
    rs = await session.execute(
        text(
            """
            SELECT DISTINCT ON (conversation_id) conversation_id, user_query
              FROM ai.ai_interactions
             WHERE tenant_id = :t
               AND created_at >= :tu AND created_at < :den
               AND branch <> 'SUMMARY'
               AND user_query IS NOT NULL AND btrim(user_query) <> ''
             ORDER BY conversation_id, created_at
            """
        ),
        {"t": tenant_id, "tu": tu, "den": den},
    )
    return [CauDau(r.conversation_id, r.user_query) for r in rs]


async def ghi_ky_bo_qua(
    session: AsyncSession,
    *,
    tenant_id: str,
    bat_dau: datetime,
    tu: datetime,
    den: datetime,
    so_hoi_thoai: int,
    nguong: int,
    trang_thai: str,
    ly_do: str,
) -> UUID:
    rs = await session.execute(
        text(
            """
            INSERT INTO ai.topic_cluster_runs (tenant_id, started_at, finished_at, window_from, window_to,
                                               conversation_count, min_conversations, status, skip_reason)
            VALUES (:t, :bd, now(), :tu, :den, :so, :nguong, :tt, :ld)
            RETURNING id
            """
        ),
        {"t": tenant_id, "bd": bat_dau, "tu": tu, "den": den, "so": so_hoi_thoai, "nguong": nguong,
         "tt": trang_thai, "ld": ly_do},
    )
    return rs.scalar_one()


async def ghi_ky_xong(
    session: AsyncSession,
    *,
    tenant_id: str,
    bat_dau: datetime,
    tu: datetime,
    den: datetime,
    nguong: int,
    nguon_vector: str,
    silhouette: float,
    cach_dat_ten: str,
    cac_cum: Sequence[CumDaDatTen],
) -> UUID:
    so = sum(len(c.conversation_ids) for c in cac_cum)
    run_id = (
        await session.execute(
            text(
                """
                INSERT INTO ai.topic_cluster_runs (tenant_id, started_at, finished_at, window_from, window_to,
                                                   conversation_count, min_conversations, status, vector_source,
                                                   k, silhouette, naming_method)
                VALUES (:t, :bd, now(), :tu, :den, :so, :nguong, 'DONE', :nv, :k, :sil, :ten)
                RETURNING id
                """
            ),
            {"t": tenant_id, "bd": bat_dau, "tu": tu, "den": den, "so": so, "nguong": nguong,
             "nv": nguon_vector, "k": len(cac_cum), "sil": round(silhouette, 4), "ten": cach_dat_ten},
        )
    ).scalar_one()
    for cum in cac_cum:
        cluster_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO ai.topic_clusters (run_id, tenant_id, label, size)
                    VALUES (:r, :t, :nhan, :co) RETURNING cluster_id
                    """
                ),
                {"r": run_id, "t": tenant_id, "nhan": cum.nhan[:200], "co": len(cum.conversation_ids)},
            )
        ).scalar_one()
        await session.execute(
            text(
                """
                INSERT INTO ai.topic_cluster_assignments (run_id, cluster_id, tenant_id, conversation_id)
                SELECT :r, :c, :t, unnest(CAST(:ids AS uuid[]))
                """
            ),
            {"r": run_id, "c": cluster_id, "t": tenant_id, "ids": [str(i) for i in cum.conversation_ids]},
        )
    return run_id


async def ky_moi_nhat(session: AsyncSession, tenant_id: str) -> dict | None:
    """Kỳ DONE gần nhất kèm cụm và gán cụm. Chưa có kỳ DONE nào thì trả kỳ gần nhất (bị bỏ qua / hỏng)
    để màn biết VÌ SAO trống. Kỳ mới hỏng KHÔNG che kỳ DONE cũ — giữ nguyên nhãn cũ (luồng phụ 2.1)."""
    ky = (
        await session.execute(
            text(
                """
                SELECT id, started_at, finished_at, window_from, window_to, conversation_count,
                       min_conversations, status, skip_reason, vector_source, k, silhouette, naming_method
                  FROM ai.topic_cluster_runs
                 WHERE tenant_id = :t
                 ORDER BY (status = 'DONE') DESC, started_at DESC
                 LIMIT 1
                """
            ),
            {"t": tenant_id},
        )
    ).mappings().first()
    if ky is None:
        return None
    ket_qua = dict(ky)
    ket_qua["clusters"] = []
    ket_qua["assignments"] = []
    if ky["status"] != "DONE":
        return ket_qua
    cum = await session.execute(
        text("SELECT cluster_id, label, size FROM ai.topic_clusters WHERE tenant_id = :t AND run_id = :r "
             "ORDER BY size DESC, label"),
        {"t": tenant_id, "r": ky["id"]},
    )
    ket_qua["clusters"] = [dict(r) for r in cum.mappings()]
    gan = await session.execute(
        text("SELECT conversation_id, cluster_id FROM ai.topic_cluster_assignments "
             "WHERE tenant_id = :t AND run_id = :r"),
        {"t": tenant_id, "r": ky["id"]},
    )
    ket_qua["assignments"] = [dict(r) for r in gan.mappings()]
    return ket_qua
