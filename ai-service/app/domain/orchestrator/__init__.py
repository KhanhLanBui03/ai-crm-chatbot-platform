"""Đồ thị LangGraph — điều phối đa nhánh.

Quyết định câu hỏi đi nhánh nào: RAG (tri thức tĩnh), Tool qua MCP (trạng thái động),
hỏi lại (thiếu ngữ cảnh), hay chuyển giao nhân viên. Ranh giới RAG/Tool: kế hoạch mục 7.3.

Độ chính xác định tuyến được đo như một chỉ số ĐỘC LẬP, tách khỏi độ chính xác câu trả lời
— vì chọn sai nhánh tạo ra lỗi nguy hiểm nhất: sai một cách rất thuyết phục. Thí nghiệm E5.

Module dự kiến: graph.py, nodes.py, edges.py, state.py, router.py
"""
