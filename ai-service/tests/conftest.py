"""Fixture dùng chung cho test tích hợp của ai-service.

Dựng một Postgres THẬT bằng testcontainers, chạy đúng dải migration V2xx của Track B,
gieo hai tenant cố định, rồi mở kết nối bằng role ``ai_app`` — role CHỊU RLS.

Ba quyết định đằng sau file này:

1. **testcontainers ở CẢ local lẫn CI**, không rẽ nhánh theo môi trường. Một đường chạy duy
   nhất thì không bao giờ có chuyện "local xanh, CI đỏ", và job CI gần như không phải viết
   thêm gì. Đánh đổi: mỗi lượt chạy chậm thêm ~40-60s.

2. **Không dùng ``scripts/migrate-ai.sh``.** Script đó bắn Flyway CLI vào mạng Docker do
   Compose sinh, không trỏ được vào container dùng một lần của testcontainers. Ở đây chạy
   thẳng từng file ``.sql`` theo thứ tự — cùng nội dung, khác cách nạp.

3. **Image bắt buộc là ``pgvector/pgvector``**, không phải ``postgres`` thuần:
   ``scripts/init-db.sql`` mở đầu bằng ``CREATE EXTENSION vector`` và ``V203`` khai cột
   ``vector(1024)``. Dùng image thuần thì gãy ngay ở file migration đầu tiên.

Driver là **psycopg3** (``base.txt`` đã có ``psycopg[binary,pool]``), nên DSN dựng tay chứ
không lấy ``get_connection_url()`` — hàm đó mặc định sinh chuỗi ``postgresql+psycopg2://``
và sẽ kéo theo một driver dự án không dùng.

Kho tệp S3 cũng thật: fixture ``kho_s3`` dựng RustFS bằng CÙNG image với
``docker-compose.yml`` (ADR-0022). Không dùng module MinIO của testcontainers — nó kéo image
``minio/minio``, mà image đó đã bị gỡ khỏi Docker Hub.
"""

import re
import time
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import psycopg
import pytest
import urllib3
from minio import Minio
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer

# ── Đường dẫn ────────────────────────────────────────────────────────────────
AI_SERVICE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_SERVICE_DIR.parent
INIT_DB_SQL = REPO_ROOT / "scripts" / "init-db.sql"
MIGRATION_DIR = AI_SERVICE_DIR / "migration"

# ── Tài khoản ────────────────────────────────────────────────────────────────
# Trùng với scripts/init-db.sql và docker-compose.yml. `crm_owner` là POSTGRES_USER của
# container nên nó là superuser — ĐÚNG như CSDL thật (đã đo: rolsuper = t, rolbypassrls = t).
# Giữ nguyên chênh lệch quyền đó là có chủ đích: test phải chạy trên cùng cấu hình quyền
# với production, không phải trên một bản dễ hơn.
OWNER_USER = "crm_owner"
OWNER_PASSWORD = "changeme"  # chỉ sống trong container dùng một lần
AI_USER = "ai_app"
AI_PASSWORD = "changeme"  # init-db.sql:26-27 hardcode đúng chuỗi này
DB_NAME = "thesis_crm"

# ── Kho tệp S3 ───────────────────────────────────────────────────────────────
RUSTFS_IMAGE = "rustfs/rustfs:1.0.0"  # trùng docker-compose.yml
S3_ACCESS_KEY = "kb-test"
S3_SECRET_KEY = "kb-test-secret"  # chỉ sống trong container dùng một lần
S3_BUCKET = "kb-tai-lieu"

# ── Dữ liệu gieo sẵn ─────────────────────────────────────────────────────────
# UUID cố định chứ không sinh ngẫu nhiên: test cách ly tenant cần trỏ đích danh "dòng của
# tenant kia", mà dòng đó theo định nghĩa là dòng phiên hiện tại KHÔNG đọc được — không tra
# ngược id ra được từ trong phiên đó.
TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")

DOC_A = UUID("aaaaaaaa-0000-0000-0000-000000000001")
DOC_B = UUID("bbbbbbbb-0000-0000-0000-000000000001")
CHUNK_A = UUID("aaaaaaaa-0000-0000-0000-000000000002")
CHUNK_B = UUID("bbbbbbbb-0000-0000-0000-000000000002")

_SEED = (
    (TENANT_A, DOC_A, CHUNK_A, "So tay noi bo cua tenant A", "Noi dung chi tenant A duoc doc."),
    (TENANT_B, DOC_B, CHUNK_B, "So tay noi bo cua tenant B", "Noi dung chi tenant B duoc doc."),
)

_SQL_CHEN_TAI_LIEU = """
    INSERT INTO knowledge.knowledge_documents
        (id, tenant_id, title, source_type, file_path, status)
    VALUES (%s, %s, %s, 'TXT', %s, 'READY')
"""

_SQL_CHEN_DOAN = """
    INSERT INTO knowledge.knowledge_chunks
        (id, tenant_id, document_id, chunk_index, content,
         embedding_model, embedding_version)
    VALUES (%s, %s, %s, 0, %s, 'seed-khong-phai-model-that', 'v0')
"""


def _dsn(host: str, port: int, user: str, password: str) -> str:
    return f"postgresql://{user}:{password}@{host}:{port}/{DB_NAME}"


def _cho_postgres_san_sang(dsn: str, so_lan: int = 30) -> None:
    """Chờ Postgres nhận kết nối thật, không tin mỗi log khởi động.

    Container in "ready to accept connections" một lần trong lúc initdb rồi khởi động lại —
    bắt log đó là bắt phải lần khởi động tạm. Thử kết nối thật thì không nhầm được.
    """
    loi: Exception | None = None
    for _ in range(so_lan):
        try:
            with psycopg.connect(dsn, connect_timeout=2):
                return
        except psycopg.OperationalError as e:
            loi = e
            time.sleep(1)
    raise RuntimeError(f"Postgres không sẵn sàng sau {so_lan}s: {loi}")


_TEN_MIGRATION = re.compile(r"V(2\d\d)__[^/]+\.sql")


def _cac_file_migration() -> list[Path]:
    """Các file V2xx theo thứ tự số, sau khi kiểm dãy LIỀN NHAU từ V201.

    Không đếm cứng số file: đếm cứng thì mỗi migration mới làm đỏ toàn bộ test tích hợp vì
    một con số trong fixture, không vì lược đồ sai. Thứ thật sự cần giữ là không thiếu số
    và không trùng số: thiếu một số thì lược đồ test âm thầm khác production, còn hai người
    cùng tạo V210 là lỗi merge hay gặp nhất của dải migration.

    Sắp theo SỐ chứ không theo tên: theo tên thì ``V210__…`` vẫn đúng chỗ, nhưng chỉ vì mọi
    số đều có ba chữ số, một giả định không nên dựa vào.
    """
    theo_so: dict[int, list[Path]] = {}
    for f in MIGRATION_DIR.glob("V2*.sql"):
        khop = _TEN_MIGRATION.fullmatch(f.name)
        if not khop:
            raise RuntimeError(f"Tên migration sai dạng V2xx__mo_ta.sql: {f.name}")
        theo_so.setdefault(int(khop.group(1)), []).append(f)

    trung = {so: [f.name for f in ds] for so, ds in theo_so.items() if len(ds) > 1}
    if trung:
        raise RuntimeError(f"Trùng số migration: {trung}")

    cac_so = sorted(theo_so)
    mong_doi = list(range(201, 201 + len(cac_so)))
    if cac_so != mong_doi:
        thieu = sorted(set(range(201, max(cac_so, default=200) + 1)) - set(cac_so))
        raise RuntimeError(f"Dãy migration phải liền nhau từ V201, thiếu: {thieu}")

    return [theo_so[so][0] for so in cac_so]


def _nap_luoc_do(dsn: str) -> None:
    """Chạy init-db.sql rồi dải V2xx theo đúng thứ tự Flyway sẽ chạy.

    ``autocommit=True`` + truy vấn KHÔNG tham số ⇒ psycopg3 gửi bằng giao thức truy vấn đơn,
    cho phép nhiều câu lệnh trong một chuỗi. Đây là điều kiện để các khối ``DO $$ ... $$``
    của V207 chạy được nguyên vẹn — tách chuỗi theo dấu ``;`` sẽ cắt đứt thân khối.

    HỆ QUẢ PHẢI BIẾT: CSDL test **không có** bảng ``knowledge.flyway_schema_history_ai``, vì
    Flyway không hề chạy ở đây. Lược đồ giống hệt production, chỉ thiếu sổ ghi chép của
    Flyway. Muốn biết migration nào đã chạy thì soi lược đồ (ví dụ cột ``description`` chỉ
    xuất hiện từ V209), đừng đếm dòng trong bảng lịch sử.
    """
    files = _cac_file_migration()

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(INIT_DB_SQL.read_text(encoding="utf-8"))
        for f in files:
            conn.execute(f.read_text(encoding="utf-8"))


def _gieo_du_lieu(dsn: str) -> None:
    """Gieo mỗi tenant một tài liệu và một đoạn.

    Mỗi lô bọc trong transaction riêng và đặt ``app.tenant_id`` trước khi chèn. Ở đây
    ``crm_owner`` có ``rolbypassrls = t`` nên RLS không chặn nó — nhưng giữ đúng hình dạng
    của ràng buộc production là có chủ đích: đổi role gieo sang một role chịu RLS thì hàm này
    vẫn chạy đúng, không phải viết lại.

    ``SET LOCAL`` không nhận placeholder, nên truyền tenant qua ``set_config(..., true)``;
    tham số thứ ba ``true`` chính là phần "LOCAL" — hết transaction là biến mất.
    """
    with psycopg.connect(dsn) as conn:
        for tenant, doc_id, chunk_id, title, content in _SEED:
            with conn.transaction():
                conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant),))
                conn.execute(_SQL_CHEN_TAI_LIEU, (doc_id, tenant, title, f"/seed/{tenant}.txt"))
                conn.execute(_SQL_CHEN_DOAN, (chunk_id, tenant, doc_id, content))


@pytest.fixture(scope="session")
def pg_dsn_ai_app() -> Iterator[str]:
    """DSN kết nối bằng ``ai_app`` tới một Postgres đã nạp đủ dải V2xx và gieo 2 tenant."""
    with PostgresContainer(
        "pgvector/pgvector:pg16",
        username=OWNER_USER,
        password=OWNER_PASSWORD,
        dbname=DB_NAME,
        driver=None,  # không để testcontainers dựng URL SQLAlchemy/psycopg2
    ) as container:
        host = container.get_container_host_ip()
        port = int(container.get_exposed_port(5432))

        dsn_owner = _dsn(host, port, OWNER_USER, OWNER_PASSWORD)
        _cho_postgres_san_sang(dsn_owner)
        _nap_luoc_do(dsn_owner)
        _gieo_du_lieu(dsn_owner)

        yield _dsn(host, port, AI_USER, AI_PASSWORD)


@pytest.fixture
async def ai_conn(pg_dsn_ai_app: str):
    """Kết nối bất đồng bộ bằng role ``ai_app`` — role CHỊU RLS.

    🔴 Đây là dòng dễ sai nhất cả file: nối bằng ``crm_owner`` thì mọi test cách ly tenant
    đều XANH GIẢ, vì ``crm_owner`` có ``rolbypassrls = t`` nên không bao giờ chạm tới policy.

    ``autocommit=True`` là cố ý, không phải cho nhanh: chỉ khi đó ``async with
    conn.transaction()`` mới phát ra BEGIN/COMMIT thật, và ``SET LOCAL`` mới có một
    transaction để sống trong đó. Để mặc định ``autocommit=False`` thì psycopg3 tự mở
    transaction ngầm từ câu lệnh đầu tiên, và ``conn.transaction()`` chỉ tạo SAVEPOINT lồng
    bên trong — phạm vi của ``SET LOCAL`` khi đó không còn như mình tưởng.
    """
    conn = await psycopg.AsyncConnection.connect(pg_dsn_ai_app, autocommit=True)
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def tenant_a() -> UUID:
    return TENANT_A


@pytest.fixture(scope="session")
def tenant_b() -> UUID:
    return TENANT_B


def _cho_s3_san_sang(endpoint: str, so_lan: int = 30) -> None:
    """Chờ RustFS trả 200 ở ``/health`` — cổng mở chưa chắc máy chủ đã nhận request."""
    http = urllib3.PoolManager(timeout=2, retries=False)
    loi: Exception | None = None
    for _ in range(so_lan):
        try:
            if http.request("GET", f"http://{endpoint}/health").status == 200:
                return
        except urllib3.exceptions.HTTPError as e:
            loi = e
        time.sleep(1)
    raise RuntimeError(f"RustFS không sẵn sàng sau {so_lan}s: {loi}")


@pytest.fixture(scope="session")
def kho_s3_endpoint() -> Iterator[str]:
    """``host:cổng`` của một RustFS thật đang chạy, bucket ``S3_BUCKET`` đã tạo sẵn.

    Session-scope: một container cho cả lượt chạy. Test nào ghi object thì dùng key có tiền
    tố riêng (ví dụ theo tên test) để không giẫm lên nhau.
    """
    container = (
        DockerContainer(RUSTFS_IMAGE)
        .with_env("RUSTFS_ACCESS_KEY", S3_ACCESS_KEY)
        .with_env("RUSTFS_SECRET_KEY", S3_SECRET_KEY)
        .with_exposed_ports(9000)
    )
    with container:
        endpoint = f"{container.get_container_host_ip()}:{container.get_exposed_port(9000)}"
        _cho_s3_san_sang(endpoint)
        Minio(
            endpoint, access_key=S3_ACCESS_KEY, secret_key=S3_SECRET_KEY, secure=False
        ).make_bucket(S3_BUCKET)
        yield endpoint


@pytest.fixture(scope="session")
def kho_s3(kho_s3_endpoint: str) -> Minio:
    """Client S3 có quyền đầy đủ trên RustFS của ``kho_s3_endpoint``."""
    return Minio(
        kho_s3_endpoint, access_key=S3_ACCESS_KEY, secret_key=S3_SECRET_KEY, secure=False
    )
