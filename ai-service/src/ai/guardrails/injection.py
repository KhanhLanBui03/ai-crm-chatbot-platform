"""[PRODUCTION] Phát hiện tiêm chỉ thị (Prompt Injection) — Master Plan §4.8 & UC022.

Ràng buộc (§3.9.2, Master Plan):
- Thuần Python, không model, không gọi mạng (độ trễ < 0.2 ms, chi phí 0đ).
- Chạy TRƯỚC LLM trên 100% lượt chat.
- Ngưỡng chấp nhận: Chặn >= 90% bộ adversarial, báo nhầm trên câu hỏi bình thường < 1%.
- KHÔNG CHẶN LUỒNG: Phát hiện tiêm chỉ thị thì ghi safety_flag="PROMPT_INJECTION_INPUT"
  rồi vẫn tiếp tục định tuyến bình thường (UC022 5.2).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SAFETY_FLAG_INJECTION = "PROMPT_INJECTION_INPUT"

# ══════════════════════════════════════════════════════════════════════════════
# BỘ MẪU TIÊM CHỈ THỊ (PROMPT INJECTION PATTERNS)
# Thiết kế chặt chẽ tránh BÁO NHẦM (False Positive < 1%) trên câu hỏi khách hàng thật
# ══════════════════════════════════════════════════════════════════════════════

# 1. Ghi đè chỉ thị / Bỏ qua hướng dẫn hệ thống
_INSTRUCTION_OVERRIDE_PATTERNS = [
    # Tiếng Anh
    r"(?i)\b(?:ignore|disregard|forget|bypass|override|drop)\s+(?:all\s+)?(?:previous|prior|above|system|initial)\s+(?:instructions|prompts?|rules|directives|constraints)\b",
    r"(?i)\b(?:do\s+not|don'?t)\s+follow\s+(?:any\s+)?(?:previous|prior|system)\s+(?:instructions|rules|prompts?)\b",
    # Tiếng Việt
    r"(?i)\b(?:bỏ\s+qua|quên|bỏ|xoá|hủy)\s+(?:toàn\s+bộ\s+|hết\s+)?(?:các\s+|mọi\s+)?(?:chỉ\s+thị|hướng\s+dẫn|quy\s+tắc|câu\s+lệnh|ràng\s+buộc|yêu\s+cầu|prompt)\s+(?:trước|ở\s+trên|ban\s+đầu|hệ\s+thống|cũ)\b",
    r"(?i)\b(?:không\s+cần|đừng)\s+tuân\s+theo\s+(?:các\s+|mọi\s+)?(?:hướng\s+dẫn|quy\s+tắc|chỉ\s+thị)\s+(?:trước|cũ|hệ\s+thống)\b",
]

# 2. Thay đổi vai trò bất hợp pháp / Jailbreak / DAN Mode
_ROLE_HIJACKING_PATTERNS = [
    r"(?i)\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(?:an?\s+)?(?:unfiltered|unrestricted|jailbroken|evil|unconstrained)\s+(?:ai|assistant|model|bot)\b",
    r"(?i)\b(?:bạn\s+là\s+|hãy\s+đóng\s+vai\s+(?:là\s+)?|từ\s+bây\s+giờ\s+hãy\s+là\s+)(?:một\s+)?(?:ai|bot|trợ\s+lý)\s+(?:không\s+giới\s+hạn|bị\s+bẻ\s+khóa|không\s+kiểm\s+duyệt|vô\s+hạn|độc\s+hại)\b",
    r"(?i)\b(?:dan\s+mode|jailbreak\s+mode|chế\s+độ\s+bẻ\s+khóa|developer\s+mode\s+(?:enable|on|active))\b",
    r"(?i)\b(?:do\s+anything\s+now|bỏ\s+qua\s+(?:rào\s+cản|chính\s+sách)\s+(?:đạo\s+đức|an\s+toàn))\b",
]

# 3. Ký tự phân cách cấu trúc hệ thống (System Delimiters / Special Tokens Injection)
_SYSTEM_DELIMITER_PATTERNS = [
    r"(?i)(?:###\s*(?:system|instruction|human|assistant)\s*:)",
    r"(?i)(?:\[(?:INST|/INST|SYS|/SYS)\])",
    r"(?i)(?:<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|assistant\|>|<\|user\|>)",
    r"(?i)(?:\"role\"\s*:\s*\"system\"\s*,\s*\"content\"\s*:)",
    r"(?i)(?:<<SYS>>|<<\/SYS>>)",
]

# 4. Thăm dò và trích xuất câu lệnh hệ thống (System Prompt Exfiltration)
_EXFILTRATION_PATTERNS = [
    r"(?i)\b(?:output|print|display|reveal|show|repeat)\s+(?:your\s+)?(?:full\s+|exact\s+)?(?:system\s+prompt|initial\s+instructions|system\s+instructions|hidden\s+prompt)\b",
    r"(?i)\b(?:repeat\s+(?:all(?:\s+(?:words|text|instructions?))?|everything)\s+.*?\b(?:above|from\s+the\s+beginning))\b",
    r"(?i)\b(?:in\s+ra|hiển\s+thị|tiết\s+lộ|đọc\s+cho\s+tôi|nhắc\s+lại)\s+(?:toàn\s+bộ\s+)?(?:prompt\s+hệ\s+thống|câu\s+lệnh\s+hệ\s+thống|chỉ\s+thị\s+ban\s+đầu|system\s+prompt)\b",
    r"(?i)\b(?:lặp\s+lại\s+(?:toàn\s+bộ|tất\s+cả)\s+(?:các\s+từ\s+|nội\s+dung\s+)?(?:ở\s+trên|phía\s+trên))\b",
]

# 5. Dò tìm và khai thác dữ liệu nền tảng / Tenant Probing
_DATA_PROBING_PATTERNS = [
    r"(?i)\b(?:access|dump|export|leak)\s+(?:all\s+)?(?:other\s+tenants?|all\s+tenants?|database\s+credentials|secret_key)\b",
    r"(?i)\b(?:truy\s+cập|lấy|đọc|xuất|trích\s+xuất|xem|tải)\s+(?:dữ\s+liệu|thông\s+tin)\s+(?:của\s+)?(?:doanh\s+nghiệp\s+khác|tenant\s+khác|toàn\s+bộ\s+khách\s+hàng\s+khác)\b",
    r"(?i)\b(?:SELECT\s+.*FROM\s+.*(?:tenants|users|auth|audit_logs)|UNION\s+SELECT|DROP\s+TABLE)\b",
]

_ALL_PATTERNS = [
    ("INSTRUCTION_OVERRIDE", [re.compile(p) for p in _INSTRUCTION_OVERRIDE_PATTERNS]),
    ("ROLE_HIJACKING", [re.compile(p) for p in _ROLE_HIJACKING_PATTERNS]),
    ("SYSTEM_DELIMITER", [re.compile(p) for p in _SYSTEM_DELIMITER_PATTERNS]),
    ("EXFILTRATION", [re.compile(p) for p in _EXFILTRATION_PATTERNS]),
    ("DATA_PROBING", [re.compile(p) for p in _DATA_PROBING_PATTERNS]),
]


@dataclass(frozen=True)
class InjectionResult:
    is_injected: bool
    safety_flag: str | None
    matched_category: str | None
    matched_snippet: str | None


def detect_injection(text: str) -> InjectionResult:
    """Phát hiện dấu vết tiêm chỉ thị trong câu nói người dùng.
    
    Quy tắc nghiệp vụ:
    - Thuần Python, chạy dưới 0.2 ms.
    - Nếu phát hiện tiêm: Trả về cờ PROMPT_INJECTION_INPUT (khớp CSDL V208).
    - KHÔNG ném ngoại lệ hay dừng luồng: Tầng orchestrator sẽ ghi nhận cờ này vào
      bản ghi ai_interactions và tiếp tục quy trình định tuyến bình thường.
    """
    if not text:
        return InjectionResult(
            is_injected=False,
            safety_flag=None,
            matched_category=None,
            matched_snippet=None,
        )

    # Duyệt qua các danh mục tấn công
    for category, regex_list in _ALL_PATTERNS:
        for r in regex_list:
            match = r.search(text)
            if match:
                return InjectionResult(
                    is_injected=True,
                    safety_flag=SAFETY_FLAG_INJECTION,
                    matched_category=category,
                    matched_snippet=match.group(0)[:100],
                )

    return InjectionResult(
        is_injected=False,
        safety_flag=None,
        matched_category=None,
        matched_snippet=None,
    )
