"""Truy cập dữ liệu. Domain gọi repository, không tự viết truy vấn.

Mọi truy vấn vector BẮT BUỘC lọc tenant_id (ADR-0007, bề mặt tấn công T6).
Đã có: chunk · document · processed_event · interaction · feedback. Dự kiến: tool_log_repository.py
"""
