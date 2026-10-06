package com.thesis.crm.engagement.service.impl;

import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.engagement.dto.request.CreateContactRequest;
import com.thesis.crm.engagement.dto.response.ContactDtos.ContactDetailDto;
import com.thesis.crm.engagement.dto.response.ContactDtos.ContactDto;
import com.thesis.crm.engagement.dto.response.ContactDtos.CreateContactResult;
import com.thesis.crm.engagement.entity.Contact;
import com.thesis.crm.engagement.repository.ContactQueryRepository;
import com.thesis.crm.engagement.repository.ContactQueryRepository.DetailExtras;
import com.thesis.crm.engagement.repository.ContactQueryRepository.SearchFilter;
import com.thesis.crm.engagement.repository.ContactRepository;
import com.thesis.crm.engagement.service.ContactService;
import com.thesis.crm.engagement.util.ContactNormalizer;
import com.thesis.crm.security.TenantTransactionScope;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC016 — logic nghiệp vụ danh bạ.
 *
 * <p>Mọi phương thức mở transaction rồi {@link TenantTransactionScope#apply} NGAY ĐẦU, trước truy
 * vấn đầu tiên — RLS chỉ có tác dụng khi biến tenant được đặt trong cùng transaction.
 */
@Service
public class ContactServiceImpl implements ContactService {

    private static final Set<String> STATUSES = Set.of("ACTIVE", "MERGED", "ANONYMIZED");
    private static final int DEFAULT_SIZE = 25;
    private static final int MAX_SIZE = 100;

    private final ContactRepository contactRepository;
    private final ContactQueryRepository contactQueries;
    private final TenantTransactionScope tenantScope;
    private final AuditLogWriter auditLog;

    public ContactServiceImpl(
            ContactRepository contactRepository,
            ContactQueryRepository contactQueries,
            TenantTransactionScope tenantScope,
            AuditLogWriter auditLog) {
        this.contactRepository = contactRepository;
        this.contactQueries = contactQueries;
        this.tenantScope = tenantScope;
        this.auditLog = auditLog;
    }

    @Override
    @Transactional(readOnly = true)
    public PageResponse<ContactDto> search(
            UUID tenantId, String q, String status, UUID tagId, Boolean hasConsent,
            String sort, int page, int size) {
        tenantScope.apply(tenantId);

        String normalizedStatus = null;
        if (status != null && !status.isBlank()) {
            normalizedStatus = status.trim().toUpperCase();
            if (!STATUSES.contains(normalizedStatus)) {
                throw new AppException("Trạng thái khách hàng không hợp lệ: " + status, HttpStatus.BAD_REQUEST);
            }
        }
        int safePage = Math.max(0, page);
        int safeSize = size <= 0 ? DEFAULT_SIZE : Math.min(size, MAX_SIZE);

        ContactQueryRepository.PageResult result = contactQueries.search(tenantId, new SearchFilter(
                ContactNormalizer.searchTokens(q), normalizedStatus, tagId, hasConsent, sort, safePage, safeSize));
        return PageResponse.of(result.items(), safePage, safeSize, result.total());
    }

    @Override
    @Transactional(readOnly = true)
    public ContactDetailDto getById(UUID tenantId, UUID contactId) {
        tenantScope.apply(tenantId);
        return loadDetail(tenantId, contactId);
    }

    @Override
    @Transactional
    public CreateContactResult create(UUID tenantId, UUID actorUserId, CreateContactRequest req) {
        tenantScope.apply(tenantId);

        String phone;
        try {
            phone = ContactNormalizer.normalizePhone(req.phone());
        } catch (IllegalArgumentException e) {
            throw new AppException(
                    "Số điện thoại không hợp lệ. Dùng số Việt Nam, ví dụ 0912345678 hoặc +84912345678.",
                    HttpStatus.UNPROCESSABLE_ENTITY);
        }
        String email = ContactNormalizer.normalizeEmail(req.email());
        // Một hồ sơ không có cách nào liên hệ lại là hồ sơ vô dụng — cùng quy tắc với giao diện SCR027.
        if (phone == null && email == null) {
            throw new AppException("Phải có ít nhất số điện thoại hoặc địa chỉ thư.", HttpStatus.UNPROCESSABLE_ENTITY);
        }
        String fullName = req.fullName() == null || req.fullName().isBlank() ? null : req.fullName().trim();

        Contact c = new Contact();
        c.setTenantId(tenantId);
        c.setFullName(fullName);
        c.setPhone(phone);
        c.setEmail(email);
        // Khách nhân viên nhập tay thường đến qua điện thoại (hợp đồng: PHONE dành cho nhập tay).
        c.setPrimaryChannel(req.primaryChannel() == null ? "PHONE" : req.primaryChannel());
        boolean consent = Boolean.TRUE.equals(req.consentGranted());
        c.setConsent(consent, req.consentSource() == null ? "AGENT_MANUAL" : req.consentSource(), Instant.now());

        // Flush ngay để các truy vấn SQL phía sau (cùng transaction) thấy bản ghi mới.
        Contact saved = contactRepository.saveAndFlush(c);

        // Nhật ký kiểm toán — giao diện SCR027 cam kết "ô đồng ý được ghi vào nhật ký kiểm toán".
        // KHÔNG chép tên/SĐT/email vào nhật ký (NĐ 13): nhật ký sống lâu hơn dữ liệu khách.
        Map<String, Object> audit = new LinkedHashMap<>();
        audit.put("primaryChannel", saved.getPrimaryChannel());
        audit.put("consentGranted", saved.isConsentGranted());
        audit.put("consentSource", saved.getConsentSource());
        audit.put("consentAt", saved.getConsentAt() == null ? null : saved.getConsentAt().toString());
        auditLog.recordUserAction(tenantId, actorUserId, "CONTACT_CREATED", "CONTACT", saved.getId(), audit);

        // Trùng KHÔNG chặn — trả danh sách nghi trùng để giao diện gợi ý hợp nhất (V124, hợp đồng).
        List<ContactDto> duplicates = contactQueries.findDuplicates(tenantId, saved.getId(), phone, email);
        return new CreateContactResult(loadDetail(tenantId, saved.getId()), duplicates);
    }

    private ContactDetailDto loadDetail(UUID tenantId, UUID contactId) {
        ContactDto c = contactQueries.findById(tenantId, contactId)
                .orElseThrow(() -> new AppException("Không tìm thấy khách hàng.", HttpStatus.NOT_FOUND));
        DetailExtras x = contactQueries.detailExtras(tenantId, contactId);
        return new ContactDetailDto(
                c.id(), c.fullName(), c.phone(), c.email(), c.primaryChannel(), c.status(),
                c.consentGranted(), c.consentAt(), c.tags(), c.lastInteractionAt(), c.createdAt(),
                x.mergedIntoContactId(),
                contactQueries.channelIdentities(tenantId, contactId),
                x.conversationCount(), x.openLeadCount(), x.openDealCount(), x.totalDealValue(),
                x.anonymizedAt());
    }
}
