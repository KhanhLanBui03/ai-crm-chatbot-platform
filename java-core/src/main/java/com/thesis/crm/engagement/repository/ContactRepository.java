package com.thesis.crm.engagement.repository;

import com.thesis.crm.engagement.entity.Contact;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

/** Ghi {@code engagement.contacts}. Đọc danh sách / hồ sơ: {@link ContactQueryRepository}. */
public interface ContactRepository extends JpaRepository<Contact, UUID> {
}
