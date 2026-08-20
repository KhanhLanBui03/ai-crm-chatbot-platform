"""Gom mọi endpoint của v1 vào một router.

MẪU. Đặt phiên bản ngay trong đường dẫn (``/v1``) từ đầu: đổi giao ước sau này mà không có
chỗ để tăng phiên bản là tự khoá tay mình.

Gateway định tuyến ``/ai/v1/**`` tới ``lb://ai-service`` và cắt tiền tố ``/ai``
(xem gateway/src/main/resources/application.yml).
"""

from fastapi import APIRouter

api_router = APIRouter()

# TODO: answer, summarize, scoring, documents
# Đặc tả giao ước: docs/openapi/ai-service-to-java-core.yaml (hạn chốt 07/09)
#
# LƯU Ý: health và metrics KHÔNG nằm ở đây. Chúng là bề mặt vận hành, không phải giao ước
# nghiệp vụ, nên không bị đánh phiên bản — xem app/main.py. Docker Compose và Prometheus
# gọi thẳng /health và /metrics.
