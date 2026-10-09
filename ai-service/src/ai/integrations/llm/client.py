"""[PRODUCTION] Client LLM không phụ thuộc nhà cung cấp — chuẩn OpenAI chat completions.

Một giao thức, hai hiện thực:

    OpenAICompatLLMClient   POST {LLM_BASE_URL}chat/completions bằng httpx (đã có trong image)
    MockLLMClient           câu trả lời cố định, không mạng — LLM_MODE=mock, CI, test

VÌ SAO CHUẨN OPENAI MÀ KHÔNG DÙNG SDK RIÊNG CỦA NHÀ CUNG CẤP (ADR-0028)
---------------------------------------------------------------------
Gemini, Mistral, OpenRouter, Groq đều phục vụ cùng một hình dạng request này. Đổi nhà cung cấp là
đổi ``LLM_BASE_URL`` + ``LLM_MODEL`` + ``LLM_API_KEY`` trong ``.env``, không sửa dòng code nào, và
không thêm gói nào vào image (đã 776 MB / ngưỡng 400 MB). Đánh đổi: tính năng riêng của từng nhà
cung cấp (bộ nhớ đệm lời nhắc, JSON schema chặt) không dùng được qua lớp tương thích.

PHÂN LOẠI LỖI — ``LLMError.co_the_thu_lai``
------------------------------------------
``429``, ``5xx``, quá hạn, lỗi mạng: nhà cung cấp tạm thời không phục vụ — thử lại có thể qua.
``400``/``401``/``403``/``422``, phản hồi sai định dạng, bị bộ lọc an toàn chặn: thử lại bao nhiêu
lần cũng ra cùng kết quả — thử lại chỉ đốt ngân sách độ trễ và hạn mức.

KHOÁ API KHÔNG BAO GIỜ VÀO LOG: nó chỉ nằm trong header của httpx client; thông điệp lỗi chỉ lấy
mã HTTP và tối đa 200 ký tự thân phản hồi (thân phản hồi lỗi không chứa khoá).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

import httpx

TinNhan = dict[str, str]


@dataclass(frozen=True, slots=True)
class KetQuaLLM:
    noi_dung: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    ly_do_dung: str | None = None


class LLMError(Exception):
    """Một lần gọi hỏng. ``ma`` đi vào log/telemetry, không bao giờ ra người dùng."""

    def __init__(self, ma: str, chi_tiet: str = "", *, co_the_thu_lai: bool) -> None:
        super().__init__(f"{ma}: {chi_tiet}" if chi_tiet else ma)
        self.ma = ma
        self.co_the_thu_lai = co_the_thu_lai


class LLMClient(Protocol):
    model: str

    async def chat(self, messages: Sequence[TinNhan], *, timeout_s: float) -> KetQuaLLM:
        """Một lần gọi, KHÔNG tự thử lại (việc của ``chiu_loi.py``). Hỏng thì ném ``LLMError``."""
        ...

    async def aclose(self) -> None: ...


class OpenAICompatLLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        reasoning_effort: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._reasoning_effort = reasoning_effort
        # transport chỉ để test tiêm httpx.MockTransport; đường production để trống.
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    async def chat(self, messages: Sequence[TinNhan], *, timeout_s: float) -> KetQuaLLM:
        body: dict = {
            "model": self.model,
            "messages": list(messages),
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if self._reasoning_effort:
            body["reasoning_effort"] = self._reasoning_effort

        try:
            resp = await self._http.post("chat/completions", json=body, timeout=timeout_s)
        except httpx.TimeoutException as e:
            raise LLMError("LLM_TIMEOUT", f"quá {timeout_s:.2f} s", co_the_thu_lai=True) from e
        except httpx.TransportError as e:
            raise LLMError("LLM_NETWORK", type(e).__name__, co_the_thu_lai=True) from e

        if resp.status_code == 429 or resp.status_code >= 500:
            raise LLMError(f"LLM_HTTP_{resp.status_code}", resp.text[:200], co_the_thu_lai=True)
        if resp.status_code >= 400:
            raise LLMError(f"LLM_HTTP_{resp.status_code}", resp.text[:200], co_the_thu_lai=False)

        try:
            data = resp.json()
            lua_chon = data["choices"][0]
            noi_dung = lua_chon["message"].get("content")
            usage = data.get("usage") or {}
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
            raise LLMError("LLM_BAD_RESPONSE", resp.text[:200], co_the_thu_lai=False) from e

        ly_do_dung = lua_chon.get("finish_reason")
        if not noi_dung:
            # Bộ lọc an toàn của nhà cung cấp trả lựa chọn rỗng — gửi lại cùng lời nhắc vẫn bị chặn.
            raise LLMError("LLM_EMPTY", f"finish_reason={ly_do_dung}", co_the_thu_lai=False)

        return KetQuaLLM(
            noi_dung=noi_dung,
            model=data.get("model") or self.model,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            ly_do_dung=ly_do_dung,
        )

    async def aclose(self) -> None:
        await self._http.aclose()


class MockLLMClient:
    """LLM giả, không mạng. Câu trả lời cố định trích ``[1]`` — đủ để đi trọn luồng hậu kiểm.

    ``loi`` để test giả lập nhà cung cấp sập: mỗi lần gọi ném đúng lỗi đó.
    """

    MODEL = "mock-llm"
    CAU_TRA_LOI = "Dạ, theo tài liệu của cửa hàng thì thông tin anh/chị cần nằm ở đoạn này [1]."

    def __init__(self, loi: LLMError | None = None, noi_dung: str | None = None) -> None:
        self.model = self.MODEL
        self._loi = loi
        self._noi_dung = noi_dung or self.CAU_TRA_LOI
        self.so_lan_goi = 0

    async def chat(self, messages: Sequence[TinNhan], *, timeout_s: float) -> KetQuaLLM:
        self.so_lan_goi += 1
        if self._loi is not None:
            raise self._loi
        return KetQuaLLM(self._noi_dung, self.MODEL, prompt_tokens=0, completion_tokens=0)

    async def aclose(self) -> None:
        return None
