"""Client ``/internal/*`` của java-core — đường dẫn, header, vỏ ``ApiResponse``, phân trang, lỗi.

Kiểm bằng ``httpx.MockTransport`` theo ĐÚNG hình dạng của nháp hợp đồng
``docs/contracts/uc026-uc041-tom-tat-va-xoa-du-lieu.md`` — Track A làm xong endpoint thì chỉ đổi
``JAVA_CORE_MODE=remote``.
"""

import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from src.ai.exceptions import JavaCoreUnavailableError
from src.ai.integrations.java_core import BanGhiTomTat, HttpJavaCoreClient, MockJavaCoreClient
from src.ai.telemetry.logging import trace_id_var

TENANT = "11111111-1111-1111-1111-111111111111"


def _client(xu_ly) -> HttpJavaCoreClient:
    return HttpJavaCoreClient(
        base_url="http://java-core:8081", timeout_s=1.0, transport=httpx.MockTransport(xu_ly)
    )


def _vo(data) -> dict:
    return {"success": True, "data": data, "message": None, "code": None}


async def test_lay_tin_nhan_doc_het_cac_trang_va_mang_header():
    conv = uuid4()
    da_goi: list[httpx.Request] = []

    def xu_ly(req: httpx.Request) -> httpx.Response:
        da_goi.append(req)
        trang = int(req.url.params["page"])
        items = [{"senderType": "CUSTOMER", "content": f"tin {trang}",
                  "sentAt": "2026-10-09T08:00:00Z", "isRedacted": trang == 1}]
        return httpx.Response(200, json=_vo({"items": items, "page": trang, "size": 200,
                                             "totalItems": 2, "totalPages": 2}))

    trace_id_var.set("trace-uc026")
    c = _client(xu_ly)
    try:
        tin = await c.lay_tin_nhan(TENANT, conv)
    finally:
        await c.aclose()

    assert [t.noi_dung for t in tin] == ["tin 0", "tin 1"] and tin[1].da_che
    assert da_goi[0].url.path == f"/internal/conversations/{conv}/messages"
    assert da_goi[0].headers["X-Tenant-Id"] == TENANT
    assert da_goi[0].headers["X-Trace-Id"] == "trace-uc026"


async def test_hoi_thoai_khong_co_tra_rong():
    c = _client(lambda req: httpx.Response(404, json={"success": False}))
    try:
        assert await c.lay_tin_nhan(TENANT, uuid4()) == []
    finally:
        await c.aclose()


async def test_ghi_tom_tat_dung_than_patch():
    than: list[dict] = []

    def xu_ly(req: httpx.Request) -> httpx.Response:
        assert req.method == "PATCH" and req.url.path.endswith("/summary")
        than.append(json.loads(req.content))
        return httpx.Response(200, json=_vo({}))

    ban_ghi = BanGhiTomTat("CLOSING", "a", "b", "c", "d", "gemini-3.5-flash-lite@tt1",
                           "phẳng", datetime(2026, 10, 9, tzinfo=UTC))
    c = _client(xu_ly)
    try:
        await c.ghi_tom_tat(TENANT, uuid4(), ban_ghi)
    finally:
        await c.aclose()
    assert set(than[0]) == {"trigger", "mainNeed", "providedInfo", "unresolvedIssues",
                            "nextSteps", "modelVersion", "summaryText", "generatedAt"}
    assert than[0]["trigger"] == "CLOSING"


async def test_xoa_dac_trung_lead():
    contact = uuid4()

    def xu_ly(req: httpx.Request) -> httpx.Response:
        assert req.method == "DELETE"
        assert req.url.path == f"/internal/contacts/{contact}/lead-scores"
        return httpx.Response(200, json=_vo({"deleted": 3}))

    c = _client(xu_ly)
    try:
        assert await c.xoa_dac_trung_lead(TENANT, contact) == 3
    finally:
        await c.aclose()


@pytest.mark.parametrize("phan_hoi", [
    httpx.Response(500, text="Khách Nguyễn Văn A 0912345678"),
    httpx.Response(401),
    httpx.Response(200, text="khong-phai-json"),
    httpx.Response(200, json={"data": None}),
])
async def test_loi_thanh_java_core_unavailable_khong_lo_than(phan_hoi):
    c = _client(lambda req: phan_hoi)
    try:
        with pytest.raises(JavaCoreUnavailableError) as loi:
            await c.xoa_dac_trung_lead(TENANT, uuid4())
    finally:
        await c.aclose()
    assert "0912345678" not in str(loi.value)


async def test_mat_ket_noi_thanh_java_core_unavailable():
    def xu_ly(req):
        raise httpx.ConnectError("từ chối kết nối")

    c = _client(xu_ly)
    try:
        with pytest.raises(JavaCoreUnavailableError):
            await c.lay_tin_nhan(TENANT, uuid4())
    finally:
        await c.aclose()


async def test_ban_gia_cach_ly_theo_tenant_va_xoa_luy_dang():
    gia = MockJavaCoreClient()
    contact = uuid4()
    gia.diem_lead[(TENANT, contact)] = 2
    assert await gia.xoa_dac_trung_lead("22222222-2222-2222-2222-222222222222", contact) == 0
    assert await gia.xoa_dac_trung_lead(TENANT, contact) == 2
    assert await gia.xoa_dac_trung_lead(TENANT, contact) == 0
