"""Nhà cung cấp mô hình ngôn ngữ — client trung lập theo chuẩn OpenAI chat completions (ADR-0028).

temperature = 0 và ghim phiên bản mô hình — bắt buộc để tái lập thí nghiệm (mục 8.1).

    client.py           giao thức LLMClient + OpenAICompatLLMClient + MockLLMClient
    circuit_breaker.py  máy trạng thái CLOSED → OPEN → HALF_OPEN (thuần, không I/O)
    chiu_loi.py         thử lại trong hạn chót + mạch ⇒ KetQuaLLM hoặc LLMKhongKhaDung
"""

from src.ai.config import Settings, get_settings
from src.ai.integrations.llm.chiu_loi import LLMChiuLoi, LLMKhongKhaDung
from src.ai.integrations.llm.circuit_breaker import CircuitBreaker, TrangThai
from src.ai.integrations.llm.client import (
    KetQuaLLM,
    LLMClient,
    LLMError,
    MockLLMClient,
    OpenAICompatLLMClient,
)


def tao_llm_client(settings: Settings | None = None) -> LLMClient:
    """Chọn hiện thực theo ``LLM_MODE``. Thiếu khoá ở chế độ remote thì ném ngay lúc khởi động."""
    settings = settings or get_settings()
    if settings.llm_mode == "mock":
        return MockLLMClient()
    if not settings.llm_api_key:
        raise ValueError("LLM_MODE=remote nhưng LLM_API_KEY trống — điền khoá vào ai-service/.env")
    return OpenAICompatLLMClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        reasoning_effort=settings.llm_reasoning_effort,
    )


def tao_llm_chiu_loi(settings: Settings | None = None) -> LLMChiuLoi:
    settings = settings or get_settings()
    return LLMChiuLoi(
        tao_llm_client(settings),
        CircuitBreaker(
            nguong_hong=settings.llm_breaker_nguong_hong,
            thoi_gian_mo_s=settings.llm_breaker_thoi_gian_mo_s,
        ),
        han_chot_s=settings.llm_timeout_s,
    )


__all__ = [
    "CircuitBreaker",
    "KetQuaLLM",
    "LLMChiuLoi",
    "LLMClient",
    "LLMError",
    "LLMKhongKhaDung",
    "MockLLMClient",
    "OpenAICompatLLMClient",
    "TrangThai",
    "tao_llm_chiu_loi",
    "tao_llm_client",
]
