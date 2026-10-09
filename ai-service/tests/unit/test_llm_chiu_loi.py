"""Client LLM + circuit breaker + thử lại trong hạn chót — ``src/ai/integrations/llm/``.

Câu hội đồng sẽ hỏi → test làm bằng chứng:

- Ba trạng thái chuyển thế nào? → ``test_breaker_*`` (đồng hồ giả, không ngủ thật)
- HALF_OPEN để làm gì? → ``test_breaker_half_open_chi_cho_mot_luot_tham_do``
- Vì sao không thử lại 400/401/422? → ``test_khong_thu_lai_loi_phia_minh``
- Thử lại có phá ngân sách 2,5 s không? → ``test_qua_han_an_het_ngan_sach_thi_khong_thu_lai``
- Nhà cung cấp sập thì người dùng thấy gì? → ``test_mach_mo_thi_hong_ngay_khong_goi``
"""

import asyncio
import json

import httpx
import pytest

from src.ai.config import Settings
from src.ai.integrations.llm import (
    CircuitBreaker,
    KetQuaLLM,
    LLMChiuLoi,
    LLMError,
    LLMKhongKhaDung,
    MockLLMClient,
    OpenAICompatLLMClient,
    TrangThai,
    tao_llm_client,
)


class _DongHo:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


# ── Circuit breaker: đủ ba trạng thái ────────────────────────────────────────


def test_breaker_closed_mo_sau_du_nguong_hong_lien_tiep():
    dh = _DongHo()
    b = CircuitBreaker(nguong_hong=3, thoi_gian_mo_s=30, dong_ho=dh)
    for _ in range(2):
        assert b.cho_phep()
        b.ghi_that_bai()
    assert b.trang_thai is TrangThai.CLOSED
    b.ghi_that_bai()
    assert b.trang_thai is TrangThai.OPEN
    assert not b.cho_phep()


def test_breaker_thanh_cong_xen_giua_dat_lai_bo_dem():
    b = CircuitBreaker(nguong_hong=3, dong_ho=_DongHo())
    b.ghi_that_bai()
    b.ghi_that_bai()
    b.ghi_thanh_cong()
    b.ghi_that_bai()
    b.ghi_that_bai()
    # "liên tiếp": 2 + 2 hỏng có một thành công xen giữa thì chưa mở
    assert b.trang_thai is TrangThai.CLOSED


def test_breaker_open_het_thoi_gian_thi_sang_half_open():
    dh = _DongHo()
    b = CircuitBreaker(nguong_hong=1, thoi_gian_mo_s=30, dong_ho=dh)
    b.ghi_that_bai()
    dh.t += 29.9
    assert not b.cho_phep() and b.trang_thai is TrangThai.OPEN
    dh.t += 0.1
    assert b.cho_phep()
    assert b.trang_thai is TrangThai.HALF_OPEN


def test_breaker_half_open_chi_cho_mot_luot_tham_do():
    dh = _DongHo()
    b = CircuitBreaker(nguong_hong=1, thoi_gian_mo_s=30, dong_ho=dh)
    b.ghi_that_bai()
    dh.t += 30
    assert b.cho_phep()  # lượt thăm dò
    assert not b.cho_phep()  # các lượt khác vẫn bị chặn tới khi thăm dò có kết quả
    assert not b.cho_phep()


def test_breaker_tham_do_thanh_cong_thi_dong_mach():
    dh = _DongHo()
    b = CircuitBreaker(nguong_hong=1, thoi_gian_mo_s=30, dong_ho=dh)
    b.ghi_that_bai()
    dh.t += 30
    assert b.cho_phep()
    b.ghi_thanh_cong()
    assert b.trang_thai is TrangThai.CLOSED
    assert b.cho_phep() and b.cho_phep()


def test_breaker_tham_do_hong_thi_mo_lai_va_dem_lai_tu_dau():
    dh = _DongHo()
    b = CircuitBreaker(nguong_hong=3, thoi_gian_mo_s=30, dong_ho=dh)
    for _ in range(3):
        b.ghi_that_bai()
    dh.t += 30
    assert b.cho_phep()
    b.ghi_that_bai()  # MỘT lần hỏng ở HALF_OPEN là đủ mở lại, không chờ đủ ngưỡng
    assert b.trang_thai is TrangThai.OPEN
    dh.t += 29
    assert not b.cho_phep()


def test_breaker_luot_tham_do_mat_tich_khong_lam_ket_half_open():
    dh = _DongHo()
    b = CircuitBreaker(nguong_hong=1, thoi_gian_mo_s=30, dong_ho=dh)
    b.ghi_that_bai()
    dh.t += 30
    assert b.cho_phep()  # lượt thăm dò bị huỷ, không bao giờ báo kết quả
    dh.t += 30
    assert b.cho_phep()  # quá hạn ⇒ cho lượt khác thăm dò


# ── OpenAICompatLLMClient qua httpx.MockTransport ────────────────────────────


def _client(handler) -> OpenAICompatLLMClient:
    return OpenAICompatLLMClient(
        base_url="https://llm.test/v1beta/openai/",
        api_key="khoa-bi-mat",
        model="gemini-test",
        reasoning_effort="minimal",
        transport=httpx.MockTransport(handler),
    )


def _tra_loi(noi_dung: str | None = "Dạ [1].", finish: str = "stop") -> dict:
    return {
        "model": "gemini-test-001",
        "choices": [
            {"message": {"role": "assistant", "content": noi_dung}, "finish_reason": finish}
        ],
        "usage": {"prompt_tokens": 120, "completion_tokens": 8},
    }


def test_client_gui_dung_request_va_doc_usage():
    gui: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        gui.append(req)
        return httpx.Response(200, json=_tra_loi())

    kq = asyncio.run(_client(handler).chat([{"role": "user", "content": "x"}], timeout_s=2.5))
    assert kq == KetQuaLLM("Dạ [1].", "gemini-test-001", 120, 8, "stop")
    req = gui[0]
    assert str(req.url) == "https://llm.test/v1beta/openai/chat/completions"
    assert req.headers["authorization"] == "Bearer khoa-bi-mat"
    body = json.loads(req.content)
    assert body["model"] == "gemini-test" and body["temperature"] == 0.0
    assert body["reasoning_effort"] == "minimal"


@pytest.mark.parametrize(
    ("ma_http", "thu_lai"), [(429, True), (500, True), (503, True), (400, False), (401, False),
                            (422, False)]
)
def test_client_phan_loai_loi_http(ma_http: int, thu_lai: bool):
    client = _client(lambda req: httpx.Response(ma_http, text="loi"))
    with pytest.raises(LLMError) as e:
        asyncio.run(client.chat([], timeout_s=1))
    assert e.value.co_the_thu_lai is thu_lai
    assert e.value.ma == f"LLM_HTTP_{ma_http}"
    assert "khoa-bi-mat" not in str(e.value)


def test_client_qua_han_la_loi_thu_lai_duoc():
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("cham", request=req)

    with pytest.raises(LLMError) as e:
        asyncio.run(_client(handler).chat([], timeout_s=0.1))
    assert e.value.ma == "LLM_TIMEOUT" and e.value.co_the_thu_lai


def test_client_bi_bo_loc_chan_thi_khong_thu_lai():
    client = _client(lambda req: httpx.Response(200, json=_tra_loi(None, "content_filter")))
    with pytest.raises(LLMError) as e:
        asyncio.run(client.chat([], timeout_s=1))
    assert e.value.ma == "LLM_EMPTY" and not e.value.co_the_thu_lai


def test_factory_mock_mac_dinh_va_remote_thieu_khoa_thi_nem():
    assert isinstance(tao_llm_client(Settings(llm_mode="mock")), MockLLMClient)
    with pytest.raises(ValueError, match="LLM_API_KEY"):
        tao_llm_client(Settings(llm_mode="remote", llm_api_key=""))


def test_mac_dinh_cua_settings_la_mock_de_ci_khong_dot_luot():
    assert Settings.model_fields["llm_mode"].default == "mock"


# ── LLMChiuLoi: thử lại trong hạn chót + mạch ────────────────────────────────


class _ClientKichBan:
    """Mỗi lần gọi lấy một phần tử: LLMError thì ném, còn lại trả kết quả."""

    model = "kich-ban"

    def __init__(self, *kich_ban, dong_ho: _DongHo | None = None, ton_s: float = 0.0) -> None:
        self.kich_ban = list(kich_ban)
        self.timeouts: list[float] = []
        self.dong_ho, self.ton_s = dong_ho, ton_s

    async def chat(self, messages, *, timeout_s: float) -> KetQuaLLM:
        self.timeouts.append(timeout_s)
        if self.dong_ho is not None:
            self.dong_ho.t += self.ton_s
        buoc = self.kich_ban.pop(0)
        if isinstance(buoc, LLMError):
            raise buoc
        return KetQuaLLM("ok [1]", self.model, 1, 1)

    async def aclose(self) -> None:
        return None


TAM_THOI = LLMError("LLM_HTTP_503", co_the_thu_lai=True)
VINH_VIEN = LLMError("LLM_HTTP_400", co_the_thu_lai=False)
OK = "ok"


def _chiu_loi(client, *, nguong: int = 3, dong_ho=None) -> LLMChiuLoi:
    dh = dong_ho or _DongHo()
    return LLMChiuLoi(
        client, CircuitBreaker(nguong_hong=nguong, dong_ho=dh), han_chot_s=2.5, dong_ho=dh
    )


def test_loi_tam_thoi_thu_lai_mot_lan_thi_qua():
    client = _ClientKichBan(TAM_THOI, OK)
    llm = _chiu_loi(client)
    kq = asyncio.run(llm.chat([]))
    assert kq.noi_dung == "ok [1]" and len(client.timeouts) == 2
    assert llm.breaker.trang_thai is TrangThai.CLOSED


def test_khong_thu_lai_loi_phia_minh():
    client = _ClientKichBan(VINH_VIEN, OK)
    llm = _chiu_loi(client, nguong=1)
    with pytest.raises(LLMKhongKhaDung) as e:
        asyncio.run(llm.chat([]))
    assert len(client.timeouts) == 1 and e.value.ma == "LLM_HTTP_400" and e.value.da_goi
    # Nhà cung cấp đã trả lời ⇒ không tính là hỏng, mạch không mở dù ngưỡng chỉ là 1
    assert llm.breaker.trang_thai is TrangThai.CLOSED


def test_qua_han_an_het_ngan_sach_thi_khong_thu_lai():
    dh = _DongHo()
    qua_han = LLMError("LLM_TIMEOUT", co_the_thu_lai=True)
    client = _ClientKichBan(qua_han, OK, dong_ho=dh, ton_s=2.5)
    with pytest.raises(LLMKhongKhaDung):
        asyncio.run(_chiu_loi(client, dong_ho=dh).chat([]))
    assert client.timeouts == [2.5]  # một lần duy nhất, nhận trọn ngân sách


def test_lan_thu_lai_chi_nhan_phan_ngan_sach_con_lai():
    dh = _DongHo()
    client = _ClientKichBan(TAM_THOI, OK, dong_ho=dh, ton_s=1.0)
    asyncio.run(_chiu_loi(client, dong_ho=dh).chat([]))
    assert client.timeouts[0] == 2.5
    assert client.timeouts[1] == pytest.approx(1.5)


def test_mach_mo_thi_hong_ngay_khong_goi():
    client = _ClientKichBan(*([TAM_THOI] * 6))
    llm = _chiu_loi(client, nguong=3)
    for _ in range(3):
        with pytest.raises(LLMKhongKhaDung):
            asyncio.run(llm.chat([]))
    # Ba request hỏng (mỗi request 2 lần gọi) ⇒ ba lần ghi vào mạch, không phải sáu
    assert llm.breaker.trang_thai is TrangThai.OPEN
    so_lan_goi = len(client.timeouts)
    with pytest.raises(LLMKhongKhaDung) as e:
        asyncio.run(llm.chat([]))
    assert e.value.ma == "CIRCUIT_OPEN" and not e.value.da_goi
    assert len(client.timeouts) == so_lan_goi
