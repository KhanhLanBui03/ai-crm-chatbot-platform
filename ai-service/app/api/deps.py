"""Phụ thuộc dùng chung cho tầng API (Dependency Injection của FastAPI).

MẪU. Mọi endpoint lấy cấu hình, phiên CSDL và ngữ cảnh tenant qua đây — không tự tạo.

``get_tenant_id`` là chốt an toàn quan trọng nhất của tệp này: thiếu tenant thì từ chối
request ngay, không đoán và không dùng giá trị mặc định (ADR-0001).
"""

from typing import Annotated

from fastapi import Depends, Header

from app.core.config import Settings, get_settings
from app.core.exceptions import TenantContextMissingError
from app.core.logging import tenant_id_var, trace_id_var

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

# TODO: SessionDep — phiên SQLAlchemy async, đặt SET LOCAL app.tenant_id cho mỗi transaction
