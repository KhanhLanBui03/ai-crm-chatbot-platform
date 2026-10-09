"""UC026 — ``service.summarize`` trên Postgres THẬT (role ``ai_app``, RLS) + java-core GIẢ. Ngày 12.

java-core chưa có ``/internal/*`` (09/10) nên dùng ``MockJavaCoreClient`` — đúng phương án dự phòng
của kế hoạch Ngày 12. LLM là kịch bản cố định: phép thử ở đây là về THỨ TỰ và TRẠNG THÁI (PATCH,
dòng ``SUMMARY``, chống trùng), không về chất lượng tóm tắt — chất lượng đo ở
``tests/eval/minh_chung_uc026.py`` với Gemini thật.

Câu hội đồng sẽ hỏi → test làm bằng chứng:

- Nhận trùng sự kiện thì sao? → ``test_su_kien_trung_khong_goi_llm_khong_patch_lan_hai``.
- PATCH hỏng giữa chừng thì sự kiện có bị đánh dấu xong không? →
  ``test_java_core_sap_khi_patch_thi_chua_danh_dau_xong``.
- Bản cũ còn truy được không? → ``test_da_ghi_patch_mot_lan_va_luu_lich_su`` (``response_text``).
- Lượt tóm tắt có làm lệch KPI "lượt không gọi LLM" không? →
  ``test_luot_tom_tat_khong_vao_tin_hieu_uc027``.
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from src.ai import service
from src.ai.db import session as db_session
from src.ai.db.repositories import interaction_repository
from src.ai.exceptions import JavaCoreUnavailableError
from src.ai.integrations.java_core import MockJavaCoreClient, TinNhanHoiThoai
from src.ai.integrations.llm import CircuitBreaker, KetQuaLLM, LLMChiuLoi
from src.ai.rag.generate.tom_tat import BoTomTat

DU_BON_PHAN = json.dumps({
    "mainNeed": "Khách cần đổi máy lạnh chảy nước.",
    "providedInfo": "Mua 02/10, Daikin FTKB25, đã cung cấp số điện thoại (đã che).",
    "unresolvedIssues": "Chưa hẹn lịch kỹ thuật.",
    "nextSteps": "Gọi khách hẹn kỹ thuật trong 24 giờ.",
}, ensure_ascii=False)

HOI_THOAI = [
    TinNhanHoiThoai("CUSTOMER", "Máy lạnh mới mua bị chảy nước"),
    TinNhanHoiThoai("BOT", "Dạ anh mua ngày nào ạ?"),
    TinNhanHoiThoai("CUSTOMER", "Ngày 02/10, Daikin FTKB25, số em 0912345678"),
    TinNhanHoiThoai("SYSTEM", "Hội thoại đã đóng"),
]


class _LLMDem:
    def __init__(self, *cac_cau: str, model: str = "gemini-3.5-flash-lite") -> None:
        self.cac_cau = list(cac_cau)
        self.model = model
        self.so_lan_goi = 0
        self.loi_nhac: list[str] = []

    async def chat(self, messages, *, timeout_s: float) -> KetQuaLLM:
        self.so_lan_goi += 1
        self.loi_nhac.append(messages[-1]["content"])
        cau = self.cac_cau.pop(0) if len(self.cac_cau) > 1 else self.cac_cau[0]
        return KetQuaLLM(cau, self.model, prompt_tokens=120, completion_tokens=60)

    async def aclose(self) -> None:
        return None


def _bo(llm) -> BoTomTat:
    return BoTomTat(LLMChiuLoi(llm, CircuitBreaker(), han_chot_s=20.0), ky_tu_moi_khoi=12_000)


@pytest.fixture
def moi_truong(ha_tang):
    factory, _ = ha_tang
    tenant, conv = str(uuid4()), uuid4()
    gia = MockJavaCoreClient()
    gia.nap_hoi_thoai(tenant, conv, HOI_THOAI)
    return factory, tenant, conv, gia


async def _cac_luot(factory, tenant: str, conv: UUID) -> list:
    async with db_session.get_tenant_session(tenant, factory=factory) as phien:
        return (await phien.execute(
            text(
                "SELECT branch, status, is_answered, refusal_reason, model_name, model_version,"
                " response_text, error_message, llm_called, prompt_tokens, user_query"
                " FROM ai.ai_interactions WHERE conversation_id = :c ORDER BY created_at"
            ),
            {"c": conv},
        )).all()


async def _da_danh_dau(factory, tenant: str, nhom: str, event_id: int) -> bool:
    async with db_session.get_tenant_session(tenant, factory=factory) as phien:
        return (await phien.execute(
            text("SELECT count(*) FROM ai.processed_events"
                 " WHERE consumer_group = :n AND event_id = :e"),
            {"n": nhom, "e": event_id},
        )).scalar_one() == 1


def _su_kien() -> service.SuKienNap:
    return service.SuKienNap(f"summarizer-cg-{uuid4().hex[:6]}", int(uuid4().int % 10**12) + 1)


async def test_da_ghi_patch_mot_lan_va_luu_lich_su(moi_truong):
    factory, tenant, conv, gia = moi_truong
    llm, sk = _LLMDem(DU_BON_PHAN), _su_kien()

    kq = await service.summarize(
        tenant, conv, trigger="CLOSING", su_kien=sk, java_core=gia, bo_tom_tat=_bo(llm),
        factory=factory,
    )

    assert kq.trang_thai == "DA_GHI" and llm.so_lan_goi == 1
    [(t, c, ban_ghi)] = gia.tom_tat_da_ghi
    assert (t, c, ban_ghi.trigger) == (tenant, conv, "CLOSING")
    assert ban_ghi.model_version == "gemini-3.5-flash-lite@tt2"
    assert "Nhu cầu chính:" in ban_ghi.summary_text
    # Che PII trước khi rời ai-service: số điện thoại không tới LLM.
    assert "0912345678" not in llm.loi_nhac[0] and "[REDACTED_PHONE]" in llm.loi_nhac[0]

    [luot] = await _cac_luot(factory, tenant, conv)
    assert luot.branch == "SUMMARY" and luot.status == "SUCCESS" and luot.is_answered
    assert luot.model_version == "gemini-3.5-flash-lite@tt2" and luot.llm_called
    assert json.loads(luot.response_text)["nextSteps"].startswith("Gọi khách")
    assert luot.prompt_tokens == 120
    assert await _da_danh_dau(factory, tenant, sk.consumer_group, sk.event_id)


async def test_su_kien_trung_khong_goi_llm_khong_patch_lan_hai(moi_truong):
    factory, tenant, conv, gia = moi_truong
    llm, sk = _LLMDem(DU_BON_PHAN), _su_kien()
    for _ in range(2):
        kq = await service.summarize(
            tenant, conv, su_kien=sk, java_core=gia, bo_tom_tat=_bo(llm), factory=factory
        )
    assert kq.trang_thai == "TRUNG"
    assert llm.so_lan_goi == 1 and len(gia.tom_tat_da_ghi) == 1
    assert len(await _cac_luot(factory, tenant, conv)) == 1


async def test_hoi_thoai_qua_ngan_bo_qua_bang_luat_khong_goi_llm(ha_tang):
    factory, _ = ha_tang
    tenant, conv, gia = str(uuid4()), uuid4(), MockJavaCoreClient()
    gia.nap_hoi_thoai(tenant, conv, [TinNhanHoiThoai("CUSTOMER", "alo"),
                                     TinNhanHoiThoai("BOT", "Dạ em chào anh")])
    llm, sk = _LLMDem(DU_BON_PHAN), _su_kien()

    kq = await service.summarize(
        tenant, conv, su_kien=sk, java_core=gia, bo_tom_tat=_bo(llm), factory=factory
    )

    assert kq.trang_thai == "BO_QUA_NGAN"
    assert llm.so_lan_goi == 0 and gia.tom_tat_da_ghi == []
    assert await _cac_luot(factory, tenant, conv) == []
    assert await _da_danh_dau(factory, tenant, sk.consumer_group, sk.event_id)


async def test_sai_dinh_dang_sau_vong_sua_ghi_failed_va_giu_ban_cu(moi_truong):
    factory, tenant, conv, gia = moi_truong
    llm, sk = _LLMDem('{"mainNeed": "chỉ một phần"}'), _su_kien()

    kq = await service.summarize(
        tenant, conv, su_kien=sk, java_core=gia, bo_tom_tat=_bo(llm), factory=factory
    )

    assert (kq.trang_thai, kq.loi) == ("SAI_DINH_DANG", "SUMMARY_SCHEMA_INVALID")
    assert llm.so_lan_goi == 2, "một lượt + đúng một vòng sửa"
    assert gia.tom_tat_da_ghi == [], "không ghi đè bản cũ bằng kết quả hỏng"
    [luot] = await _cac_luot(factory, tenant, conv)
    assert (luot.status, luot.is_answered, luot.refusal_reason, luot.error_message) == (
        "FAILED", False, "LOW_CONFIDENCE", "SUMMARY_SCHEMA_INVALID"
    )
    assert await _da_danh_dau(factory, tenant, sk.consumer_group, sk.event_id)


async def test_java_core_sap_khi_patch_thi_chua_danh_dau_xong(moi_truong):
    """PATCH hỏng ⇒ ném ra (worker thử lại) và KHÔNG có dòng chống trùng: lần nhận lại phải làm
    lại từ đầu. Đánh dấu trước rồi PATCH sau thì lỗi này là mất tóm tắt vĩnh viễn."""
    factory, tenant, conv, gia = moi_truong
    llm, sk = _LLMDem(DU_BON_PHAN), _su_kien()

    class _PatchSap(MockJavaCoreClient):
        async def ghi_tom_tat(self, *a):
            raise JavaCoreUnavailableError("java-core 503")

    sap = _PatchSap(tin_nhan=gia.tin_nhan)
    with pytest.raises(JavaCoreUnavailableError):
        await service.summarize(
            tenant, conv, su_kien=sk, java_core=sap, bo_tom_tat=_bo(llm), factory=factory
        )
    assert not await _da_danh_dau(factory, tenant, sk.consumer_group, sk.event_id)
    assert await _cac_luot(factory, tenant, conv) == []

    # java-core sống lại → lần giao lại đi trọn.
    kq = await service.summarize(
        tenant, conv, su_kien=sk, java_core=gia, bo_tom_tat=_bo(llm), factory=factory
    )
    assert kq.trang_thai == "DA_GHI" and len(gia.tom_tat_da_ghi) == 1


async def test_tenant_khac_khong_doc_duoc_lich_su(moi_truong):
    """Sự kiện giả mang tenant khác trỏ vào hội thoại này: java-core (RLS) trả rỗng ⇒ bỏ qua."""
    factory, _, conv, gia = moi_truong
    llm = _LLMDem(DU_BON_PHAN)
    kq = await service.summarize(
        str(uuid4()), conv, java_core=gia, bo_tom_tat=_bo(llm), factory=factory
    )
    assert kq.trang_thai == "BO_QUA_NGAN" and llm.so_lan_goi == 0


async def test_luot_tom_tat_khong_vao_tin_hieu_uc027(moi_truong):
    factory, tenant, conv, gia = moi_truong
    await service.summarize(
        tenant, conv, java_core=gia, bo_tom_tat=_bo(_LLMDem(DU_BON_PHAN)), factory=factory
    )
    bay_gio = datetime.now(UTC)
    async with db_session.get_tenant_session(tenant, factory=factory) as phien:
        th = await interaction_repository.tin_hieu_luot(
            phien, bay_gio - timedelta(hours=1), bay_gio + timedelta(minutes=1)
        )
    assert len(await _cac_luot(factory, tenant, conv)) == 1
    assert th.so_luot == 0 and th.so_loi == 0, "lượt nền SUMMARY không phải lượt chat"
