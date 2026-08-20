"""Kết nối và mô hình ORM.

Chỉ ba schema Track B sở hữu: knowledge, ai, integration. Tuyệt đối không ánh xạ bảng của
Track A (platform, engagement, sales, analytics) vào đây — mọi thao tác với chúng đi qua
app/integrations/java_core/ (ADR-0002).
"""
