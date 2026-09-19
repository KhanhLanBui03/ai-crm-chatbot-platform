"""Kiểm thử tích hợp — dùng Postgres và Kafka thật qua testcontainers.

Gồm luôn phần kiểm thử đầu-cuối (trước ở ``tests/e2e/``): §3.9.2 chỉ khai ba thư mục
``unit`` · ``integration`` · ``eval`` nên nhánh đầu-cuối gộp vào đây. Nhóm test này chạy
vào ngày tích hợp — Ngày 38 và Ngày 39 của kế hoạch 49 ngày.

Hai bài bắt buộc phải nằm ở đây, không được để trôi:
- ``test_rls.py``   — đọc chéo tenant phải trả rỗng, kể cả khi lấy connection trực tiếp
                      từ pool mà quên đặt tenant (fail-closed). Master Plan §4.3.
- ``test_contract.py`` — chạy ở CI của CẢ HAI phía để bắt lệch hợp đồng. Master Plan §2.8.
"""
