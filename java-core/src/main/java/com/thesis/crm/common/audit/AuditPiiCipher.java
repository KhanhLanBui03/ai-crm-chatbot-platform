package com.thesis.crm.common.audit;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.Optional;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * Mã hoá bản gốc dữ liệu cá nhân của nhật ký kiểm toán (UC040, V136) bằng AES-256-GCM.
 *
 * <p>Khoá nằm NGOÀI CSDL — biến môi trường {@code AUDIT_PII_KEY} (32 byte, base64) kèm mã khoá
 * {@code AUDIT_PII_KEY_ID}. Ai đọc được bảng {@code audit_logs} (kể cả tài khoản chủ bảng) chỉ thấy khối byte
 * vô nghĩa; muốn xem bản gốc phải đi qua ứng dụng, tức là qua quyền + lý do + một dòng nhật ký mới.
 *
 * <p>Không cấu hình khoá thì {@link #encrypt} trả rỗng và bên ghi bỏ hẳn phần trước/sau (UC040 luồng 2.1:
 * "thà thiếu dữ liệu so sánh còn hơn để dữ liệu thật nằm trong bảng"). Không bao giờ rơi về lưu bản rõ.
 *
 * <p>Khuôn byte: {@code [12 byte IV][bản mã + 16 byte thẻ xác thực]}. IV ngẫu nhiên mỗi lần — GCM dùng lại IV
 * với cùng khoá là lộ khoá.
 */
@Component
public class AuditPiiCipher {

    private static final String THUAT_TOAN = "AES/GCM/NoPadding";
    private static final int IV_BYTES = 12;
    private static final int TAG_BITS = 128;

    private final SecretKey key;
    private final String keyId;
    private final SecureRandom random = new SecureRandom();

    public AuditPiiCipher(@Value("${AUDIT_PII_KEY:}") String keyBase64,
                          @Value("${AUDIT_PII_KEY_ID:k1}") String keyId) {
        this.key = parse(keyBase64);
        this.keyId = keyId;
    }

    /** Có khoá để mã hoá không — không có thì nhật ký không giữ bản gốc dữ liệu cá nhân. */
    public boolean enabled() {
        return key != null;
    }

    public String keyId() {
        return keyId;
    }

    /** Rỗng khi chưa cấu hình khoá hoặc mã hoá lỗi — bên gọi KHÔNG được rơi về lưu bản rõ. */
    public Optional<byte[]> encrypt(String plaintext) {
        if (key == null) {
            return Optional.empty();
        }
        try {
            byte[] iv = new byte[IV_BYTES];
            random.nextBytes(iv);
            Cipher c = Cipher.getInstance(THUAT_TOAN);
            c.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, iv));
            byte[] ct = c.doFinal(plaintext.getBytes(StandardCharsets.UTF_8));
            return Optional.of(ByteBuffer.allocate(iv.length + ct.length).put(iv).put(ct).array());
        } catch (GeneralSecurityException e) {
            return Optional.empty();
        }
    }

    /**
     * Giải mã bằng khoá hiện hành. Mã khoá của dòng phải khớp — dòng mã bằng khoá đã xoay đi thì báo lỗi rõ
     * thay vì giải mã sai.
     */
    public String decrypt(byte[] data, String dataKeyId) {
        if (key == null) {
            throw new IllegalStateException("Chưa cấu hình AUDIT_PII_KEY — không giải mã được nhật ký.");
        }
        if (!keyId.equals(dataKeyId)) {
            throw new IllegalStateException("Bản ghi mã hoá bằng khoá '" + dataKeyId + "', khoá hiện hành là '"
                    + keyId + "'.");
        }
        try {
            Cipher c = Cipher.getInstance(THUAT_TOAN);
            c.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, data, 0, IV_BYTES));
            byte[] pt = c.doFinal(data, IV_BYTES, data.length - IV_BYTES);
            return new String(pt, StandardCharsets.UTF_8);
        } catch (GeneralSecurityException e) {
            // GCM xác thực thất bại = dữ liệu bị sửa hoặc sai khoá
            throw new IllegalStateException("Không giải mã được — sai khoá hoặc dữ liệu đã bị sửa.", e);
        }
    }

    private static SecretKey parse(String keyBase64) {
        if (keyBase64 == null || keyBase64.isBlank()) {
            return null;
        }
        byte[] raw = Base64.getDecoder().decode(keyBase64.trim());
        if (raw.length != 32) {
            throw new IllegalStateException("AUDIT_PII_KEY phải là 32 byte (AES-256) mã base64, đang là "
                    + raw.length + " byte.");
        }
        return new SecretKeySpec(raw, "AES");
    }
}
