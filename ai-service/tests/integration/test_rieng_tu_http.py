"""UC041 + UC026 qua HTTP — chốt ``X-Internal-Token``, hình dạng phản hồi, mã lỗi. Ngày 12.

- 403 ``INTERNAL_ONLY`` — thiếu token, sai token, hoặc ai-service chưa cấu hình token (endpoint
  đóng hẳn): ``test_xoa_khong_token_hop_le_thi_403_va_khong_xoa_gi``. Gateway mở ``/ai/v1/**``
  cho mọi JWT của tenant — đây là chốt duy nhất giữa một nhân viên bất kỳ và một thao tác xoá vĩnh
  viễn không qua bước xác minh danh tính.
- 401 ``TENANT_CONTEXT_MISSING`` — thiếu ``X-Tenant-Id``, kể cả khi token đúng.
- ``POST /v1/ai/summarize``: 200 bốn phần camelCase; 422 ``CONVERSATION_TOO_SHORT``.
"""

from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from src.ai import service
from src.ai.config import get_settings
from src.ai.db import session as db_session
from src.ai.integrations.java_core import MockJavaCoreClient
from src.api.main import create_app
from tests.integration.nap_chung import nap, tai_lieu_pending

TOKEN = "bi-mat-noi-bo-chi-java-core-biet"


@pytest.fixture
def java_core_gia(monkeypatch):
    gia = MockJavaCoreClient()
    monkeypatch.setattr(service, "tao_java_core_client", lambda *a, **k: gia)
    return gia


@pytest.fixture
async def client(ha_tang, monkeypatch, java_core_gia):
    factory, cau_hinh = ha_tang
    # Hai endpoint này không dùng SessionDep — facade tự mở phiên qua factory mặc định.
    monkeypatch.setattr(db_session, "async_session", factory)
    co_token = cau_hinh.model_copy(update={"internal_api_token": TOKEN})
    monkeypatch.setattr(service, "get_settings", lambda: co_token)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: co_token
    chuyen = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=chuyen, base_url="http://t") as c:
        c.app = app
        yield c


async def _doc_cua_khach(factory, kho_s3, tenant, khach):
    doc = await tai_lieu_pending(factory, kho_s3, tenant, "faq-thanh-toan.txt", "TXT")
    assert (await nap(factory, tenant, doc)).trang_thai == "READY"
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        await phien.execute(
            text("UPDATE knowledge.knowledge_documents SET contact_id = :k WHERE id = :d"),
            {"k": khach, "d": doc},
        )
    return doc


async def _con(factory, tenant, doc) -> bool:
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        return bool((await phien.execute(
            text("SELECT count(*) FROM knowledge.knowledge_documents WHERE id = :d"), {"d": doc}
        )).scalar_one())


@pytest.mark.parametrize("header", [{}, {"X-Internal-Token": "doan-bua"},
                                    {"X-Internal-Token": TOKEN[:-1]}])
async def test_xoa_khong_token_hop_le_thi_403_va_khong_xoa_gi(client, ha_tang, kho_s3, header):
    factory, _ = ha_tang
    tenant, khach = uuid4(), uuid4()
    doc = await _doc_cua_khach(factory, kho_s3, tenant, khach)

    r = await client.delete(
        f"/v1/ai/privacy/contacts/{khach}", headers={"X-Tenant-Id": str(tenant), **header}
    )

    assert (r.status_code, r.json()["code"]) == (403, "INTERNAL_ONLY")
    assert await _con(factory, tenant, doc)


async def test_chua_cau_hinh_token_thi_endpoint_dong_han(client, ha_tang):
    _, cau_hinh = ha_tang
    client.app.dependency_overrides[get_settings] = lambda: cau_hinh  # token rỗng
    r = await client.delete(
        f"/v1/ai/privacy/contacts/{uuid4()}",
        headers={"X-Tenant-Id": str(uuid4()), "X-Internal-Token": ""},
    )
    assert (r.status_code, r.json()["code"]) == (403, "INTERNAL_ONLY")


async def test_thieu_tenant_thi_401_du_token_dung(client):
    r = await client.delete(
        f"/v1/ai/privacy/contacts/{uuid4()}", headers={"X-Internal-Token": TOKEN}
    )
    assert (r.status_code, r.json()["code"]) == (401, "TENANT_CONTEXT_MISSING")


async def test_xoa_hop_le_tra_tien_do_theo_bang(client, ha_tang, kho_s3, java_core_gia):
    factory, _ = ha_tang
    tenant, khach = uuid4(), uuid4()
    doc = await _doc_cua_khach(factory, kho_s3, tenant, khach)
    java_core_gia.diem_lead[(str(tenant), khach)] = 1

    r = await client.delete(
        f"/v1/ai/privacy/contacts/{khach}",
        params=[("conversationId", str(uuid4())), ("conversationId", str(uuid4()))],
        headers={"X-Tenant-Id": str(tenant), "X-Internal-Token": TOKEN},
    )

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "COMPLETED" and body["contactId"] == str(khach)
    muc = {f"{m['targetSchema']}.{m['targetTable']}": m for m in body["items"]}
    assert muc["knowledge.knowledge_documents"]["affectedRows"] == 1
    assert muc["sales.lead_scores"]["affectedRows"] == 1
    assert {"action", "status", "affectedRows"} <= set(muc["ai.ai_interactions"])
    assert not await _con(factory, tenant, doc)


async def test_conversation_id_sai_dinh_dang_thi_422(client):
    r = await client.delete(
        f"/v1/ai/privacy/contacts/{uuid4()}", params={"conversationId": "khong-phai-uuid"},
        headers={"X-Tenant-Id": str(uuid4()), "X-Internal-Token": TOKEN},
    )
    assert r.status_code == 422


# ── POST /v1/ai/summarize ────────────────────────────────────────────────────


async def test_tom_tat_dong_bo_tra_bon_phan(client):
    r = await client.post(
        "/v1/ai/summarize",
        json={"conversation_id": str(uuid4()), "trigger": "MANUAL", "messages": [
            {"sender": "CUSTOMER", "text": "Tủ lạnh nhà em không lạnh"},
            {"sender": "BOT", "text": "Dạ anh dùng model nào ạ?"},
            {"sender": "CUSTOMER", "text": "Toshiba GR-RT325"},
        ]},
        headers={"X-Tenant-Id": str(uuid4())},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["trigger"] == "MANUAL"
    for khoa in ("mainNeed", "providedInfo", "unresolvedIssues", "nextSteps", "summaryText",
                 "modelVersion", "generatedAt", "interactionId"):
        assert body[khoa], khoa
    assert body["modelVersion"].endswith("@tt2")


async def test_tom_tat_dong_bo_hoi_thoai_ngan_422(client):
    r = await client.post(
        "/v1/ai/summarize",
        json={"conversation_id": str(uuid4()),
              "messages": [{"sender": "CUSTOMER", "text": "alo"}]},
        headers={"X-Tenant-Id": str(uuid4())},
    )
    assert (r.status_code, r.json()["code"]) == (422, "CONVERSATION_TOO_SHORT")


@pytest.mark.parametrize("body", [
    {"conversation_id": "x", "messages": [{"sender": "CUSTOMER", "text": "a"}]},
    {"conversation_id": str(uuid4()), "messages": []},
    {"conversation_id": str(uuid4()), "trigger": "CONVERSATION_CLOSED",
     "messages": [{"sender": "CUSTOMER", "text": "a"}]},
])
async def test_tom_tat_dong_bo_body_sai_422(client, body):
    r = await client.post("/v1/ai/summarize", json=body, headers={"X-Tenant-Id": str(uuid4())})
    assert (r.status_code, r.json()["code"]) == (422, "INVALID_REQUEST")
