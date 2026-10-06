package com.thesis.crm.engagement.service;

import com.thesis.crm.engagement.dto.request.CreateTagRequest;
import com.thesis.crm.engagement.dto.response.ContactDtos.TagDto;
import java.util.List;
import java.util.UUID;

/** UC017 — thẻ phân loại khách hàng, gắn ở cấp khách hàng. */
public interface TagService {

    /** @param created {@code false} khi trùng tên với thẻ đã có (trả về thẻ cũ, mã 200). */
    record CreateTagResult(TagDto tag, boolean created) {}

    List<TagDto> list(UUID tenantId);

    CreateTagResult create(UUID tenantId, UUID actorUserId, CreateTagRequest request);

    void attach(UUID tenantId, UUID actorUserId, UUID contactId, UUID tagId);

    void detach(UUID tenantId, UUID actorUserId, UUID contactId, UUID tagId);
}
