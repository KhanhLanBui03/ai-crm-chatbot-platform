"""Nhận diện định dạng THẬT của tệp — UC018 bước 8. [PRODUCTION]

Đuôi tệp do người dùng đặt, nên không tin được: một tệp PNG đổi đuôi thành ``.pdf`` vẫn lọt
qua mọi kiểm tra dựa trên tên. Ở đây đọc vài byte đầu (magic bytes) để biết nội dung thật,
rồi đối chiếu với đuôi đã khai. Lệch nhau thì trả ``UNSUPPORTED_FORMAT`` (415).

Thuần thư viện chuẩn, cố ý KHÔNG dùng ``python-magic``: nó kéo theo libmagic ở tầng hệ điều
hành, trong khi image đang nợ 776/400 MB. Năm định dạng cần nhận chỉ cần ba phép thử:

    PDF      có chữ ký ``%PDF-`` trong 1 024 byte đầu
    DOCX     là tệp ZIP có ``word/document.xml`` trong danh mục
    TXT/MD/HTML   là văn bản UTF-8: không có byte NUL, giải mã UTF-8 không lỗi

Thứ tự kiểm cố ý khớp với java-core: tồn tại → dung lượng (413) → đuôi (415) → nội dung
(415). Tệp vừa quá lớn vừa sai đuôi thì hai tầng cùng trả 413, không tầng nào trả 415.

Giới hạn đã biết (ghi vào báo cáo, không phải lỗi): văn bản UTF-16 (có byte NUL) và bảng mã
cũ Windows-1258/TCVN3 bị từ chối — chỉ nhận UTF-8.
"""

import codecs
import zipfile
from dataclasses import dataclass
from pathlib import Path

from src.ai.exceptions import FileTooLargeError, StoredFileNotFoundError, UnsupportedFormatError

# Đuôi → source_type. Giá trị phải nằm trong ràng buộc CHECK source_type của V202.
DINH_DANG_THEO_DUOI: dict[str, str] = {
    ".pdf": "PDF",
    ".docx": "DOCX",
    ".txt": "TXT",
    ".md": "MD",
    ".markdown": "MD",
    ".html": "HTML",
    ".htm": "HTML",
}

MIME_THEO_DINH_DANG: dict[str, str] = {
    "PDF": "application/pdf",
    "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "TXT": "text/plain",
    "MD": "text/markdown",
    "HTML": "text/html",
}

_DINH_DANG_VAN_BAN = frozenset({"TXT", "MD", "HTML"})

# 8 KiB đủ để thấy chữ ký PDF và đủ mẫu để đoán văn bản hay nhị phân, mà không đọc cả tệp
# 20 MB vào bộ nhớ chỉ để kiểm định dạng.
_SO_BYTE_DOC = 8 * 1024
# Đặc tả PDF cho phép rác đứng trước "%PDF-" trong 1 024 byte đầu — vài trình xuất có làm vậy.
_VUNG_CHU_KY_PDF = 1024


@dataclass(frozen=True)
class KetQuaNhanDien:
    """Kết quả đã kiểm: định dạng, MIME chuẩn và dung lượng thật trên đĩa."""

    source_type: str
    mime_type: str
    size_bytes: int


def _la_pdf(dau_tep: bytes) -> bool:
    return b"%PDF-" in dau_tep[:_VUNG_CHU_KY_PDF]


def _la_docx(duong_dan: Path, dau_tep: bytes) -> bool:
    """ZIP có ``word/document.xml``. Chỉ đọc DANH MỤC của ZIP, không giải nén nội dung nào —
    nên một ZIP bom đổi đuôi ``.docx`` cũng không làm phình bộ nhớ ở bước này."""
    if not dau_tep.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(duong_dan) as z:
            return "word/document.xml" in z.namelist()
    except zipfile.BadZipFile:
        return False


def _la_van_ban_utf8(dau_tep: bytes) -> bool:
    """Không có NUL và giải mã UTF-8 được.

    Dùng bộ giải mã TĂNG DẦN với ``final=False``: 8 KiB đầu có thể cắt ngang một chữ tiếng
    Việt nhiều byte ở cuối vùng đọc. Giải mã thường sẽ báo lỗi oan cho một tệp hoàn toàn hợp
    lệ; bộ giải mã tăng dần giữ phần dở dang lại thay vì báo lỗi.
    """
    if b"\x00" in dau_tep:
        return False
    try:
        codecs.getincrementaldecoder("utf-8")().decode(dau_tep, final=False)
    except UnicodeDecodeError:
        return False
    return True


def nhan_dien_tep(duong_dan: Path, file_name: str, max_bytes: int) -> KetQuaNhanDien:
    """Kiểm tệp đã lưu và trả về định dạng thật. Hàm đồng bộ, có I/O đĩa — gọi qua
    ``asyncio.to_thread`` từ code async.

    ``duong_dan`` phải là đường dẫn ĐÃ kiểm thuộc tenant (``luu_tru.kiem_uri_thuoc_tenant``).
    ``file_name`` là tên người dùng khai — chỉ dùng để lấy đuôi.
    """
    if not duong_dan.is_file():
        raise StoredFileNotFoundError(f"Không có tệp tại {duong_dan}")

    size = duong_dan.stat().st_size
    if size > max_bytes:
        raise FileTooLargeError(f"Tệp {size} byte, vượt giới hạn {max_bytes} byte")

    duoi = Path(file_name).suffix.lower()
    dinh_dang = DINH_DANG_THEO_DUOI.get(duoi)
    if dinh_dang is None:
        nhan = ", ".join(sorted(DINH_DANG_THEO_DUOI))
        raise UnsupportedFormatError(f"Không nhận đuôi {duoi or '(trống)'!r}. Chỉ nhận: {nhan}")

    with duong_dan.open("rb") as f:
        dau_tep = f.read(_SO_BYTE_DOC)

    if dinh_dang == "PDF":
        khop = _la_pdf(dau_tep)
    elif dinh_dang == "DOCX":
        khop = _la_docx(duong_dan, dau_tep)
    else:
        khop = _la_van_ban_utf8(dau_tep)

    if not khop:
        mong_doi = "văn bản UTF-8" if dinh_dang in _DINH_DANG_VAN_BAN else dinh_dang
        raise UnsupportedFormatError(f"Đuôi {duoi!r} nhưng nội dung không phải {mong_doi}")

    return KetQuaNhanDien(
        source_type=dinh_dang,
        mime_type=MIME_THEO_DINH_DANG[dinh_dang],
        size_bytes=size,
    )
