"""[PRODUCTION] Phát hiện tiêm chỉ thị (Prompt Injection) — Master Plan §4.8 & UC022.

Ràng buộc (§3.9.2, Master Plan):
- Thuần Python, không model, không gọi mạng (độ trễ < 0.2 ms, chi phí 0đ).
- Chạy TRƯỚC LLM trên 100% lượt chat.
- Ngưỡng chấp nhận: Chặn >= 90% bộ adversarial, báo nhầm trên câu hỏi bình thường < 1%.
- KHÔNG CHẶN LUỒNG: Phát hiện tiêm chỉ thị thì ghi safety_flag="PROMPT_INJECTION_INPUT"
  rồi vẫn tiếp tục định tuyến bình thường (UC022 5.2).

So khớp trên bản ĐÃ BỎ DẤU, viết thường (``_fold``): 20% lượt chat là tiếng Việt không dấu,
mẫu viết có dấu thì "bo qua cac huong dan truoc" lọt hoàn toàn. Vì thế mọi mẫu dưới đây
viết không dấu, chữ thường.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

SAFETY_FLAG_INJECTION = "PROMPT_INJECTION_INPUT"

# Cho phép tối đa N từ chen giữa động từ và tân ngữ: "ignore ALL THE previous instructions",
# "bo qua TAT CA huong dan truoc". Giới hạn cứng để regex không quét cả đoạn văn dài.
_GAP2 = r"(?:\w+\s+){0,2}?"
_GAP3 = r"(?:\w+\s+){0,3}?"

# ══════════════════════════════════════════════════════════════════════════════
# BỘ MẪU TIÊM CHỈ THỊ (PROMPT INJECTION PATTERNS) — viết KHÔNG DẤU, chữ thường
# Thiết kế chặt chẽ tránh BÁO NHẦM (False Positive < 1%) trên câu hỏi khách hàng thật
# ══════════════════════════════════════════════════════════════════════════════

# 1. Ghi đè chỉ thị / Bỏ qua hướng dẫn hệ thống
_INSTRUCTION_OVERRIDE_PATTERNS = [
    # Tiếng Anh
    rf"\b(?:ignore|disregard|forget|bypass|override)\s+{_GAP3}(?:previous|prior|above|earlier|system|initial|original)\s+{_GAP2}(?:instructions?|prompts?|rules|directives|constraints|guidelines)\b",
    r"\b(?:ignore|disregard|forget)\s+(?:everything|all)\s+(?:above|before|previously|you\s+were\s+told)\b",
    rf"\b(?:do\s+not|don'?t)\s+follow\s+{_GAP2}(?:previous|prior|system|original)\s+(?:instructions?|rules|prompts?)\b",
    # Tiếng Việt — tân ngữ "mạnh" (chỉ thị, prompt, ràng buộc): động từ nào cũng tính.
    # KHÔNG có "yêu cầu": "cho em hủy yêu cầu trước đó" là câu khách hàng hợp lệ.
    rf"\b(?:bo\s+qua|quen|bo|xoa|huy|phot\s+lo|vo\s+hieu\s+hoa)\s+{_GAP3}(?:chi\s+thi|prompt|rang\s+buoc|cau\s+lenh\s+he\s+thong)\s+{_GAP2}(?:truoc|o\s+tren|phia\s+tren|ban\s+dau|he\s+thong|cu|goc)\b",
    # Tân ngữ "yếu" (hướng dẫn, quy tắc): khách vẫn nói "em quên hướng dẫn cũ rồi" —
    # chỉ tính khi động từ mang nghĩa phớt lờ, không tính "quên".
    rf"\b(?:bo\s+qua|phot\s+lo|vo\s+hieu\s+hoa)\s+{_GAP3}(?:huong\s+dan|quy\s+tac)\s+{_GAP2}(?:truoc|o\s+tren|phia\s+tren|ban\s+dau|he\s+thong|cu|goc)\b",
    rf"\b(?:khong\s+can|dung|khong\s+phai)\s+tuan\s+theo\s+{_GAP2}(?:huong\s+dan|quy\s+tac|chi\s+thi)\s+{_GAP2}(?:truoc|cu|he\s+thong|ban\s+dau)\b",
]

# 2. Thay đổi vai trò bất hợp pháp / Jailbreak / DAN Mode
_ROLE_HIJACKING_PATTERNS = [
    rf"\b(?:you\s+are\s+now|act\s+as|pretend\s+(?:to\s+be|you\s+are))\s+{_GAP2}(?:unfiltered|unrestricted|jailbroken|evil|unconstrained|uncensored)\b",
    r"\b(?:ban\s+la|hay\s+dong\s+vai(?:\s+la)?|tu\s+bay\s+gio\s+(?:hay\s+la|ban\s+la))\s+(?:mot\s+)?(?:ai|bot|tro\s+ly|chatbot)\s+(?:khong\s+gioi\s+han|bi\s+be\s+khoa|khong\s+kiem\s+duyet|vo\s+han|doc\s+hai|khong\s+bi\s+rang\s+buoc)\b",
    r"\b(?:dan\s+mode|jailbreak\s+mode|che\s+do\s+be\s+khoa|developer\s+mode\s+(?:enabled?|on|active))\b",
    r"\b(?:do\s+anything\s+now|bo\s+qua\s+(?:rao\s+can|chinh\s+sach|bo\s+loc)\s+(?:dao\s+duc|an\s+toan|kiem\s+duyet))\b",
]

# 3. Ký tự phân cách cấu trúc hệ thống (System Delimiters / Special Tokens Injection)
_SYSTEM_DELIMITER_PATTERNS = [
    r"###\s*(?:system|instruction|human|assistant)\s*:",
    r"\[(?:inst|/inst|sys|/sys)\]",
    r"<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|assistant\|>|<\|user\|>",
    r"\"role\"\s*:\s*\"system\"\s*,\s*\"content\"\s*:",
    r"<<sys>>|<</sys>>",
]

# 4. Thăm dò và trích xuất câu lệnh hệ thống (System Prompt Exfiltration)
_EXFILTRATION_PATTERNS = [
    rf"\b(?:output|print|display|reveal|show|repeat|tell\s+me)\s+{_GAP2}(?:system\s+prompt|initial\s+instructions|system\s+instructions|hidden\s+prompt|original\s+prompt)\b",
    r"\brepeat\s+(?:all(?:\s+(?:the\s+)?(?:words|text|instructions?))?|everything)\s+.*?\b(?:above|from\s+the\s+beginning)\b",
    rf"\b(?:in\s+ra|hien\s+thi|tiet\s+lo|doc\s+cho\s+(?:toi|tao|minh)|nhac\s+lai|cho\s+(?:toi|tao|minh)\s+xem)\s+{_GAP3}(?:prompt\s+he\s+thong|cau\s+lenh\s+he\s+thong|chi\s+thi\s+(?:ban\s+dau|he\s+thong)|system\s+prompt)\b",
    r"\blap\s+lai\s+(?:toan\s+bo|tat\s+ca)\s+(?:cac\s+tu\s+|noi\s+dung\s+)?(?:o\s+tren|phia\s+tren)\b",
]

# 5. Dò tìm và khai thác dữ liệu nền tảng / Tenant Probing
_DATA_PROBING_PATTERNS = [
    r"\b(?:access|dump|export|leak)\s+(?:all\s+)?(?:other\s+tenants?|all\s+tenants?|database\s+credentials|secret_key)\b",
    r"\b(?:truy\s+cap|lay|doc|xuat|trich\s+xuat|xem|tai)\s+(?:du\s+lieu|thong\s+tin)\s+(?:cua\s+)?(?:doanh\s+nghiep\s+khac|tenant\s+khac|toan\s+bo\s+khach\s+hang\s+khac)\b",
    r"\b(?:select\s+.*\bfrom\s+.*(?:tenants|users|auth|audit_logs)|union\s+select|drop\s+table)\b",
]

_ALL_PATTERNS = [
    ("INSTRUCTION_OVERRIDE", [re.compile(p) for p in _INSTRUCTION_OVERRIDE_PATTERNS]),
    ("ROLE_HIJACKING", [re.compile(p) for p in _ROLE_HIJACKING_PATTERNS]),
    ("SYSTEM_DELIMITER", [re.compile(p) for p in _SYSTEM_DELIMITER_PATTERNS]),
    ("EXFILTRATION", [re.compile(p) for p in _EXFILTRATION_PATTERNS]),
    ("DATA_PROBING", [re.compile(p) for p in _DATA_PROBING_PATTERNS]),
]

_WHITESPACE = re.compile(r"\s+")


def _fold(text: str) -> str:
    """Bỏ dấu tiếng Việt, viết thường, gộp khoảng trắng: "Bỏ  Qua" -> "bo qua"."""
    s = unicodedata.normalize("NFD", text)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D").lower()
    return _WHITESPACE.sub(" ", s)


@dataclass(frozen=True)
class InjectionResult:
    is_injected: bool
    safety_flag: str | None
    matched_category: str | None
    matched_snippet: str | None


_CLEAN = InjectionResult(
    is_injected=False,
    safety_flag=None,
    matched_category=None,
    matched_snippet=None,
)


def detect_injection(text: str) -> InjectionResult:
    """Phát hiện dấu vết tiêm chỉ thị trong câu nói người dùng.

    Quy tắc nghiệp vụ:
    - Thuần Python, chạy dưới 0.2 ms.
    - Nếu phát hiện tiêm: Trả về cờ PROMPT_INJECTION_INPUT (khớp CSDL V208).
    - KHÔNG ném ngoại lệ hay dừng luồng: Tầng orchestrator sẽ ghi nhận cờ này vào
      bản ghi ai_interactions và tiếp tục quy trình định tuyến bình thường.
    - ``matched_snippet`` là đoạn khớp ở dạng đã bỏ dấu.
    """
    if not text:
        return _CLEAN

    folded = _fold(text)
    for category, regex_list in _ALL_PATTERNS:
        for r in regex_list:
            match = r.search(folded)
            if match:
                return InjectionResult(
                    is_injected=True,
                    safety_flag=SAFETY_FLAG_INJECTION,
                    matched_category=category,
                    matched_snippet=match.group(0)[:100],
                )

    return _CLEAN
