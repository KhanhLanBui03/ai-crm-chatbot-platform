package com.thesis.crm.engagement.service.impl;

import com.thesis.crm.common.audit.AuditLogWriter;
import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.engagement.dto.request.CreateTagRequest;
import com.thesis.crm.engagement.dto.response.ContactDtos.TagDto;
import com.thesis.crm.engagement.repository.ContactQueryRepository;
import com.thesis.crm.engagement.repository.TagRepository;
import com.thesis.crm.engagement.service.TagService;
import com.thesis.crm.engagement.util.TagColors;
import com.thesis.crm.security.TenantTransactionScope;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * UC017 — thẻ. Trùng tên (kể cả khác hoa thường / khác dấu) trả thẻ cũ; chạm trần gói thì 409.
 * Gắn thẻ đã gắn / gỡ thẻ chưa gắn: không lỗi, không ghi kiểm toán (không có gì thay đổi).
 */
@Service
public class TagServiceImpl implements TagService {

    private final TagRepository tags;
    private final ContactQueryRepository contacts;
    private final TenantTransactionScope tenantScope;
    private final AuditLogWriter auditLog;

    public TagServiceImpl(
            TagRepository tags, ContactQueryRepository contacts,
            TenantTransactionScope tenantScope, AuditLogWriter auditLog) {
        this.tags = tags;
        this.contacts = contacts;
        this.tenantScope = tenantScope;
        this.auditLog = auditLog;
    }

    @Override
    @Transactional(readOnly = true)
    public List<TagDto> list(UUID tenantId) {
        tenantScope.apply(tenantId);
        return tags.listAll(tenantId);
    }

    @Override
    @Transactional
    public CreateTagResult create(UUID tenantId, UUID actorUserId, CreateTagRequest req) {
        tenantScope.apply(tenantId);
        String name = req.name().trim();

        // Đã có (khác hoa thường / khác dấu) → trả thẻ cũ, KHÔNG tính vào hạn mức
        var existing = tags.findByFoldedName(tenantId, name);
        if (existing.isPresent()) {
            return new CreateTagResult(existing.get(), false);
        }
        int limit = tags.maxTags(tenantId);
        if (tags.count(tenantId) >= limit) {
            throw new AppException(
                    "Đã đạt giới hạn " + limit + " thẻ của gói dịch vụ. Hãy dùng lại thẻ có sẵn hoặc nâng cấp gói.",
                    HttpStatus.CONFLICT);
        }
        String color = req.color() == null ? TagColors.forName(name) : req.color().toUpperCase();
        var inserted = tags.insertIfAbsent(tenantId, actorUserId, name, color);
        if (inserted.isEmpty()) {
            // Người khác vừa tạo cùng tên giữa lần kiểm và lần chèn
            return new CreateTagResult(tags.findByFoldedName(tenantId, name).orElseThrow(), false);
        }
        TagDto tag = inserted.get();
        auditLog.recordUserAction(tenantId, actorUserId, "TAG_CREATED", "TAG", tag.id(),
                Map.of("name", tag.name(), "color", tag.color()));
        return new CreateTagResult(tag, true);
    }

    @Override
    @Transactional
    public void attach(UUID tenantId, UUID actorUserId, UUID contactId, UUID tagId) {
        tenantScope.apply(tenantId);
        requireWritableContact(tenantId, contactId);
        TagDto tag = requireTag(tenantId, tagId);
        if (tags.attach(tenantId, contactId, tagId, actorUserId)) {
            auditLog.recordUserAction(tenantId, actorUserId, "CONTACT_TAGGED", "CONTACT", contactId,
                    Map.of("tagId", tagId.toString(), "tagName", tag.name()));
        }
    }

    @Override
    @Transactional
    public void detach(UUID tenantId, UUID actorUserId, UUID contactId, UUID tagId) {
        tenantScope.apply(tenantId);
        requireWritableContact(tenantId, contactId);
        TagDto tag = requireTag(tenantId, tagId);
        if (tags.detach(tenantId, contactId, tagId)) {
            auditLog.recordUserAction(tenantId, actorUserId, "CONTACT_UNTAGGED", "CONTACT", contactId,
                    Map.of("tagId", tagId.toString(), "tagName", tag.name()));
        }
    }

    private TagDto requireTag(UUID tenantId, UUID tagId) {
        return tags.findById(tenantId, tagId)
                .orElseThrow(() -> new AppException("Không tìm thấy thẻ.", HttpStatus.NOT_FOUND));
    }

    private void requireWritableContact(UUID tenantId, UUID contactId) {
        String status = contacts.findStatus(tenantId, contactId)
                .orElseThrow(() -> new AppException("Không tìm thấy khách hàng.", HttpStatus.NOT_FOUND));
        if (!"ACTIVE".equals(status)) {
            throw new AppException("MERGED".equals(status)
                    ? "Khách hàng đã được hợp nhất — hãy thao tác trên hồ sơ được giữ lại."
                    : "Khách hàng đã được ẩn danh hoá — không thể gắn thêm thông tin.", HttpStatus.CONFLICT);
        }
    }
}
