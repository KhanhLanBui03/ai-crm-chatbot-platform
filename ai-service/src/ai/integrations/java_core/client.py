"""[PRODUCTION] Client gọi bề mặt ``/internal/*`` của java-core — UC026, UC041 (ADR-0002).

Một giao thức, hai hiện thực — cùng khuôn với ``integrations/llm/client.py``:

    HttpJavaCoreClient   httpx tới JAVA_CORE_URL, mỗi request mang X-Tenant-Id + X-Trace-Id
    MockJavaCoreClient   trong bộ nhớ, không mạng — JAVA_CORE_MODE=mock, CI, test, minh chứng

VÌ SAO CÓ BẢN GIẢ LÀM MẶC ĐỊNH (09/10)
--------------------------------------
Ba endpoint dưới đây CHƯA có ở java-core — ``docs/openapi/java-core-to-ai-service.yaml`` mới khai
đường dẫn, thân còn ``# TODO``. Hình dạng request/response chốt ở nháp
``docs/contracts/uc026-uc041-tom-tat-va-xoa-du-lieu.md``; ``HttpJavaCoreClient`` viết ĐÚNG theo
nháp đó và được kiểm bằng ``httpx.MockTransport``. Track A làm xong thì đổi
``JAVA_CORE_MODE=remote``, không sửa dòng code nào ở đây (kế hoạch Ngày 12: "mock lời gọi, ghi
nợ, nối thật ở N18").

    GET    /internal/conversations/{id}/messages   UC026 bước 2 — nạp lịch sử
    PATCH  /internal/conversations/{id}/summary    UC026 bước 4 — ghi bốn phần + phiên bản model
    DELETE /internal/contacts/{id}/lead-scores     UC041 — xoá đặc trưng lead (sales.lead_scores)

ai-service KHÔNG ghi schema ``engagement``/``sales``: ``ai_app`` không có USAGE trên đó (V206), và
đó là lớp chặn cuối nếu mô hình bị tiêm chỉ thị. Mọi thay đổi dữ liệu nghiệp vụ đi qua đây.

``tenant_id`` truyền vào là tenant ĐÃ XÁC THỰC của luồng gọi (header gateway, hoặc vỏ sự kiện
outbox) — client chỉ chuyển tiếp, không bao giờ tự suy ra.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

import httpx

from src.ai.exceptions import JavaCoreUnavailableError
from src.ai.telemetry.logging import trace_id_var

NguoiGui = Literal["CUSTOMER", "BOT", "AGENT", "SYSTEM"]

# Trần số trang khi đọc lịch sử — phòng thủ trước một java-core trả ``totalPages`` sai, không phải
# giới hạn nghiệp vụ: 50 trang × 200 tin là 10.000 tin, hội thoại CSKH thật không tới gần.
_TRANG_TOI_DA = 50
_CO_TRANG = 200


@dataclass(frozen=True, slots=True)
class TinNhanHoiThoai:
    """Một tin nhắn của ``engagement.messages`` (V107) như java-core trả về.

    ``da_che``: tin đã bị che nội dung theo UC041 (``is_redacted``) — KHÔNG được đưa vào lời nhắc.
    """

    nguoi_gui: NguoiGui
    noi_dung: str
    gui_luc: datetime | None = None
    da_che: bool = False


@dataclass(frozen=True, slots=True)
class BanGhiTomTat:
    """Thân ``PATCH …/summary`` — khớp cột V114 (``summary_data`` + ``summary_trigger`` +
    ``summary_model_version`` + ``summarized_at``) và V107 (``summary`` bản phẳng)."""

    trigger: Literal["HANDOFF", "CLOSING", "TURN_THRESHOLD", "MANUAL"]
    main_need: str
    provided_info: str
    unresolved_issues: str
    next_steps: str
    model_version: str
    summary_text: str
    generated_at: datetime

    def thanh_json(self) -> dict:
        return {
            "trigger": self.trigger,
            "mainNeed": self.main_need,
            "providedInfo": self.provided_info,
            "unresolvedIssues": self.unresolved_issues,
            "nextSteps": self.next_steps,
            "modelVersion": self.model_version,
            "summaryText": self.summary_text,
            "generatedAt": self.generated_at.isoformat(),
        }


class JavaCoreClient(Protocol):
    async def lay_tin_nhan(self, tenant_id: str, conversation_id: UUID) -> list[TinNhanHoiThoai]:
        """Toàn bộ lịch sử, cũ trước mới sau. Hội thoại không có / thuộc tenant khác: ``[]``."""
        ...

    async def ghi_tom_tat(
        self, tenant_id: str, conversation_id: UUID, ban_ghi: BanGhiTomTat
    ) -> None:
        """Ghi đè bản tóm tắt mới nhất. LUỸ ĐẲNG: gọi lại cùng thân thì kết quả như một lần."""
        ...

    async def xoa_dac_trung_lead(self, tenant_id: str, contact_id: UUID) -> int:
        """Xoá mọi dòng ``sales.lead_scores`` của khách (chứa vector đặc trưng). Trả số dòng đã
        xoá; LUỸ ĐẲNG — lần hai trả 0."""
        ...

    async def aclose(self) -> None: ...


class HttpJavaCoreClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_s: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        # transport chỉ để test tiêm httpx.MockTransport; đường production để trống.
        self._http = httpx.AsyncClient(base_url=base_url, timeout=timeout_s, transport=transport)

    @staticmethod
    def _header(tenant_id: str) -> dict[str, str]:
        return {"X-Tenant-Id": tenant_id, "X-Trace-Id": trace_id_var.get()}

    async def _goi(self, phuong_thuc: str, duong_dan: str, tenant_id: str, **kw) -> httpx.Response:
        try:
            resp = await self._http.request(
                phuong_thuc, duong_dan, headers=self._header(tenant_id), **kw
            )
        except httpx.TimeoutException as e:
            raise JavaCoreUnavailableError(f"{phuong_thuc} {duong_dan}: quá hạn") from e
        except httpx.TransportError as e:
            raise JavaCoreUnavailableError(
                f"{phuong_thuc} {duong_dan}: {type(e).__name__}"
            ) from e
        if resp.status_code >= 400 and resp.status_code != 404:
            # Không lặp lại thân phản hồi: nó có thể chứa nội dung tin nhắn của khách (NĐ 13).
            raise JavaCoreUnavailableError(f"{phuong_thuc} {duong_dan}: HTTP {resp.status_code}")
        return resp

    @staticmethod
    def _du_lieu(resp: httpx.Response) -> dict:
        """``ApiResponse.data`` của java-core."""
        try:
            data = resp.json()["data"]
        except (ValueError, KeyError, TypeError) as e:
            raise JavaCoreUnavailableError("java-core trả phản hồi sai vỏ ApiResponse") from e
        if not isinstance(data, dict):
            raise JavaCoreUnavailableError("java-core trả ApiResponse.data không phải object")
        return data

    async def lay_tin_nhan(self, tenant_id: str, conversation_id: UUID) -> list[TinNhanHoiThoai]:
        duong_dan = f"/internal/conversations/{conversation_id}/messages"
        ket_qua: list[TinNhanHoiThoai] = []
        for trang in range(_TRANG_TOI_DA):
            resp = await self._goi(
                "GET", duong_dan, tenant_id, params={"page": trang, "size": _CO_TRANG}
            )
            if resp.status_code == 404:
                return []
            data = self._du_lieu(resp)
            try:
                for m in data["items"]:
                    ket_qua.append(
                        TinNhanHoiThoai(
                            nguoi_gui=m["senderType"],
                            noi_dung=m.get("content") or "",
                            gui_luc=(
                                datetime.fromisoformat(m["sentAt"]) if m.get("sentAt") else None
                            ),
                            da_che=bool(m.get("isRedacted", False)),
                        )
                    )
                het = trang + 1 >= int(data["totalPages"])
            except (KeyError, TypeError, ValueError) as e:
                raise JavaCoreUnavailableError("Trang tin nhắn sai lược đồ") from e
            if het:
                break
        return ket_qua

    async def ghi_tom_tat(
        self, tenant_id: str, conversation_id: UUID, ban_ghi: BanGhiTomTat
    ) -> None:
        duong_dan = f"/internal/conversations/{conversation_id}/summary"
        resp = await self._goi("PATCH", duong_dan, tenant_id, json=ban_ghi.thanh_json())
        if resp.status_code == 404:
            # Hội thoại đã bị xoá (UC041) giữa lúc đóng và lúc tóm tắt — không còn gì để ghi.
            raise JavaCoreUnavailableError(f"PATCH {duong_dan}: hội thoại không còn")

    async def xoa_dac_trung_lead(self, tenant_id: str, contact_id: UUID) -> int:
        duong_dan = f"/internal/contacts/{contact_id}/lead-scores"
        resp = await self._goi("DELETE", duong_dan, tenant_id)
        if resp.status_code == 404:
            return 0
        try:
            return int(self._du_lieu(resp)["deleted"])
        except (KeyError, TypeError, ValueError) as e:
            raise JavaCoreUnavailableError("Phản hồi xoá điểm lead sai lược đồ") from e

    async def aclose(self) -> None:
        await self._http.aclose()


@dataclass
class MockJavaCoreClient:
    """java-core giả trong bộ nhớ, theo tenant — đủ để đi trọn UC026/UC041 mà không có java-core.

    ``tin_nhan[(tenant, conversation)]`` là lịch sử trả về; ``tom_tat_da_ghi`` ghi lại mọi lần
    PATCH (test kiểm "đúng một lần"); ``diem_lead[(tenant, contact)]`` là số dòng lead hiện có.
    ``loi`` khác ``None`` thì MỌI lời gọi ném đúng lỗi đó (giả lập java-core sập).
    """

    tin_nhan: dict[tuple[str, UUID], list[TinNhanHoiThoai]] = field(default_factory=dict)
    diem_lead: dict[tuple[str, UUID], int] = field(default_factory=dict)
    tom_tat_da_ghi: list[tuple[str, UUID, BanGhiTomTat]] = field(default_factory=list)
    loi: Exception | None = None

    def nap_hoi_thoai(
        self, tenant_id: str, conversation_id: UUID, cac_tin: Sequence[TinNhanHoiThoai]
    ) -> None:
        self.tin_nhan[(tenant_id, conversation_id)] = list(cac_tin)

    def _kiem_loi(self) -> None:
        if self.loi is not None:
            raise self.loi

    async def lay_tin_nhan(self, tenant_id: str, conversation_id: UUID) -> list[TinNhanHoiThoai]:
        self._kiem_loi()
        return list(self.tin_nhan.get((tenant_id, conversation_id), []))

    async def ghi_tom_tat(
        self, tenant_id: str, conversation_id: UUID, ban_ghi: BanGhiTomTat
    ) -> None:
        self._kiem_loi()
        self.tom_tat_da_ghi.append((tenant_id, conversation_id, ban_ghi))

    async def xoa_dac_trung_lead(self, tenant_id: str, contact_id: UUID) -> int:
        self._kiem_loi()
        return self.diem_lead.pop((tenant_id, contact_id), 0)

    async def aclose(self) -> None:
        return None
