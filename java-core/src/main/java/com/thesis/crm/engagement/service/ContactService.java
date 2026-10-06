package com.thesis.crm.engagement.service;

import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.engagement.dto.request.CreateContactRequest;
import com.thesis.crm.engagement.dto.response.ContactDtos.ContactDetailDto;
import com.thesis.crm.engagement.dto.response.ContactDtos.ContactDto;
import com.thesis.crm.engagement.dto.response.ContactDtos.CreateContactResult;
import java.util.UUID;

/** UC016 — Quản lý danh bạ: danh sách (SCR026), hồ sơ (SCR024), tạo thủ công (SCR027). */
public interface ContactService {

    PageResponse<ContactDto> search(
            UUID tenantId, String q, String status, UUID tagId, Boolean hasConsent,
            String sort, int page, int size);

    ContactDetailDto getById(UUID tenantId, UUID contactId);

    CreateContactResult create(UUID tenantId, CreateContactRequest request);
}
