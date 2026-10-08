"""[PRODUCTION] Nhánh trả lời từ tri thức doanh nghiệp — UC023, hiện thực ``KnowledgeAnswerer``.

Cắm vào ``orchestrator/turn.py::run_turn`` ở bước 7 (ADR-0027: pipeline tuần tự, không LangGraph)::

    nhúng câu hỏi ─► truy hồi lai (RRF) ─► [xếp lại nếu mơ hồ] ─► sàn liên quan ─┬─► từ chối, 0 LLM
                                                                                 └─► LLM ─► hậu kiểm

BA LỐI RA, KHÔNG LỐI NÀO LÀ 5xx DO LLM
-------------------------------------
- **Từ chối không gọi LLM** — không đoạn nào đạt sàn cosine toàn tập: gửi LLM cũng chỉ nhận lại
  ``KHONG_DU_CAN_CU`` sau 2 s và tốn một lượt. Lượt này tính vào KPI "không gọi LLM".
- **Trả lời** — LLM sinh, hậu kiểm lọc trích dẫn, đo độ bám nguồn, che PII lạ.
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
from src.ai.schemas import ChatRequest, Citation

logger = logging.getLogger(__name__)

# (tenant_id, câu hỏi đã chuẩn hoá, vector câu hỏi, k) → top-k. Test tiêm bản giả, không cần CSDL.
TruyHoi = Callable[[str, str, KetQuaNhung, int], Awaitable[list[DoanTimDuoc]]]

DO_DAI_TRICH = 200
DO_DAI_TRICH_SUY_GIAM = 400

CAU_TU_CHOI = (
    "Dạ hiện em chưa tìm thấy thông tin phù hợp trong tài liệu của cửa hàng cho câu hỏi này. "
    "Anh/chị có muốn em chuyển cho nhân viên tư vấn không ạ?"
)


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
    ) -> None:
        self._embed = embed
        self._llm = llm
        self._settings = settings or get_settings()
        self._rerank = rerank if self._settings.rerank_enabled else None
        self._truy_hoi = truy_hoi or functools.partial(truy_hoi_csdl, factory=factory)

    async def answer(
        self, *, tenant_id: str, question: str, request: ChatRequest
    ) -> KnowledgeAnswer:
        s = self._settings
        dong_ho = _DongHo()
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
        cac_doan = cac_doan[: s.rag_so_doan_loi_nhac]

        diem_cao_nhat = max(
            (d.do_tuong_dong for d in cac_doan if d.do_tuong_dong is not None), default=None
        )
        logger.info(
            "rag tenant=%s so_doan=%d cosine_max=%s mo_ho=%s",
            tenant_id, len(cac_doan), diem_cao_nhat, mo_ho,
        )

        # Sàn từng đoạn: đoạn quá xa không vào lời nhắc — nó chỉ là nhiễu để mô hình bám nhầm.
        cac_doan = [
            d for d in cac_doan if d.do_tuong_dong is not None
            and d.do_tuong_dong >= s.rag_san_tung_doan
        ]
        # Sàn toàn tập: không đoạn nào đủ gần ⇒ từ chối, KHÔNG gọi LLM.
        if not cac_doan or diem_cao_nhat is None or diem_cao_nhat < s.rag_san_toan_tap:
            return KnowledgeAnswer(
                answer=CAU_TU_CHOI,
                refused=True,
                refusal_reason="NOT_COVERED",
                retrieval_top_score=diem_cao_nhat,
                latency_breakdown=dong_ho.ket_qua,
            )

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
            # Mô hình đọc đoạn rồi kết luận không đủ căn cứ — từ chối có lý do (UC025).
            return KnowledgeAnswer(
                answer=CAU_TU_CHOI,
                refused=True,
                refusal_reason="NOT_COVERED",
                latency_breakdown=dong_ho.ket_qua,
                **chung,
            )

        kiem = hau_kiem(ket_qua_llm.noi_dung, [d.content for d in cac_doan])
        dong_ho.ghi("postguard_ms")
        if kiem.so_trich_dan_bi_loai or kiem.so_pii_da_che:
            logger.warning(
                "Hậu kiểm: bỏ %d trích dẫn sai, che %d PII lạ",
                kiem.so_trich_dan_bi_loai, kiem.so_pii_da_che,
            )
        return KnowledgeAnswer(
            answer=kiem.cau_tra_loi,
            citations=[_trich_dan(cac_doan[n - 1]) for n in kiem.trich_dan],
            groundedness_score=kiem.groundedness_score,
            latency_breakdown=dong_ho.ket_qua,
            **chung,
        )

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
