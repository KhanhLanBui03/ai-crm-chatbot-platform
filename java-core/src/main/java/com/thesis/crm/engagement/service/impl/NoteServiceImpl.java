package com.thesis.crm.engagement.service.impl;

import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.engagement.dto.request.NoteRequests.CreateNoteRequest;
import com.thesis.crm.engagement.dto.request.NoteRequests.UpdateNoteRequest;
import com.thesis.crm.engagement.dto.response.NoteDto;
import com.thesis.crm.engagement.repository.ContactQueryRepository;
import com.thesis.crm.engagement.repository.NoteRepository;
import com.thesis.crm.engagement.repository.NoteRepository.NoteRow;
import com.thesis.crm.engagement.service.NoteService;
import com.thesis.crm.engagement.util.SensitiveDataDetector;
import com.thesis.crm.security.TenantTransactionScope;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC017 — ghi chú nội bộ. Sửa/xoá/ghim: tác giả hoặc quản trị viên. Khách đã gộp/ẩn danh: chỉ
 * xem, không ghi thêm. Nhật ký kiểm toán cho sửa/xoá — KHÔNG chép nội dung ghi chú (NĐ 13).
 */
@Service
public class NoteServiceImpl implements NoteService {

    private final NoteRepository notes;
    private final ContactQueryRepository contacts;
    private final TenantTransactionScope tenantScope;
    private final AuditLogWriter auditLog;

    public NoteServiceImpl(
            NoteRepository notes, ContactQueryRepository contacts,
            TenantTransactionScope tenantScope, AuditLogWriter auditLog) {
        this.notes = notes;
        this.contacts = contacts;
        this.tenantScope = tenantScope;
        this.auditLog = auditLog;
    }

    @Override
    @Transactional(readOnly = true)
    public List<NoteDto> list(UUID tenantId, Actor actor, UUID contactId) {
        tenantScope.apply(tenantId);
        requireContact(tenantId, contactId);
        return notes.list(tenantId, contactId).stream().map(r -> toDto(r, actor)).toList();
    }

    @Override
    @Transactional
    public NoteDto create(UUID tenantId, Actor actor, UUID contactId, CreateNoteRequest req) {
        tenantScope.apply(tenantId);
        requireWritableContact(tenantId, contactId);
        if (req.conversationId() != null
                && !notes.conversationBelongsToContact(tenantId, req.conversationId(), contactId)) {
            throw new AppException("Hội thoại không thuộc khách hàng này.", HttpStatus.UNPROCESSABLE_ENTITY);
        }
        UUID id = notes.insert(tenantId, contactId, actor.userId(), req.content().trim(), req.conversationId());
        return toDto(notes.find(tenantId, contactId, id).orElseThrow(), actor);
    }

    @Override
    @Transactional
    public NoteDto update(UUID tenantId, Actor actor, UUID contactId, UUID noteId, UpdateNoteRequest req) {
        tenantScope.apply(tenantId);
        requireWritableContact(tenantId, contactId);
        NoteRow note = requireEditableNote(tenantId, actor, contactId, noteId);

        Map<String, Object> changes = new LinkedHashMap<>();
        if (req.content() != null) {
            String content = req.content().trim();
            if (content.isEmpty()) {
                throw new AppException("Ghi chú không được để trống.", HttpStatus.UNPROCESSABLE_ENTITY);
            }
            if (!content.equals(note.content())) {
                notes.updateContent(tenantId, noteId, content);
                changes.put("contentChanged", true);
                changes.put("contentLength", content.length());
            }
        }
        if (req.isPinned() != null && req.isPinned() != note.pinned()) {
            notes.updatePinned(tenantId, noteId, req.isPinned());
            changes.put("isPinned", req.isPinned());
        }
        if (!changes.isEmpty()) {
            changes.put("contactId", contactId.toString());
            auditLog.recordUserAction(tenantId, actor.userId(), "NOTE_UPDATED", "CONTACT_NOTE", noteId, changes);
        }
        return toDto(notes.find(tenantId, contactId, noteId).orElseThrow(), actor);
    }

    @Override
    @Transactional
    public void delete(UUID tenantId, Actor actor, UUID contactId, UUID noteId) {
        tenantScope.apply(tenantId);
        requireContact(tenantId, contactId);
        requireEditableNote(tenantId, actor, contactId, noteId);
        notes.softDelete(tenantId, noteId);
        auditLog.recordUserAction(tenantId, actor.userId(), "NOTE_DELETED", "CONTACT_NOTE", noteId,
                Map.of("contactId", contactId.toString()));
    }

    // ── nội bộ ──────────────────────────────────────────────────────────────────

    private String requireContact(UUID tenantId, UUID contactId) {
        return contacts.findStatus(tenantId, contactId)
                .orElseThrow(() -> new AppException("Không tìm thấy khách hàng.", HttpStatus.NOT_FOUND));
    }

    /** Khách đã gộp phải thao tác trên hồ sơ giữ lại; khách đã ẩn danh không được ghi thêm thông tin. */
    private void requireWritableContact(UUID tenantId, UUID contactId) {
        String status = requireContact(tenantId, contactId);
        if (!"ACTIVE".equals(status)) {
            throw new AppException("MERGED".equals(status)
                    ? "Khách hàng đã được hợp nhất — hãy thao tác trên hồ sơ được giữ lại."
                    : "Khách hàng đã được ẩn danh hoá — không thể ghi thêm thông tin.", HttpStatus.CONFLICT);
        }
    }

    private NoteRow requireEditableNote(UUID tenantId, Actor actor, UUID contactId, UUID noteId) {
        NoteRow note = notes.find(tenantId, contactId, noteId)
                .orElseThrow(() -> new AppException("Không tìm thấy ghi chú.", HttpStatus.NOT_FOUND));
        if (!canEdit(note, actor)) {
            throw new AppException("Chỉ tác giả hoặc quản trị viên mới sửa/xoá được ghi chú này.", HttpStatus.FORBIDDEN);
        }
        return note;
    }

    private static boolean canEdit(NoteRow note, Actor actor) {
        return actor.tenantAdmin() || note.authorUserId().equals(actor.userId());
    }

    private static NoteDto toDto(NoteRow r, Actor actor) {
        return new NoteDto(r.id(), r.content(), r.conversationId(), r.authorUserId(), r.authorName(),
                r.pinned(), SensitiveDataDetector.containsSensitive(r.content()), canEdit(r, actor),
                r.editedAt(), r.createdAt());
    }
}
