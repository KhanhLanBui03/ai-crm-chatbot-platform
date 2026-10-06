package com.thesis.crm.client;

/**
 * ai-service không trả 202 — hoặc không trả lời gì.
 *
 * <p>Chỉ MANG thông tin phía ai-service trả về (mã HTTP + {@code code} nghiệp vụ). Dịch sang lỗi
 * cho người dùng là việc của service gọi nó: cùng một 403 {@code FORBIDDEN_FILE_URI}, với luồng
 * tải lên là lỗi lập trình (500), với luồng khác có thể nghĩa khác.
 */
public class AiServiceException extends RuntimeException {

    /** Mã HTTP ai-service trả; {@code 0} khi không nhận được phản hồi nào. */
    private final int status;
    /** {@code code} trong thân lỗi {@code {code, message}}; {@code null} nếu thân không đọc được. */
    private final String code;

    public AiServiceException(int status, String code, String message) {
        super(message);
        this.status = status;
        this.code = code;
    }

    /** Không kết nối được, hết thời gian chờ — không có phản hồi HTTP nào. */
    public static AiServiceException unreachable(Throwable cause) {
        AiServiceException ex = new AiServiceException(0, null, "Không gọi được ai-service: " + cause.getMessage());
        ex.initCause(cause);
        return ex;
    }

    public int getStatus() {
        return status;
    }

    public String getCode() {
        return code;
    }

    public boolean isUnreachable() {
        return status == 0;
    }
}
