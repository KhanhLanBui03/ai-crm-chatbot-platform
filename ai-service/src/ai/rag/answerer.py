"""[PRODUCTION] Nhánh trả lời từ tri thức — UC023 + UC025, hiện thực ``KnowledgeAnswerer``.

Cắm vào ``orchestrator/turn.py::run_turn`` ở bước 7 (ADR-0027: pipeline tuần tự, không LangGraph)::

    luật dò tìm / dữ liệu nghiệp vụ ─► nhúng ─► truy hồi lai (RRF) ─► [xếp lại nếu mơ hồ]
          │ (từ chối, 0 nhúng, 0 LLM)                                       │
          ▼                                         sàn liên quan ─┬─► từ chối, 0 LLM
                                                                   └─► LLM ─► hậu kiểm
                                                                               ─► cổng bám nguồn

BA LỐI RA, KHÔNG LỐI NÀO LÀ 5xx DO LLM
-------------------------------------
- **Từ chối** (UC025, ``rag/tu_choi.py``) — một trong bốn lý do, mẫu câu theo lý do. Ba chỗ không
  gọi LLM (luật trước truy hồi, sàn cosine) tính vào KPI "không gọi LLM"; hai chỗ sau LLM (mô hình
  nói không đủ căn cứ, cổng bám nguồn huỷ câu đã sinh) thì đã tốn một lượt.
- **Trả lời** — LLM sinh, hậu kiểm lọc trích dẫn, đo độ bám nguồn, che PII lạ, qua cổng bám nguồn.
- **Suy giảm** (``degraded=true``) — LLM không phục vụ được: trích nguyên văn đoạn liên quan nhất
  kèm trích dẫn của nó. Vẫn đúng sự thật (chép từ tài liệu), chỉ kém tự nhiên.

Nhúng hay CSDL hỏng thì lỗi đi ra ngoài như cũ (``run_turn`` ghi FAILED rồi ném): không có câu
trả lời "suy giảm" trung thực nào khi chưa có lấy một đoạn tài liệu.

DÙNG ``request.message``, KHÔNG DÙNG ``question`` ĐÃ CHUẨN HOÁ TEENCODE
--------------------------------------------------------------------
``run_turn`` truyền vào ``question`` đã qua ``normalize_vietnamese_text`` của guardrails (mở rộng
"ko" → "không"…). Truy hồi thì dùng câu gốc qua ``normalize_vi`` — CÙNG hàm chuẩn hoá lúc nạp
(rag-eval.md: một hàm cho cả hai đầu) và đúng đường đã đo ở thí nghiệm E3 (dense 0,800 · hybrid
0,740). Đổi đầu vào truy hồi là đổi một biến chưa đo; muốn đổi thì đo lại E3 trước.
"""

import functools
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.ai.config import Settings, get_settings
from src.ai.db.repositories import interaction_repository
from src.ai.db.session import get_tenant_session
from src.ai.guardrails import mask_pii
from src.ai.inference.clients import EmbedClient, KetQuaNhung, RerankClient
from src.ai.integrations.llm import LLMChiuLoi, LLMKhongKhaDung
from src.ai.orchestrator.turn import KnowledgeAnswer
from src.ai.rag.chuan_hoa import normalize_vi
from src.ai.rag.generate.hau_kiem import hau_kiem
from src.ai.rag.generate.loi_nhac import KHONG_DU_CAN_CU, dung_loi_nhac
from src.ai.rag.rerank.quyet_dinh import SO_UNG_VIEN_RERANK, needs_rerank, xep_lai
from src.ai.rag.retrieve.hybrid import DoanTimDuoc, tim_kiem_lai
from src.ai.rag.tsquery import build_tsquery
from src.ai.rag.tu_choi import (
    CAU_CHUYEN_GIAO_LAP_LAI,
    LOW_CONFIDENCE,
    LY_DO_TINH_LAP_LAI,
    NOT_COVERED,
    khong_bam_nguon,
    kiem_truoc_truy_hoi,
    search_or_abstain,
)
from src.ai.rag.tu_choi import CAU_TU_CHOI as MAU_TU_CHOI
from src.ai.schemas import ChatRequest, Citation

logger = logging.getLogger(__name__)

# (tenant_id, câu hỏi đã chuẩn hoá, vector câu hỏi, k) → top-k. Test tiêm bản giả, không cần CSDL.
TruyHoi = Callable[[str, str, KetQuaNhung, int], Awaitable[list[DoanTimDuoc]]]
# (tenant_id, conversation_id) → số lượt liền trước chưa trả lời được (UC025 luồng phụ 3.3).
DemTuChoi = Callable[[str, str], Awaitable[int]]

DO_DAI_TRICH = 200
DO_DAI_TRICH_SUY_GIAM = 400

CAU_TU_CHOI = MAU_TU_CHOI[NOT_COVERED]


@dataclass
class _DongHo:
    """Bấm giờ từng chặng — ``latency_breakdown`` của response."""

    _moc: float = field(default_factory=time.perf_counter)
    ket_qua: dict[str, int] = field(default_factory=dict)

    def ghi(self, chang: str) -> None:
        bay_gio = time.perf_counter()
        self.ket_qua[chang] = int((bay_gio - self._moc) * 1000)
        self._moc = bay_gio


def _trich(van_ban: str, toi_da: int) -> str:
    van_ban = " ".join(van_ban.split())
    return van_ban if len(van_ban) <= toi_da else van_ban[: toi_da - 1].rstrip() + "…"


def _trich_dan(doan: DoanTimDuoc) -> Citation:
    return Citation(
        chunk_id=doan.chunk_id,
        document_id=doan.document_id,
        title=doan.title,
        snippet=_trich(doan.content, DO_DAI_TRICH),
        score=round(doan.do_tuong_dong if doan.do_tuong_dong is not None else doan.diem_rrf, 4),
    )


async def truy_hoi_csdl(
    tenant_id: str,
    cau_hoi: str,
    nhung: KetQuaNhung,
    k: int,
    *,
    factory: async_sessionmaker[AsyncSession] | None = None,
) -> list[DoanTimDuoc]:
    """Truy hồi lai trên kho của ``tenant_id`` — đường production của ``TruyHoi``."""
    # get_tenant_session: set_config('app.tenant_id', …, true) CÙNG transaction với câu SQL.
    async with get_tenant_session(tenant_id, factory) as phien:
        return await tim_kiem_lai(
            phien,
            vector=nhung.vectors[0],
            tsquery=build_tsquery(cau_hoi),
            # Danh tính lấy từ phía ĐÃ SINH vector — hai không gian vector không được trộn.
            embedding_model=nhung.model_id,
            embedding_version=nhung.model_version,
            k=k,
        )


async def dem_tu_choi_csdl(
    tenant_id: str,
    conversation_id: str,
    *,
    factory: async_sessionmaker[AsyncSession] | None = None,
) -> int:
    """Đường production của ``DemTuChoi`` — đọc ``ai_interactions`` của hội thoại dưới RLS."""
    async with get_tenant_session(tenant_id, factory) as phien:
        return await interaction_repository.dem_tu_choi_lien_tiep(phien, conversation_id)


class RagAnswerer:
    def __init__(
        self,
        *,
        embed: EmbedClient,
        llm: LLMChiuLoi,
        settings: Settings | None = None,
        rerank: RerankClient | None = None,
        factory: async_sessionmaker[AsyncSession] | None = None,
        truy_hoi: TruyHoi | None = None,
        dem_tu_choi: DemTuChoi | None = None,
    ) -> None:
        self._embed = embed
        self._llm = llm
        self._settings = settings or get_settings()
        self._rerank = rerank if self._settings.rerank_enabled else None
        self._truy_hoi = truy_hoi or functools.partial(truy_hoi_csdl, factory=factory)
        self._dem_tu_choi = dem_tu_choi or functools.partial(dem_tu_choi_csdl, factory=factory)

    async def answer(
        self, *, tenant_id: str, question: str, request: ChatRequest
    ) -> KnowledgeAnswer:
        s = self._settings
        dong_ho = _DongHo()

        # UC025 — luật, 0 ms: dò tìm dữ liệu không thuộc về người hỏi, câu cần dữ liệu nghiệp vụ.
        # Xét TRƯỚC khi nhúng: câu này không có đáp án trong kho, nhúng và truy hồi chỉ tốn thời
        # gian.
        som = kiem_truoc_truy_hoi(request.message, question)
        if som is not None:
            return await self._tu_choi(
                som.ly_do,
                tenant_id=tenant_id,
                request=request,
                dong_ho=dong_ho,
                safety_flag=som.safety_flag,
                chuyen_giao=som.chuyen_giao,
            )

        cau_hoi = normalize_vi(request.message)
        nhung = await self._embed.embed_batch([cau_hoi])
        dong_ho.ghi("embed_ms")

        k = SO_UNG_VIEN_RERANK if self._rerank else s.rag_so_doan_loi_nhac
        cac_doan = await self._truy_hoi(tenant_id, cau_hoi, nhung, k)
        dong_ho.ghi("retrieve_ms")

        mo_ho = needs_rerank(cac_doan)
        if self._rerank and mo_ho:
            cac_doan = await xep_lai(self._rerank, cau_hoi, cac_doan)
            dong_ho.ghi("rerank_ms")
        sang = search_or_abstain(
            cac_doan[: s.rag_so_doan_loi_nhac],
            san_toan_tap=s.rag_san_toan_tap,
            san_tung_doan=s.rag_san_tung_doan,
        )
        diem_cao_nhat = sang.diem_cao_nhat
        logger.info(
            "rag tenant=%s so_doan=%d cosine_max=%s mo_ho=%s",
            tenant_id, len(sang.giu_lai), diem_cao_nhat, mo_ho,
        )
        if sang.ly_do is not None:
            # Không đoạn nào đủ gần ⇒ từ chối NOT_COVERED, KHÔNG gọi LLM.
            return await self._tu_choi(
                sang.ly_do,
                tenant_id=tenant_id,
                request=request,
                dong_ho=dong_ho,
                retrieval_top_score=diem_cao_nhat,
            )
        cac_doan = sang.giu_lai

        # Đây là chỗ dữ liệu rời hệ thống sang nhà cung cấp ngoài ⇒ che PII của khách trước.
        cau_hoi_gui_di, _ = mask_pii(request.message)
        try:
            ket_qua_llm = await self._llm.chat(dung_loi_nhac(cau_hoi_gui_di, cac_doan))
        except LLMKhongKhaDung as loi:
            dong_ho.ghi("generate_ms")
            # Đoạn cosine cao nhất, không phải hạng 1 RRF: không có LLM chọn hộ thì một đoạn duy
            # nhất phải tự đứng được, và làn dense một mình trúng nhiều hơn hybrid (E3: 0,800 vs
            # 0,740). Đo 08/10: hạng 1 RRF của "mất hoá đơn còn bảo hành không" là đoạn xuất hoá
            # đơn GTGT; đoạn cosine cao nhất là đúng đoạn Gemini đã trích.
            gan_nhat = max(cac_doan, key=lambda d: d.do_tuong_dong or 0.0)
            return self._suy_giam(gan_nhat, loi, diem_cao_nhat, dong_ho)
        dong_ho.ghi("generate_ms")

        chi_phi = self._chi_phi(ket_qua_llm.prompt_tokens, ket_qua_llm.completion_tokens)
        chung = {
            "model_name": ket_qua_llm.model,
            "llm_called": True,
            "cost_vnd": chi_phi,
            "retrieval_top_score": diem_cao_nhat,
            "prompt_tokens": ket_qua_llm.prompt_tokens,
            "completion_tokens": ket_qua_llm.completion_tokens,
        }

        if ket_qua_llm.noi_dung.strip().startswith(KHONG_DU_CAN_CU):
            # Mô hình đọc đoạn rồi kết luận không đoạn nào liên quan — bằng chứng VẮNG MẶT (UC025).
            return await self._tu_choi(
                NOT_COVERED, tenant_id=tenant_id, request=request, dong_ho=dong_ho, **chung
            )

        kiem = hau_kiem(ket_qua_llm.noi_dung, [d.content for d in cac_doan])
        dong_ho.ghi("postguard_ms")
        if kiem.so_trich_dan_bi_loai or kiem.so_pii_da_che:
            logger.warning(
                "Hậu kiểm: bỏ %d trích dẫn sai, che %d PII lạ",
                kiem.so_trich_dan_bi_loai, kiem.so_pii_da_che,
            )
        if not kiem.trich_dan or kiem.khong_phai_tra_loi:
            # Mô hình không ghi đúng mã KHONG_DU_CAN_CU mà viết "Dạ cửa hàng chưa có thông tin…":
            # (a) không câu nào trích đoạn nào (G001, G004 đo 08/10), hoặc (b) có gắn trích dẫn
            # nhưng chỉ nói "chưa có thông tin" — hoặc nói vậy mà 0 câu bám nguồn (N005, N012,
            # G031 đo 09/10). Đều là bằng chứng VẮNG MẶT ⇒ NOT_COVERED. Luật cấu trúc trên đầu ra,
            # không phải ngưỡng — xem hau_kiem.py.
            return await self._tu_choi(
                NOT_COVERED,
                tenant_id=tenant_id,
                request=request,
                dong_ho=dong_ho,
                groundedness_score=kiem.groundedness_score,
                **chung,
            )
        if khong_bam_nguon(kiem.groundedness_score, s.rag_nguong_bam_nguon):
            # Có đoạn liên quan, đã sinh, nhưng hậu kiểm không xác nhận được câu trả lời dựa vào
            # đoạn — THẤT BẠI KIỂM CHỨNG (UC025). HUỶ câu đã sinh; điểm vẫn ghi để hiệu chỉnh
            # ngưỡng.
            logger.info(
                "Huỷ câu trả lời: groundedness %.3f < %.2f",
                kiem.groundedness_score, s.rag_nguong_bam_nguon,
            )
            return await self._tu_choi(
                LOW_CONFIDENCE,
                tenant_id=tenant_id,
                request=request,
                dong_ho=dong_ho,
                groundedness_score=kiem.groundedness_score,
                **chung,
            )
        return KnowledgeAnswer(
            answer=kiem.cau_tra_loi,
            citations=[_trich_dan(cac_doan[n - 1]) for n in kiem.trich_dan],
            groundedness_score=kiem.groundedness_score,
            latency_breakdown=dong_ho.ket_qua,
            **chung,
        )

    async def _tu_choi(
        self,
        ly_do: str,
        *,
        tenant_id: str,
        request: ChatRequest,
        dong_ho: _DongHo,
        safety_flag: str | None = None,
        chuyen_giao: bool = False,
        **cac_truong,
    ) -> KnowledgeAnswer:
        """Câu từ chối theo lý do (UC025 bước 3), và quyết định có chuyển nhân viên không (bước 5).

        Lượt từ chối thứ ``rag_tu_choi_lap_lai_chuyen_giao`` liên tiếp trong hội thoại ⇒ chuyển
        giao (luồng phụ 3.3): khách đã hỏi lại mà bot vẫn chịu, hỏi tiếp lần ba chỉ thêm bực.
        """
        cau = MAU_TU_CHOI[ly_do]
        if ly_do in LY_DO_TINH_LAP_LAI and not chuyen_giao:
            so_truoc = await self._dem_tu_choi_an_toan(tenant_id, str(request.conversation_id))
            if so_truoc + 1 >= self._settings.rag_tu_choi_lap_lai_chuyen_giao:
                cau, chuyen_giao = CAU_CHUYEN_GIAO_LAP_LAI, True
        return KnowledgeAnswer(
            answer=cau,
            refused=True,
            refusal_reason=ly_do,
            safety_flag=safety_flag,
            handoff=chuyen_giao,
            latency_breakdown=dong_ho.ket_qua,
            **cac_truong,
        )

    async def _dem_tu_choi_an_toan(self, tenant_id: str, conversation_id: str) -> int:
        """Đọc lịch sử hỏng (CSDL chớp tắt) thì coi như chưa từ chối lần nào: câu từ chối vẫn đúng,
        chỉ mất lần chuyển giao sớm — không đáng biến một lượt từ chối thành HTTP 500."""
        try:
            return await self._dem_tu_choi(tenant_id, conversation_id)
        except Exception:  # noqa: BLE001
            logger.warning("Không đọc được lịch sử từ chối của hội thoại %s", conversation_id)
            return 0

    def _suy_giam(
        self, doan: DoanTimDuoc, loi: LLMKhongKhaDung, diem_cao_nhat: float, dong_ho: _DongHo
    ) -> KnowledgeAnswer:
        """Trích nguyên văn đoạn liên quan nhất. Đúng sự thật vì chép từ tài liệu — chỉ kém mượt."""
        logger.warning("LLM không khả dụng (%s) — trả câu suy giảm", loi.ma)
        trich = _trich(doan.content, DO_DAI_TRICH_SUY_GIAM)
        return KnowledgeAnswer(
            answer=(
                "Dạ hệ thống trả lời tự động đang bận, em gửi anh/chị nội dung liên quan nhất "
                f"trong tài liệu của cửa hàng: «{trich}» [1]. "
                "Anh/chị cần nhân viên hỗ trợ thêm thì nhắn em nhé ạ."
            ),
            citations=[_trich_dan(doan)],
            degraded=True,
            llm_called=loi.da_goi,
            model_name=self._llm.model,
            retrieval_top_score=diem_cao_nhat,
            latency_breakdown=dong_ho.ket_qua,
        )

    def _chi_phi(self, vao: int, ra: int) -> float:
        s = self._settings
        return round(
            (vao * s.llm_gia_vao_vnd_trieu_token + ra * s.llm_gia_ra_vnd_trieu_token) / 1_000_000, 2
        )

    async def aclose(self) -> None:
        await self._embed.aclose()
        await self._llm.aclose()
