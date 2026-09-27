"""Bộ đọc kho S3 — ``src/ai/integrations/object_storage.py`` — trên RustFS thật.

Kiểm hai lời hứa của adapter: đọc đúng và KHÔNG đọc quá giới hạn, và dịch lỗi đúng về hai
loại mà tầng trên phân biệt được: thiếu object (422) hay hạ tầng hỏng (503).
"""

import io

import pytest
from minio import Minio

from src.ai.config import Settings
from src.ai.exceptions import StorageUnavailableError, StoredFileNotFoundError
from src.ai.integrations import object_storage
from tests.conftest import S3_ACCESS_KEY, S3_BUCKET

TIEN_TO = "test-object-storage"


def _ghi(kho: Minio, key: str, du_lieu: bytes) -> str:
    kho.put_object(S3_BUCKET, f"{TIEN_TO}/{key}", io.BytesIO(du_lieu), len(du_lieu))
    return f"{TIEN_TO}/{key}"


def test_lay_dung_luong_bang_head(kho_s3):
    key = _ghi(kho_s3, "a.pdf", b"%PDF-1.7\n" + b"x" * 91)
    assert object_storage.lay_dung_luong(S3_BUCKET, key, client=kho_s3) == 100


def test_tai_ve_nguyen_ven(kho_s3, tmp_path):
    du_lieu = "Chính sách bảo hành 24 tháng".encode()
    key = _ghi(kho_s3, "b.txt", du_lieu)
    dich = tmp_path / "tep"
    object_storage.tai_ve(S3_BUCKET, key, dich, gioi_han=1000, client=kho_s3)
    assert dich.read_bytes() == du_lieu


def test_tai_ve_khong_doc_qua_gioi_han_cong_mot(kho_s3, tmp_path):
    """Object 5 000 byte, giới hạn 1 000 → chỉ kéo về 1 001 byte, đủ để phía sau trả 413."""
    key = _ghi(kho_s3, "lon.bin", b"x" * 5000)
    dich = tmp_path / "tep"
    object_storage.tai_ve(S3_BUCKET, key, dich, gioi_han=1000, client=kho_s3)
    assert dich.stat().st_size == 1001


def test_tai_ve_object_rong(kho_s3, tmp_path):
    """Yêu cầu theo khoảng byte trên object rỗng không thoả được — vẫn phải ra tệp rỗng."""
    key = _ghi(kho_s3, "rong.txt", b"")
    dich = tmp_path / "tep"
    object_storage.tai_ve(S3_BUCKET, key, dich, gioi_han=1000, client=kho_s3)
    assert dich.read_bytes() == b""


@pytest.mark.parametrize(("bucket", "key"), [(S3_BUCKET, "khong-co.pdf"), ("bucket-khac", "a.pdf")])
def test_thieu_object_hoac_bucket_la_file_not_found(kho_s3, bucket, key):
    with pytest.raises(StoredFileNotFoundError):
        object_storage.lay_dung_luong(bucket, key, client=kho_s3)


def test_sai_khoa_la_storage_unavailable(kho_s3_endpoint):
    """Sai khoá là lỗi cấu hình hạ tầng — không được báo nhầm thành "tệp không tồn tại"."""
    sai = Minio(kho_s3_endpoint, access_key=S3_ACCESS_KEY, secret_key="sai-khoa", secure=False)
    with pytest.raises(StorageUnavailableError):
        object_storage.lay_dung_luong(S3_BUCKET, "bat-ky.pdf", client=sai)


def test_may_chu_tat_la_storage_unavailable():
    """Không ai nghe ở cổng 1 → lỗi kết nối, phải nổi lên nhanh thành 503 chứ không treo."""
    client = object_storage.tao_client(
        Settings(s3_endpoint="127.0.0.1:1", s3_access_key="a", s3_secret_key="bbbbbbbb")
    )
    with pytest.raises(StorageUnavailableError):
        object_storage.lay_dung_luong(S3_BUCKET, "a.pdf", client=client)
