package com.thesis.crm.client;

import com.thesis.crm.common.exception.BusinessException;
import com.thesis.crm.config.S3Properties;
import java.io.IOException;
import java.io.UncheckedIOException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.io.InputStreamSource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import software.amazon.awssdk.core.exception.SdkException;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;

/**
 * Ghi và xoá tệp gốc trên kho S3 — adapter ra hệ thống ngoài, cùng vai với
 * {@code ai-service/src/ai/integrations/object_storage.py} ở phía bên kia.
 *
 * <p>Không biết tenant là gì: key do phía gọi dựng ({@code platform/service/impl/KbObjectKey}).
 * java-core chỉ GHI và XOÁ; đọc nội dung tệp là việc của ai-service (ranh giới UC018).
 */
@Component
public class ObjectStorageClient {

    private static final Logger log = LoggerFactory.getLogger(ObjectStorageClient.class);

    /** MIME trình duyệt khai không đáng tin — ai-service tự nhận diện định dạng thật. */
    private static final String CONTENT_TYPE = "application/octet-stream";

    private final S3Client s3;
    private final String bucket;

    public ObjectStorageClient(S3Client s3, S3Properties properties) {
        this.s3 = s3;
        this.bucket = properties.bucket();
    }

    /**
     * Ghi {@code content} vào {@code key}, trả URI {@code s3://{bucket}/{key}}.
     *
     * <p>Nhận {@link InputStreamSource} (chính là {@code MultipartFile}) thay vì một luồng đã mở:
     * SDK thử lại khi lỗi mạng, và mỗi lần thử cần một luồng MỚI từ đầu tệp. Luồng đã đọc dở thì
     * lần thử lại gửi thiếu dữ liệu.
     */
    public String put(String key, InputStreamSource content, long size) {
        try {
            s3.putObject(r -> r.bucket(bucket).key(key).contentType(CONTENT_TYPE).contentLength(size),
                    RequestBody.fromContentProvider(() -> moLuong(content), size, CONTENT_TYPE));
        } catch (SdkException | UncheckedIOException e) {
            log.error("Không ghi được object lên kho S3 (bucket {})", bucket, e);
            throw new BusinessException(HttpStatus.SERVICE_UNAVAILABLE, "STORAGE_UNAVAILABLE",
                    "Kho lưu trữ tệp tạm thời không phản hồi. Thử lại sau.");
        }
        return uri(key);
    }

    /**
     * Xoá object của một lượt tải thất bại. KHÔNG ném: đây là bước dọn dẹp trên đường trả lỗi,
     * và lỗi gốc mới là thứ người dùng cần thấy. Xoá hỏng thì để lại object mồ côi — ghi WARN
     * kèm key để dọn tay (hợp đồng UC018 mục 4).
     */
    public void deleteQuietly(String key) {
        try {
            s3.deleteObject(r -> r.bucket(bucket).key(key));
        } catch (SdkException e) {
            log.warn("Không xoá được object mồ côi s3://{}/{}", bucket, key, e);
        }
    }

    public String uri(String key) {
        return "s3://" + bucket + "/" + key;
    }

    private static java.io.InputStream moLuong(InputStreamSource content) {
        try {
            return content.getInputStream();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
