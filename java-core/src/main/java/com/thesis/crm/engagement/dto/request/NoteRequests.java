package com.thesis.crm.engagement.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import java.util.UUID;

/** Thân request ghi chú — UC017. Giới hạn 4000 ký tự khớp giao diện AddNoteDialog. */
public final class NoteRequests {

    private NoteRequests() {}

    public record CreateNoteRequest(
            @NotBlank(message = "Ghi chú không được để trống.")
            @Size(max = 4000, message = "Ghi chú tối đa 4000 ký tự.")
            String content,

            UUID conversationId) {}

    /** Sửa nội dung và/hoặc ghim — trường để trống (null) là không đổi. */
    public record UpdateNoteRequest(
            @Size(max = 4000, message = "Ghi chú tối đa 4000 ký tự.")
            String content,

            Boolean isPinned) {}
}
