"""Chốt chặn tenant ở tầng kho lưu trữ — ``src/ai/rag/ingest/luu_tru.py``.

Hàm thuần, không chạm mạng. Mỗi ca bị chặn ứng với một cách thật để đọc tệp của tenant khác
hoặc làm lệch key mà kho S3 sẽ đọc.
"""

import pytest

from src.ai.exceptions import ForbiddenFileUriError
from src.ai.rag.ingest.luu_tru import kiem_uri_thuoc_tenant

BUCKET = "kb-tai-lieu"
TENANT = "11111111-1111-1111-1111-111111111111"
KHAC = "22222222-2222-2222-2222-222222222222"


def test_hop_le_tra_ve_key():
    uri = f"s3://{BUCKET}/{TENANT}/7f3a/bang-gia.pdf"
    assert kiem_uri_thuoc_tenant(uri, TENANT, BUCKET) == f"{TENANT}/7f3a/bang-gia.pdf"


def test_ten_tep_tieng_viet_va_ky_tu_la_nhung_hop_le_giu_nguyen():
    """Không qua urlparse nên # và ? là ký tự bình thường của key, không bị cắt."""
    key = f"{TENANT}/7f3a/Bảng giá #2026 (bản mới?).pdf"
    assert kiem_uri_thuoc_tenant(f"s3://{BUCKET}/{key}", TENANT, BUCKET) == key


def test_tenant_trong_header_viet_hoa_van_khop():
    """Header có thể mang UUID viết hoa; key luôn ở dạng chuẩn chữ thường."""
    uri = f"s3://{BUCKET}/{TENANT}/a.pdf"
    assert kiem_uri_thuoc_tenant(uri, TENANT.upper(), BUCKET) == f"{TENANT}/a.pdf"


@pytest.mark.parametrize(
    "uri",
    [
        # 1. scheme không phải s3
        f"http://{BUCKET}/{TENANT}/a.pdf",
        f"file:///data/kb/{TENANT}/a.pdf",
        f"/data/kb/{TENANT}/a.pdf",
        f"S3://{BUCKET}/{TENANT}/a.pdf",
        # 2. bucket khác, hoặc không có key
        f"s3://bucket-khac/{TENANT}/a.pdf",
        f"s3://{BUCKET}-backup/{TENANT}/a.pdf",
        f"s3://{BUCKET}",
        # 3. thư mục của tenant khác
        f"s3://{BUCKET}/{KHAC}/a.pdf",
        # 4. chỉ trùng TIỀN TỐ chuỗi với tenant
        f"s3://{BUCKET}/{TENANT}-evil/a.pdf",
        f"s3://{BUCKET}/{TENANT}evil/a.pdf",
        # 5. key bất thường
        f"s3://{BUCKET}/{TENANT}/../{KHAC}/a.pdf",
        f"s3://{BUCKET}/{TENANT}/./a.pdf",
        f"s3://{BUCKET}//{TENANT}/a.pdf",
        f"s3://{BUCKET}/{TENANT}//a.pdf",
        f"s3://{BUCKET}/{TENANT}/",
        f"s3://{BUCKET}/{TENANT}",
        f"s3://{BUCKET}/{TENANT}/..\\{KHAC}\\a.pdf",
        f"s3://{BUCKET}/{TENANT}/a\x00.pdf",
        f"s3://{BUCKET}/{TENANT}/a\n.pdf",
        f"s3://{BUCKET}/{TENANT}/gnp‮.exe",
        f"s3://{BUCKET}/{TENANT}/a​.pdf",
    ],
)
def test_uri_ngoai_vung_bi_chan(uri):
    with pytest.raises(ForbiddenFileUriError):
        kiem_uri_thuoc_tenant(uri, TENANT, BUCKET)


def test_tenant_khong_phai_uuid_bi_chan():
    """Tenant rác không được đi tiếp tới chỗ so phân đoạn — so với rác thì kết quả vô nghĩa."""
    with pytest.raises(ForbiddenFileUriError):
        kiem_uri_thuoc_tenant("s3://kb-tai-lieu/tenant-a/a.pdf", "tenant-a", BUCKET)


def test_thong_diep_loi_khong_chua_ten_tep():
    """Tên tệp có thể chứa tên người — thông điệp đi vào log, không được mang theo (NĐ 13)."""
    with pytest.raises(ForbiddenFileUriError) as e:
        kiem_uri_thuoc_tenant(f"s3://{BUCKET}/{KHAC}/hop-dong-nguyen-van-a.pdf", TENANT, BUCKET)
    assert "nguyen-van-a" not in str(e.value)
