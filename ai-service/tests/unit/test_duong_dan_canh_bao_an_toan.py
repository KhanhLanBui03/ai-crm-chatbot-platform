"""UC040 bước 8 · UC038 bước 7 — đường dẫn java-core gọi phải khớp hợp đồng. [PRODUCTION]

Lỗi đã gặp khi chạy thật: route khai ``/v1/safety-events`` trong khi ``main.py`` đã gắn tiền tố ``/v1``
→ đường thật thành ``/v1/v1/safety-events``, java-core nhận 404 và màn "Cảnh báo an toàn" báo 503.
Test tích hợp chỉ kiểm tầng đọc DB nên không bắt được — test này khoá đường dẫn.

Đọc qua ``app.openapi()["paths"]`` chứ KHÔNG duyệt ``app.routes``: từ FastAPI 0.141, router được gói
thành ``_IncludedRouter`` nên ``app.routes`` không còn phẳng và bản cũ của test này đỏ trên máy Dev A
trong khi đường thật vẫn chạy (báo 10/11/2026). ``openapi()`` là bề mặt công khai, ổn định giữa các
phiên bản — và cũng chính là thứ sinh ra hợp đồng, nên test đo đúng cái java-core đọc.
"""

from src.api.main import create_app

# (đường java-core gọi, use case) — thêm dòng mới ở đây khi mở thêm bề mặt nội bộ
DUONG_NOI_BO = [
    ("/v1/safety-events", "UC040 bước 8 — cảnh báo an toàn"),
    ("/v1/topic-clusters/latest", "UC038 bước 7 — kỳ phân cụm chủ đề"),
]


def test_duong_dan_dung_hop_dong_khong_lap_tien_to():
    duong = set(create_app().openapi()["paths"])
    for mong_doi, uc in DUONG_NOI_BO:
        assert mong_doi in duong, f"{uc}: thiếu {mong_doi} — java-core sẽ nhận 404"
        assert f"/v1{mong_doi}" not in duong, f"{uc}: {mong_doi} bị lặp tiền tố /v1"
