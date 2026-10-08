"""``RagAnswerer`` trên Postgres THẬT, role ``ai_app`` chịu RLS — cô lập tenant đi trọn nhánh UC023.

``test_tim_kiem_lai.py`` đã khoá câu SQL. Tệp này khoá phần nối dây quanh nó: phiên mở bằng
``get_tenant_session`` với ĐÚNG tenant của lượt chat, và mọi đoạn vào lời nhắc lẫn trích dẫn đều
thuộc tenant đó — ca khó nhất: hai tenant có tài liệu GIỐNG HỆT nhau, cùng vector.

``RagAnswerer`` tự commit qua ``get_tenant_session`` nên không bọc được trong một transaction rồi
rollback như ``test_tim_kiem_lai.py``: dữ liệu gieo bằng ``crm_owner`` và xoá ở cuối fixture.
"""

import math
import uuid
from collections.abc import AsyncIterator, Iterator
from uuid import UUID, uuid4

import psycopg
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.ai.config import Settings
from src.ai.db import session as db_session
from src.ai.db.repositories.chunk_repository import vector_sang_chuoi
from src.ai.inference.clients import KetQuaNhung
from src.ai.integrations.llm import CircuitBreaker, KetQuaLLM, LLMChiuLoi
from src.ai.rag.answerer import RagAnswerer
from src.ai.schemas import ChatRequest
from tests.conftest import AI_PASSWORD, AI_USER, OWNER_PASSWORD, OWNER_USER

MODEL, VERSION = "BAAI/bge-m3", "int8-test-rag"
DIM = 1024


def _v(**truc: float) -> list[float]:
    v = [0.0] * DIM
    for ten, gia_tri in truc.items():
        v[int(ten[1:])] = gia_tri
    do_dai = math.sqrt(sum(x * x for x in v))
    return [x / do_dai for x in v]


class _NhungCoDinh:
    """Mọi câu hỏi nhúng thành cùng một vector trên trục t0 — thứ hạng làn vector biết trước."""

    async def embed_batch(self, texts):
        return KetQuaNhung(MODEL, VERSION, [_v(t0=1) for _ in texts])

    async def aclose(self) -> None:
        return None


class _LLMTrichHet:
    """Trích MỌI đoạn được đưa vào lời nhắc ⇒ trích dẫn trả về = toàn bộ đoạn đã truy hồi."""

    model = "llm-gia"

    def __init__(self) -> None:
        self.loi_nhac: list[str] = []

    async def chat(self, messages, *, timeout_s: float) -> KetQuaLLM:
        noi_dung = messages[1]["content"]
        self.loi_nhac.append(noi_dung)
        so_doan = noi_dung.count("<doan ")
        trich = "".join(f"[{i}]" for i in range(1, so_doan + 1))
        return KetQuaLLM(f"Máy lạnh được bảo hành theo tài liệu {trich}.", self.model, 1, 1)

    async def aclose(self) -> None:
        return None


def _dsn_owner(pg_dsn_ai_app: str) -> str:
    return pg_dsn_ai_app.replace(f"{AI_USER}:{AI_PASSWORD}@", f"{OWNER_USER}:{OWNER_PASSWORD}@")


@pytest.fixture
def hai_tenant(pg_dsn_ai_app) -> Iterator[dict[UUID, set[UUID]]]:
    """Hai tenant, mỗi tenant 4 đoạn cùng nội dung + cùng vector. Trả {tenant: {chunk_id}}."""
    cac_tenant: dict[UUID, set[UUID]] = {uuid4(): set(), uuid4(): set()}
    with psycopg.connect(_dsn_owner(pg_dsn_ai_app)) as conn:
        for tenant, cac_doan in cac_tenant.items():
            with conn.transaction():
                conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant),))
                doc = uuid4()
                conn.execute(
                    "INSERT INTO knowledge.knowledge_documents"
                    " (id, tenant_id, title, source_type, file_path, file_name, status)"
                    " VALUES (%s, %s, 'Chính sách bảo hành', 'TXT', %s, 'bh.txt', 'READY')",
                    (doc, tenant, f"/test/{doc}.txt"),
                )
                for i in range(4):
                    ma = uuid4()
                    conn.execute(
                        "INSERT INTO knowledge.knowledge_chunks (id, tenant_id, document_id,"
                        " chunk_index, content, embedding, embedding_model, embedding_version)"
                        " VALUES (%s, %s, %s, %s, %s, CAST(%s AS vector), %s, %s)",
                        (ma, tenant, doc, i, f"Máy lạnh được bảo hành {i + 1} năm",
                         vector_sang_chuoi(_v(t0=4 - i, t1=1)), MODEL, VERSION),
                    )
                    cac_doan.add(ma)
    yield cac_tenant
    with psycopg.connect(_dsn_owner(pg_dsn_ai_app), autocommit=True) as conn:
        for tenant in cac_tenant:
            conn.execute("DELETE FROM knowledge.knowledge_chunks WHERE tenant_id = %s", (tenant,))
            conn.execute(
                "DELETE FROM knowledge.knowledge_documents WHERE tenant_id = %s", (tenant,)
            )


@pytest.fixture
async def factory(pg_dsn_ai_app) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = db_session.tao_engine(pg_dsn_ai_app.replace("postgresql://", "postgresql+psycopg://"))
    yield db_session.tao_session_factory(engine)
    await engine.dispose()


async def test_moi_doan_vao_loi_nhac_va_trich_dan_deu_cua_tenant_dang_hoi(hai_tenant, factory):
    llm = _LLMTrichHet()
    tra_loi = RagAnswerer(
        embed=_NhungCoDinh(),
        llm=LLMChiuLoi(llm, CircuitBreaker(), han_chot_s=2.5),
        settings=Settings(llm_mode="mock"),
        factory=factory,
    )
    for tenant, cua_minh in hai_tenant.items():
        cua_nguoi_khac = set().union(*(d for t, d in hai_tenant.items() if t != tenant))
        cau = "máy lạnh bảo hành bao lâu"
        kq = await tra_loi.answer(
            tenant_id=str(tenant),
            question=cau,
            request=ChatRequest(conversation_id=uuid.uuid4(), message=cau),
        )
        trich = {c.chunk_id for c in kq.citations}
        assert len(trich) == 4, "phải lấy về đủ 4 đoạn của chính tenant"
        assert trich <= cua_minh and not trich & cua_nguoi_khac
        assert kq.retrieval_top_score is not None and kq.retrieval_top_score > 0.9

