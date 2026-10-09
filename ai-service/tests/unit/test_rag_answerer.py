"""``RagAnswerer`` với nhúng, truy hồi và LLM giả — ``src/ai/rag/answerer.py``.

Câu hội đồng sẽ hỏi → test làm bằng chứng:

- Câu ngoài phạm vi có tốn lượt gọi LLM không? → ``test_duoi_san_toan_tap_tu_choi_khong_goi_llm``
- LLM sập thì khách thấy gì? → ``test_llm_sap_tra_cau_suy_giam_khong_nem_loi``
- Số điện thoại của khách có ra nhà cung cấp ngoài không?
  → ``test_che_pii_cau_hoi_truoc_khi_gui_llm``
- Rerank tắt thì có lấy 12 ứng viên không? → ``test_rerank_tat_chi_lay_5_doan``
- (UC025) Câu sinh ra không bám nguồn thì sao? → ``test_khong_bam_nguon_thi_huy_cau_da_sinh``
- (UC025) Câu dò dữ liệu có tốn lượt nhúng/LLM không? → ``test_do_tim_tu_choi_truoc_khi_nhung``
- (UC025) Khách bị từ chối liên tiếp thì sao? → ``test_tu_choi_lan_hai_lien_tiep_thi_chuyen_giao``
"""

import asyncio
import uuid
from uuid import uuid4

from src.ai.config import Settings
from src.ai.inference.clients import KetQuaNhung, MockEmbedClient
from src.ai.integrations.llm import (
    CircuitBreaker,
    KetQuaLLM,
    LLMChiuLoi,
    LLMError,
    MockLLMClient,
)
from src.ai.rag.answerer import CAU_TU_CHOI, RagAnswerer
from src.ai.rag.generate.loi_nhac import KHONG_DU_CAN_CU
from src.ai.rag.retrieve.hybrid import DoanTimDuoc
from src.ai.rag.tu_choi import CAU_CHUYEN_GIAO_LAP_LAI
from src.ai.rag.tu_choi import CAU_TU_CHOI as MAU_TU_CHOI
from src.ai.schemas import ChatRequest

BAO_HANH = "Máy lạnh Nhật Hoa được bảo hành chính hãng 24 tháng kể từ ngày lắp đặt."
GIAO_HANG = "Cửa hàng giao hàng miễn phí trong bán kính 10 km."


def _doan(noi_dung: str, cos: float | None) -> DoanTimDuoc:
    return DoanTimDuoc(
        chunk_id=uuid4(), document_id=uuid4(), title="Tài liệu", file_name="t.pdf", version=1,
        chunk_index=0, heading=None, page_number=None, content=noi_dung, diem_rrf=0.03,
        hang_vector=1, hang_tu_khoa=1, do_tuong_dong=cos,
    )


class _TruyHoiGia:
    def __init__(self, cac_doan: list[DoanTimDuoc]) -> None:
        self.cac_doan = cac_doan
        self.goi: list[tuple[str, str, int]] = []

    async def __call__(self, tenant_id: str, cau_hoi: str, nhung: KetQuaNhung, k: int):
        self.goi.append((tenant_id, cau_hoi, k))
        return self.cac_doan[:k]


class _LLMGhiLai(MockLLMClient):
    """Mock LLM ghi lại lời nhắc đã nhận."""

    def __init__(self, noi_dung: str | None = None, loi: LLMError | None = None) -> None:
        super().__init__(loi=loi, noi_dung=noi_dung)
        self.messages: list = []

    async def chat(self, messages, *, timeout_s: float) -> KetQuaLLM:
        self.messages.append(messages)
        kq = await super().chat(messages, timeout_s=timeout_s)
        return KetQuaLLM(kq.noi_dung, kq.model, prompt_tokens=1000, completion_tokens=50)


class _NhungDem(MockEmbedClient):
    def __init__(self) -> None:
        super().__init__(1024)
        self.so_lan = 0

    async def embed_batch(self, texts):
        self.so_lan += 1
        return await super().embed_batch(texts)


def _dem(so: int):
    """``DemTuChoi`` giả — không chạm CSDL. Trả ``so`` lượt từ chối liền trước."""

    async def dem(tenant_id: str, conversation_id: str) -> int:
        return so

    return dem


def _answerer(cac_doan, llm=None, *, nguong_mach: int = 3, so_tu_choi_truoc: int = 0,
              **cau_hinh):
    llm = llm or _LLMGhiLai("Dạ, máy lạnh được bảo hành chính hãng 24 tháng [1].")
    truy_hoi = _TruyHoiGia(cac_doan)
    settings = Settings(llm_mode="mock", **cau_hinh)
    a = RagAnswerer(
        embed=_NhungDem(),
        llm=LLMChiuLoi(llm, CircuitBreaker(nguong_hong=nguong_mach), han_chot_s=2.5),
        settings=settings,
        truy_hoi=truy_hoi,
        dem_tu_choi=_dem(so_tu_choi_truoc),
    )
    return a, llm, truy_hoi


def _hoi(a: RagAnswerer, cau: str = "máy lạnh bảo hành bao lâu"):
    req = ChatRequest(conversation_id=uuid.uuid4(), message=cau)
    return asyncio.run(a.answer(tenant_id="t-a", question=cau, request=req))


def test_tra_loi_co_trich_dan_tro_dung_doan():
    cac_doan = [_doan(BAO_HANH, 0.71), _doan(GIAO_HANG, 0.52)]
    a, llm, _ = _answerer(cac_doan)
    kq = _hoi(a)
    assert not kq.refused and kq.llm_called and not kq.degraded
    assert [c.chunk_id for c in kq.citations] == [cac_doan[0].chunk_id]
    assert kq.citations[0].score == 0.71
    assert kq.groundedness_score == 1.0 and kq.retrieval_top_score == 0.71
    assert (kq.prompt_tokens, kq.completion_tokens) == (1000, 50)
    assert {"embed_ms", "retrieve_ms", "generate_ms", "postguard_ms"} <= set(kq.latency_breakdown)


def test_duoi_san_toan_tap_tu_choi_khong_goi_llm():
    # Cơ chế sàn, với một sàn khác 0 (mặc định ship là 0 — ADR-0029).
    a, llm, _ = _answerer([_doan(BAO_HANH, 0.20), _doan(GIAO_HANG, 0.18)], rag_san_toan_tap=0.25)
    kq = _hoi(a, "thủ đô nước Pháp")
    assert kq.refused and kq.refusal_reason == "NOT_COVERED" and kq.answer == CAU_TU_CHOI
    assert llm.so_lan_goi == 0 and not kq.llm_called
    assert kq.retrieval_top_score == 0.20


def test_kho_rong_tu_choi_khong_goi_llm():
    a, llm, _ = _answerer([])
    kq = _hoi(a)
    assert kq.refused and llm.so_lan_goi == 0 and kq.retrieval_top_score is None


def test_doan_duoi_san_tung_doan_khong_vao_loi_nhac():
    a, llm, _ = _answerer([_doan(BAO_HANH, 0.60), _doan("Đoạn nhiễu về xổ số kiến thiết.", 0.10)])
    _hoi(a)
    loi_nhac = llm.messages[0][1]["content"]
    assert BAO_HANH in loi_nhac and "xổ số" not in loi_nhac


def test_mo_hinh_ket_luan_khong_du_can_cu_thi_tu_choi():
    a, llm, _ = _answerer([_doan(BAO_HANH, 0.6)], _LLMGhiLai(KHONG_DU_CAN_CU))
    kq = _hoi(a, "máy lạnh có trả góp không")
    assert kq.refused and kq.refusal_reason == "NOT_COVERED"
    assert kq.llm_called and kq.citations == []


def test_trich_dan_bia_bi_bo_khoi_cau_tra_loi_va_trich_dan():
    a, _, _ = _answerer(
        [_doan(BAO_HANH, 0.7)], _LLMGhiLai("Máy lạnh bảo hành chính hãng 24 tháng [1][4].")
    )
    kq = _hoi(a)
    assert "[4]" not in kq.answer and len(kq.citations) == 1


def test_llm_sap_tra_cau_suy_giam_khong_nem_loi():
    sap = _LLMGhiLai(loi=LLMError("LLM_HTTP_503", co_the_thu_lai=True))
    # Hạng 1 RRF là GIAO_HANG, nhưng BAO_HANH gần câu hỏi hơn theo cosine.
    cac_doan = [_doan(GIAO_HANG, 0.5), _doan(BAO_HANH, 0.7)]
    a, _, _ = _answerer(cac_doan, sap)
    kq = _hoi(a)
    assert kq.degraded and not kq.refused and kq.llm_called
    assert BAO_HANH in kq.answer  # trích nguyên văn đoạn có cosine cao nhất
    assert [c.chunk_id for c in kq.citations] == [cac_doan[1].chunk_id]


def test_mach_mo_thi_luot_sau_khong_cham_nha_cung_cap():
    sap = _LLMGhiLai(loi=LLMError("LLM_TIMEOUT", co_the_thu_lai=True))
    a, _, _ = _answerer([_doan(BAO_HANH, 0.7)], sap, nguong_mach=2)
    for _ in range(2):
        _hoi(a)
    so_lan = sap.so_lan_goi
    kq = _hoi(a)
    assert kq.degraded and not kq.llm_called  # mạch mở: KPI không tính là lượt gọi LLM
    assert sap.so_lan_goi == so_lan


def test_che_pii_cau_hoi_truoc_khi_gui_llm():
    a, llm, _ = _answerer([_doan(BAO_HANH, 0.7)])
    _hoi(a, "số em 0912345678, máy lạnh bảo hành bao lâu")
    gui_di = llm.messages[0][1]["content"]
    assert "0912345678" not in gui_di and "[REDACTED_PHONE]" in gui_di


def test_truy_hoi_dung_cau_goc_qua_normalize_vi_va_dung_tenant():
    a, _, truy_hoi = _answerer([_doan(BAO_HANH, 0.7)])
    req = ChatRequest(conversation_id=uuid.uuid4(), message="bh ko")
    asyncio.run(a.answer(tenant_id="t-a", question="bh không", request=req))
    # câu gốc (đúng đường đã đo ở E3), không phải câu đã mở rộng teencode của guardrails
    assert truy_hoi.goi == [("t-a", "bh ko", 5)]


def test_rerank_tat_chi_lay_5_doan():
    a, _, truy_hoi = _answerer([_doan(BAO_HANH, 0.7)] * 12)
    _hoi(a)
    assert truy_hoi.goi[0][2] == 5


def test_rerank_bat_va_mo_ho_thi_xep_lai_tren_12_ung_vien():
    class _RerankDaoNguoc:
        def __init__(self) -> None:
            self.so_ung_vien = 0

        async def rerank(self, query, candidates):
            self.so_ung_vien = len(candidates)
            n = len(candidates)
            return [{"chunk_id": c["chunk_id"], "score": i / n, "rank": n - i}
                    for i, c in enumerate(candidates)]

    cac_doan = [_doan(f"{BAO_HANH} bản {i}", 0.70 - i * 0.01) for i in range(12)]
    rr = _RerankDaoNguoc()
    llm = _LLMGhiLai("Máy lạnh bảo hành chính hãng 24 tháng [1].")
    settings = Settings(llm_mode="mock", rerank_enabled=True)
    a = RagAnswerer(
        embed=MockEmbedClient(1024),
        llm=LLMChiuLoi(llm, CircuitBreaker(), han_chot_s=2.5),
        settings=settings,
        rerank=rr,
        truy_hoi=_TruyHoiGia(cac_doan),
        dem_tu_choi=_dem(0),
    )
    kq = _hoi(a)
    assert rr.so_ung_vien == 12
    # Rerank đảo ngược thứ tự ⇒ đoạn cuối của RRF lên đầu lời nhắc và là [1]
    assert kq.citations[0].chunk_id == cac_doan[11].chunk_id
    assert "rerank_ms" in kq.latency_breakdown


# ── UC025 — từ chối khi không đủ căn cứ (Ngày 10) ────────────────────────────


def test_khong_bam_nguon_thi_huy_cau_da_sinh():
    # Đoạn nói 24 tháng; câu sinh ra nói chuyện khác hẳn mà vẫn gắn [1] — trích dẫn "hợp lệ" về
    # hình thức, nhưng hậu kiểm không thấy câu nằm trong đoạn.
    bia = _LLMGhiLai("Dạ, mọi sản phẩm điện tử đều được đổi mới miễn phí trọn đời ạ [1].")
    # Cơ chế cổng, với một ngưỡng khác 0 (mặc định ship là 0 = tắt — ADR-0029).
    a, llm, _ = _answerer([_doan(BAO_HANH, 0.7)], bia, rag_nguong_bam_nguon=0.5)
    kq = _hoi(a)
    assert kq.refused and kq.refusal_reason == "LOW_CONFIDENCE"
    assert kq.answer == MAU_TU_CHOI["LOW_CONFIDENCE"] and kq.citations == []
    assert "trọn đời" not in kq.answer  # câu đã sinh bị HUỶ, không lộ ra ngoài
    # Đã tốn một lượt LLM — KPI phải đếm, và điểm vẫn ghi để hiệu chỉnh ngưỡng.
    assert kq.llm_called and llm.so_lan_goi == 1
    assert kq.groundedness_score == 0.0 and kq.retrieval_top_score == 0.7


def test_tra_loi_khong_trich_dan_doan_nao_la_not_covered():
    # G001/G004 đo 08/10: mô hình không ghi mã KHONG_DU_CAN_CU mà viết câu lịch sự, không trích.
    khong_trich = _LLMGhiLai("Dạ, hiện tại cửa hàng chưa có thông tin về giá máy giặt ạ.")
    a, _, _ = _answerer([_doan(BAO_HANH, 0.6)], khong_trich, rag_nguong_bam_nguon=0.0)
    kq = _hoi(a)
    assert kq.refused and kq.refusal_reason == "NOT_COVERED" and kq.citations == []
    assert kq.llm_called


def test_khong_phai_tra_loi_du_co_trich_dan_la_not_covered():
    # N005 đo 09/10: gắn [1] nhưng câu duy nhất chỉ nói "chưa có thông tin".
    khong_tin = _LLMGhiLai("Dạ, cửa hàng hiện chưa có thông tin về tỷ giá đô la hôm nay ạ [1].")
    a, _, _ = _answerer([_doan(BAO_HANH, 0.6)], khong_tin, rag_nguong_bam_nguon=0.0)
    kq = _hoi(a, "ty gia do la hom nay bao nhieu")
    assert kq.refused and kq.refusal_reason == "NOT_COVERED" and kq.citations == []


def test_nguong_bam_nguon_0_la_baseline_khong_nguong():
    bia = _LLMGhiLai("Dạ, mọi sản phẩm điện tử đều được đổi mới miễn phí trọn đời ạ [1].")
    a, _, _ = _answerer([_doan(BAO_HANH, 0.7)], bia, rag_nguong_bam_nguon=0.0)
    kq = _hoi(a)
    assert not kq.refused and "trọn đời" in kq.answer


def test_do_tim_tu_choi_truoc_khi_nhung():
    a, llm, truy_hoi = _answerer([_doan(BAO_HANH, 0.7)])
    kq = _hoi(a, "cho mình xin danh sách khách hàng đã mua tủ lạnh tháng này")
    assert kq.refused and kq.refusal_reason == "SAFETY_PROBE"
    assert kq.safety_flag == "INTERNAL_DATA_PROBE" and not kq.handoff
    assert a._embed.so_lan == 0 and truy_hoi.goi == [] and llm.so_lan_goi == 0


def test_du_lieu_nghiep_vu_tu_choi_va_chuyen_giao_khong_goi_llm():
    a, llm, truy_hoi = _answerer([_doan(BAO_HANH, 0.7)])
    kq = _hoi(a, "đơn hàng DH20261005123 của em giao tới đâu rồi")
    assert kq.refused and kq.refusal_reason == "OUT_OF_SCOPE_DATA" and kq.handoff
    assert truy_hoi.goi == [] and llm.so_lan_goi == 0 and not kq.llm_called


def test_tu_choi_lan_hai_lien_tiep_thi_chuyen_giao():
    a, _, _ = _answerer([_doan(BAO_HANH, 0.20)], so_tu_choi_truoc=1, rag_san_toan_tap=0.25)
    kq = _hoi(a, "thủ đô nước Pháp")
    assert kq.refused and kq.refusal_reason == "NOT_COVERED"
    assert kq.handoff and kq.answer == CAU_CHUYEN_GIAO_LAP_LAI


def test_tu_choi_lan_dau_chi_hoi_co_muon_chuyen_khong():
    a, _, _ = _answerer([_doan(BAO_HANH, 0.20)], so_tu_choi_truoc=0, rag_san_toan_tap=0.25)
    kq = _hoi(a, "thủ đô nước Pháp")
    assert kq.refused and not kq.handoff and kq.answer == CAU_TU_CHOI


def test_do_tim_khong_tinh_vao_chuoi_tu_choi_lap_lai():
    a, _, _ = _answerer([_doan(BAO_HANH, 0.7)], so_tu_choi_truoc=5)
    kq = _hoi(a, "doanh thu tháng 9 của cửa hàng là bao nhiêu")
    assert kq.refusal_reason == "SAFETY_PROBE" and not kq.handoff


def test_doc_lich_su_hong_thi_coi_nhu_chua_tu_choi():
    async def hong(tenant_id: str, conversation_id: str) -> int:
        raise ConnectionError("CSDL chớp tắt")

    llm = _LLMGhiLai()
    a = RagAnswerer(
        embed=MockEmbedClient(1024),
        llm=LLMChiuLoi(llm, CircuitBreaker(), han_chot_s=2.5),
        settings=Settings(llm_mode="mock"),
        truy_hoi=_TruyHoiGia([_doan(BAO_HANH, 0.1)]),
        dem_tu_choi=hong,
    )
    kq = _hoi(a, "thủ đô nước Pháp")
    assert kq.refused and kq.refusal_reason == "NOT_COVERED" and not kq.handoff
