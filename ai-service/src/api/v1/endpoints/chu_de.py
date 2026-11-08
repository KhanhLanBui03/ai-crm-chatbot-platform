"""Kỳ phân cụm chủ đề mới nhất — UC038 bước 7 (phần Track B). [PRODUCTION]

``GET /v1/topic-clusters/latest`` — java-core gọi trong mạng nội bộ rồi ghép với số liệu từ chối nó tự
cộng ở ``analytics.topic_conversations`` (V138). Gateway CHẶN đường này từ bên ngoài
(``/ai/v1/topic-clusters/**``): ai-service không kiểm vai trò người dùng, mà thống kê chủ đề chỉ dành cho
quản trị viên.

``tenant_id`` lấy từ ``X-Tenant-Id`` (luật 1), không bao giờ từ tham số.
"""

from fastapi import APIRouter, Response

from src.ai.clustering import kho
from src.ai.schemas import TopicClusterRun
from src.api.deps import SessionDep, TenantIdDep

router = APIRouter(tags=["chu-de"])


@router.get("/topic-clusters/latest", response_model=TopicClusterRun, operation_id="getLatestTopicClusters",
            responses={204: {"description": "Doanh nghiệp chưa có kỳ phân cụm nào"},
                       401: {"description": "TENANT_CONTEXT_MISSING — thiếu X-Tenant-Id"}})
async def ky_moi_nhat(tenant_id: TenantIdDep, session: SessionDep) -> TopicClusterRun | Response:
    ky = await kho.ky_moi_nhat(session, tenant_id)
    if ky is None:
        return Response(status_code=204)
    silhouette = ky.pop("silhouette")
    return TopicClusterRun(run_id=ky.pop("id"), silhouette=float(silhouette) if silhouette is not None else None, **ky)
