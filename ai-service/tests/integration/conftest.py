"""Fixture dùng chung cho test nạp tài liệu (UC019) — Postgres (RLS) + RustFS (S3) thật.

``test_upload_documents.py`` tự khai ``ha_tang`` riêng (giới hạn dung lượng khác) — fixture cùng
tên trong module thắng fixture ở đây, đúng quy tắc của pytest.
"""

import pytest

from src.ai import service
from src.ai.config import Settings
from src.ai.db import session as db_session
from src.ai.integrations import object_storage
from tests.conftest import S3_ACCESS_KEY, S3_BUCKET, S3_SECRET_KEY


@pytest.fixture
async def ha_tang(pg_dsn_ai_app, kho_s3_endpoint, monkeypatch):
    """Nối facade vào Postgres và RustFS của test. Trả về (factory phiên CSDL, cấu hình).

    Lô nhúng 4 đoạn (không phải 32) để tệp mẫu vài chục đoạn cũng đi qua NHIỀU lô — các ca mất
    quyền và lỗi giữa chừng cần ít nhất hai lô. Không chờ giữa các lượt thử.
    """
    engine = db_session.tao_engine(pg_dsn_ai_app.replace("postgresql://", "postgresql+psycopg://"))
    factory = db_session.tao_session_factory(engine)
    cau_hinh = Settings(
        s3_endpoint=kho_s3_endpoint,
        s3_bucket=S3_BUCKET,
        s3_access_key=S3_ACCESS_KEY,
        s3_secret_key=S3_SECRET_KEY,
        ai_mode="mock",
        kb_embed_batch=4,
        kb_cho_thu_lai_s=(0.0,),
    )
    monkeypatch.setattr(service, "get_settings", lambda: cau_hinh)
    client_s3 = object_storage.tao_client(cau_hinh)
    monkeypatch.setattr(object_storage, "_client_mac_dinh", lambda: client_s3)
    yield factory, cau_hinh
    await engine.dispose()


@pytest.fixture
def doi_cau_hinh(ha_tang, monkeypatch):
    """Đổi vài tham số cấu hình giữa chừng test: ``doi_cau_hinh(kb_job_ket_sau_s=0)``."""
    _, goc = ha_tang

    def doi(**thay):
        moi = goc.model_copy(update=thay)
        monkeypatch.setattr(service, "get_settings", lambda: moi)
        return moi

    return doi
