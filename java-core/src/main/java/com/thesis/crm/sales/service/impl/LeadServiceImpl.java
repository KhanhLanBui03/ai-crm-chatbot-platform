package com.thesis.crm.sales.service.impl;

import com.thesis.crm.sales.dto.request.CreateLeadRequest;
import com.thesis.crm.sales.dto.response.LeadResponse;
import com.thesis.crm.sales.repository.LeadRepository;
import com.thesis.crm.sales.service.LeadService;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * MẪU — bản cài đặt. Đây là nơi duy nhất chứa logic nghiệp vụ của lead.
 *
 * <p><b>Quy tắc quan trọng nhất của lớp này:</b> mọi thay đổi trạng thái đáng kể phải ghi một
 * bản ghi vào {@code platform.outbox_events} TRONG CÙNG {@code @Transactional} với thao tác
 * nghiệp vụ. Không gọi {@code KafkaTemplate.send()} trực tiếp ở đây.
 *
 * <p>Lý do (ADR-0003): bắn sự kiện thẳng trong transaction thì khi rollback vẫn có sự kiện đã
 * gửi đi; bắn sau commit thì tiến trình chết giữa chừng là mất sự kiện. Outbox đảm bảo giao
 * nhận ít nhất một lần và cách ly hoàn toàn lỗi của khối phân tích khỏi luồng phục vụ khách.
 */
@Service
public class LeadServiceImpl implements LeadService {

    private final LeadRepository leadRepository;

    public LeadServiceImpl(LeadRepository leadRepository) {
        this.leadRepository = leadRepository;
    }

    @Override
    @Transactional
    public LeadResponse create(CreateLeadRequest request) {
        // TODO: ánh xạ request -> Lead, lấy tenantId từ ngữ cảnh bảo mật (KHÔNG lấy từ request)
        // TODO: đặt source = LeadSource.MANUAL — nhánh AI_AUTO đi qua API nội bộ của Track B
        // TODO: đặt status = LeadStatus.NEW; KHÔNG đặt currentScore (Track B tính, ghi qua API)
        // TODO: leadRepository.save(lead)
        // TODO: ghi outbox_events {aggregate_type=lead, event_type=LeadCreated, event_version=1}
        //       trong CÙNG transaction này — xem platform/messaging/
        throw new UnsupportedOperationException("Chưa cài đặt — đây là file mẫu");
    }

    @Override
    @Transactional(readOnly = true)
    public LeadResponse getById(UUID id) {
        // TODO: leadRepository.findById(id) -> ánh xạ sang LeadResponse
        // Không cần lọc tenant ở đây: RLS đã lọc (ADR-0001)
        throw new UnsupportedOperationException("Chưa cài đặt — đây là file mẫu");
    }
}
