"""UC038 bước 1–6 — một kỳ phân cụm chủ đề cho MỘT doanh nghiệp. [PRODUCTION]

    1. Khoá kỳ (advisory lock theo doanh nghiệp) — không cho hai kỳ chạy chồng
    2. Đọc câu hỏi đầu của mỗi hội thoại trong ``chu_de_cua_so_ngay`` ngày
    3. Dưới ``chu_de_toi_thieu_hoi_thoai`` hội thoại → bỏ kỳ, TOO_FEW_CONVERSATIONS (luồng phụ 1.1)
    4. Vector: bge-m3 qua ai-embed nếu ``AI_MODE=remote`` (đúng đặc tả); không có thì để ai-classify tự
       biến câu thành vector n-gram ký tự của router (nguồn thay thế — người dùng chốt 08/11/2026).
       KHÔNG BAO GIỜ phân cụm trên vector giả ``mock-hash`` — gom cụm trên số ngẫu nhiên cho ra tên chủ
       đề trông như thật mà vô nghĩa.
    5. ``POST /v1/topics/cluster`` ở ai-inference (giảm chiều 50, k 5…25, silhouette, hạt giống ghim)
    6. Đặt tên từng cụm (LLM nếu có, luật từ khoá nếu không) → ghi kỳ vào V215

Mọi kỳ đều được ghi, kể cả kỳ bị bỏ — màn hình đọc kỳ mới nhất để nói VÌ SAO chưa có cụm thay vì
hiện một bảng trống không lời giải thích. Kỳ hỏng không xoá kỳ cũ: java-core vẫn đọc được kỳ DONE
gần nhất (luồng phụ 2.1 "giữ nguyên nhãn cũ").
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from sqlalchemy import text

from src.ai.clustering import dat_ten, kho
from src.ai.config import Settings, get_settings
from src.ai.db.session import get_system_session, get_tenant_session
from src.ai.exceptions import AiServiceError
from src.ai.inference.clients import EmbedClient
from src.ai.integrations.llm import LLMChiuLoi
from src.ai.telemetry.metrics import topic_cluster_runs

logger = logging.getLogger(__name__)

LO_NHUNG = 32
NGUON_BGE = "bge-m3"


@dataclass(frozen=True)
class KetQuaKy:
    tenant_id: str
    trang_thai: str               # DONE | SKIPPED | FAILED | BUSY (kỳ khác đang chạy — không ghi gì)
    ly_do: str | None
    so_hoi_thoai: int
    k: int | None = None
    silhouette: float | None = None
    nguon_vector: str | None = None
    cach_dat_ten: str | None = None


class _BoKy(Exception):
    def __init__(self, trang_thai: str, ly_do: str) -> None:
        super().__init__(ly_do)
        self.trang_thai = trang_thai
        self.ly_do = ly_do


async def _vector_bge(embed: EmbedClient | None, cau: Sequence[str], s: Settings) -> list[list[float]] | None:
    """Vector bge-m3 nếu chạy thật; ``None`` nếu không có — để phía gọi chuyển sang nguồn thay thế."""
    if embed is None or s.ai_mode != "remote":
        return None
    vectors: list[list[float]] = []
    try:
        for i in range(0, len(cau), LO_NHUNG):
            kq = await embed.embed_batch(cau[i : i + LO_NHUNG])
            if kq.model_id.startswith("mock"):
                return None
            vectors.extend(kq.vectors)
    except AiServiceError as e:
        logger.warning("ai-embed không dùng được cho phân cụm (%s) — chuyển sang vector n-gram", e.code)
        return None
    return vectors


async def _phan_cum(http: httpx.AsyncClient, s: Settings, than: dict) -> dict:
    try:
        resp = await http.post(f"{s.inference_classify_url.rstrip('/')}/v1/topics/cluster", json=than,
                               timeout=s.chu_de_timeout_s)
    except httpx.HTTPError as e:
        raise _BoKy("FAILED", "CLUSTER_SERVICE_ERROR") from e
    if resp.status_code == 503:
        raise _BoKy("SKIPPED", "EMBED_UNAVAILABLE")
    if resp.status_code == 422:
        raise _BoKy("SKIPPED", "TOO_FEW_CONVERSATIONS")
    if resp.status_code >= 400:
        raise _BoKy("FAILED", "CLUSTER_SERVICE_ERROR")
    return resp.json()


async def chay_ky(
    tenant_id: str,
    *,
    http: httpx.AsyncClient,
    embed: EmbedClient | None = None,
    llm: LLMChiuLoi | None = None,
    settings: Settings | None = None,
    bay_gio: datetime,
    factory=None,
) -> KetQuaKy:
    s = settings or get_settings()
    den = bay_gio
    tu = den - timedelta(days=s.chu_de_cua_so_ngay)
    nguong = s.chu_de_toi_thieu_hoi_thoai

    # Khoá kỳ: giữ suốt kỳ trong một phiên hệ thống riêng. pg_try_* — kỳ thứ hai không chờ mà thôi luôn.
    async with get_system_session(factory) as khoa:
        duoc = (await khoa.execute(text("SELECT pg_try_advisory_xact_lock(hashtextextended(:k, 0))"),
                                   {"k": f"uc038:{tenant_id}"})).scalar_one()
        if not duoc:
            logger.info("Kỳ phân cụm của %s đang chạy ở nơi khác — bỏ qua", tenant_id)
            return KetQuaKy(tenant_id, "BUSY", None, 0)

        async with get_tenant_session(tenant_id, factory) as phien:
            cac_cau = await kho.cau_dau_moi_hoi_thoai(phien, tenant_id, tu, den)
        so = len(cac_cau)

        async def ghi_bo(trang_thai: str, ly_do: str) -> KetQuaKy:
            async with get_tenant_session(tenant_id, factory) as phien:
                await kho.ghi_ky_bo_qua(phien, tenant_id=tenant_id, bat_dau=bay_gio, tu=tu, den=den,
                                        so_hoi_thoai=so, nguong=nguong, trang_thai=trang_thai, ly_do=ly_do)
            topic_cluster_runs.labels(status=trang_thai, reason=ly_do).inc()
            logger.info("Kỳ phân cụm %s: %s %s (%d hội thoại, ngưỡng %d)", tenant_id, trang_thai, ly_do, so,
                        nguong)
            return KetQuaKy(tenant_id, trang_thai, ly_do, so)

        if so < nguong:
            return await ghi_bo("SKIPPED", "TOO_FEW_CONVERSATIONS")

        cau = [c.cau_hoi for c in cac_cau]
        try:
            vectors = await _vector_bge(embed, cau, s)
            than = {"vectors": vectors} if vectors is not None else {"texts": cau}
            kq = await _phan_cum(http, s, than)
        except _BoKy as e:
            return await ghi_bo(e.trang_thai, e.ly_do)
        nguon = NGUON_BGE if vectors is not None else kq["vector_source"]

        nhan = kq["labels"]
        dai_dien = {int(c): idx for c, idx in kq["representatives"].items()}
        cac_cum: list[kho.CumDaDatTen] = []
        so_llm = 0
        for c in sorted(set(nhan)):
            mau = [cau[i] for i in dai_dien.get(c, [])]
            ten = await dat_ten.bang_llm(llm, mau) if llm is not None else None
            if ten:
                so_llm += 1
            else:
                ten = dat_ten.theo_tu_khoa(mau)
            ids = [cac_cau[i].conversation_id for i, l in enumerate(nhan) if l == c]
            cac_cum.append(kho.CumDaDatTen(ten, ids))
        cach = "llm" if so_llm == len(cac_cum) else ("tu-khoa" if so_llm == 0 else "hon-hop")

        async with get_tenant_session(tenant_id, factory) as phien:
            await kho.ghi_ky_xong(phien, tenant_id=tenant_id, bat_dau=bay_gio, tu=tu, den=den, nguong=nguong,
                                  nguon_vector=nguon, silhouette=float(kq["silhouette"]), cach_dat_ten=cach,
                                  cac_cum=cac_cum)
    topic_cluster_runs.labels(status="DONE", reason="-").inc()
    logger.info("Kỳ phân cụm %s: DONE k=%d silhouette=%.4f nguồn=%s tên=%s (%d hội thoại)", tenant_id,
                len(cac_cum), kq["silhouette"], nguon, cach, so)
    return KetQuaKy(tenant_id, "DONE", None, so, len(cac_cum), float(kq["silhouette"]), nguon, cach)


async def chay_moi_tenant(
    *,
    http: httpx.AsyncClient,
    embed: EmbedClient | None = None,
    llm: LLMChiuLoi | None = None,
    settings: Settings | None = None,
    bay_gio: datetime,
    factory=None,
) -> list[KetQuaKy]:
    """Mỗi doanh nghiệp có hội thoại trong cửa sổ một kỳ riêng — không gộp dữ liệu nhiều doanh nghiệp
    vào một lần phân cụm. Một doanh nghiệp hỏng không chặn doanh nghiệp khác."""
    s = settings or get_settings()
    async with get_system_session(factory) as phien:
        cac_tenant = await kho.tenant_co_hoi_thoai(phien, bay_gio - timedelta(days=s.chu_de_cua_so_ngay))
    ket_qua = []
    for tenant_id, _ in cac_tenant:
        try:
            ket_qua.append(await chay_ky(tenant_id, http=http, embed=embed, llm=llm, settings=s,
                                         bay_gio=bay_gio, factory=factory))
        except Exception:  # noqa: BLE001 — một doanh nghiệp hỏng không làm mất kỳ của doanh nghiệp khác
            logger.exception("Kỳ phân cụm của %s hỏng", tenant_id)
            topic_cluster_runs.labels(status="FAILED", reason="EXCEPTION").inc()
    return ket_qua
