"""Phiên CSDL có RLS — chỗ DUY NHẤT đặt ``app.tenant_id`` cho mỗi transaction.

Cô lập tenant của Track B đứng trên đúng một bất biến: mọi truy vấn chạy trong một transaction
đã đặt ``app.tenant_id``, bằng role ``ai_app`` (role CHỊU RLS). File này thi hành bất biến đó —
repository KHÔNG tự thêm ``WHERE tenant_id = ?``, để RLS lo (``.claude/rules/database.md``).
Tự lọc ở tầng ứng dụng tạo cảm giác an toàn giả và che mất lỗi cấu hình RLS.

BẪY CONNECTION POOL — lý do file này tồn tại:

    SET app.tenant_id = A   ->  dính lại trên kết nối, theo nó về pool
    request cua tenant B mượn trúng kết nối đó mà quên đặt
    ->  đọc được dữ liệu của A. Không exception, không log, không dấu vết.

``set_config(..., true)`` — tương đương ``SET LOCAL`` — chết theo transaction nên không bao giờ
theo kết nối về pool được. Dùng ``set_config`` chứ không ``SET LOCAL`` vì ``SET LOCAL`` không
nhận bind parameter.

Test ``tests/integration/test_rls.py`` là lưới an toàn của file này. Sửa file này xong phải
chạy lại nó; đỏ thì file này sai, không phải test sai.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.ai.config import get_settings
from src.ai.exceptions import AiServiceError

# Role runtime DUY NHẤT được phép. ADR-0001, ADR-0016.
ROLE_RUNTIME = "ai_app"


def _kiem_role_runtime(dsn: str) -> None:
    """Chặn ngay lúc dựng engine nếu chạy bằng role đi vòng qua được RLS.

    ``crm_owner`` có ``rolsuper = t`` VÀ ``rolbypassrls = t`` (đã đo trên CSDL thật): nối bằng
    nó thì mọi policy lặng lẽ mất tác dụng — không lỗi, không log, chỉ là dữ liệu của tenant
    khác hiện ra như thể đó là chuyện bình thường. Đặt ``DB_USERNAME=crm_owner`` trong ``.env``
    là đủ để vô hiệu hoá toàn bộ cô lập tenant mà không một dòng code nào phải đổi.

    Nên fail-closed ngay lúc khởi động, cùng tinh thần với ``ai.current_tenant()`` ở V201:
    ồn ào còn hơn im lặng.
    """
    user = make_url(dsn).username
    if user != ROLE_RUNTIME:
        raise AiServiceError(
            f"ai-service phải chạy bằng role {ROLE_RUNTIME!r}, đang là {user!r}. "
            "Role chủ bảng bypass RLS kể cả khi đã FORCE — xem ADR-0001."
        )


# ---------------------------------------------------------
# 1. ENGINE ("Máy bơm tổng")
# Nhận dsn để test trỏ được vào testcontainer (cổng ngẫu nhiên mỗi lần chạy) và
# ép pool_size=1 mà KHÔNG phải sửa file này.
# ---------------------------------------------------------
def tao_engine(dsn: str | None = None, **engine_kwargs: Any) -> AsyncEngine:
    """Dựng engine. Không truyền gì thì lấy DSN production từ ``get_settings()``."""
    dsn = dsn or get_settings().database_url
    _kiem_role_runtime(dsn)
    # Dịch vụ chạy dài ngày: kết nối nằm không trong pool có thể bị phía server đóng.
    # pre_ping đổi một lỗi khó đoán giữa request lấy một lượt kiểm rẻ tiền.
    engine_kwargs.setdefault("pool_pre_ping", True)
    return create_async_engine(dsn, **engine_kwargs)


# ---------------------------------------------------------
# 2. SESSION FACTORY ("Xưởng đúc phiên làm việc")
# ---------------------------------------------------------
def tao_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """expire_on_commit=False: không có nó thì object rỗng ruột ngay sau khi commit."""
    return async_sessionmaker(engine, expire_on_commit=False)


engine = tao_engine()
async_session = tao_session_factory(engine)


# ---------------------------------------------------------
# 3. TRÁI TIM (Người gác cổng RLS)
# ---------------------------------------------------------
@asynccontextmanager
async def get_tenant_session(
    tenant_id: str,
    factory: async_sessionmaker[AsyncSession] | None = None,
) -> AsyncIterator[AsyncSession]:
    """Cấp một session đã gắn tenant, cô lập trong đúng một transaction.

    ``factory`` chỉ để test tiêm sessionmaker của riêng nó; đường production để trống.
    """
    async with (factory or async_session)() as session:
        # Bắt buộc: mở transaction TRƯỚC khi đặt tenant.
        async with session.begin():
            # Tham số 'true' ở cuối chính là phần "LOCAL" — hết transaction là mất.
            await session.execute(
                text("SELECT set_config('app.tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )

            # yield nằm hoàn toàn bên TRONG session.begin(): truy vấn của người gọi phải
            # chạy cùng transaction với set_config, nếu không thì tenant chưa được đặt.
            yield session


# ---------------------------------------------------------
# 4. DISPOSE ("Ngắt kết nối an toàn")
# ---------------------------------------------------------
async def dispose() -> None:
    """Trả kết nối cho CSDL lúc tắt ứng dụng. Engine do test tự dựng thì test tự dispose."""
    await engine.dispose()
