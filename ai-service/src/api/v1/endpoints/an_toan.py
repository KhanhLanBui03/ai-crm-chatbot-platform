"""Cảnh báo an toàn phía AI — UC040 bước 8 (phần Track B). [PRODUCTION]

``GET /v1/safety-events`` — java-core gọi trong mạng nội bộ rồi gộp với ``audit_logs`` mức CRITICAL thành màn
"Cảnh báo an toàn". Gateway CHẶN đường này từ bên ngoài (``/ai/v1/safety-events/**``): ai-service không kiểm
vai trò người dùng, nên để lộ ra là nhân viên thường đọc được cảnh báo chỉ dành cho quản trị viên.

``tenant_id`` lấy từ ``X-Tenant-Id`` (luật 1), không bao giờ từ tham số.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query

from src.ai.db.repositories import safety_repository
from src.ai.db.repositories.safety_repository import DongAnToan
from src.ai.schemas import SafetyEventItem
from src.api.deps import SessionDep, TenantIdDep

router = APIRouter(tags=["an-toan"])

# (mức nghiêm trọng, bề mặt đe doạ trong docs/threat-model.md, lớp phát hiện)
_PHAN_LOAI: dict[str, tuple[str, str, str]] = {
    "PROMPT_INJECTION_INPUT": ("HIGH", "T2", "guardrails.injection"),
    "PROMPT_INJECTION_DOCUMENT": ("HIGH", "T3", "rag.postguard"),
    "PROMPT_INJECTION_TOOL_RESULT": ("HIGH", "T4", "mcp.tool_result_guard"),
    "TOOL_CALL_BLOCKED": ("HIGH", "T4", "mcp.allowlist"),
    "INTERNAL_DATA_PROBE": ("HIGH", "T5", "guardrails.injection"),
    # Dò dữ liệu doanh nghiệp khác là mục tiêu số 1 của mô hình đa tenant — mức cao nhất
    "CROSS_TENANT_PROBE": ("CRITICAL", "T5", "guardrails.injection"),
}


def thanh_su_kien(d: DongAnToan) -> SafetyEventItem:
    """Một dòng thô → cảnh báo theo hợp đồng. Hàm thuần, test không cần CSDL."""
    muc, be_mat, phat_hien = _PHAN_LOAI.get(d.loai, ("MEDIUM", None, "khong-ro"))
    if d.nguon == "TOOL_CALL":
        hanh_dong = "BLOCKED"
    elif d.tu_choi == "SAFETY_PROBE":
        hanh_dong = "REFUSED"
    elif d.chuyen_giao:
        hanh_dong = "ESCALATED"
    else:
        # Guardrails không chặn luồng: nội dung khả nghi được đối xử như DỮ LIỆU, không như chỉ thị
        hanh_dong = "TREATED_AS_DATA"
    bang_chung: dict[str, str] = {}
    if d.trich:
        bang_chung["excerpt"] = d.trich + ("…" if len(d.trich) >= safety_repository.DO_DAI_TRICH else "")
    if d.chi_tiet:
        bang_chung["detail"] = d.chi_tiet
    if d.nhanh:
        bang_chung["branch"] = d.nhanh
    return SafetyEventItem(
        event_id=d.id,
        event_type=d.loai,
        severity=muc,
        threat_surface=be_mat,
        conversation_id=d.conversation_id,
        interaction_id=d.interaction_id,
        detector=phat_hien,
        action_taken=hanh_dong,
        evidence=bang_chung,
        occurred_at=d.luc,
        reason=d.loai,
    )


@router.get("/v1/safety-events", response_model=list[SafetyEventItem], operation_id="listSafetyEvents",
            responses={401: {"description": "TENANT_CONTEXT_MISSING — thiếu X-Tenant-Id"}})
async def danh_sach_canh_bao(
    tenant_id: TenantIdDep,
    session: SessionDep,
    tu: Annotated[datetime | None, Query(alias="from")] = None,
    den: Annotated[datetime | None, Query(alias="to")] = None,
    limit: int = Query(default=200, ge=1, le=500),
) -> list[SafetyEventItem]:
    """Cảnh báo trong ``[from, to)``, mới nhất trước. Mặc định 30 ngày qua."""
    den = den or datetime.now(UTC)
    tu = tu or den - timedelta(days=30)
    dong = await safety_repository.cac_su_kien(session, tenant_id=tenant_id, tu=tu, den=den, gioi_han=limit)
    return [thanh_su_kien(d) for d in dong]
