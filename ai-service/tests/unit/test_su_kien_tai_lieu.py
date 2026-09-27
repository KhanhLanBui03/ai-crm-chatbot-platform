"""Giải mã ``DocumentUploaded`` — ``src/ai/events/su_kien_tai_lieu.py`` + header DLQ."""

import json
from uuid import uuid4

import pytest

from src.ai.events.dlq import doc_header, dung_header_dlq
from src.ai.events.su_kien_tai_lieu import giai_ma
from src.ai.exceptions import EventSchemaInvalidError, EventUnsupportedError

TENANT = "11111111-1111-1111-1111-111111111111"


def _vo(**sua) -> dict:
    doc = str(uuid4())
    vo = {
        "event_id": 42, "event_version": 1, "event_type": "DocumentUploaded",
        "tenant_id": TENANT, "aggregate_id": doc, "occurred_at": "2026-09-27T08:00:00Z",
        "payload": {"document_id": doc, "version": 1, "source_type": "MD",
                    "mime_type": "text/markdown", "size_bytes": 10, "language": "vi",
                    "uploaded_by": None},
    }
    vo.update(sua)
    return vo


def _b(vo) -> bytes:
    return json.dumps(vo).encode()


def test_vo_dung_khuon_java_core():
    vo = _vo()
    sk = giai_ma(_b(vo))
    assert (sk.event_id, sk.tenant_id, str(sk.document_id)) == (42, TENANT, vo["aggregate_id"])


def test_truong_la_trong_payload_bi_bo_qua():
    """java-core thêm trường mới (không phá tương thích) thì worker cũ vẫn chạy."""
    vo = _vo()
    vo["payload"]["truong_moi"] = "x"
    assert giai_ma(_b(vo)).event_id == 42


@pytest.mark.parametrize(
    "gia_tri",
    [
        None,
        b"",
        b"khong phai json",
        b"\xff\xfe",
        b"[1, 2]",
        _b(_vo(tenant_id="khong-phai-uuid")),
        _b(_vo(event_id="42")),         # chuỗi — không tự ép kiểu
        _b(_vo(event_id=0)),
        _b({k: v for k, v in _vo().items() if k != "tenant_id"}),
        _b(_vo(payload={})),
        _b(_vo(aggregate_id=str(uuid4()))),  # vỏ và payload nói về hai tài liệu
    ],
)
def test_sai_luoc_do_thi_event_schema_invalid(gia_tri):
    with pytest.raises(EventSchemaInvalidError):
        giai_ma(gia_tri)


@pytest.mark.parametrize("sua", [{"event_type": "DocumentDeleted"}, {"event_version": 2}])
def test_loai_hoac_phien_ban_la_thi_event_unsupported(sua):
    with pytest.raises(EventUnsupportedError):
        giai_ma(_b(_vo(**sua)))


def test_thong_diep_loi_khong_lap_lai_noi_dung_ban_tin():
    """Thông điệp đi vào header DLQ và log — không được chép dữ liệu người dùng (NĐ 13)."""
    vo = _vo(tenant_id="ten-khach-hang-bi-mat")
    with pytest.raises(EventSchemaInvalidError) as loi:
        giai_ma(_b(vo))
    assert "bi-mat" not in str(loi.value)


def test_header_dlq_giu_header_goc_va_thay_dlq_cu():
    goc = [("X-Trace-Id", b"trace-1"), ("dlq.error_code", b"CU")]
    h = dung_header_dlq(
        goc, topic="crm.kb.document.uploaded", partition=2, offset=17,
        consumer_group="ingestion-cg", ma_loi="EVENT_SCHEMA_INVALID", thong_diep="x" * 900,
    )
    assert doc_header(h, "X-Trace-Id") == "trace-1"
    assert doc_header(h, "dlq.error_code") == "EVENT_SCHEMA_INVALID"
    assert [k for k, _ in h].count("dlq.error_code") == 1
    assert (doc_header(h, "dlq.original_partition"), doc_header(h, "dlq.original_offset")) == (
        "2", "17",
    )
    assert len(doc_header(h, "dlq.error_message")) == 500
