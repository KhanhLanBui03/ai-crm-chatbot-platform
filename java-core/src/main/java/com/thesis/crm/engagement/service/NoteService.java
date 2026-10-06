package com.thesis.crm.engagement.service;

import com.thesis.crm.engagement.dto.request.NoteRequests.CreateNoteRequest;
import com.thesis.crm.engagement.dto.request.NoteRequests.UpdateNoteRequest;
import com.thesis.crm.engagement.dto.response.NoteDto;
import java.util.List;
import java.util.UUID;

/** UC017 — ghi chú nội bộ về khách hàng (SCR028). */
public interface NoteService {

    /** Người đang thao tác — quyết định {@code canEdit} và quyền sửa/xoá. */
    record Actor(UUID userId, boolean tenantAdmin) {}

    List<NoteDto> list(UUID tenantId, Actor actor, UUID contactId);

    NoteDto create(UUID tenantId, Actor actor, UUID contactId, CreateNoteRequest request);

    NoteDto update(UUID tenantId, Actor actor, UUID contactId, UUID noteId, UpdateNoteRequest request);

    void delete(UUID tenantId, Actor actor, UUID contactId, UUID noteId);
}
