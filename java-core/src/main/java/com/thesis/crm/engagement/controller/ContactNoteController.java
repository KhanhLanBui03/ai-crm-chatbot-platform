package com.thesis.crm.engagement.controller;

import static com.thesis.crm.security.CurrentActor.isTenantAdmin;
import static com.thesis.crm.security.CurrentActor.requireTenantId;
import static com.thesis.crm.security.CurrentActor.requireUserId;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.engagement.dto.request.NoteRequests.CreateNoteRequest;
import com.thesis.crm.engagement.dto.request.NoteRequests.UpdateNoteRequest;
import com.thesis.crm.engagement.dto.response.NoteDto;
import com.thesis.crm.engagement.service.NoteService;
import com.thesis.crm.engagement.service.NoteService.Actor;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** UC017 — {@code /api/v1/contacts/{contactId}/notes} (SCR028). */
@RestController
@RequestMapping("/api/v1/contacts/{contactId}/notes")
public class ContactNoteController {

    private final NoteService noteService;

    public ContactNoteController(NoteService noteService) {
        this.noteService = noteService;
    }

    @GetMapping
    public ResponseEntity<ApiResponse<List<NoteDto>>> list(@PathVariable UUID contactId) {
        return ResponseEntity.ok(ApiResponse.ok(noteService.list(requireTenantId(), actor(), contactId)));
    }

    @PostMapping
    public ResponseEntity<ApiResponse<NoteDto>> create(
            @PathVariable UUID contactId, @Valid @RequestBody CreateNoteRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.ok(noteService.create(requireTenantId(), actor(), contactId, request)));
    }

    /** Sửa nội dung và/hoặc ghim — tác giả hoặc quản trị viên. */
    @PatchMapping("/{noteId}")
    public ResponseEntity<ApiResponse<NoteDto>> update(
            @PathVariable UUID contactId, @PathVariable UUID noteId,
            @Valid @RequestBody UpdateNoteRequest request) {
        return ResponseEntity.ok(ApiResponse.ok(
                noteService.update(requireTenantId(), actor(), contactId, noteId, request)));
    }

    /** Xoá mềm — tác giả hoặc quản trị viên. */
    @DeleteMapping("/{noteId}")
    public ResponseEntity<ApiResponse<Void>> delete(@PathVariable UUID contactId, @PathVariable UUID noteId) {
        noteService.delete(requireTenantId(), actor(), contactId, noteId);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    private static Actor actor() {
        return new Actor(requireUserId(), isTenantAdmin());
    }
}
