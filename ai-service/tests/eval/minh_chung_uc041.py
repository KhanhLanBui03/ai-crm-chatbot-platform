"""Minh chứng UC041 trên hạ tầng thật: xoá dữ liệu cá nhân một khách, hỏi lại trước/sau. [R&D]

    docker compose up -d postgres rustfs-init
    docker compose -f inference/compose.inference.yml up -d ai-embed
    cd ai-service && source .venv/bin/activate
    LLM_MODE=remote INTERNAL_API_TOKEN=minh-chung-uc041 python -m tests.eval.minh_chung_uc041

ai-embed THẬT (bge-m3 INT8), RustFS THẬT, Postgres dev (role ``ai_app``, RLS), Gemini THẬT cho hai
câu trả lời. Endpoint xoá gọi qua HTTP (ASGI trong tiến trình) — đi qua đúng chốt
``X-Internal-Token`` như java-core sẽ gọi. Tenant riêng ``dddddddd-…-d041``.

Phần GIẢ, khai trung thực: đặc trưng lead (``sales.lead_scores``) xoá qua java-core GIẢ — endpoint
``/internal/contacts/{id}/lead-scores`` chưa có ở java-core (09/10). Lượt chat và đánh giá được ghi
thẳng bằng repository (không qua ``/v1/ai/chat``) — phép thử là về XOÁ, không về sinh lượt.

In ra: biên bản xoá theo từng bảng; tệp gốc còn/mất trên S3; câu trả lời + trích dẫn TRƯỚC và SAU.
"""

import asyncio
import io
import os
from uuid import UUID, uuid4

import httpx
from sqlalchemy import text

from src.ai import service
from src.ai.config import get_settings
from src.ai.db import session as db_session
from src.ai.db.repositories import document_repository, feedback_repository, interaction_repository
from src.ai.inference.clients import tao_embed_client
from src.ai.integrations import object_storage
from src.ai.integrations.java_core import tao_java_core_client
from src.ai.integrations.llm import tao_llm_chiu_loi
from src.ai.rag.answerer import RagAnswerer
from src.ai.schemas import ChatRequest, DocumentMetadataUpdate
from src.api.main import create_app

TENANT = "dddddddd-0000-0000-0000-00000000d041"
CAU_HOI = "máy lạnh được bảo trì mấy lần mỗi năm"
DAU_VET = "HD-CT-0917"
TAI_LIEU = {
    "hop-dong-bao-tri-khach.txt": (
        "Hợp đồng bảo trì máy lạnh số HD-CT-0917 ký với khách Trần Thị Bích. "
        "Theo hợp đồng này, máy lạnh được bảo trì 4 lần mỗi năm tại nhà riêng của khách, "
        "phí trọn gói 1.200.000 đồng mỗi năm, kỹ thuật viên phụ trách là anh Hùng."
    ),
    "chinh-sach-bao-tri-chung.txt": (
        "Chính sách bảo trì máy lạnh của cửa hàng: máy lạnh mua tại cửa hàng được bảo trì định kỳ "
        "2 lần mỗi năm trong thời gian bảo hành, miễn phí công, chỉ tính vật tư phát sinh."
    ),
}


async def _tai_len_va_nap(s, embed, ten: str, noi_dung: str) -> UUID:
    du_lieu = noi_dung.encode()
    key = f"{TENANT}/{uuid4()}/{ten}"
    object_storage._client_mac_dinh().put_object(
        s.s3_bucket, key, io.BytesIO(du_lieu), len(du_lieu)
    )
    async with db_session.get_tenant_session(TENANT) as phien:
        doc = await document_repository.them_tai_lieu_pending(
            phien, title=f"{ten} [{uuid4().hex[:6]}]", description=None, language="vi",
            source_type="TXT", file_name=ten, file_path=f"s3://{s.s3_bucket}/{key}",
            mime_type="text/plain", file_size_bytes=len(du_lieu), version=1, uploaded_by=None,
        )
    kq = await service.nap_tai_lieu(TENANT, doc, embed=embed)
    print(f"  nạp {ten}: {kq.trang_thai}, {kq.so_doan} đoạn")
    return doc


async def _luot(conv: UUID, danh_gia: bool) -> None:
    ma = uuid4()
    async with db_session.get_tenant_session(TENANT) as phien:
        await interaction_repository.ghi_luot(
            phien, id=ma, conversation_id=str(conv), branch="RAG", intent="KB_SEARCH",
            intent_confidence=0.9, user_query="hợp đồng bảo trì của chị còn mấy lần",
            response_text="Dạ hợp đồng HD-CT-0917 còn 3 lần bảo trì [1].",
            retrieved_chunk_ids=[], retrieval_top_score=0.8, is_answered=True,
            refusal_reason=None, model_name="gemini-3.5-flash-lite", model_version=None,
            prompt_tokens=0, completion_tokens=0, cost_vnd=0.0, latency_ms=1000,
            status="SUCCESS", error_message=None, safety_flag=None, groundedness_score=1.0,
            llm_called=True, is_degraded=False, is_handoff=False,
        )
        if danh_gia:
            await feedback_repository.ghi_danh_gia(
                phien, interaction_id=ma, rater_type="CUSTOMER", rater_user_id=None,
                rating="POSITIVE", reason_code=None, comment="cảm ơn, nhà chị ở 12 Lê Lợi",
                correction_text=None,
            )


def _in_tra_loi(nhan: str, kq, tai_lieu_khach: UUID) -> None:
    trich_khach = sum(c.document_id == tai_lieu_khach for c in kq.citations)
    print(f"\n{nhan}: {kq.answer}")
    print(f"  trích dẫn: {len(kq.citations)} đoạn, của tài liệu khách: {trich_khach}; "
          f"có '{DAU_VET}' trong câu trả lời: {DAU_VET in kq.answer}; LLM: {kq.llm_called}")


async def chay() -> None:
    s = get_settings()
    token = os.environ.get("INTERNAL_API_TOKEN") or s.internal_api_token
    if s.llm_mode != "remote" or not token:
        raise SystemExit("Cần LLM_MODE=remote và INTERNAL_API_TOKEN")
    khach, khach_khac = uuid4(), uuid4()
    embed = tao_embed_client(s)
    tra_loi = RagAnswerer(embed=embed, llm=tao_llm_chiu_loi(s), settings=s)
    try:
        print(f"Tenant {TENANT} — khách {khach}")
        doc_khach = await _tai_len_va_nap(s, embed, *list(TAI_LIEU.items())[0])
        doc_chung = await _tai_len_va_nap(s, embed, *list(TAI_LIEU.items())[1])
        async with db_session.get_tenant_session(TENANT) as phien:
            await service.update_document_metadata(
                phien, doc_khach, DocumentMetadataUpdate(contact_id=khach)
            )
        conv1, conv2, conv_khac = uuid4(), uuid4(), uuid4()
        await _luot(conv1, danh_gia=True)
        await _luot(conv1, danh_gia=False)
        await _luot(conv2, danh_gia=True)
        await _luot(conv_khac, danh_gia=True)
        gia = tao_java_core_client(s)
        gia.diem_lead[(TENANT, khach)] = 3  # java-core GIẢ — xem docstring

        cau = ChatRequest(conversation_id=uuid4(), message=CAU_HOI)
        _in_tra_loi("TRƯỚC khi xoá", await tra_loi.answer(
            tenant_id=TENANT, question=CAU_HOI, request=cau), doc_khach)

        async with db_session.get_tenant_session(TENANT) as phien:
            key = (await phien.execute(text(
                "SELECT file_path FROM knowledge.knowledge_documents WHERE id = :d"
            ), {"d": doc_khach})).scalar_one().removeprefix(f"s3://{s.s3_bucket}/")

        app = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://ai-service"
        ) as c:
            h = {"X-Tenant-Id": TENANT}
            r = await c.delete(f"/v1/ai/privacy/contacts/{khach}", headers=h)
            print(f"\nKhông token: HTTP {r.status_code} {r.json()['code']}")
            r = await c.delete(
                f"/v1/ai/privacy/contacts/{khach}",
                params=[("conversationId", str(conv1)), ("conversationId", str(conv2))],
                headers={**h, "X-Internal-Token": token},
            )
        body = r.json()
        print(f"Có token: HTTP {r.status_code}, trạng thái {body['status']}")
        print("| Bảng | Hành động | Trạng thái | Số dòng |\n|---|---|---|---|")
        for m in body["items"]:
            print(f"| {m['targetSchema']}.{m['targetTable']} | {m['action']} | {m['status']} | "
                  f"{m['affectedRows']} |")
        try:
            object_storage._client_mac_dinh().stat_object(s.s3_bucket, key)
            print("Tệp gốc trên S3: CÒN")
        except Exception as e:  # noqa: BLE001
            print(f"Tệp gốc trên S3: đã xoá ({type(e).__name__})")

        _in_tra_loi("SAU khi xoá", await tra_loi.answer(
            tenant_id=TENANT, question=CAU_HOI,
            request=ChatRequest(conversation_id=uuid4(), message=CAU_HOI)), doc_khach)

        async with db_session.get_tenant_session(TENANT) as phien:
            con = (await phien.execute(text(
                "SELECT count(*) FROM ai.ai_interactions WHERE conversation_id = :c"
            ), {"c": conv_khac})).scalar_one()
            con_chung = await document_repository.lay_tai_lieu(phien, doc_chung)
        print(f"\nKhông đụng: lượt của khách khác còn {con}; tài liệu chung còn "
              f"{con_chung is not None}; khách khác {khach_khac} không có dòng nào bị xoá.")
    finally:
        await tra_loi.aclose()
        await db_session.dispose()


if __name__ == "__main__":
    asyncio.run(chay())
