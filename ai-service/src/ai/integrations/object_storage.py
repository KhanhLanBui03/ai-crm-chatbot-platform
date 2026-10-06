"""Đọc tệp gốc từ kho S3 — RustFS ở dev, AWS S3 trên cloud (ADR-0022). [PRODUCTION]

ai-service chỉ ĐỌC: java-core ghi tệp, ai-service lấy dung lượng và tải về để kiểm định dạng
(UC018) hoặc để phân tích cú pháp (UC019). Không có hàm ghi hay xoá ở đây — thêm khi UC020 và
UC041 cần, và lúc đó quyền của ai-service trên bucket cũng phải mở rộng đúng bằng chừng ấy.

Mọi hàm nhận ``key`` ĐÃ được kiểm thuộc tenant (``rag/ingest/luu_tru.kiem_uri_thuoc_tenant``).
Module này không biết tenant là gì — đúng vai một adapter ra hệ thống ngoài.

Hàm đồng bộ (thư viện ``minio`` chạy trên urllib3): code async gọi qua ``asyncio.to_thread``.
"""

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

import urllib3
from minio import Minio
from minio.credentials import IamAwsProvider
from minio.error import MinioException, S3Error

from src.ai.config import Settings, get_settings
from src.ai.exceptions import StorageUnavailableError, StoredFileNotFoundError

# Mã lỗi S3 nghĩa là "không có thứ đó" — lỗi của dữ liệu phía gọi, không phải của hạ tầng.
_KHONG_CO = frozenset({"NoSuchKey", "NoSuchBucket", "NoSuchObject"})


def tao_client(settings: Settings) -> Minio:
    """Dựng client S3. Không cấu hình khoá thì lấy quyền qua IAM role (IRSA) — đường của EKS."""
    http = urllib3.PoolManager(
        # Mặc định của urllib3 không giới hạn thời gian chờ đọc, và minio thử lại nhiều lần:
        # kho S3 chết là request treo hàng phút. Ghim lại để lỗi nổi lên nhanh thành 503.
        timeout=urllib3.Timeout(connect=3, read=30),
        retries=urllib3.Retry(total=2, backoff_factor=0.2, status_forcelist=(500, 502, 503, 504)),
    )
    chung = {"secure": settings.s3_secure, "region": settings.s3_region, "http_client": http}
    if settings.s3_access_key:
        return Minio(
            settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            **chung,
        )
    return Minio(settings.s3_endpoint, credentials=IamAwsProvider(), **chung)


@lru_cache
def _client_mac_dinh() -> Minio:
    return tao_client(get_settings())


@contextmanager
def _dich_loi(bucket: str, key: str) -> Iterator[None]:
    """Dịch lỗi của thư viện S3 sang hai ngoại lệ nghiệp vụ: thiếu object hay hạ tầng hỏng."""
    try:
        yield
    except S3Error as e:
        if e.code in _KHONG_CO:
            raise StoredFileNotFoundError(f"Kho S3 không có s3://{bucket}/{key}") from e
        raise StorageUnavailableError(f"Kho S3 từ chối yêu cầu ({e.code})") from e
    except (MinioException, urllib3.exceptions.HTTPError) as e:
        raise StorageUnavailableError(f"Không kết nối được kho S3: {type(e).__name__}") from e


def lay_dung_luong(bucket: str, key: str, client: Minio | None = None) -> int:
    """Dung lượng object theo byte, lấy bằng HEAD — không tải nội dung.

    Gọi TRƯỚC khi tải để trả 413 cho tệp quá lớn mà không phải kéo nó về.
    """
    with _dich_loi(bucket, key):
        return (client or _client_mac_dinh()).stat_object(bucket, key).size


def tai_ve(bucket: str, key: str, dich: Path, gioi_han: int, client: Minio | None = None) -> None:
    """Tải object về ``dich``, đọc TỐI ĐA ``gioi_han + 1`` byte.

    Dư đúng 1 byte để hàm kiểm phía sau (``mime.nhan_dien_tep``) vẫn thấy tệp vượt giới hạn và
    trả 413 — nhưng không bao giờ kéo cả tệp vài GB về nếu object bị thay giữa lúc HEAD và GET.
    """
    c = client or _client_mac_dinh()
    with _dich_loi(bucket, key):
        try:
            resp = c.get_object(bucket, key, offset=0, length=gioi_han + 1)
        except S3Error as e:
            # Object rỗng: yêu cầu theo khoảng byte không thoả được. Tệp rỗng vẫn là tệp hợp lệ
            # ở bước này — nó sẽ bị loại ở bước kiểm định dạng hoặc ở bước trích văn bản.
            if e.code == "InvalidRange":
                dich.write_bytes(b"")
                return
            raise
        try:
            with dich.open("wb") as f:
                shutil.copyfileobj(resp, f)
        finally:
            resp.close()
            resp.release_conn()
