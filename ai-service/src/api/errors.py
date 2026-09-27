"""Dịch ngoại lệ sang phản hồi HTTP — chỗ DUY NHẤT biết mã HTTP của từng lỗi nghiệp vụ.

``src/ai/`` chỉ ném ngoại lệ mang ``code`` (``src/ai/exceptions.py``); bảng dưới đây gắn mã
HTTP cho chúng. Worker dùng cùng các ngoại lệ đó mà không cần biết HTTP là gì.

Mọi phản hồi lỗi có cùng một hình dạng: ``{"code": ..., "message": ...}``. java-core rẽ nhánh
theo ``code``, không theo ``message``.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.ai.exceptions import (
    AiServiceError,
    FileTooLargeError,
    ForbiddenFileUriError,
    StorageUnavailableError,
    StoredFileNotFoundError,
    TenantContextMissingError,
    UnsupportedFormatError,
)

logger = logging.getLogger(__name__)

# Ngoại lệ nào không có ở đây thì là 500 — lỗi mình chưa lường trước, không phải lỗi của
# phía gọi. Tra theo MRO nên lớp con kế thừa mã của lớp cha nếu không khai riêng.
_MA_HTTP: dict[type[AiServiceError], int] = {
    TenantContextMissingError: 401,
    ForbiddenFileUriError: 403,
    StoredFileNotFoundError: 422,
    FileTooLargeError: 413,
    UnsupportedFormatError: 415,
    StorageUnavailableError: 503,
}

# Mã nghiệp vụ cho lỗi validate, theo từng đường dẫn. Đặc tả UC018 gọi lỗi siêu dữ liệu là
# INVALID_METADATA; các endpoint sau này (chat, extract…) sẽ có tên riêng, nên không đặt
# INVALID_METADATA làm mặc định chung.
_MA_VALIDATE_THEO_DUONG_DAN: dict[str, str] = {
    "/v1/ai/kb/documents": "INVALID_METADATA",
}


def _ma_http(exc: AiServiceError) -> int:
    for lop in type(exc).__mro__:
        if lop in _MA_HTTP:
            return _MA_HTTP[lop]
    return 500


async def _xu_ly_loi_nghiep_vu(request: Request, exc: AiServiceError) -> JSONResponse:
    status = _ma_http(exc)
    if isinstance(exc, ForbiddenFileUriError):
        # Luôn ghi — đây là dấu hiệu tấn công hoặc java-core cấu hình sai volume.
        logger.warning("Chặn URI ngoài vùng của tenant: %s", exc)
    elif status >= 500:
        # Chi tiết chỉ vào log; phía gọi nhận thông điệp chung, không lộ cấu trúc bên trong.
        logger.error("Lỗi chưa phân loại: %s", exc, exc_info=exc)
        return JSONResponse(
            status_code=status, content={"code": exc.code, "message": "Lỗi nội bộ ai-service"}
        )
    return JSONResponse(status_code=status, content={"code": exc.code, "message": str(exc)})


async def _xu_ly_loi_validate(request: Request, exc: RequestValidationError) -> JSONResponse:
    code = _MA_VALIDATE_THEO_DUONG_DAN.get(request.url.path, "INVALID_REQUEST")
    # Chỉ trả vị trí + lý do, KHÔNG trả lại giá trị "input": body có thể chứa mô tả tài liệu
    # dài, và lặp lại nguyên văn dữ liệu người dùng vào log/phản hồi là thói quen xấu (NĐ 13).
    loi = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse(
        status_code=422,
        content={"code": code, "message": "Dữ liệu gửi lên không hợp lệ", "errors": loi},
    )


def dang_ky_xu_ly_loi(app: FastAPI) -> None:
    """Gắn hai bộ dịch lỗi vào ứng dụng. Gọi một lần trong ``create_app()``."""
    app.add_exception_handler(AiServiceError, _xu_ly_loi_nghiep_vu)
    app.add_exception_handler(RequestValidationError, _xu_ly_loi_validate)
