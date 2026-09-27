package com.thesis.crm.platform.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import jakarta.mail.internet.MimeMessage;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;

@Service
public class EmailService {

    private static final Logger log = LoggerFactory.getLogger(EmailService.class);
    private static final String RESEND_API_URL = "https://api.resend.com/emails";

    @Value("${spring.mail.username:}")
    private String springMailUsername;

    @Value("${crm.mail.resend.api-key:}")
    private String resendApiKey;

    @Value("${crm.mail.resend.from:CRM AI Platform <onboarding@resend.dev>}")
    private String fromEmail;

    @Value("${crm.app.frontend-url:http://localhost:5173}")
    private String frontendUrl;

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final JavaMailSender javaMailSender;

    public EmailService(ObjectMapper objectMapper, ObjectProvider<JavaMailSender> mailSenderProvider) {
        this.objectMapper = objectMapper;
        this.javaMailSender = mailSenderProvider.getIfAvailable();
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .build();
    }

    /**
     * Gửi mã OTP xác thực khi đăng ký tài khoản doanh nghiệp mới.
     */
    @Async
    public void guiOtpDangKy(String toEmail, String otpCode, String companyName) {
        String tieuDe = "[CRM AI] Mã OTP xác nhận đăng ký tài khoản: " + otpCode;
        String noiDungHtml = taoTemplateOtp(
                "Xác nhận tạo tài khoản doanh nghiệp",
                "Cảm ơn bạn đã đăng ký sử dụng nền tảng CRM AI cho <strong>" + escapeHtml(companyName) + "</strong>.",
                otpCode,
                "Mã xác thực có hiệu lực trong vòng <strong>5 phút</strong>. Tuyệt đối không chia sẻ mã này cho bất kỳ ai vì lý do an toàn bảo mật."
        );

        guiEmail(toEmail, tieuDe, noiDungHtml, "OTP: " + otpCode);
    }

    /**
     * Gửi mã OTP khi người dùng yêu cầu đặt lại mật khẩu.
     */
    @Async
    public void guiOtpQuenMatKhau(String toEmail, String otpCode) {
        String tieuDe = "[CRM AI] Mã OTP đặt lại mật khẩu: " + otpCode;
        String noiDungHtml = taoTemplateOtp(
                "Yêu cầu đặt lại mật khẩu",
                "Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản <strong>" + escapeHtml(toEmail) + "</strong>.",
                otpCode,
                "Mã có hiệu lực trong <strong>5 phút</strong>. Nếu bạn không yêu cầu hành động này, hãy bỏ qua email và đổi mật khẩu ngay."
        );

        guiEmail(toEmail, tieuDe, noiDungHtml, "OTP: " + otpCode);
    }

    /**
     * Gửi thư mời tham gia tổ chức/doanh nghiệp cho nhân viên mới.
     */
    @Async
    public void guiThuMoiThanhVien(String toEmail, String fullName, String companyName, String roleName) {
        String inviteUrl = frontendUrl + "/xac-thuc/kich-hoat?email=" + toEmail;
        String tieuDe = "[CRM AI] Lời mời tham gia " + companyName + " trên nền tảng CRM AI";
        String noiDungHtml = taoTemplateMoiThanhVien(fullName, companyName, roleName, inviteUrl);

        guiEmail(toEmail, tieuDe, noiDungHtml, "Link kích hoạt: " + inviteUrl);
    }

    private void guiEmail(String toEmail, String subject, String htmlContent, String debugInfo) {
        log.info("==================================================================");
        log.info("📧 [EMAIL DISPATCH] Gửi tới: {} | Tiêu đề: [{}] | Info: [{}]", toEmail, subject, debugInfo);
        log.info("==================================================================");

        // 1. Ưu tiên gửi qua Spring Boot JavaMailSender (Gmail SMTP)
        if (javaMailSender != null && springMailUsername != null && !springMailUsername.isBlank()) {
            try {
                MimeMessage mimeMessage = javaMailSender.createMimeMessage();
                MimeMessageHelper helper = new MimeMessageHelper(mimeMessage, true, "UTF-8");
                helper.setFrom(springMailUsername, "CRM AI Platform");
                helper.setTo(toEmail);
                helper.setSubject(subject);
                helper.setText(htmlContent, true);

                javaMailSender.send(mimeMessage);
                log.info("✅ Gửi email thành công qua Gmail SMTP (from: {}) tới: {}", springMailUsername, toEmail);
                return;
            } catch (Exception e) {
                log.error("⚠️ Gửi qua Gmail SMTP thất bại: {}. Đang thử phương thức tiếp theo...", e.getMessage());
            }
        }

        // 2. Dự phòng: Gửi qua Resend HTTP API nếu có cấu hình
        if (resendApiKey != null && !resendApiKey.isBlank() && !resendApiKey.startsWith("re_dummy")) {
            try {
                Map<String, Object> payload = Map.of(
                        "from", fromEmail,
                        "to", List.of(toEmail),
                        "subject", subject,
                        "html", htmlContent
                );

                String requestBody = objectMapper.writeValueAsString(payload);

                HttpRequest request = HttpRequest.newBuilder()
                        .uri(URI.create(RESEND_API_URL))
                        .header("Authorization", "Bearer " + resendApiKey.trim())
                        .header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                        .timeout(Duration.ofSeconds(15))
                        .build();

                HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

                if (response.statusCode() >= 200 && response.statusCode() < 300) {
                    log.info("✅ Gửi email thành công qua Resend tới: {} (Response: {})", toEmail, response.body());
                    return;
                } else {
                    log.warn("⚠️ Gửi email Resend trả về mã lỗi {}: {}", response.statusCode(), response.body());
                }
            } catch (Exception e) {
                log.error("❌ Lỗi khi gửi email qua Resend API: {}. Debug Info: [{}]", e.getMessage(), debugInfo);
            }
        } else {
            log.info("ℹ️ Đã ghi nhận email dispatch vào log (debugInfo: [{}])", debugInfo);
        }
    }

    private String taoTemplateMoiThanhVien(String fullName, String companyName, String roleName, String inviteUrl) {
        String tenNguoiNhan = (fullName != null && !fullName.isBlank()) ? escapeHtml(fullName) : "bạn";
        return """
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }
                .card { max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); }
                .header { text-align: center; margin-bottom: 24px; }
                .brand { font-size: 20px; font-weight: 700; color: #4f46e5; letter-spacing: -0.5px; }
                .title { font-size: 18px; font-weight: 600; margin-top: 12px; color: #0f172a; }
                .desc { font-size: 14px; line-height: 1.6; color: #475569; margin: 16px 0; }
                .role-badge { display: inline-block; background: #e0e7ff; color: #4338ca; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 13px; }
                .btn-box { text-align: center; margin: 30px 0; }
                .btn { background: #4f46e5; color: #ffffff !important; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 14px; display: inline-block; box-shadow: 0 2px 6px rgba(79, 70, 229, 0.3); }
                .footer { font-size: 12px; color: #94a3b8; text-align: center; margin-top: 24px; line-height: 1.5; border-top: 1px solid #f1f5f9; padding-top: 16px; }
              </style>
            </head>
            <body>
              <div class="card">
                <div class="header">
                  <div class="brand">✦ CRM AI PLATFORM</div>
                  <div class="title">Lời mời tham gia doanh nghiệp</div>
                </div>
                <div class="desc">
                  Xin chào <strong>""" + tenNguoiNhan + """
                  </strong>,<br><br>
                  Bạn được mời tham gia vào tổ chức <strong>""" + escapeHtml(companyName) + """
                  </strong> với vai trò: <span class="role-badge">""" + escapeHtml(roleName) + """
                  </span>.
                </div>
                <div class="desc">
                  Để kích hoạt tài khoản và tự đặt mật khẩu cá nhân, vui lòng nhấn vào nút bên dưới:
                </div>
                <div class="btn-box">
                  <a href=\"""" + inviteUrl + """
                  \" class="btn" target="_blank">Kích hoạt tài khoản</a>
                </div>
                <div class="desc" style="font-size: 12px; color: #64748b; word-break: break-all;">
                  Nếu không bấm được nút trên, hãy sao chép liên kết này vào trình duyệt:<br>
                  <a href=\"""" + inviteUrl + """
                  \" style="color: #4f46e5;">""" + inviteUrl + """
                  </a>
                </div>
                <div class="footer">
                  Email này được gửi tự động từ hệ thống Nền tảng CRM AI.<br>
                  Vui lòng không trả lời thư này.
                </div>
              </div>
            </body>
            </html>
            """;
    }

    private String taoTemplateOtp(String tieuDeChinh, String moDau, String otpCode, String ghiChuBaoMat) {
        return """
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }
                .card { max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); }
                .header { text-align: center; margin-bottom: 24px; }
                .brand { font-size: 20px; font-weight: 700; color: #4f46e5; letter-spacing: -0.5px; }
                .title { font-size: 18px; font-weight: 600; margin-top: 12px; color: #0f172a; }
                .desc { font-size: 14px; line-height: 1.6; color: #475569; margin: 16px 0; }
                .otp-box { background: #f1f5f9; border: 2px dashed #cbd5e1; border-radius: 8px; padding: 18px; text-align: center; margin: 24px 0; }
                .otp-code { font-family: 'Courier New', Courier, monospace; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #4f46e5; }
                .footer { font-size: 12px; color: #94a3b8; text-align: center; margin-top: 24px; line-height: 1.5; border-top: 1px solid #f1f5f9; padding-top: 16px; }
              </style>
            </head>
            <body>
              <div class="card">
                <div class="header">
                  <div class="brand">✦ CRM AI PLATFORM</div>
                  <div class="title">""" + tieuDeChinh + """
                  </div>
                </div>
                <div class="desc">
                  """ + moDau + """
                </div>
                <div class="otp-box">
                  <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 6px;">Mã xác thực OTP của bạn</div>
                  <div class="otp-code">""" + otpCode + """
                  </div>
                </div>
                <div class="desc" style="font-size: 13px; color: #64748b;">
                  """ + ghiChuBaoMat + """
                </div>
                <div class="footer">
                  Email này được gửi tự động từ hệ thống Nền tảng CRM AI.<br>
                  Vui lòng không trả lời thư này.
                </div>
              </div>
            </body>
            </html>
            """;
    }

    private String escapeHtml(String input) {
        if (input == null) return "";
        return input.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&#39;");
    }
}
