"""UC040 bước 8 — đường dẫn ``/v1/safety-events`` phải khớp đúng chỗ java-core gọi. [PRODUCTION]

Lỗi đã gặp khi chạy thật: route khai ``/v1/safety-events`` trong khi ``main.py`` đã gắn tiền tố ``/v1``
→ đường thật thành ``/v1/v1/safety-events``, java-core nhận 404 và màn "Cảnh báo an toàn" báo 503.
Test tích hợp chỉ kiểm tầng đọc DB nên không bắt được — test này khoá đường dẫn.
"""

from src.api.main import create_app


def test_duong_dan_dung_hop_dong_khong_lap_tien_to():
    duong = {getattr(r, "path", "") for r in create_app().routes}
    assert "/v1/safety-events" in duong
    assert "/v1/v1/safety-events" not in duong
