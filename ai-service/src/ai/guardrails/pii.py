"""[PRODUCTION] Che giấu dữ liệu định danh cá nhân (PII) Việt Nam — Master Plan §4.8.

Quy định pháp lý & kiến trúc:
- Tuân thủ Nghị định 13/2023/NĐ-CP (Bảo vệ dữ liệu cá nhân, Bề mặt T8).
- RÀNG BUỘC THEN CHỐT: Che ở TẦNG GHI (vào DB và log), KHÔNG PHẢI lúc hiển thị (UC040).
  Che lúc hiển thị nghĩa là dữ liệu thật vẫn nằm trong bảng và trong log — chỉ giấu khỏi mắt
  người xem, không giấu khỏi người đọc được CSDL hoặc kiểm toán viên.
- Thực thể PII đặc thù Việt Nam:
  1. Số điện thoại (10 chữ số, các đầu số di động 03, 05, 07, 08, 09 hoặc +84).
  2. Số CCCD (12 chữ số) và CMND cũ (9 chữ số).
  3. Địa chỉ Email.
"""

from __future__ import annotations

import re
from typing import Literal

# ══════════════════════════════════════════════════════════════════════════════
# BIỂU THỨC CHÍNH QUY PII VIỆT NAM
# ══════════════════════════════════════════════════════════════════════════════

# 1. Số điện thoại Việt Nam (03x, 05x, 07x, 08x, 09x hoặc +84/84)
# Hỗ trợ phân cách bằng dấu chấm, gạch ngang hoặc khoảng trắng
_PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:(?:\+?84|0)(?:3[2-9]|5[25689]|7[06-9]|8[1-9]|9[0-9]))(?:[.\-\s]?\d{3})(?:[.\-\s]?\d{3,4})(?!\d)"
)

# 2. Số CCCD (12 chữ số) và CMND cũ (9 chữ số)
# Bắt buộc ranh giới từ để tránh nhầm mã đơn hàng hoặc timestamp
_CCCD_PATTERN = re.compile(r"(?<!\d)(?:0\d{11})(?!\d)")
_CMND_PATTERN = re.compile(r"(?<!\d)(?:\d{9})(?!\d)")

# 3. Địa chỉ Email
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)


def _mask_phone_partial(match: re.Match[str]) -> str:
    raw = match.group(0)
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 10:
        prefix = raw[:4]
        suffix = raw[-3:]
        return f"{prefix}***{suffix}"
    return f"{raw[:2]}***{raw[-2:]}"


def _mask_cccd_partial(match: re.Match[str]) -> str:
    raw = match.group(0)
    # CCCD 12 số: Giữ 4 số đầu (mã tỉnh/giới tính/năm sinh), 2 số cuối, che 6 số ở giữa
    return f"{raw[:4]}******{raw[-2:]}"


def _mask_cmnd_partial(match: re.Match[str]) -> str:
    raw = match.group(0)
    # CMND 9 số: Giữ 3 số đầu, 2 số cuối, che 4 số giữa
    return f"{raw[:3]}****{raw[-2:]}"


def _mask_email_partial(match: re.Match[str]) -> str:
    raw = match.group(0)
    parts = raw.split("@", 1)
    if len(parts) == 2:
        local, domain = parts
        masked_local = f"{local[0]}***" if len(local) > 0 else "***"
        return f"{masked_local}@{domain}"
    return "***@***"


def mask_pii(
    text: str,
    mode: Literal["partial", "redact"] = "partial",
) -> tuple[str, dict[str, int]]:
    """Che giấu thông tin PII trong văn bản trước khi ghi vào CSDL hoặc nhật ký log.
    
    Tham số:
    - text: Văn bản người dùng nhập vào.
    - mode:
        + 'partial': Giữ lại đầu/cuối để nhận diện khách hàng (vd: 0912***678, k***@gmail.com).
        + 'redact': Thay thế hoàn toàn bằng nhãn thẻ ([REDACTED_PHONE], [REDACTED_CCCD]).
        
    Trả về:
    - masked_text: Văn bản đã được làm mờ dữ liệu nhạy cảm.
    - summary: Thống kê số lượng PII đã được phát hiện và che giấu theo từng loại.
    """
    if not text:
        return "", {}

    summary: dict[str, int] = {
        "phone": 0,
        "cccd": 0,
        "cmnd": 0,
        "email": 0,
    }

    result = text

    # 1. Che giấu Email trước (tránh số trong email bị regex phone/cmnd bắt nhầm)
    emails = _EMAIL_PATTERN.findall(result)
    if emails:
        summary["email"] = len(emails)
        if mode == "partial":
            result = _EMAIL_PATTERN.sub(_mask_email_partial, result)
        else:
            result = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", result)

    # 2. Che giấu CCCD (12 chữ số)
    cccds = _CCCD_PATTERN.findall(result)
    if cccds:
        summary["cccd"] = len(cccds)
        if mode == "partial":
            result = _CCCD_PATTERN.sub(_mask_cccd_partial, result)
        else:
            result = _CCCD_PATTERN.sub("[REDACTED_CCCD]", result)

    # 3. Che giấu Số điện thoại
    phones = _PHONE_PATTERN.findall(result)
    if phones:
        summary["phone"] = len(phones)
        if mode == "partial":
            result = _PHONE_PATTERN.sub(_mask_phone_partial, result)
        else:
            result = _PHONE_PATTERN.sub("[REDACTED_PHONE]", result)

    # 4. Che giấu CMND (9 chữ số) - chạy sau Phone vì Phone 10 số có thể trùng lặp
    cmnds = _CMND_PATTERN.findall(result)
    if cmnds:
        summary["cmnd"] = len(cmnds)
        if mode == "partial":
            result = _CMND_PATTERN.sub(_mask_cmnd_partial, result)
        else:
            result = _CMND_PATTERN.sub("[REDACTED_CMND]", result)

    # Lọc bỏ các mục thống kê = 0
    active_summary = {k: v for k, v in summary.items() if v > 0}
    return result, active_summary


def contains_pii(text: str) -> bool:
    """Kiểm tra nhanh xem văn bản có chứa dữ liệu PII nào hay không."""
    if not text:
        return False
    return bool(
        _EMAIL_PATTERN.search(text)
        or _CCCD_PATTERN.search(text)
        or _PHONE_PATTERN.search(text)
        or _CMND_PATTERN.search(text)
    )
