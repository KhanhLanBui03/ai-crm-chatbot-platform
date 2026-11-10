package com.thesis.crm.platform.service.impl;

import com.thesis.crm.client.AiKnowledgeClient.KbChunk;
import com.thesis.crm.client.AiKnowledgeClient.KbDocument;
import com.thesis.crm.client.AiKnowledgeClient.KbIngestionJob;
import com.thesis.crm.platform.dto.response.CongViecNapResponse;
import com.thesis.crm.platform.dto.response.DoanTaiLieuResponse;
import com.thesis.crm.platform.dto.response.TaiLieuChiTietResponse;
import com.thesis.crm.platform.dto.response.TaiLieuResponse;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.regex.Pattern;

/**
 * Gương ai-service → hình {@code dashboard-api.yaml}. Chỉ ĐỔI TÊN, không tính lại gì: con số nào
 * cũng là số ai-service đã tính (số đoạn đếm thật, trạng thái chiếu từ {@code status}).
 *
 * <p>Bảng ánh xạ đầy đủ ở kế hoạch tích hợp giao diện, mục UC019 và UC020.
 */
final class KnowledgeMapper {

    /**
     * ai-service lưu {@code error_message} dạng {@code "{MÃ}: {câu cho người đọc}"}
     * ({@code document_repository.danh_dau_that_bai}); tiến độ nạp đã tách sẵn hai phần. Danh sách
     * và chi tiết chỉ hiện câu cho người đọc — mã nằm ở {@code CongViecNap.errorCode}.
     */
    private static final Pattern TIEN_TO_MA_LOI = Pattern.compile("^[A-Z][A-Z0-9_]*: ");

    private KnowledgeMapper() {
    }

    static TaiLieuResponse taiLieu(KbDocument d, String uploadedByName) {
        return new TaiLieuResponse(d.id(), d.title(), d.description(), d.sourceType(), d.fileName(), d.mimeType(),
                d.fileSizeBytes(), d.language(), d.status(), d.chunkCount(), d.version(), cauLoi(d.errorMessage()),
                uploadedByName, instant(d.indexedAt()), instant(d.createdAt()));
    }

    static TaiLieuChiTietResponse chiTiet(KbDocument d, String uploadedByName, CongViecNapResponse latestJob) {
        return new TaiLieuChiTietResponse(d.id(), d.title(), d.description(), d.sourceType(), d.fileName(),
                d.mimeType(), d.fileSizeBytes(), d.language(), d.status(), d.chunkCount(), d.version(),
                cauLoi(d.errorMessage()), uploadedByName, instant(d.indexedAt()), instant(d.createdAt()),
                d.replacesDocumentId(), latestJob, null);
    }

    static CongViecNapResponse congViec(KbIngestionJob j) {
        return new CongViecNapResponse(j.jobId(), j.documentId(), j.documentTitle(), j.trigger(), j.state(),
                j.attempt(), j.chunksCreated(), null, null, j.errorCode(), j.errorMessage(), j.durationMs(),
                instant(j.startedAt()), instant(j.finishedAt()), instant(j.createdAt()));
    }

    static DoanTaiLieuResponse doan(KbChunk c) {
        return new DoanTaiLieuResponse(c.chunkId(), c.chunkIndex(), c.content(), c.heading(), c.tokenCount(),
                c.embeddingModel(), c.embeddingVersion());
    }

    static String cauLoi(String errorMessage) {
        return errorMessage == null ? null : TIEN_TO_MA_LOI.matcher(errorMessage).replaceFirst("");
    }

    private static Instant instant(OffsetDateTime t) {
        return t == null ? null : t.toInstant();
    }
}
