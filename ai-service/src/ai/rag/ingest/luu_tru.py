"""Cô lập tenant ở TẦNG KHO LƯU TRỮ — UC018. [PRODUCTION]

java-core ghi tệp vào bucket S3 dưới key ``{tenant_id}/…`` rồi gửi URI sang đây (ADR-0019).
RLS chỉ bảo vệ các dòng trong CSDL — nó không biết gì về kho S3. Nếu ai-service tải bất cứ
object nào được gửi tới, thì một URI trỏ sang key của tenant khác sẽ được đọc, cắt đoạn, nhúng
vector rồi ghi vào kho tri thức của tenant đang gọi — đúng kiểu rò rỉ chéo tenant mà chỉ số
"rò rỉ = 0" (§1.6) phải chặn.

ai-service có quyền ĐỌC toàn bucket (một bucket chung cho mọi tenant), nên kho S3 sẽ không tự
từ chối giúp. Hàm dưới đây là chốt chặn duy nhất.
"""

import unicodedata
from uuid import UUID

from src.ai.exceptions import ForbiddenFileUriError

_SCHEME = "s3://"

# Cc: ký tự điều khiển (\x00–\x1f, \x7f, \x80–\x9f). Cf: ký tự định dạng vô hình — rộng bằng
# không (U+200B), đảo chiều chữ (U+202E, dùng để giả tên tệp "gnp.exe" thành "exe.png"), BOM.
_LOAI_KY_TU_CAM = frozenset({"Cc", "Cf"})


def _phan_doan_bat_thuong(phan_doan: str) -> bool:
    if phan_doan in ("", ".", ".."):
        return True
    if "\\" in phan_doan:
        return True
    return any(unicodedata.category(c) in _LOAI_KY_TU_CAM for c in phan_doan)


def kiem_uri_thuoc_tenant(file_uri: str, tenant_id: str, bucket: str) -> str:
    """Trả về key của object nếu ``file_uri`` nằm trong vùng của ``tenant_id``, ngược lại ném.

    Dạng hợp lệ DUY NHẤT: ``s3://{bucket}/{tenant_id}/…/{ten-tep}``, trong đó ``tenant_id`` viết
    ở dạng UUID chuẩn (chữ thường, có gạch nối — đúng dạng ``UUID.toString()`` của Java).

    Ném ``ForbiddenFileUriError`` khi: scheme không phải ``s3``; bucket khác ``bucket``; phân
    đoạn đầu của key không BẰNG ĐÚNG tenant; key có phân đoạn rỗng, ``.``, ``..``, dấu ``\\``,
    ký tự điều khiển hoặc ký tự vô hình; hoặc không có tên tệp sau thư mục tenant.

    Ném chứ không trả ``False``: trả bool thì chỉ cần một chỗ gọi quên ``if`` là lọt — ném thì
    quên bắt vẫn là từ chối (fail-closed).

    Tự tách chuỗi, cố ý KHÔNG dùng ``urllib.parse``: ``urlparse`` tách mất phần sau ``?`` và
    ``#`` (``…/bao-gia#2026.pdf`` thành key ``…/bao-gia``), và ``path.lstrip('/')`` nuốt luôn
    phân đoạn rỗng ở đầu (``s3://kb//…``). Chốt chặn bảo mật phải đọc chuỗi đúng từng ký tự như
    kho S3 sẽ đọc, không qua một bộ phân tích có quy tắc riêng.

    Thông điệp lỗi không chứa nguyên URI: tên tệp có thể chứa tên người (Nghị định 13), mà
    thông điệp này đi vào log cảnh báo và phản hồi.
    """
    try:
        tenant = str(UUID(tenant_id))
    except ValueError:
        raise ForbiddenFileUriError("Tenant của phiên không phải UUID hợp lệ") from None

    if not file_uri.startswith(_SCHEME):
        raise ForbiddenFileUriError("URI phải có dạng s3://{bucket}/{tenant_id}/…")

    bucket_uri, co_gach, key = file_uri[len(_SCHEME) :].partition("/")
    if not co_gach or bucket_uri != bucket:
        raise ForbiddenFileUriError("URI trỏ ra ngoài bucket của kho tri thức")

    phan_doan = key.split("/")
    if len(phan_doan) < 2:
        raise ForbiddenFileUriError("Key thiếu thư mục tenant hoặc tên tệp")

    # So BẰNG ĐÚNG cả phân đoạn, không so tiền tố chuỗi: key.startswith(tenant) sẽ cho lọt
    # "{tenant}-evil/…" — một thư mục khác hẳn chỉ tình cờ trùng phần đầu.
    if phan_doan[0] != tenant:
        raise ForbiddenFileUriError("Key không nằm trong thư mục của tenant đang gọi")

    if any(_phan_doan_bat_thuong(p) for p in phan_doan):
        raise ForbiddenFileUriError("Key có phân đoạn bất thường")

    return key
