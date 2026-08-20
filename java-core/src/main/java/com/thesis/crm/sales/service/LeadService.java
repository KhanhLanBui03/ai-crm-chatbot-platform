package com.thesis.crm.sales.service;

import com.thesis.crm.sales.dto.request.CreateLeadRequest;
import com.thesis.crm.sales.dto.response.LeadResponse;
import java.util.UUID;

/**
 * MẪU — interface nghiệp vụ. Cặp {@code service/} + {@code service/impl/} là quy ước của dự án.
 *
 * <p>Interface đứng ở đây có hai tác dụng thật, không phải hình thức: nó là bề mặt mà các
 * context khác và {@code controller/} được phép nhìn thấy, và nó cho phép thay bản cài đặt
 * bằng bản giả lập khi kiểm thử mà không cần khung mock nặng.
 */
public interface LeadService {

    LeadResponse create(CreateLeadRequest request);

    LeadResponse getById(UUID id);
}
