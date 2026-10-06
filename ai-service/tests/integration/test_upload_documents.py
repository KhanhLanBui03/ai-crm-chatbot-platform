"""UC018 — ``POST /v1/ai/kb/documents`` đầu-cuối trên Postgres (RLS) và RustFS (S3) thật.

Cổng ra Ngày 3: 25/25 tệp của ``data/kb_samples/manifest.csv`` ra đúng mã HTTP. Thêm các ca
không gắn với tệp: tiêu đề, tenant trong body, URI ngoài vùng tenant, object không tồn tại,
kho S3 chết, và hai lượt tải cùng tiêu đề chạy đồng thời.

Mỗi test dùng tiêu đề và key riêng (hậu tố ngẫu nhiên) vì CSDL và bucket dùng chung cả lượt
chạy — version của test này không được lẫn vào test kia.

Ca 409 (chạm hạn mức gói) không có ở đây: java-core kiểm hạn mức trước khi gọi ai-service.
"""

import asyncio
import csv
import io
import unicodedata
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from minio import Minio
from sqlalchemy import text

from src.ai import service
from src.ai.config import Settings
from src.ai.db import session as db_session
from src.ai.integrations import object_storage
from src.api import deps
from src.api.main import create_app
from tests.conftest import S3_ACCESS_KEY, S3_BUCKET, S3_SECRET_KEY

ENDPOINT = "/v1/ai/kb/documents"
MAU = Path(__file__).resolve().parents[3] / "data" / "kb_samples"
GIOI_HAN = 20 * 1024 * 1024


# ── Fixture và tiện ích ──────────────────────────────────────────────────────


@pytest.fixture
async def ha_tang(pg_dsn_ai_app, kho_s3_endpoint, monkeypatch):
    """Nối app vào Postgres và RustFS của test. Trả về (factory phiên CSDL, cấu hình)."""
    engine = db_session.tao_engine(pg_dsn_ai_app.replace("postgresql://", "postgresql+psycopg://"))
    factory = db_session.tao_session_factory(engine)
    cau_hinh = Settings(
        s3_endpoint=kho_s3_endpoint,
        s3_bucket=S3_BUCKET,
        s3_access_key=S3_ACCESS_KEY,
        s3_secret_key=S3_SECRET_KEY,
        kb_max_file_bytes=GIOI_HAN,
    )
    monkeypatch.setattr(service, "get_settings", lambda: cau_hinh)
    # Client dựng bằng CHÍNH hàm production (timeout, số lần thử lại), chỉ khác cấu hình.
    client_s3 = object_storage.tao_client(cau_hinh)
    monkeypatch.setattr(object_storage, "_client_mac_dinh", lambda: client_s3)
    yield factory, cau_hinh
    await engine.dispose()


@pytest.fixture
async def client(ha_tang) -> AsyncIterator[httpx.AsyncClient]:
    """Client HTTP gọi thẳng vào app qua ASGI — không dựng máy chủ, không cần cổng mạng."""
    factory, _ = ha_tang

    async def _phien_test(tenant_id: deps.TenantIdDep):
        async with db_session.get_tenant_session(tenant_id, factory=factory) as phien:
            yield phien

    app = create_app()
    app.dependency_overrides[deps.get_session] = _phien_test
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


def _dua_len(kho: Minio, tenant: UUID, ten_tep: str, du_lieu: bytes) -> str:
    """Ghi tệp lên S3 như java-core sẽ làm: key {tenant}/{uuid mỗi lần tải}/{tên tệp}."""
    key = f"{tenant}/{uuid4()}/{ten_tep}"
    kho.put_object(S3_BUCKET, key, io.BytesIO(du_lieu), len(du_lieu))
    return f"s3://{S3_BUCKET}/{key}"


def _than(uri: str, ten_tep: str, title: str, **them) -> dict:
    return {"file_uri": uri, "file_name": ten_tep, "title": title, **them}


def _hau_to() -> str:
    return uuid4().hex[:8]


async def _cac_dong(factory, tenant: UUID, title: str) -> list[tuple]:
    async with db_session.get_tenant_session(str(tenant), factory=factory) as phien:
        ket_qua = await phien.execute(
            text(
                "SELECT version, status, source_type, file_path FROM knowledge.knowledge_documents"
                " WHERE title = :t ORDER BY version"
            ),
            {"t": title},
        )
        return [tuple(r) for r in ket_qua]


# ── Cổng ra Ngày 3: 25/25 tệp mẫu ────────────────────────────────────────────


async def test_manifest_25_tep_dung_ma_http(client, ha_tang, kho_s3, tenant_a):
    factory, _ = ha_tang
    hau_to = _hau_to()
    dong = list(csv.DictReader(open(MAU / "manifest.csv", encoding="utf-8")))
    assert len(dong) == 25

    ket_qua = []
    for r in dong:
        if r["file"] == "tep-qua-lon.pdf":  # không commit tệp 20 MiB — sinh tại chỗ
            du_lieu = b"%PDF-1.7\n" + b"0" * GIOI_HAN
        else:
            du_lieu = (MAU / r["file"]).read_bytes()
        uri = _dua_len(kho_s3, tenant_a, r["file"], du_lieu)
        title = f"{r['title']} [{hau_to}]"
        resp = await client.post(
            ENDPOINT,
            json=_than(uri, r["file"], title, language=r["language"]),
            headers={"X-Tenant-Id": str(tenant_a)},
        )
        ket_qua.append((r["file"], r["ma_http"], resp.status_code, resp.json()))

    sai = [(f, mong, thuc, body) for f, mong, thuc, body in ket_qua if str(thuc) != mong]
    assert not sai, f"{len(sai)} tệp sai mã: {sai}"

    # Mã lỗi nghiệp vụ khớp đúng cột ma_loi của manifest
    for (f, _, _, body), r in zip(ket_qua, dong, strict=True):
        if r["ma_loi"]:
            assert body["code"] == r["ma_loi"], f

    # Hai bản "Chính sách đổi trả" thành version 1 và 2, bản cũ còn nguyên
    dong_doi_tra = await _cac_dong(factory, tenant_a, f"Chính sách đổi trả [{hau_to}]")
    assert [(v, s, t) for v, s, t, _ in dong_doi_tra] == [
        (1, "PENDING", "DOCX"),
        (2, "PENDING", "MD"),
    ]
    assert dong_doi_tra[0][3] != dong_doi_tra[1][3]


# ── Version ──────────────────────────────────────────────────────────────────


async def test_trung_tieu_de_tang_version(client, kho_s3, tenant_a):
    title = f"Bảng giá {_hau_to()}"
    versions = []
    for _ in range(3):
        uri = _dua_len(kho_s3, tenant_a, "bang-gia.txt", "Giá 2026".encode())
        resp = await client.post(
            ENDPOINT, json=_than(uri, "bang-gia.txt", title), headers={"X-Tenant-Id": str(tenant_a)}
        )
        assert resp.status_code == 202
        versions.append(resp.json()["version"])
    assert versions == [1, 2, 3]


async def test_nhieu_luot_dong_thoi_cung_tieu_de(client, kho_s3, tenant_a):
    """Bẫy chính của tinh_version_ke_tiep. Không có khoá advisory, các lượt cùng đọc một MAX
    và lượt sau đụng uq_doc_title_version thành 500. Có khoá: đủ 202, version liền nhau."""
    title = f"Chính sách trả góp {_hau_to()}"
    so_luot = 6
    uris = [_dua_len(kho_s3, tenant_a, "tra-gop.txt", b"Tra gop 0%") for _ in range(so_luot)]
    ha = {"X-Tenant-Id": str(tenant_a)}
    resps = await asyncio.gather(
        *(client.post(ENDPOINT, json=_than(u, "tra-gop.txt", title), headers=ha) for u in uris)
    )
    assert [r.status_code for r in resps] == [202] * so_luot, [r.json() for r in resps]
    assert sorted(r.json()["version"] for r in resps) == list(range(1, so_luot + 1))


async def test_version_tach_rieng_theo_tenant(client, kho_s3, tenant_a, tenant_b):
    """Cùng tiêu đề ở hai tenant là hai chuỗi version độc lập — đều bắt đầu từ 1."""
    title = f"Giờ mở cửa {_hau_to()}"
    for tenant in (tenant_a, tenant_b):
        uri = _dua_len(kho_s3, tenant, "gio.txt", b"8:00 - 21:30")
        resp = await client.post(
            ENDPOINT, json=_than(uri, "gio.txt", title), headers={"X-Tenant-Id": str(tenant)}
        )
        assert (resp.status_code, resp.json()["version"]) == (202, 1)


# ── Tenant: header và vùng lưu trữ ───────────────────────────────────────────


async def test_thieu_header_tenant_401(client, kho_s3, tenant_a):
    uri = _dua_len(kho_s3, tenant_a, "a.txt", b"x")
    resp = await client.post(ENDPOINT, json=_than(uri, "a.txt", "Không có tenant"))
    assert (resp.status_code, resp.json()["code"]) == (401, "TENANT_CONTEXT_MISSING")


async def test_gui_tenant_id_trong_body_422(client, kho_s3, tenant_a, tenant_b):
    uri = _dua_len(kho_s3, tenant_a, "a.txt", b"x")
    resp = await client.post(
        ENDPOINT,
        json=_than(uri, "a.txt", "Leo tenant", tenant_id=str(tenant_b)),
        headers={"X-Tenant-Id": str(tenant_a)},
    )
    assert (resp.status_code, resp.json()["code"]) == (422, "INVALID_METADATA")
    assert resp.json()["errors"][0]["loc"] == ["body", "tenant_id"]


@pytest.mark.parametrize(
    "bien_dang",
    ["tenant_khac", "tien_to_evil", "cham_cham", "gach_kep", "http", "bucket_khac"],
)
async def test_uri_ngoai_vung_tenant_403_du_object_co_that(
    client, ha_tang, kho_s3, tenant_a, tenant_b, bien_dang
):
    """Object của tenant B CÓ THẬT trên S3 — nên chỉ chốt chặn tenant mới cứu được, không phải
    vì "không tìm thấy tệp". Không dòng nào được ghi vào CSDL của tenant A."""
    factory, _ = ha_tang
    bi_mat = _dua_len(kho_s3, tenant_b, "bi-mat.txt", "Bảng lương".encode())
    key_b = bi_mat.removeprefix(f"s3://{S3_BUCKET}/")
    uri = {
        "tenant_khac": bi_mat,
        "tien_to_evil": f"s3://{S3_BUCKET}/{tenant_a}-evil/{key_b}",
        "cham_cham": f"s3://{S3_BUCKET}/{tenant_a}/../{key_b}",
        "gach_kep": f"s3://{S3_BUCKET}//{tenant_a}/x.txt",
        "http": f"http://{S3_BUCKET}/{tenant_a}/x.txt",
        "bucket_khac": f"s3://bucket-khac/{tenant_a}/x.txt",
    }[bien_dang]
    title = f"Đánh cắp {_hau_to()}"
    resp = await client.post(
        ENDPOINT, json=_than(uri, "bi-mat.txt", title), headers={"X-Tenant-Id": str(tenant_a)}
    )
    assert (resp.status_code, resp.json()["code"]) == (403, "FORBIDDEN_FILE_URI")
    assert await _cac_dong(factory, tenant_a, title) == []


# ── Siêu dữ liệu ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("title", "ma"),
    [("", 422), ("ab", 422), ("a" * 256, 422), ("   ", 422), ("abc", 202)],
)
async def test_bien_tieu_de(client, kho_s3, tenant_a, title, ma):
    uri = _dua_len(kho_s3, tenant_a, "a.txt", b"x")
    tieu_de = title if ma == 422 else f"{title} {_hau_to()}"
    resp = await client.post(
        ENDPOINT, json=_than(uri, "a.txt", tieu_de), headers={"X-Tenant-Id": str(tenant_a)}
    )
    assert resp.status_code == ma
    if ma == 422:
        assert resp.json()["code"] == "INVALID_METADATA"


async def test_tieu_de_dung_255_ky_tu_duoc_nhan(client, kho_s3, tenant_a):
    uri = _dua_len(kho_s3, tenant_a, "a.txt", b"x")
    title = (_hau_to() + "a" * 255)[:255]
    resp = await client.post(
        ENDPOINT, json=_than(uri, "a.txt", title), headers={"X-Tenant-Id": str(tenant_a)}
    )
    assert resp.status_code == 202


async def test_tieu_de_nfd_luu_thanh_nfc(client, ha_tang, kho_s3, tenant_a):
    """120 chữ 'ệ' dạng NFD = 360 code point, vượt 255 — nhưng sau NFC chỉ 120, phải nhận."""
    factory, _ = ha_tang
    goc = "ệ" * 120 + _hau_to()
    uri = _dua_len(kho_s3, tenant_a, "a.txt", b"x")
    resp = await client.post(
        ENDPOINT,
        json=_than(uri, "a.txt", unicodedata.normalize("NFD", goc)),
        headers={"X-Tenant-Id": str(tenant_a)},
    )
    assert resp.status_code == 202
    assert len(await _cac_dong(factory, tenant_a, goc)) == 1  # tìm được bằng dạng NFC


async def test_ngon_ngu_ngoai_vi_en_422(client, kho_s3, tenant_a):
    uri = _dua_len(kho_s3, tenant_a, "a.txt", b"x")
    resp = await client.post(
        ENDPOINT,
        json=_than(uri, "a.txt", "Tài liệu tiếng Pháp", language="fr"),
        headers={"X-Tenant-Id": str(tenant_a)},
    )
    assert (resp.status_code, resp.json()["code"]) == (422, "INVALID_METADATA")


# ── Kho S3 ───────────────────────────────────────────────────────────────────


async def test_object_khong_ton_tai_422(client, tenant_a):
    uri = f"s3://{S3_BUCKET}/{tenant_a}/{uuid4()}/khong-co.pdf"
    resp = await client.post(
        ENDPOINT, json=_than(uri, "khong-co.pdf", "Tệp ma"), headers={"X-Tenant-Id": str(tenant_a)}
    )
    assert (resp.status_code, resp.json()["code"]) == (422, "FILE_NOT_FOUND")


async def test_kho_s3_khong_ket_noi_duoc_503(client, ha_tang, monkeypatch, tenant_a):
    """Kho S3 chết là lỗi hạ tầng: 503 để java-core thử lại, không phải 422 bắt sửa tệp."""
    _, cau_hinh = ha_tang
    chet = object_storage.tao_client(cau_hinh.model_copy(update={"s3_endpoint": "127.0.0.1:1"}))
    monkeypatch.setattr(object_storage, "_client_mac_dinh", lambda: chet)
    uri = f"s3://{S3_BUCKET}/{tenant_a}/{uuid4()}/a.pdf"
    resp = await client.post(
        ENDPOINT, json=_than(uri, "a.pdf", "Kho chết"), headers={"X-Tenant-Id": str(tenant_a)}
    )
    assert (resp.status_code, resp.json()["code"]) == (503, "STORAGE_UNAVAILABLE")
