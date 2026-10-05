"""[PRODUCTION] Bảng mẫu câu cho các nhánh KHÔNG gọi mô hình ngôn ngữ — UC022 bước 6.

Mỗi lượt trả bằng mẫu câu ở đây là một lượt đóng góp vào KPI ">= 55% lượt không gọi LLM"
(§1.6). Mẫu câu thuộc về AI, không thuộc java-core (đặc tả UC022, ranh giới AI ↔ CRM).
"""

from __future__ import annotations

import unicodedata

from src.ai.orchestrator.router import Branch

_THANKS = ("cam on", "camon", "thank", "tks")
_BYE = ("tam biet", "bye", "goodbye", "hen gap lai", "chao nhe")

GREETING_REPLY = (
    "Dạ em chào anh/chị ạ! Em là trợ lý tư vấn tự động. "
    "Anh/chị cần em hỗ trợ thông tin gì hôm nay ạ?"
)
THANKS_REPLY = "Dạ không có gì ạ! Anh/chị cần thêm thông tin gì cứ nhắn em nhé."
BYE_REPLY = "Dạ em cảm ơn anh/chị đã liên hệ. Chúc anh/chị một ngày tốt lành ạ!"

CLARIFY_REPLY = (
    "Dạ em chưa hiểu rõ ý anh/chị lắm. Anh/chị có thể nói cụ thể hơn giúp em được không ạ? "
    "Ví dụ: hỏi về bảng giá, tính năng sản phẩm, báo lỗi, hay cần gặp nhân viên tư vấn."
)

HANDOFF_REPLY = (
    "Dạ em đã chuyển cuộc trò chuyện cho nhân viên tư vấn. "
    "Anh/chị vui lòng chờ trong giây lát, nhân viên sẽ phản hồi ngay ạ."
)
# TOOL_CALL: ghi đơn/hợp đồng cần người duyệt, bot không tự làm (nhóm MCP đã hoãn).
TOOL_CALL_REPLY = (
    "Dạ cảm ơn anh/chị đã quan tâm! Em đã chuyển yêu cầu cho nhân viên kinh doanh "
    "để hỗ trợ đặt mua và xác nhận thông tin. Anh/chị vui lòng chờ trong giây lát ạ."
)


def _fold(text: str) -> str:
    s = unicodedata.normalize("NFD", text)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()


def small_talk_reply(message: str) -> str:
    """Chọn mẫu câu xã giao theo nội dung: cảm ơn / tạm biệt / chào."""
    t = _fold(message)
    if any(k in t for k in _THANKS):
        return THANKS_REPLY
    if any(k in t for k in _BYE):
        return BYE_REPLY
    return GREETING_REPLY


def template_reply(branch: Branch, message: str) -> str | None:
    """Mẫu câu cho nhánh, hoặc None nếu nhánh cần đường ống khác (RAG)."""
    if branch is Branch.SMALL_TALK:
        return small_talk_reply(message)
    if branch is Branch.CLARIFY:
        return CLARIFY_REPLY
    if branch is Branch.HANDOFF:
        return HANDOFF_REPLY
    if branch is Branch.TOOL_CALL:
        return TOOL_CALL_REPLY
    return None
