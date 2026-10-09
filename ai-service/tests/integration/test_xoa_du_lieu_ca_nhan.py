"""UC041 — xoá dữ liệu cá nhân phía Track B: Postgres (RLS, role ``ai_app``) + RustFS THẬT. Ngày 12.

Câu hội đồng sẽ hỏi → test làm bằng chứng:

- Câu trả lời sinh SAU khi xoá còn trích dữ liệu đã xoá không? →
  ``test_cau_tra_loi_sau_khi_xoa_khong_con_trich_du_lieu_da_xoa`` (đúng ``RagAnswerer`` của
  production, LLM giả trích MỌI đoạn được đưa vào lời nhắc — đoạn còn sót là lộ ngay).
- Xoá khách X có đụng khách Y, tài liệu chung, tenant khác không? →
  ``test_xoa_dung_pham_vi_khong_dung_khach_khac_tenant_khac``.
- Bản cũ đã lưu trữ của cùng tệp thì sao? → ``test_xoa_ca_dong_doi_cung_tep``.
- Hỏng giữa chừng thì chạy lại được không? → ``test_chay_lai_luy_dang`` +
  ``test_java_core_sap_thi_partially_failed_ma_phan_ai_van_xong``.

Xoá hội thoại nguồn KHÔNG kéo theo xoá cơ hội tiềm năng: ràng buộc nằm ở java-core —
``sales.leads.source_conversation_id`` ``ON DELETE SET NULL (source_conversation_id)`` (V132) và
``LeadIntegrationTest`` đã khoá nó. Phía AI không có bảng lead nào để xoá nhầm (ADR-0016).
"""

import math
import uuid
from uuid import UUID, uuid4

import pytest
from minio.error import S3Error
from sqlalchemy import text

from src.ai import service
from src.ai.config import Settings
from src.ai.db import session as db_session
from src.ai.db.repositories import feedback_repository, interaction_repository
from src.ai.exceptions import JavaCoreUnavailableError
from src.ai.inference.clients import KetQuaNhung
from src.ai.integrations.java_core import MockJavaCoreClient
from src.ai.integrations.llm import CircuitBreaker, KetQuaLLM, LLMChiuLoi
from src.ai.rag.answerer import RagAnswerer
from src.ai.schemas import ChatRequest, DocumentMetadataUpdate
from tests.conftest import S3_BUCKET
from tests.integration.nap_chung import nap, tai_lieu_pending

DIM = 1024
HOP_DONG_X = (
    "Hợp đồng bảo trì máy lạnh số HD-CT-0917 của khách Trần Thị Bích: bảo trì 4 lần mỗi năm "
    "tại nhà riêng, phí 1.200.000 đồng."
).encode()
CHINH_SACH_CHUNG = (
    "Chính sách bảo trì máy lạnh của cửa hàng: bảo trì định kỳ 2 lần mỗi năm cho mọi khách."
).encode()
HOP_DONG_Y = "Hợp đồng bảo trì máy giặt số HD-CT-0001 của khách Lê Văn Cường.".encode()


class _NhungCoDinh:
    """Mọi văn bản nhúng thành CÙNG một vector — cosine 1 với mọi đoạn: không đoạn nào bị sàn
    liên quan loại oan, nên đoạn nào còn trong kho là đoạn đó vào lời nhắc."""

    async def embed_batch(self, texts):
        v = [0.0] * DIM
        v[0] = 1.0
        return KetQuaNhung("test/co-dinh", "v1", [list(v) for _ in texts])

    async def aclose(self) -> None:
        return None


class _LLMTrichHet:
    model = "llm-gia"

    def __init__(self) -> None:
        self.loi_nhac: list[str] = []

    async def chat(self, messages, *, timeout_s: float) -> KetQuaLLM:
        noi_dung = messages[1]["content"]
        self.loi_nhac.append(noi_dung)
        trich = "".join(f"[{i}]" for i in range(1, noi_dung.count("<doan ") + 1))
        cau = f"Dạ theo tài liệu thì cửa hàng bảo trì định kỳ {trich}."
        return KetQuaLLM(cau, self.model, 1, 1)

    async def aclose(self) -> None:
        return None


async def _tai_lieu(factory, kho_s3, tenant: UUID, du_lieu: bytes, contact: UUID | None) -> UUID:
    doc = await tai_lieu_pending(factory, kho_s3, tenant, "hop-dong.txt", "TXT", du_lieu)
    assert (await nap(factory, tenant, doc, embed=_NhungCoDinh())).trang_thai == "READY"
    if contact is not None:
        async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
            await service.update_document_metadata(
                phien, doc, DocumentMetadataUpdate(contact_id=contact)
            )
    return doc


async def _luot(factory, tenant: UUID, conv: UUID, *, danh_gia: bool = False,
                goi_cong_cu: bool = False) -> UUID:
    ma = uuid4()
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        await interaction_repository.ghi_luot(
            phien, id=ma, conversation_id=str(conv), branch="RAG", intent="KB_SEARCH",
            intent_confidence=0.9, user_query="hợp đồng của em bảo trì mấy lần",
            response_text="Dạ 4 lần mỗi năm [1].", retrieved_chunk_ids=[],
            retrieval_top_score=0.8, is_answered=True, refusal_reason=None,
            model_name="gemini-3.5-flash-lite", model_version=None, prompt_tokens=10,
            completion_tokens=5, cost_vnd=0.0, latency_ms=900, status="SUCCESS",
            error_message=None, safety_flag=None, groundedness_score=1.0, llm_called=True,
            is_degraded=False, is_handoff=False,
        )
        if danh_gia:
            await feedback_repository.ghi_danh_gia(
                phien, interaction_id=ma, rater_type="CUSTOMER", rater_user_id=None,
                rating="NEGATIVE", reason_code="WRONG_INFO",
                comment="sai rồi, nhà em ở 12 Lê Lợi", correction_text=None,
            )
        if goi_cong_cu:
            await phien.execute(
                text(
                    "INSERT INTO ai.ai_tool_calls (tenant_id, ai_interaction_id, tool_name,"
                    " arguments, decision, block_reason) VALUES (ai.current_tenant(), :id,"
                    " 'tra_don_hang', CAST(:arg AS jsonb), 'BLOCKED', 'NOT_ALLOWLISTED')"
                ),
                {"id": ma, "arg": '{"so_dien_thoai": "0912345678"}'},
            )
    return ma


async def _dem(factory, tenant: UUID, sql: str, **tham_so) -> int:
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        return (await phien.execute(text(sql), tham_so)).scalar_one()


async def _so_luot(factory, tenant: UUID, conv: UUID) -> int:
    return await _dem(
        factory, tenant, "SELECT count(*) FROM ai.ai_interactions WHERE conversation_id = :c",
        c=conv,
    )


async def _con_tai_lieu(factory, tenant: UUID, doc: UUID) -> bool:
    return bool(await _dem(
        factory, tenant, "SELECT count(*) FROM knowledge.knowledge_documents WHERE id = :d", d=doc
    ))


async def _key(factory, tenant: UUID, doc: UUID) -> str:
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        uri = (await phien.execute(
            text("SELECT file_path FROM knowledge.knowledge_documents WHERE id = :d"), {"d": doc}
        )).scalar_one()
    return uri.removeprefix(f"s3://{S3_BUCKET}/")


def _con_tep(kho_s3, key: str) -> bool:
    try:
        kho_s3.stat_object(S3_BUCKET, key)
        return True
    except S3Error as e:
        assert e.code == "NoSuchKey"
        return False


def _muc(kq, bang: str):
    return next(m for m in kq.items if f"{m.target_schema}.{m.target_table}" == bang)


# ── Phạm vi xoá ─────────────────────────────────────────────────────────────


async def test_xoa_dung_pham_vi_khong_dung_khach_khac_tenant_khac(ha_tang, kho_s3):
    factory, _ = ha_tang
    tenant, tenant_khac = uuid4(), uuid4()
    x, y = uuid4(), uuid4()
    doc_x = await _tai_lieu(factory, kho_s3, tenant, HOP_DONG_X, x)
    doc_y = await _tai_lieu(factory, kho_s3, tenant, HOP_DONG_Y, y)
    doc_chung = await _tai_lieu(factory, kho_s3, tenant, CHINH_SACH_CHUNG, None)
    # Tenant khác có tài liệu gắn CÙNG giá trị contact_id và hội thoại CÙNG id — RLS phải che.
    doc_khac = await _tai_lieu(factory, kho_s3, tenant_khac, HOP_DONG_X, x)
    key_x = await _key(factory, tenant, doc_x)

    conv1, conv2, conv_y = uuid4(), uuid4(), uuid4()
    await _luot(factory, tenant, conv1, danh_gia=True, goi_cong_cu=True)
    await _luot(factory, tenant, conv1)
    await _luot(factory, tenant, conv2, danh_gia=True)
    await _luot(factory, tenant, conv_y, danh_gia=True)
    await _luot(factory, tenant_khac, conv1, danh_gia=True)

    gia = MockJavaCoreClient(diem_lead={(str(tenant), x): 2})
    kq = await service.forget_contact(str(tenant), x, [conv1, conv2], java_core=gia,
                                      factory=factory)

    assert kq.status == "COMPLETED"
    so = {f"{m.target_schema}.{m.target_table}": m.affected_rows for m in kq.items}
    assert so == {
        "knowledge.knowledge_documents": 1, "knowledge.knowledge_chunks": 1,
        "ai.ai_interactions": 3, "ai.ai_feedback": 2, "ai.ai_tool_calls": 1,
        f"s3.{S3_BUCKET}": 1, "sales.lead_scores": 2,
    }
    assert "MCP" in kq.note

    assert not await _con_tai_lieu(factory, tenant, doc_x) and not _con_tep(kho_s3, key_x)
    assert await _dem(factory, tenant, "SELECT count(*) FROM knowledge.knowledge_chunks"
                      " WHERE document_id = :d", d=doc_x) == 0
    assert await _so_luot(factory, tenant, conv1) == 0
    assert await _so_luot(factory, tenant, conv2) == 0
    assert await _dem(factory, tenant, "SELECT count(*) FROM ai.ai_tool_calls") == 0
    # Không đụng: khách Y, tài liệu chung, tenant khác.
    assert await _con_tai_lieu(factory, tenant, doc_y)
    assert await _con_tai_lieu(factory, tenant, doc_chung)
    assert await _so_luot(factory, tenant, conv_y) == 1
    assert await _con_tai_lieu(factory, tenant_khac, doc_khac)
    assert await _so_luot(factory, tenant_khac, conv1) == 1
    assert _con_tep(kho_s3, await _key(factory, tenant_khac, doc_khac))


async def test_xoa_ca_dong_doi_cung_tep(ha_tang, kho_s3):
    """Nạp lại (ADR-0031) để lại bản cũ ``ARCHIVED`` trỏ CÙNG tệp. ``contact_id`` gắn lên bản MỚI
    sau đó — bản cũ không mang nó nhưng vẫn là dữ liệu của khách."""
    factory, _ = ha_tang
    tenant, x = uuid4(), uuid4()
    cu = await _tai_lieu(factory, kho_s3, tenant, HOP_DONG_X, None)
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        moi = (await service.reindex_document(phien, cu)).job_id
    assert (await nap(factory, tenant, moi, embed=_NhungCoDinh())).trang_thai == "READY"
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        await service.update_document_metadata(phien, moi, DocumentMetadataUpdate(contact_id=x))
        # Nạp lại lần nữa: bản bóng phải CHÉP contact_id.
        bong = (await service.reindex_document(phien, moi)).job_id
    assert await _dem(factory, tenant, "SELECT count(*) FROM knowledge.knowledge_documents"
                      " WHERE id = :d AND contact_id = :x", d=bong, x=x) == 1

    kq = await service.forget_contact(str(tenant), x, [], java_core=MockJavaCoreClient(),
                                      factory=factory)

    assert _muc(kq, "knowledge.knowledge_documents").affected_rows == 3
    for doc in (cu, moi, bong):
        assert not await _con_tai_lieu(factory, tenant, doc)


async def test_chay_lai_luy_dang(ha_tang, kho_s3):
    factory, _ = ha_tang
    tenant, x, conv = uuid4(), uuid4(), uuid4()
    await _tai_lieu(factory, kho_s3, tenant, HOP_DONG_X, x)
    await _luot(factory, tenant, conv)
    gia = MockJavaCoreClient(diem_lead={(str(tenant), x): 1})

    lan1 = await service.forget_contact(str(tenant), x, [conv], java_core=gia, factory=factory)
    lan2 = await service.forget_contact(str(tenant), x, [conv], java_core=gia, factory=factory)

    assert lan1.status == lan2.status == "COMPLETED"
    assert sum(m.affected_rows for m in lan1.items) > 0
    assert all(m.affected_rows == 0 and m.status == "DONE" for m in lan2.items)


async def test_java_core_sap_thi_partially_failed_ma_phan_ai_van_xong(ha_tang, kho_s3):
    factory, _ = ha_tang
    tenant, x, conv = uuid4(), uuid4(), uuid4()
    doc = await _tai_lieu(factory, kho_s3, tenant, HOP_DONG_X, x)
    await _luot(factory, tenant, conv)
    sap = MockJavaCoreClient(loi=JavaCoreUnavailableError("java-core 503"))

    kq = await service.forget_contact(str(tenant), x, [conv], java_core=sap, factory=factory)

    assert kq.status == "PARTIALLY_FAILED"
    lead = _muc(kq, "sales.lead_scores")
    assert (lead.status, lead.error_code) == ("FAILED", "JAVA_CORE_UNAVAILABLE")
    assert all(m.status == "DONE" for m in kq.items if m is not lead)
    assert not await _con_tai_lieu(factory, tenant, doc)
    assert await _so_luot(factory, tenant, conv) == 0

    # java-core sống lại → gọi lại làm nốt đúng phần hỏng.
    gia = MockJavaCoreClient(diem_lead={(str(tenant), x): 2})
    lai = await service.forget_contact(str(tenant), x, [conv], java_core=gia, factory=factory)
    assert lai.status == "COMPLETED" and _muc(lai, "sales.lead_scores").affected_rows == 2


# ── 🖐 Câu trả lời sinh SAU khi xoá ──────────────────────────────────────────


async def test_cau_tra_loi_sau_khi_xoa_khong_con_trich_du_lieu_da_xoa(ha_tang, kho_s3):
    factory, _ = ha_tang
    tenant, x = uuid4(), uuid4()
    doc_x = await _tai_lieu(factory, kho_s3, tenant, HOP_DONG_X, x)
    doc_chung = await _tai_lieu(factory, kho_s3, tenant, CHINH_SACH_CHUNG, None)
    llm = _LLMTrichHet()
    tra_loi = RagAnswerer(
        embed=_NhungCoDinh(),
        llm=LLMChiuLoi(llm, CircuitBreaker(), han_chot_s=2.5),
        settings=Settings(llm_mode="mock"),
        factory=factory,
    )
    cau = "hợp đồng bảo trì máy lạnh bảo trì mấy lần mỗi năm"

    async def hoi():
        return await tra_loi.answer(
            tenant_id=str(tenant), question=cau,
            request=ChatRequest(conversation_id=uuid.uuid4(), message=cau),
        )

    truoc = await hoi()
    assert doc_x in {c.document_id for c in truoc.citations}, "trước khi xoá: phải trích được X"
    assert "HD-CT-0917" in llm.loi_nhac[-1]

    await service.forget_contact(str(tenant), x, [], java_core=MockJavaCoreClient(),
                                 factory=factory)

    sau = await hoi()
    trich = {c.document_id for c in sau.citations}
    assert doc_x not in trich and trich <= {doc_chung}
    assert "HD-CT-0917" not in llm.loi_nhac[-1] and "Trần Thị Bích" not in llm.loi_nhac[-1]
    assert all("HD-CT-0917" not in (c.snippet or "") for c in sau.citations)


@pytest.mark.parametrize("contact", [None, "khong-phai-uuid"])
def test_patch_contact_id_chi_nhan_uuid_hoac_null(contact):
    if contact is None:
        assert DocumentMetadataUpdate(contact_id=None).model_fields_set == {"contact_id"}
    else:
        with pytest.raises(ValueError):
            DocumentMetadataUpdate(contact_id=contact)


def test_vector_co_dinh_da_chuan_hoa():
    """Phòng thủ cho chính test: vector giả phải chuẩn L2 như bge-m3, nếu không cosine sai."""
    import asyncio

    v = asyncio.run(_NhungCoDinh().embed_batch(["a"])).vectors[0]
    assert math.isclose(sum(x * x for x in v), 1.0)
