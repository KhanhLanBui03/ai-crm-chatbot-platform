"""MCP Client — khám phá và gọi tool trên hệ thống nghiệp vụ ngoài (ADR-0005).

Máy chủ giả lập nằm ở REPOSITORY RIÊNG mcp-server-mock — cố ý tách để chứng minh nó là
hệ thống ngoài, không thuộc CRM.

Lớp bảo vệ (bề mặt tấn công T4 trong docs/threat-model.md):
- danh sách tool cho phép theo tenant
- risk_level và requires_confirmation trên từng tool
- kiểm tra đối số trước khi gọi
- ghi kiểm toán mọi lượt gọi vào integration.TOOL_CALL_LOGS

Ghim spec_version — đặc tả MCP đang tiến hóa nhanh.
Thí nghiệm E9: Attack Success Rate, bật lần lượt từng lớp phòng thủ.

Module dự kiến: client.py, discovery.py, registry.py, guard.py, audit.py
"""
