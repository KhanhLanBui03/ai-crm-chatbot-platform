"""[PRODUCTION] Chuẩn hoá tiếng Việt — Master Plan §4.8.

Ràng buộc kiến trúc (§3.9.2):
- Chạy trên 100% lượt chat trước mọi bước xử lý.
- Thuần Python, không model, không gọi mạng (độ trễ < 0.2 ms, chi phí 0đ).
- Hàm chuẩn hoá này dùng chung cho cả nạp tài liệu (ingestion) và câu hỏi lúc truy vấn (retrieval).
  Lệch nhau là truy hồi hụt mà không có lỗi nào báo ra.
"""

from __future__ import annotations

import re
import unicodedata

# Ký tự zero-width và ký tự điều khiển ẩn không hiển thị
_ZERO_WIDTH_PATTERN = re.compile(
    r"[\u200B-\u200D\uFEFF\u00AD\u200E\u200F\u202A-\u202E\u2060-\u206F]"
)

# Bảng chuẩn hoá thống nhất kiểu đặt dấu thanh tiếng Việt (chuẩn mới: hòa, tòa, thủy, khỏe)
# Thay thế kiểu dấu cũ (hoà, toà, thuỷ, khoẻ) về kiểu dấu chuẩn thống nhất
_ACCENT_MAP = {
    # oà -> hòa
    "oà": "òa", "oá": "óa", "oả": "ỏa", "oã": "õa", "oạ": "ọa",
    "Oà": "Òa", "Oá": "Óa", "Oả": "Ỏa", "Oã": "Õa", "Oạ": "Ọa",
    # oè -> khỏe
    "oè": "òe", "oé": "óe", "oẻ": "ỏe", "oẽ": "õe", "oẹ": "ọe",
    "Oè": "Òe", "Oé": "Óe", "Oẻ": "Ỏe", "Oẽ": "Õe", "Oẹ": "Ọe",
    # uỳ -> thủy
    "uỳ": "ùy", "uý": "úy", "uỷ": "ủy", "uỹ": "ũy", "uỵ": "ụy",
    "Uỳ": "Ùy", "Uý": "Úy", "Uỷ": "Ủy", "Uỹ": "Ũy", "Uỵ": "Ụy",
}

_ACCENT_REGEX = re.compile(
    "|".join(re.escape(k) for k in _ACCENT_MAP.keys())
)

# Gộp ký tự chữ lặp quá 2 lần (ví dụ: "chàoooooo" -> "chào", "đẹpppp" -> "đẹp")
_CHAR_REPEAT_PATTERN = re.compile(r"([^\W\d_])\1{2,}", re.IGNORECASE)

# Gộp các nguyên âm không dấu đi liền sau nguyên âm có dấu (teencode: "quáaaa" -> "quá")
_ACCENTED_VOWEL_PATTERNS = [
    (re.compile(r"([aáàảãạăắằẳẵặâấầẩẫậ])a+", re.IGNORECASE), r"\1"),
    (re.compile(r"([eéèẻẽẹêếềểễệ])e+", re.IGNORECASE), r"\1"),
    (re.compile(r"([iíìỉĩị])i+", re.IGNORECASE), r"\1"),
    (re.compile(r"([oóòỏõọôốồổỗộơớờởỡợ])o+", re.IGNORECASE), r"\1"),
    (re.compile(r"([uúùủũụưứừửữự])u+", re.IGNORECASE), r"\1"),
    (re.compile(r"([yýỳỷỹỵ])y+", re.IGNORECASE), r"\1"),
]

# Gộp dấu câu lặp quá mức (ví dụ: "????" -> "?", "!!!!!" -> "!", "....." -> "...")
_PUNCT_REPEAT_PATTERN = re.compile(r"([?!])\1+")
_DOT_REPEAT_PATTERN = re.compile(r"\.{4,}")

# Khoảng trắng và ngắt dòng
_LINE_WHITESPACE_PATTERN = re.compile(r"[ \t]*\n[ \t]*")
_MULTI_SPACE_PATTERN = re.compile(r"[ \t]+")
_MULTI_NEWLINE_PATTERN = re.compile(r"\n{3,}")


def normalize_vietnamese_text(text: str) -> str:
    """Chuẩn hoá văn bản tiếng Việt toàn diện cho Guardrails và Retrieval.
    
    Quy trình 5 bước:
    1. Lọc sạch ký tự zero-width và ký tự ẩn.
    2. Chuẩn hoá Unicode về chuẩn NFC (tránh phân rã NFD làm lỗi so khớp chuỗi).
    3. Thống nhất quy tắc đặt dấu thanh (chuyển hoà/toà/thuỷ -> hòa/tòa/thủy).
    4. Gộp các ký tự chữ lặp quá mức (kể cả teencode kéo dài) và dấu câu lặp.
    5. Chuẩn hoá khoảng trắng và ngắt dòng.
    """
    if not text:
        return ""

    # Bước 1: Xóa ký tự zero-width
    s = _ZERO_WIDTH_PATTERN.sub("", text)

    # Bước 2: Chuẩn hoá Unicode NFC
    s = unicodedata.normalize("NFC", s)

    # Bước 3: Thống nhất kiểu dấu thanh
    s = _ACCENT_REGEX.sub(lambda m: _ACCENT_MAP[m.group(0)], s)

    # Bước 4: Gộp ký tự chữ lặp quá mức (ví dụ: "đượcccc" -> "được")
    s = _CHAR_REPEAT_PATTERN.sub(r"\1", s)
    for p, repl in _ACCENTED_VOWEL_PATTERNS:
        s = p.sub(repl, s)

    # Gộp dấu chấm, hỏi, cảm thán lặp
    s = _PUNCT_REPEAT_PATTERN.sub(r"\1", s)
    s = _DOT_REPEAT_PATTERN.sub("...", s)

    # Bước 5: Chuẩn hoá khoảng trắng và ngắt dòng
    s = _LINE_WHITESPACE_PATTERN.sub("\n", s)
    s = _MULTI_NEWLINE_PATTERN.sub("\n\n", s)
    s = _MULTI_SPACE_PATTERN.sub(" ", s)

    return s.strip()
