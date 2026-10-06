"""Giải mã sự kiện ``DocumentUploaded`` (``crm.kb.document.uploaded``) — UC018 → UC019. [PRODUCTION]

Vỏ do ``OutboxPublisher.banTin`` của java-core dựng (hợp đồng UC018 mục 6)::

    {"event_id": 42, "event_version": 1, "event_type": "DocumentUploaded",
     "tenant_id": "1111…", "aggregate_id": "5f0c…", "occurred_at": "2026-09-27T…Z",
     "payload": {"document_id": "5f0c…", "version": 2, "source_type": "MD", …}}

Trace ID đi ở HEADER ``X-Trace-Id`` của bản tin, không ở đây (docs/events/README.md, quy ước 3).

``tenant_id`` ở vỏ là ngữ cảnh ĐÃ XÁC THỰC của luồng bất đồng bộ: java-core lấy nó từ JWT lúc
nhận tệp và ghi outbox cùng transaction. Dù vậy nó chỉ được dùng để ĐẶT phiên RLS — sự kiện giả
mang tenant A trỏ vào tài liệu của tenant B sẽ không nhìn thấy tài liệu đó và bị bỏ qua.

Module thuần: không I/O, để test lược đồ không cần Kafka.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.ai.exceptions import EventSchemaInvalidError, EventUnsupportedError

LOAI_SU_KIEN = "DocumentUploaded"
PHIEN_BAN_HO_TRO = frozenset({1})


class _Payload(BaseModel):
    # extra="ignore": java-core thêm trường mới vào payload (không phá tương thích) thì worker cũ
    # vẫn chạy. Phá tương thích thì phải tăng event_version — bị chặn ở dưới.
    model_config = ConfigDict(extra="ignore")

    document_id: UUID


class _Vo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # strict: "42" (chuỗi) là dấu hiệu producer khác đang ghi vào topic — không tự ép kiểu.
    event_id: int = Field(gt=0, strict=True)
    event_version: int = Field(strict=True)
    event_type: str
    tenant_id: UUID
    aggregate_id: UUID
    occurred_at: datetime
    payload: _Payload


@dataclass(frozen=True, slots=True)
class SuKienTaiLieu:
    """Những gì worker cần từ một sự kiện đã kiểm."""

    event_id: int
    tenant_id: str
    document_id: UUID
    occurred_at: datetime


def giai_ma(gia_tri: bytes | None) -> SuKienTaiLieu:
    """Bytes của bản tin → ``SuKienTaiLieu``. Ném ``EVENT_SCHEMA_INVALID`` / ``EVENT_UNSUPPORTED``.

    Thông điệp lỗi KHÔNG lặp lại nội dung bản tin: nó đi vào header DLQ và log, mà bản tin có thể
    chứa dữ liệu người dùng (NĐ 13) — chỉ nêu vị trí và lý do.
    """
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
    if vo.aggregate_id != vo.payload.document_id:
        # Hai chỗ nói về hai tài liệu khác nhau: không đoán cái nào đúng.
        raise EventSchemaInvalidError("aggregate_id khác payload.document_id")

    return SuKienTaiLieu(
        event_id=vo.event_id,
        tenant_id=str(vo.tenant_id),
        document_id=vo.payload.document_id,
        occurred_at=vo.occurred_at,
    )
