"""[PRODUCTION] Che giấu dữ liệu định danh cá nhân (PII) Việt Nam — Master Plan §4.8.

Quy định pháp lý & kiến trúc:
- Tuân thủ Nghị định 13/2023/NĐ-CP (Bảo vệ dữ liệu cá nhân, Bề mặt T8).
- RÀNG BUỘC THEN CHỐT: Che ở TẦNG GHI (vào DB và log), KHÔNG PHẢI lúc hiển thị (UC040).
  Che lúc hiển thị nghĩa là dữ liệu thật vẫn nằm trong bảng và trong log — chỉ giấu khỏi mắt
  người xem, không giấu khỏi người đọc được CSDL hoặc kiểm toán viên.
- Tầng ghi dùng ``redact`` (mặc định). ``partial`` chỉ để hiển thị/debug: nó vẫn để lộ
  một phần số.
- Thực thể PII đặc thù Việt Nam:
  1. Số điện thoại di động (10 chữ số, đầu 03, 05, 07, 08, 09 hoặc +84), mọi kiểu phân
     cách thường gặp: 0912345678, 0912.345.678, 0912 345 678, +84 912 345 678.
  2. Số CCCD (12 chữ số) và CMND cũ (9 chữ số — chỉ khi có từ khoá CMND/CMT đi kèm).
  3. Địa chỉ Email.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

# ══════════════════════════════════════════════════════════════════════════════
# BIỂU THỨC CHÍNH QUY PII VIỆT NAM
# ══════════════════════════════════════════════════════════════════════════════

# 1. Số điện thoại di động Việt Nam: tiền tố (+84 / 84 / 0) + đầu mạng 2 số + 7 số thuê bao.
# Cho phép một ký tự phân cách (. - khoảng trắng) trước mỗi chữ số của phần thuê bao, nên
# bắt được mọi cách nhóm 4-3-3, 3-3-4, 4-2-2-2... chứ không chỉ viết liền.
_PHONE_PATTERN = re.compile(
    r"(?<![\d+])(?:\+?84[.\-\s]?|0)(?:3[2-9]|5[25689]|7[06-9]|8[1-9]|9\d)(?:[.\-\s]?\d){7}(?!\d)"
)

# 2. Số CCCD (12 chữ số, mã tỉnh bắt đầu bằng 0)
_CCCD_PATTERN = re.compile(r"(?<!\d)0\d{11}(?!\d)")

# CMND cũ (9 chữ số). Chín chữ số trần trùng với tiền ("150000000 đồng") và mã đơn hàng,
# nên chỉ che khi trong ~30 ký tự phía trước có từ khoá CMND.
_CMND_PATTERN = re.compile(r"(?<!\d)\d{9}(?!\d)")
_CMND_KEYWORD = re.compile(r"\b(?:cmnd|cmt|chung\s+minh(?:\s+nhan\s+dan|\s+thu)?)\b")
_CMND_CONTEXT_CHARS = 30

# 3. Địa chỉ Email
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def _fold(text: str) -> str:
    """Bỏ dấu, viết thường — chỉ để dò từ khoá trong cửa sổ ngữ cảnh."""
    s = unicodedata.normalize("NFD", text)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def _cmnd_matches(text: str) -> list[re.Match[str]]:
    """Các dãy 9 chữ số có từ khoá CMND ngay phía trước."""
    hits = []
    for m in _CMND_PATTERN.finditer(text):
        window = _fold(text[max(0, m.start() - _CMND_CONTEXT_CHARS):m.start()])
        if _CMND_KEYWORD.search(window):
            hits.append(m)
    return hits


def _mask_phone_partial(match: re.Match[str]) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if digits.startswith("84"):
        digits = "0" + digits[2:]
    # Giữ đầu mạng (3 số) và 2 số cuối, che 5 số giữa — giữ 7/10 số như "0912***678"
    # thì chỉ còn 1.000 khả năng, dò ra số thật quá dễ.
    return f"{digits[:3]}*****{digits[-2:]}"


def _mask_cccd_partial(match: re.Match[str]) -> str:
    raw = match.group(0)
    # CCCD 12 số: Giữ 4 số đầu (mã tỉnh/giới tính/năm sinh), 2 số cuối, che 6 số ở giữa
    return f"{raw[:4]}******{raw[-2:]}"


def _mask_cmnd_partial(raw: str) -> str:
    # CMND 9 số: Giữ 3 số đầu, 2 số cuối, che 4 số giữa
    return f"{raw[:3]}****{raw[-2:]}"


def _mask_email_partial(match: re.Match[str]) -> str:
    local, domain = match.group(0).split("@", 1)
    return f"{local[0]}***@{domain}"


def mask_pii(
    text: str,
    mode: Literal["partial", "redact"] = "redact",
) -> tuple[str, dict[str, int]]:
    """Che giấu thông tin PII trong văn bản trước khi ghi vào CSDL hoặc nhật ký log.

    Tham số:
    - text: Văn bản người dùng nhập vào.
    - mode:
        + 'redact' (mặc định, dùng cho tầng ghi): Thay thế hoàn toàn bằng nhãn thẻ
          ([REDACTED_PHONE], [REDACTED_CCCD], [REDACTED_CMND], [REDACTED_EMAIL]).
        + 'partial' (chỉ hiển thị/debug): Giữ lại đầu/cuối (vd: 091*****78, k***@gmail.com).

    Trả về:
    - masked_text: Văn bản đã được làm mờ dữ liệu nhạy cảm.
    - summary: Thống kê số lượng PII đã được phát hiện và che giấu theo từng loại.
    """
    if not text:
        return "", {}

    summary: dict[str, int] = {}
    partial = mode == "partial"
    result = text

    # Thứ tự có chủ đích: Email trước (số trong email không bị bắt nhầm), rồi CCCD 12 số,
    # rồi điện thoại, cuối cùng CMND 9 số (dãy đã bị che ở các bước trước không còn khớp).
    for kind, pattern, partial_fn, tag in (
        ("email", _EMAIL_PATTERN, _mask_email_partial, "[REDACTED_EMAIL]"),
        ("cccd", _CCCD_PATTERN, _mask_cccd_partial, "[REDACTED_CCCD]"),
        ("phone", _PHONE_PATTERN, _mask_phone_partial, "[REDACTED_PHONE]"),
    ):
        result, n = pattern.subn(partial_fn if partial else tag, result)
        if n:
            summary[kind] = n

    cmnds = _cmnd_matches(result)
    if cmnds:
        summary["cmnd"] = len(cmnds)
        for m in reversed(cmnds):
            repl = _mask_cmnd_partial(m.group(0)) if partial else "[REDACTED_CMND]"
            result = result[:m.start()] + repl + result[m.end():]

    return result, summary


def contains_pii(text: str) -> bool:
    """Kiểm tra nhanh xem văn bản có chứa dữ liệu PII nào hay không."""
    if not text:
        return False
    return bool(
        _EMAIL_PATTERN.search(text)
        or _CCCD_PATTERN.search(text)
        or _PHONE_PATTERN.search(text)
        or _cmnd_matches(text)
    )
