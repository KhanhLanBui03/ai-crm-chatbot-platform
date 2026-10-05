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
# Chỉ áp dụng cho các âm tiết mở (kết thúc bằng nguyên âm), không áp dụng khi có phụ âm cuối
# (như toàn, hoàn, khoản)
_VOWEL_ACCENT_PAIRS = {
    "à": "òa", "á": "óa", "ả": "ỏa", "ã": "õa", "ạ": "ọa",
    "è": "òe", "é": "óe", "ẻ": "ỏe", "ẽ": "õe", "ẹ": "ọe",
    "ỳ": "ùy", "ý": "úy", "ỷ": "ủy", "ỹ": "ũy", "ỵ": "ụy",
}

_OPEN_OA_PATTERN = re.compile(r"(?i)\b([b-df-zđ]*)o([àáảãạ])\b")
_OPEN_OE_PATTERN = re.compile(r"(?i)\b([b-df-zđ]*)o([èéẻẽẹ])\b")
_OPEN_UY_PATTERN = re.compile(r"(?i)\b([b-df-zđ]*)u([ỳýỷỹỵ])\b")


def _replace_open_syllable(m: re.Match[str]) -> str:
    cons = m.group(1)
    # "qu" là một phụ âm đầu, "u" trong đó không phải nguyên âm: "quý", "quỹ" giữ nguyên
    # (không thì thành "qúy", "qũy" — "Quý khách" có trong gần như mọi câu trả lời CRM).
    if cons.lower().endswith("q"):
        return m.group(0)
    replacement = _VOWEL_ACCENT_PAIRS[m.group(2).lower()]
    if m.group(0)[0].isupper():
        return cons.capitalize() + replacement
    return cons + replacement


# Gộp ký tự chữ thường lặp từ 3 lần trở lên ("chàoooooo" -> "chào", "đẹpppp" -> "đẹp").
# Ngưỡng 3 chứ không phải 2: tiếng Anh và từ mượn có nhiều chữ đôi hợp lệ
# (Facebook, Google, free, feedback, cái xoong). Không gộp chữ hoa (CCCD, IEEE).
_CHAR_REPEAT_PATTERN = re.compile(r"([a-zà-ỹ])\1{2,}")

# Gộp nguyên âm kéo dài sau nguyên âm có dấu ("quáaaa" -> "quá"). Cũng đòi từ 2 ký tự
# lặp trở lên (tổng >= 3) vì cùng lý do trên. Phải chạy TRƯỚC _CHAR_REPEAT_PATTERN:
# chạy sau thì "quáaaa" đã thành "quáa" và không còn khớp.
_ACCENTED_VOWEL_PATTERNS = [
    (re.compile(r"([aáàảãạăắằẳẵặâấầẩẫậ])a{2,}", re.IGNORECASE), r"\1"),
    (re.compile(r"([eéèẻẽẹêếềểễệ])e{2,}", re.IGNORECASE), r"\1"),
    (re.compile(r"([iíìỉĩị])i{2,}", re.IGNORECASE), r"\1"),
    (re.compile(r"([oóòỏõọôốồổỗộơớờởỡợ])o{2,}", re.IGNORECASE), r"\1"),
    (re.compile(r"([uúùủũụưứừửữự])u{2,}", re.IGNORECASE), r"\1"),
    (re.compile(r"([yýỳỷỹỵ])y{2,}", re.IGNORECASE), r"\1"),
]

# Email và URL đi nguyên vẹn qua bước 3–5: "www" không được gộp thành "w", và
# "ad@shop.vn" không được biến thành "admin@shop.vn" (đổi luôn cả dữ liệu PII).
_PROTECTED_PATTERN = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"|(?:https?://|www\.)\S+"
)

# Gộp dấu câu lặp quá mức (ví dụ: "????" -> "?", "!!!!!" -> "!", "....." -> "...")
_PUNCT_REPEAT_PATTERN = re.compile(r"([?!])\1+")
_DOT_REPEAT_PATTERN = re.compile(r"\.{4,}")

# Bảng chuẩn hoá từ viết tắt / teencode thông dụng trong hội thoại khách hàng Việt Nam
_TEENCODE_MAP: dict[str, str] = {
    # Không
    "ko": "không",
    "kô": "không",
    "khg": "không",
    "khong": "không",
    "hok": "không",
    "hem": "không",
    "k": "không",  # "50 k" (nghìn) và "K" viết hoa được giữ — xem _replace_teencode
    # Được
    "đc": "được",
    "dc": "được",
    # Sản phẩm
    "sp": "sản phẩm",
    # Nhân viên
    "nv": "nhân viên",
    "nvien": "nhân viên",
    # Như thế nào / thế nào
    "ntn": "như thế nào",
    "tnao": "thế nào",
    # Tin nhắn / Phản hồi
    "ib": "nhắn tin",
    "inb": "nhắn tin",
    "rep": "phản hồi",
    # Quản trị viên
    "ad": "admin",
    # Chưa
    "chx": "chưa",
    # Thích
    "thik": "thích",
    "thjk": "thích",
    # Bây giờ — KHÔNG có "bh": trong CRM "bh" thường là "bảo hành"
    "bjo": "bây giờ",
    "bgiờ": "bây giờ",
    # KHÔNG có "mk": trong hỗ trợ kỹ thuật "quên mk" là "quên mật khẩu", không phải "mình".
    # Từ viết tắt hai nghĩa thì để nguyên — router đã học trên văn bản thô, đoán sai
    # nghĩa còn tệ hơn không đoán.
}

# Regex bắt teencode độc lập giữa ranh giới từ (\b), ưu tiên từ dài trước
_TEENCODE_REGEX = re.compile(
    r"(?i)\b("
    + "|".join(re.escape(k) for k in sorted(_TEENCODE_MAP, key=len, reverse=True))
    + r")\b"
)
_NUMBER_BEFORE = re.compile(r"\d\s*$")


def _replace_teencode(m: re.Match[str]) -> str:
    raw = m.group(0)
    lower = raw.lower()
    if lower == "k":
        # "K" viết hoa là tên riêng (vitamin K, gói K); "50 k", "50k" là nghìn đồng.
        if raw == "K" or _NUMBER_BEFORE.search(m.string, 0, m.start()):
            return raw
    repl = _TEENCODE_MAP.get(lower, raw)
    if raw.isupper():
        return repl.upper()
    if raw[0].isupper():
        return repl.capitalize()
    return repl


# Khoảng trắng và ngắt dòng
_LINE_WHITESPACE_PATTERN = re.compile(r"[ \t]*\n[ \t]*")
_MULTI_SPACE_PATTERN = re.compile(r"[ \t]+")
_MULTI_NEWLINE_PATTERN = re.compile(r"\n{3,}")


def _normalize_segment(s: str) -> str:
    """Bước 3–5 cho một đoạn văn bản không chứa email/URL."""
    if not s:
        return s

    # Bước 3: Thống nhất kiểu dấu thanh (chỉ áp dụng âm tiết mở: hoà/toà/thuỷ -> hòa/tòa/thủy)
    s = _OPEN_OA_PATTERN.sub(_replace_open_syllable, s)
    s = _OPEN_OE_PATTERN.sub(_replace_open_syllable, s)
    s = _OPEN_UY_PATTERN.sub(_replace_open_syllable, s)

    # Bước 4: Gộp ký tự chữ lặp quá mức (ví dụ: "quáaaa" -> "quá", "đượcccc" -> "được")
    for p, repl in _ACCENTED_VOWEL_PATTERNS:
        s = p.sub(repl, s)
    s = _CHAR_REPEAT_PATTERN.sub(r"\1", s)

    # Gộp dấu chấm, hỏi, cảm thán lặp
    s = _PUNCT_REPEAT_PATTERN.sub(r"\1", s)
    s = _DOT_REPEAT_PATTERN.sub("...", s)

    # Bước 5: Chuẩn hoá từ viết tắt / teencode (ko -> không, đc -> được, sp -> sản phẩm)
    return _TEENCODE_REGEX.sub(_replace_teencode, s)


def normalize_vietnamese_text(text: str) -> str:
    """Chuẩn hoá văn bản tiếng Việt toàn diện cho Guardrails và Retrieval.
    
    Quy trình 6 bước:
    1. Lọc sạch ký tự zero-width và ký tự ẩn.
    2. Chuẩn hoá Unicode về chuẩn NFC (tránh phân rã NFD làm lỗi so khớp chuỗi).
    3. Thống nhất quy tắc đặt dấu thanh (chuyển hoà/toà/thuỷ -> hòa/tòa/thủy).
    4. Gộp các ký tự chữ lặp quá mức (kể cả teencode kéo dài) và dấu câu lặp.
    5. Chuẩn hoá từ viết tắt / teencode phổ biến (ko -> không, đc -> được, sp -> sản phẩm).
    6. Chuẩn hoá khoảng trắng và ngắt dòng.
    """
    if not text:
        return ""

    # Bước 1: Xóa ký tự zero-width
    s = _ZERO_WIDTH_PATTERN.sub("", text)

    # Bước 2: Chuẩn hoá Unicode NFC
    s = unicodedata.normalize("NFC", s)

    # Bước 3–5 chạy trên từng đoạn nằm giữa email/URL, email/URL giữ nguyên văn
    parts: list[str] = []
    last = 0
    for m in _PROTECTED_PATTERN.finditer(s):
        parts.append(_normalize_segment(s[last:m.start()]))
        parts.append(m.group(0))
        last = m.end()
    parts.append(_normalize_segment(s[last:]))
    s = "".join(parts)

    # Bước 6: Chuẩn hoá khoảng trắng và ngắt dòng
    s = _LINE_WHITESPACE_PATTERN.sub("\n", s)
    s = _MULTI_NEWLINE_PATTERN.sub("\n\n", s)
    s = _MULTI_SPACE_PATTERN.sub(" ", s)

    return s.strip()
