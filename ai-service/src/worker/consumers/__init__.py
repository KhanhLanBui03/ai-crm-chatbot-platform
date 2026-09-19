"""Consumer Kafka. Nhóm ingestion-cg tiêu thụ crm.document.v1 để nạp lại chỉ mục.

Chống trùng: sự kiện chắc chắn sẽ đến hơn một lần (giao nhận ít nhất một lần - ADR-0003).
"""
