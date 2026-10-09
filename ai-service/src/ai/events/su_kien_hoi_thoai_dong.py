"""Giải mã sự kiện ``ConversationClosed`` (``crm.conversation.closed``) — UC026. [PRODUCTION]

Lược đồ: ``docs/events/crm.conversation.closed.v1.json``. Vỏ do ``OutboxPublisher.banTin`` của
java-core dựng, cùng hình với ``DocumentUploaded``::

    {"event_id": 77, "event_version": 1, "event_type": "ConversationClosed",
     "tenant_id": "1111…", "aggregate_id": "9c2e…", "occurred_at": "2026-10-09T…Z",
     "payload": {"conversation_id": "9c2e…", "closed_by": "…", "closed_at": "…", …}}

Worker CHỈ cần ``conversation_id``: lịch sử tin nhắn đọc qua ``/internal`` của java-core, không
chở trong sự kiện — sự kiện nằm trên Kafka 7 ngày, và nội dung tin nhắn là dữ liệu cá nhân (NĐ 13).
``closed_by`` lược đồ ghi bắt buộc nhưng worker không đọc: hội thoại do hệ thống tự đóng không có
người đóng — nháp hợp đồng Ngày 12 đề xuất nới thành tuỳ chọn.

``tenant_id`` ở vỏ chỉ dùng để ĐẶT ngữ cảnh: mọi lời gọi java-core mang nó làm ``X-Tenant-Id`` và
java-core lọc theo RLS — sự kiện giả mang tenant A trỏ vào hội thoại của tenant B nhận về ``[]``.

Module thuần: không I/O, để test lược đồ không cần Kafka.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.ai.exceptions import EventSchemaInvalidError, EventUnsupportedError

LOAI_SU_KIEN = "ConversationClosed"
PHIEN_BAN_HO_TRO = frozenset({1})


class _Payload(BaseModel):
    # extra="ignore": java-core thêm trường mới (không phá tương thích) thì worker cũ vẫn chạy.
    model_config = ConfigDict(extra="ignore")

    conversation_id: UUID


class _Vo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # strict: "77" (chuỗi) là dấu hiệu producer khác đang ghi vào topic — không tự ép kiểu.
    event_id: int = Field(gt=0, strict=True)
    event_version: int = Field(strict=True)
    event_type: str
    tenant_id: UUID
    # Lược đồ để tuỳ chọn; có mặt thì phải khớp payload.
    aggregate_id: UUID | None = None
    occurred_at: datetime
    payload: _Payload


@dataclass(frozen=True, slots=True)
class SuKienHoiThoaiDong:
    event_id: int
    tenant_id: str
    conversation_id: UUID
    occurred_at: datetime


def giai_ma(gia_tri: bytes | None) -> SuKienHoiThoaiDong:
    """Bytes của bản tin → ``SuKienHoiThoaiDong``. Ném ``EVENT_SCHEMA_INVALID`` /
    ``EVENT_UNSUPPORTED``. Thông điệp lỗi không lặp lại nội dung bản tin (đi vào header DLQ)."""
    if not gia_tri:
        raise EventSchemaInvalidError("Bản tin rỗng")
    try:
        du_lieu = json.loads(gia_tri)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise EventSchemaInvalidError(f"Không phải JSON: {type(e).__name__}") from e
    if not isinstance(du_lieu, dict):
        raise EventSchemaInvalidError("Vỏ sự kiện phải là object JSON")

    try:
        vo = _Vo.model_validate(du_lieu)
    except ValidationError as e:
        vi_tri = "; ".join(
            f"{'.'.join(str(p) for p in loi['loc'])}: {loi['type']}" for loi in e.errors()
        )
        raise EventSchemaInvalidError(f"Sai lược đồ — {vi_tri}") from e

    if vo.event_type != LOAI_SU_KIEN:
        raise EventUnsupportedError(f"event_type {vo.event_type!r} chưa hỗ trợ")
    if vo.event_version not in PHIEN_BAN_HO_TRO:
        raise EventUnsupportedError(f"event_version {vo.event_version} chưa hỗ trợ")
    if vo.aggregate_id is not None and vo.aggregate_id != vo.payload.conversation_id:
        raise EventSchemaInvalidError("aggregate_id khác payload.conversation_id")

    return SuKienHoiThoaiDong(
        event_id=vo.event_id,
        tenant_id=str(vo.tenant_id),
        conversation_id=vo.payload.conversation_id,
        occurred_at=vo.occurred_at,
    )
