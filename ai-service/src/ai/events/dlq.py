"""Dựng bản tin cho hàng đợi chết ``ai.dlq`` — Master Plan §2.6, ADR-0024. [PRODUCTION]

GIÁ TRỊ VÀ KHOÁ GIỮ NGUYÊN BYTE của bản tin gốc — phát lại từ DLQ phải đưa vào worker đúng thứ đã
hỏng, không phải một bản đã qua tay mình. Lý do hỏng đi ở HEADER ``dlq.*``, cạnh các header gốc
(``X-Trace-Id`` giữ nguyên để truy được về lượt tải ban đầu).

Cái gì vào DLQ, cái gì không (ADR-0024):

    VÀO   sự kiện KHÔNG biến được thành trạng thái tài liệu
          - sai lược đồ / loại hay phiên bản chưa hỗ trợ   → ngay lập tức
          - lỗi tạm thời (thường là CSDL chết) hết lượt thử → sau ``so_lan_thu_ban_tin`` lần
    KHÔNG tài liệu đã nhận xử lý rồi hỏng (PARSE_*, INGEST_RETRY_EXHAUSTED…) — đã là FAILED kèm
          lý do trên SCR033, người dùng tự thấy và tải lại. Đẩy thêm vào DLQ là báo một lỗi ở hai
          nơi, và phát lại sẽ bị ``ai.processed_events`` chặn vì sự kiện đã được ghi nhận.
"""

from datetime import UTC, datetime

# Header Kafka có giới hạn thực tế theo cỡ bản tin; thông điệp lỗi chỉ cần đủ để đọc.
_THONG_DIEP_TOI_DA = 500


def dung_header_dlq(
    header_goc: list[tuple[str, bytes]] | tuple[tuple[str, bytes], ...] | None,
    *,
    topic: str,
    partition: int,
    offset: int,
    consumer_group: str,
    ma_loi: str,
    thong_diep: str,
    luc: datetime | None = None,
) -> list[tuple[str, bytes]]:
    """Header gốc (bỏ ``dlq.*`` cũ nếu bản tin từng qua DLQ) + sáu header mô tả lần hỏng này."""
    giu_lai = [(k, v) for k, v in (header_goc or ()) if not k.startswith("dlq.")]
    them = {
        "dlq.original_topic": topic,
        "dlq.original_partition": str(partition),
        "dlq.original_offset": str(offset),
        "dlq.consumer_group": consumer_group,
        "dlq.error_code": ma_loi,
        "dlq.error_message": thong_diep[:_THONG_DIEP_TOI_DA],
        "dlq.failed_at": (luc or datetime.now(UTC)).isoformat(),
    }
    return giu_lai + [(k, v.encode("utf-8")) for k, v in them.items()]


def doc_header(headers: list[tuple[str, bytes]] | tuple[tuple[str, bytes], ...] | None,
               ten: str) -> str | None:
    """Giá trị (chuỗi) của header ``ten``, ``None`` nếu không có."""
    for k, v in headers or ():
        if k == ten:
            return v.decode("utf-8", errors="replace") if v is not None else None
    return None
