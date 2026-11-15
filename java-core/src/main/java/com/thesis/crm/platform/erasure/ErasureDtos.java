package com.thesis.crm.platform.erasure;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/** Hình dạng dữ liệu của {@code /api/v1/erasure-requests/**} — khớp schema trong dashboard-api.yaml. */
public final class ErasureDtos {

    private ErasureDtos() {
    }

    /** {@code YeuCauXoa} — một dòng của SCR056. */
    public record ErasureRequestDto(
            UUID id, UUID contactId, String contactName, String requestedBy, String legalBasis, String status,
            String identityVerifiedByName, Instant identityVerifiedAt, Instant requestedAt, Instant completedAt) {
    }

    /**
     * {@code YeuCauXoaChiTiet}. {@code certificateUri} luôn {@code null} — biên bản bản gọn (chốt Q4 của
     * GD3): biên bản là chính {@code items} + người/lúc xác minh + lúc hoàn tất, lưu trên yêu cầu và trong
     * dòng kiểm toán {@code ERASURE_EXECUTED}, không xuất tệp.
     */
    public record ErasureRequestDetail(
            UUID id, UUID contactId, String contactName, String requestedBy, String legalBasis, String status,
            String identityVerifiedByName, Instant identityVerifiedAt, Instant requestedAt, Instant completedAt,
            List<ErasureItem> items, String externalSystemsNote, String certificateUri, Instant startedAt) {
    }

    /**
     * {@code MucXoa} — một bảng trong phạm vi xoá. Lưu NGUYÊN hình này trong cột jsonb
     * {@code data_erasure_requests.items} (comment V109: "Mảng MucXoa"), nên đọc/ghi không phải dịch.
     *
     * @param affectedRows {@code null} = chưa biết (phía AI trước khi thực thi, hoặc mục giữ tổng hợp)
     */
    public record ErasureItem(String targetSchema, String targetTable, String action, String status,
                              Long affectedRows, String errorMessage, Instant executedAt) {

        String key() {
            return targetSchema + "." + targetTable;
        }

        ErasureItem done(Long rows, Instant at) {
            return new ErasureItem(targetSchema, targetTable, action, "DONE", rows, null, at);
        }

        ErasureItem failed(String message, Instant at) {
            return new ErasureItem(targetSchema, targetTable, action, "FAILED", affectedRows, message, at);
        }
    }

    /** Thân {@code POST /api/v1/erasure-requests} — UC041 bước 1–2. */
    public record CreateErasureRequest(UUID contactId, String legalBasis, String requestedBy) {
    }
}
