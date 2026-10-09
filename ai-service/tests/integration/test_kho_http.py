"""UC020 qua HTTP — 4 mã lỗi của đặc tả, sửa không đụng chỉ mục, nạp lại tới lúc đổi bản. Ngày 11.

- 404 ``DOCUMENT_NOT_FOUND`` — tài liệu của tenant KHÁC, không phân biệt được với "không tồn
  tại": ``test_404_tenant_khac_moi_duong``.
- 409 ``DOCUMENT_BUSY`` — đang nạp / đang nạp lại: ``test_409_dang_ban``.
- 422 ``INVALID_METADATA`` — trùng ``title + version``, sai định dạng:
  ``test_422_trung_tieu_de_va_sai_dinh_dang``.
- 5xx và trạng thái giữ nguyên — CSDL hỏng giữa lúc gỡ (java-core trả 502):
  ``test_go_hong_giua_chung_tra_5xx_va_giu_nguyen``.
"""

from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import text

from src.ai import service
from src.ai.db import session as db_session
from src.ai.db.repositories import document_repository
from src.api import deps
from src.api.main import create_app
from tests.integration.nap_chung import cac_doan, nap, tai_lieu_pending, trang_thai

TEP = "faq-thanh-toan.txt"


@pytest.fixture
async def client(ha_tang):
    factory, _ = ha_tang

    async def _phien_test(tenant_id: deps.TenantIdDep):
        async with db_session.get_tenant_session(tenant_id, factory=factory) as phien:
            yield phien

    app = create_app()
    app.dependency_overrides[deps.get_session] = _phien_test
    # raise_app_exceptions=False: lỗi chưa xử lý thành HTTP 500 như máy chủ thật.
    chuyen = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=chuyen, base_url="http://t") as c:
        yield c


def _h(tenant) -> dict[str, str]:
    return {"X-Tenant-Id": str(tenant)}


async def _ready(factory, kho_s3, tenant) -> UUID:
    doc = await tai_lieu_pending(factory, kho_s3, tenant, TEP, "TXT")
    assert (await nap(factory, tenant, doc)).trang_thai == "READY"
    return doc


async def test_404_tenant_khac_moi_duong(client, ha_tang, kho_s3):
    factory, _ = ha_tang
    a, b = uuid4(), uuid4()
    doc = await _ready(factory, kho_s3, a)
    for phuong_thuc, duong, body in [
        ("GET", f"/v1/documents/{doc}", None),
        ("GET", f"/v1/documents/{doc}/chunks", None),
        ("PATCH", f"/v1/documents/{doc}", {"description": "x"}),
        ("POST", f"/v1/documents/{doc}/reindex", None),
        ("DELETE", f"/v1/documents/{doc}", None),
        ("DELETE", f"/v1/ai/kb/documents/{doc}", None),
    ]:
        r = await client.request(phuong_thuc, duong, json=body, headers=_h(b))
        assert (r.status_code, r.json()["code"]) == (404, "DOCUMENT_NOT_FOUND"), duong
    # Tài liệu của A không bị ai đụng tới.
    assert (await trang_thai(factory, a, doc))[0] == "READY"


async def test_409_dang_ban(client, ha_tang, kho_s3):
    factory, _ = ha_tang
    t = uuid4()
    dang_cho = await tai_lieu_pending(factory, kho_s3, t, TEP, "TXT")
    r = await client.delete(f"/v1/documents/{dang_cho}", headers=_h(t))
    assert (r.status_code, r.json()["code"]) == (409, "DOCUMENT_BUSY")

    doc = await _ready(factory, kho_s3, t)
    assert (await client.post(f"/v1/documents/{doc}/reindex", headers=_h(t))).status_code == 200
    for phuong_thuc, duong, body in [
        ("POST", f"/v1/documents/{doc}/reindex", None),  # nạp lại chồng
        ("DELETE", f"/v1/documents/{doc}", None),  # gỡ giữa lúc nạp lại
        ("PATCH", f"/v1/documents/{doc}", {"title": "Tiêu đề mới"}),
    ]:
        r = await client.request(phuong_thuc, duong, json=body, headers=_h(t))
        assert (r.status_code, r.json()["code"]) == (409, "DOCUMENT_BUSY"), duong


async def test_422_trung_tieu_de_va_sai_dinh_dang(client, ha_tang, kho_s3):
    factory, _ = ha_tang
    t = uuid4()
    mot, hai = await _ready(factory, kho_s3, t), await _ready(factory, kho_s3, t)
    tieu_de_mot = (await client.get(f"/v1/documents/{mot}", headers=_h(t))).json()["title"]

    r = await client.patch(f"/v1/documents/{hai}", json={"title": tieu_de_mot}, headers=_h(t))
    assert (r.status_code, r.json()["code"]) == (422, "INVALID_METADATA")  # cùng version 1
    for body in ({"title": "ab"}, {"title": None}, {"language": "en"},
                 {"tenant_id": str(uuid4())}):
        r = await client.patch(f"/v1/documents/{hai}", json=body, headers=_h(t))
        assert (r.status_code, r.json()["code"]) == (422, "INVALID_METADATA"), body


async def test_go_hong_giua_chung_tra_5xx_va_giu_nguyen(client, ha_tang, kho_s3, monkeypatch):
    factory, _ = ha_tang
    t = uuid4()
    doc = await _ready(factory, kho_s3, t)
    so_doan = len(await cac_doan(factory, t, doc))
    that = document_repository.xoa_khoi_chi_muc

    async def xoa_roi_hong(session, document_id):
        await that(session, document_id)  # đoạn ĐÃ xoá, tài liệu ĐÃ ARCHIVED — trong transaction
        raise ConnectionError("giả lập CSDL rớt kết nối trước khi commit")

    monkeypatch.setattr(document_repository, "xoa_khoi_chi_muc", xoa_roi_hong)
    r = await client.delete(f"/v1/documents/{doc}", headers=_h(t))
    assert r.status_code == 500
    assert (await trang_thai(factory, t, doc))[0] == "READY"
    assert len(await cac_doan(factory, t, doc)) == so_doan


async def test_sua_sieu_du_lieu_khong_dung_chi_muc_vector(client, ha_tang, kho_s3):
    factory, _ = ha_tang
    t = uuid4()
    doc = await _ready(factory, kho_s3, t)
    sql = ("SELECT id, embedding::text, updated_at FROM knowledge.knowledge_chunks"
           " WHERE document_id = :id ORDER BY chunk_index")

    async def anh_chup():
        async with db_session.get_tenant_session(str(t), factory=factory) as phien:
            return (await phien.execute(text(sql), {"id": doc})).all()

    truoc = await anh_chup()
    r = await client.patch(
        f"/v1/documents/{doc}", json={"title": "Câu hỏi thường gặp về thanh toán (2026)",
                                      "description": None}, headers=_h(t),
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Câu hỏi thường gặp về thanh toán (2026)"
    assert r.json()["description"] is None and r.json()["chunk_count"] == len(truoc)
    assert await anh_chup() == truoc  # cùng đoạn, cùng vector, cùng updated_at


async def test_danh_sach_tim_khong_dau_va_xem_doan_khong_co_vector(client, ha_tang, kho_s3):
    factory, _ = ha_tang
    t = uuid4()
    doc = await _ready(factory, kho_s3, t)
    await client.patch(f"/v1/documents/{doc}", json={"title": "Bảng báo giá dịch vụ"},
                       headers=_h(t))
    r = await client.get("/v1/documents", params={"keyword": "BAO GIA"}, headers=_h(t))
    assert r.status_code == 200 and [d["id"] for d in r.json()["items"]] == [str(doc)]
    assert (await client.get("/v1/documents", params={"keyword": "khong co"},
                             headers=_h(t))).json()["total"] == 0
    r = await client.get("/v1/documents", params={"sourceType": "PDF"}, headers=_h(t))
    assert r.json()["total"] == 0

    r = await client.get(f"/v1/documents/{doc}/chunks", params={"size": 3}, headers=_h(t))
    d = r.json()
    assert d["total"] == len(await cac_doan(factory, t, doc)) and len(d["items"]) <= 3
    assert all("embedding" not in item and item["has_vector"] for item in d["items"])


async def test_nap_lai_qua_http_toi_luc_doi_ban(client, ha_tang, kho_s3, doi_cau_hinh):
    factory, _ = ha_tang
    t = uuid4()
    cu = await _ready(factory, kho_s3, t)
    r = await client.post(f"/v1/documents/{cu}/reindex", headers=_h(t))
    assert r.status_code == 200
    moi = UUID(r.json()["job_id"])
    chi_tiet = (await client.get(f"/v1/documents/{cu}", headers=_h(t))).json()
    assert chi_tiet["status"] == "READY" and chi_tiet["reindex_document_id"] == str(moi)

    # Worker: bộ quét nhặt bản bóng (không chờ quá hạn), rồi nạp như tài liệu mới.
    doi_cau_hinh(kb_job_ket_sau_s=300.0)
    assert service.JobCanNapLai(str(t), moi) in await service.quet_job_ket(factory=factory)
    assert (await nap(factory, t, moi)).trang_thai == "READY"

    cu_sau = (await client.get(f"/v1/documents/{cu}", headers=_h(t))).json()
    moi_sau = (await client.get(f"/v1/documents/{moi}", headers=_h(t))).json()
    assert (cu_sau["status"], cu_sau["chunk_count"]) == ("ARCHIVED", 0)
    assert moi_sau["status"] == "READY" and moi_sau["replaces_document_id"] == str(cu)
    assert moi_sau["version"] == cu_sau["version"] + 1
    ds = (await client.get("/v1/documents", headers=_h(t))).json()
    assert [d["id"] for d in ds["items"]] == [str(moi)]  # bản cũ ARCHIVED bị ẩn


async def test_nap_lai_toan_kho_va_go_luy_dang(client, ha_tang, kho_s3):
    factory, _ = ha_tang
    t = uuid4()
    a, b = await _ready(factory, kho_s3, t), await _ready(factory, kho_s3, t)
    await tai_lieu_pending(factory, kho_s3, t, TEP, "TXT")  # PENDING không thuộc diện nạp lại
    r = await client.post("/v1/ai/kb/reindex", headers=_h(t))
    assert r.status_code == 200
    assert r.json() == {"tenant_id": str(t), "status": "ACCEPTED", "total_documents": 2}
    # Gọi lại khi cả hai đang có bản bóng chạy: không tạo bản bóng thứ hai.
    assert (await client.post("/v1/ai/kb/reindex", headers=_h(t))).json()["total_documents"] == 0

    t2 = uuid4()
    doc = await _ready(factory, kho_s3, t2)
    r = await client.delete(f"/v1/ai/kb/documents/{doc}", headers=_h(t2))
    assert r.status_code == 200 and r.json()["chunks_deleted"] > 0
    r = await client.delete(f"/v1/documents/{doc}", headers=_h(t2))
    assert r.status_code == 200 and r.json()["chunks_deleted"] == 0  # luỹ đẳng
    for x in (a, b):
        assert (await trang_thai(factory, t, x))[0] == "READY"  # bản cũ vẫn phục vụ
