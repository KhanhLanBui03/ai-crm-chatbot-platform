"""Phụ thuộc dùng chung cho tầng API (Dependency Injection của FastAPI).

MẪU. Mọi endpoint lấy cấu hình, phiên CSDL và ngữ cảnh tenant qua đây — không tự tạo.

``get_tenant_id`` là chốt an toàn quan trọng nhất của tệp này: thiếu tenant thì từ chối
request ngay, không đoán và không dùng giá trị mặc định (ADR-0001).
"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.config import Settings, get_settings
from src.ai.db.session import get_tenant_session
from src.ai.exceptions import TenantContextMissingError
from src.ai.telemetry.logging import tenant_id_var, trace_id_var

SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_trace_id(x_trace_id: Annotated[str | None, Header()] = None) -> str:
    """Lấy Trace ID do gateway gắn và đưa vào ngữ cảnh log."""
    trace_id = x_trace_id or "-"
    trace_id_var.set(trace_id)
    return trace_id


async def get_tenant_id(x_tenant_id: Annotated[str | None, Header()] = None) -> str:
    """Lấy tenant từ header đã được gateway xác thực.

    Ném lỗi khi thiếu. Không bao giờ mặc định về một tenant nào đó — sai ở đây là rò rỉ
    dữ liệu chéo khách hàng.
    """
    if not x_tenant_id:
        raise TenantContextMissingError("Thiếu X-Tenant-Id")
    tenant_id_var.set(x_tenant_id)
    return x_tenant_id


TraceIdDep = Annotated[str, Depends(get_trace_id)]
TenantIdDep = Annotated[str, Depends(get_tenant_id)]


async def get_session(tenant_id: TenantIdDep) -> AsyncIterator[AsyncSession]:
    """Phiên CSDL đã gắn tenant — trọn một request nằm trong MỘT transaction.

    Tenant đi thẳng từ ``get_tenant_id`` vào ``get_tenant_session``: không có đường nào khác
    để đặt ``app.tenant_id``. Commit (hoặc rollback) xảy ra lúc dependency này kết thúc.
    """
    async with get_tenant_session(tenant_id) as session:
        yield session


# scope="function" là BẮT BUỘC, không phải tuỳ chọn. Mặc định ("request") phần sau yield
# chạy SAU KHI phản hồi đã gửi đi — tức commit xảy ra sau khi client đã nhận 202. Commit mà
# hỏng lúc đó thì client cầm job_id của một bản ghi không tồn tại. Với "function", commit
# xong (hoặc lỗi thành 5xx) rồi mới trả phản hồi. Cần FastAPI >= 0.121.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]
