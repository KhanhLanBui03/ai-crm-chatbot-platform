package com.thesis.crm.platform.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.platform.dto.*;
import com.thesis.crm.platform.entity.*;
import com.thesis.crm.platform.repository.*;
import com.thesis.crm.security.JwtTokenProvider;
import com.thesis.crm.security.TenantContextExecutor;
import jakarta.persistence.EntityManager;
import org.hibernate.Session;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.sql.PreparedStatement;
import java.text.Normalizer;
import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.regex.Pattern;

@Service
public class AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);
    private static final short MAX_FAILED_LOGIN_ATTEMPTS = 5;
    private static final Duration LOCK_DURATION = Duration.ofMinutes(15);
    private static final Pattern NONLATIN = Pattern.compile("[^\\w-]");
    private static final Pattern WHITESPACE = Pattern.compile("[\\s]");

    private final TenantRepository tenantRepository;
    private final UserRepository userRepository;
    private final RoleRepository roleRepository;
    private final UserRoleRepository userRoleRepository;
    private final SubscriptionPlanRepository subscriptionPlanRepository;
    private final TenantSubscriptionRepository tenantSubscriptionRepository;
    private final UsageRecordRepository usageRecordRepository;
    private final TenantContextExecutor tenantContextExecutor;
    private final EntityManager entityManager;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;
    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    private final EmailService emailService;

    public AuthService(
            TenantRepository tenantRepository,
            UserRepository userRepository,
            RoleRepository roleRepository,
            UserRoleRepository userRoleRepository,
            SubscriptionPlanRepository subscriptionPlanRepository,
            TenantSubscriptionRepository tenantSubscriptionRepository,
            UsageRecordRepository usageRecordRepository,
            TenantContextExecutor tenantContextExecutor,
            EntityManager entityManager,
            PasswordEncoder passwordEncoder,
            JwtTokenProvider jwtTokenProvider,
            StringRedisTemplate redisTemplate,
            ObjectMapper objectMapper,
            EmailService emailService) {
        this.tenantRepository = tenantRepository;
        this.userRepository = userRepository;
        this.roleRepository = roleRepository;
        this.userRoleRepository = userRoleRepository;
        this.subscriptionPlanRepository = subscriptionPlanRepository;
        this.tenantSubscriptionRepository = tenantSubscriptionRepository;
        this.usageRecordRepository = usageRecordRepository;
        this.tenantContextExecutor = tenantContextExecutor;
        this.entityManager = entityManager;
        this.passwordEncoder = passwordEncoder;
        this.jwtTokenProvider = jwtTokenProvider;
        this.redisTemplate = redisTemplate;
        this.objectMapper = objectMapper;
        this.emailService = emailService;
    }

    public void guiOtp(SendOtpRequest req) {
        String normalizedEmail = req.email().trim().toLowerCase();

        if ("REGISTER".equalsIgnoreCase(req.purpose()) && userRepository.existsByEmailAcrossSystem(normalizedEmail)) {
            throw new AppException("Địa chỉ thư này đã đăng ký một doanh nghiệp. Đăng nhập hoặc dùng thư khác.", HttpStatus.CONFLICT);
        }

        // Sinh mã OTP 6 số ngẫu nhiên (100000 - 999999)
        int randomPin = 100000 + new Random().nextInt(900000);
        String otpCode = String.valueOf(randomPin);

        String purpose = req.purpose() != null ? req.purpose().toLowerCase() : "register";
        String redisKey = "otp:" + purpose + ":" + normalizedEmail;
        redisTemplate.opsForValue().set(redisKey, otpCode, Duration.ofMinutes(5));

        log.info("🔐 Đã lưu OTP vào Redis: key={} | code={}", redisKey, otpCode);

        if ("forgot_password".equalsIgnoreCase(purpose)) {
            emailService.guiOtpQuenMatKhau(normalizedEmail, otpCode);
        } else {
            String company = req.companyName() != null && !req.companyName().isBlank() ? req.companyName() : "Doanh nghiệp của bạn";
            emailService.guiOtpDangKy(normalizedEmail, otpCode, company);
        }
    }

    public VerifyOtpResult xacThucOtp(VerifyOtpRequest req) {
        String normalizedEmail = req.email().trim().toLowerCase();
        String purpose = req.purpose() != null ? req.purpose().toLowerCase() : "forgot_password";
        String redisKey = "otp:" + purpose + ":" + normalizedEmail;
        String savedOtp = redisTemplate.opsForValue().get(redisKey);

        if (savedOtp == null || !savedOtp.equals(req.otpCode().trim())) {
            throw new AppException("Mã OTP không chính xác hoặc đã hết hạn (5 phút). Vui lòng thử lại.", HttpStatus.BAD_REQUEST);
        }

        // Xóa OTP sau khi đã xác thực thành công
        redisTemplate.delete(redisKey);

        String resetToken = null;
        if ("forgot_password".equalsIgnoreCase(purpose)) {
            resetToken = UUID.randomUUID().toString();
            String tokenKey = "auth:reset_password:" + resetToken;
            redisTemplate.opsForValue().set(tokenKey, normalizedEmail, Duration.ofMinutes(15));
            log.info("🔑 Đã tạo reset token cho {}: token={}", normalizedEmail, resetToken);
        }

        return new VerifyOtpResult(true, resetToken);
    }

    @Transactional
    public DangKyResult dangKy(DangKyRequest req) {
        String normalizedEmail = req.email().trim().toLowerCase();

        if (userRepository.existsByEmailAcrossSystem(normalizedEmail)) {
            throw new AppException("Địa chỉ thư này đã đăng ký một doanh nghiệp. Đăng nhập hoặc dùng thư khác.", HttpStatus.CONFLICT);
        }

        if (req.acceptedTerms() == null || !req.acceptedTerms()) {
            throw new AppException("Cần đồng ý điều khoản trước khi tạo tài khoản.", HttpStatus.UNPROCESSABLE_ENTITY);
        }

        // Xác thực mã OTP nếu có gửi lên
        if (req.otpCode() != null && !req.otpCode().isBlank()) {
            String redisKey = "otp:register:" + normalizedEmail;
            String savedOtp = redisTemplate.opsForValue().get(redisKey);
            if (savedOtp == null || !savedOtp.equals(req.otpCode().trim())) {
                throw new AppException("Mã OTP không chính xác hoặc đã hết hạn (5 phút). Vui lòng thử lại.", HttpStatus.BAD_REQUEST);
            }
            redisTemplate.delete(redisKey);
        }

        String baseSlug = toSlug(req.companyName());
        String slug = baseSlug;
        int count = 1;
        while (tenantRepository.isSlugTaken(slug)) {
            slug = baseSlug + "-" + count++;
        }

        UUID newTenantId = UUID.randomUUID();
        String passwordHash = passwordEncoder.encode(req.password());

        // Gọi hàm SECURITY DEFINER — bypass RLS hoàn toàn.
        // Giống find_login_identity dùng cho đăng nhập, hàm register_tenant chạy bằng
        // quyền crm_owner, không bị ảnh hưởng bởi app.tenant_id chưa đặt trên phiên.
        Session session = entityManager.unwrap(Session.class);
        final String finalSlug = slug;
        Object[] result = session.doReturningWork(connection -> {
            try (PreparedStatement ps = connection.prepareStatement(
                    "SELECT tenant_id, tenant_slug, user_id, user_email " +
                    "FROM platform.register_tenant(?, ?, ?, ?, ?, ?, ?, ?)")) {
                ps.setObject(1, newTenantId);
                ps.setString(2, req.companyName().trim());
                ps.setString(3, finalSlug);
                ps.setString(4, normalizedEmail);
                ps.setString(5, passwordHash);
                ps.setString(6, req.fullName().trim());
                ps.setString(7, req.industry());
                ps.setString(8, req.timezone());
                try (var rs = ps.executeQuery()) {
                    if (rs.next()) {
                        return new Object[]{
                            rs.getObject("tenant_id", UUID.class),
                            rs.getString("tenant_slug"),
                            rs.getObject("user_id", UUID.class),
                            rs.getString("user_email")
                        };
                    }
                    throw new RuntimeException("register_tenant không trả về kết quả");
                }
            }
        });

        UUID tenantId = (UUID) result[0];
        String tenantSlug = (String) result[1];
        UUID userId = (UUID) result[2];
        String userEmail = (String) result[3];

        String verifyToken = UUID.randomUUID().toString();
        redisTemplate.opsForValue().set("auth:email_verify:" + verifyToken, userId.toString(), Duration.ofHours(24));
        log.info("Mã xác thực email tạo cho {}: token={}", normalizedEmail, verifyToken);

        return new DangKyResult(tenantId, tenantSlug, userEmail, false);
    }

    @Transactional
    public KetQuaDangNhap dangNhap(DangNhapRequest req, HttpServletResponse response) {
        String normalizedEmail = req.email().trim().toLowerCase();

        LoginIdentityProjection identity = userRepository.findLoginIdentity(normalizedEmail)
                .orElseThrow(() -> new AppException("Email hoặc mật khẩu không chính xác.", HttpStatus.UNAUTHORIZED));

        Instant now = Instant.now();
        if (identity.getLocked_until() != null && identity.getLocked_until().isAfter(now)) {
            throw new AppException("Tài khoản bị khóa tạm thời sau nhiều lần sai mật khẩu. Vui lòng thử lại sau.", HttpStatus.LOCKED);
        }

        // Đặt ngữ cảnh tenant để PostgreSQL mở khóa RLS cho các câu lệnh phía sau
        if (identity.getTenant_id() != null) {
            tenantContextExecutor.setTenantContext(identity.getTenant_id());
        }

        if (!passwordEncoder.matches(req.password(), identity.getPassword_hash())) {
            short newFailCount = (short) ((identity.getFailed_login_count() != null ? identity.getFailed_login_count() : 0) + 1);
            Instant lockedUntil = null;
            if (newFailCount >= MAX_FAILED_LOGIN_ATTEMPTS) {
                lockedUntil = now.plus(LOCK_DURATION);
            }
            userRepository.updateFailedLogin(identity.getUser_id(), newFailCount, lockedUntil);

            if (lockedUntil != null) {
                throw new AppException("Tài khoản bị khóa tạm thời 15 phút do nhập sai mật khẩu 5 lần.", HttpStatus.LOCKED);
            }
            throw new AppException("Email hoặc mật khẩu không chính xác.", HttpStatus.UNAUTHORIZED);
        }

        if ("DISABLED".equalsIgnoreCase(identity.getStatus())) {
            throw new AppException("Tài khoản của bạn đã bị vô hiệu hóa.", HttpStatus.FORBIDDEN);
        }

        if ("PENDING".equalsIgnoreCase(identity.getStatus())) {
            userRepository.activateUser(identity.getUser_id(), now);
        }

        userRepository.resetFailedLoginAndSetLastLogin(identity.getUser_id(), now);

        List<Role> roles = identity.getTenant_id() != null
                ? roleRepository.findRolesByUserId(identity.getUser_id())
                : List.of();
        String accessToken = jwtTokenProvider.generateAccessToken(
                identity.getUser_id(),
                identity.getTenant_id(),
                normalizedEmail,
                identity.getScope(),
                roles
        );

        String refreshToken = jwtTokenProvider.createRefreshToken(identity.getUser_id(), identity.getTenant_id());

        Cookie cookie = new Cookie("refresh_token", refreshToken);
        cookie.setHttpOnly(true);
        cookie.setSecure(false);
        cookie.setPath("/api/v1/auth");
        cookie.setMaxAge((int) Duration.ofDays(7).toSeconds());
        response.addCookie(cookie);

        NguoiDungHienTaiDto userInfo = buildUserInfo(identity.getUser_id(), identity.getTenant_id(), normalizedEmail, roles);

        return new KetQuaDangNhap(accessToken, userInfo);
    }

    @Transactional
    public void xacThucThu(String token) {
        if (token == null || token.isBlank()) {
            throw new AppException("Liên kết xác thực đã hết hạn hoặc đã được dùng.", HttpStatus.GONE);
        }
        String key = "auth:email_verify:" + token.trim();
        String userIdStr = redisTemplate.opsForValue().get(key);
        if (userIdStr == null || userIdStr.isBlank()) {
            throw new AppException("Liên kết xác thực đã hết hạn hoặc đã được dùng.", HttpStatus.GONE);
        }
        redisTemplate.delete(key);
        userRepository.verifyEmail(UUID.fromString(userIdStr));
    }

    public void guiLaiThuXacThuc(String email) {
        if (email == null || email.isBlank()) {
            return;
        }
        String normalizedEmail = email.trim().toLowerCase();
        userRepository.findLoginIdentity(normalizedEmail).ifPresent(identity -> {
            String verifyToken = UUID.randomUUID().toString();
            redisTemplate.opsForValue().set("auth:email_verify:" + verifyToken, identity.getUser_id().toString(), Duration.ofHours(24));
            log.info("Mã xác thực email tạo lại cho {}: token={}", normalizedEmail, verifyToken);
        });
    }

    public void quenMatKhau(ForgotPasswordRequest req) {
        String normalizedEmail = req.email().trim().toLowerCase();
        guiOtp(new SendOtpRequest(normalizedEmail, null, "FORGOT_PASSWORD"));
    }

    @Transactional
    public void datLaiMatKhau(ResetPasswordRequest req) {
        String normalizedEmail = req.email() != null ? req.email().trim().toLowerCase() : null;

        // Trường hợp 1: Sử dụng Token đặt lại mật khẩu từ liên kết email
        if (req.token() != null && !req.token().isBlank()) {
            String tokenKey = "auth:reset_password:" + req.token().trim();
            String emailFromRedis = redisTemplate.opsForValue().get(tokenKey);
            if (emailFromRedis == null || emailFromRedis.isBlank()) {
                throw new AppException("Mã đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.", HttpStatus.GONE);
            }
            normalizedEmail = emailFromRedis.trim().toLowerCase();
            redisTemplate.delete(tokenKey);
        } else if (req.otpCode() != null && !req.otpCode().isBlank() && normalizedEmail != null) {
            // Trường hợp 2: Sử dụng mã xác thực OTP 6 số
            String redisKey = "otp:forgot_password:" + normalizedEmail;
            String savedOtp = redisTemplate.opsForValue().get(redisKey);
            if (savedOtp == null || !savedOtp.equals(req.otpCode().trim())) {
                throw new AppException("Mã OTP không chính xác hoặc đã hết hạn (5 phút). Vui lòng thử lại.", HttpStatus.BAD_REQUEST);
            }
            redisTemplate.delete(redisKey);
        } else {
            throw new AppException("Vui lòng cung cấp mã OTP hoặc mã đặt lại mật khẩu hợp lệ.", HttpStatus.BAD_REQUEST);
        }

        if (normalizedEmail == null || normalizedEmail.isBlank()) {
            throw new AppException("Email không hợp lệ.", HttpStatus.BAD_REQUEST);
        }

        String passwordHash = passwordEncoder.encode(req.newPassword());
        boolean updated = userRepository.resetPasswordByEmail(normalizedEmail, passwordHash);
        if (!updated) {
            throw new AppException("Không tìm thấy tài khoản tương ứng với email này.", HttpStatus.NOT_FOUND);
        }
        log.info("🔒 Đã đặt lại mật khẩu thành công cho tài khoản: {}", normalizedEmail);
    }

    @Transactional(readOnly = true)
    public TokenRefreshResult lamMoiToken(String refreshToken) {
        if (refreshToken == null || refreshToken.isBlank()) {
            throw new AppException("Chưa đăng nhập hoặc phiên làm việc đã hết hạn.", HttpStatus.UNAUTHORIZED);
        }
        String key = "auth:refresh:" + refreshToken.trim();
        String sessionJson = redisTemplate.opsForValue().get(key);
        if (sessionJson == null || sessionJson.isBlank()) {
            throw new AppException("Phiên làm việc không tồn tại hoặc đã hết hạn.", HttpStatus.UNAUTHORIZED);
        }

        try {
            Map<String, String> data = objectMapper.readValue(sessionJson, new TypeReference<Map<String, String>>() {});
            UUID userId = UUID.fromString(data.get("userId"));
            UUID tenantId = data.containsKey("tenantId") && data.get("tenantId") != null
                    ? UUID.fromString(data.get("tenantId"))
                    : null;

            if (tenantId != null) {
                tenantContextExecutor.setTenantContext(tenantId);
            }

            User user = null;
            if (tenantId != null) {
                user = userRepository.findById(userId).orElse(null);
            }
            if (user != null && "DISABLED".equalsIgnoreCase(user.getStatus())) {
                throw new AppException("Tài khoản của bạn đã bị vô hiệu hóa.", HttpStatus.FORBIDDEN);
            }

            List<Role> roles = tenantId != null ? roleRepository.findRolesByUserId(userId) : List.of();
            String email = user != null ? user.getEmail() : "admin@platform.vn";
            String scope = user != null ? user.getScope() : (tenantId == null ? "PLATFORM" : "TENANT");
            String newAccessToken = jwtTokenProvider.generateAccessToken(
                    userId,
                    tenantId,
                    email,
                    scope,
                    roles
            );

            return new TokenRefreshResult(newAccessToken);
        } catch (AppException e) {
            throw e;
        } catch (Exception e) {
            log.error("Lỗi khi giải mã phiên làm mới", e);
            throw new AppException("Phiên làm việc không hợp lệ.", HttpStatus.UNAUTHORIZED);
        }
    }

    public void dangXuat(String refreshToken, HttpServletResponse response) {
        if (refreshToken != null && !refreshToken.isBlank()) {
            redisTemplate.delete("auth:refresh:" + refreshToken.trim());
        }
        Cookie cookie = new Cookie("refresh_token", "");
        cookie.setHttpOnly(true);
        cookie.setSecure(false);
        cookie.setPath("/api/v1/auth");
        cookie.setMaxAge(0);
        response.addCookie(cookie);
    }

    @Transactional(readOnly = true)
    public NguoiDungHienTaiDto layHoSoCuaToi(UUID userId) {
        User user = null;
        try {
            user = userRepository.findById(userId).orElse(null);
        } catch (Exception ignored) {}
        UUID tenantId = user != null ? user.getTenantId() : null;
        String email = user != null ? user.getEmail() : "admin@platform.vn";
        List<Role> roles = tenantId != null ? roleRepository.findRolesByUserId(userId) : List.of();
        return buildUserInfo(userId, tenantId, email, roles);
    }

    private NguoiDungHienTaiDto buildUserInfo(UUID userId, UUID tenantId, String email, List<Role> roles) {
        User user = null;
        if (tenantId != null) {
            try {
                user = userRepository.findById(userId).orElse(null);
            } catch (Exception ignored) {}
        }
        String fullName = user != null ? user.getFullName() : (tenantId == null ? "Quản trị viên Hệ thống" : email);

        String tenantName = "Doanh nghiệp";
        String planName = "Trial";

        if (tenantId != null) {
            Optional<Tenant> tenantOpt = tenantRepository.findById(tenantId);
            if (tenantOpt.isPresent()) {
                tenantName = tenantOpt.get().getName();
            }

            Optional<TenantSubscription> subOpt = tenantSubscriptionRepository.findFirstByTenantIdOrderByCreatedAtDesc(tenantId);
            if (subOpt.isPresent()) {
                Optional<SubscriptionPlan> planOpt = subscriptionPlanRepository.findById(subOpt.get().getPlanId());
                if (planOpt.isPresent()) {
                    planName = planOpt.get().getName();
                }
            }
        } else {
            tenantName = "Nền tảng CRM AI";
            planName = "Platform";
        }

        String primaryRole = tenantId == null ? "PLATFORM_ADMIN" : "AGENT";
        Set<String> allPermissions = new HashSet<>();
        if (tenantId == null) {
            allPermissions.addAll(List.of(
                    "platform.tenants.read",
                    "platform.tenants.write",
                    "platform.plans.read",
                    "platform.plans.write",
                    "platform.ai-usage.read",
                    "platform.audit.read"
            ));
        }
        for (Role role : roles) {
            if ("TENANT_ADMIN".equalsIgnoreCase(role.getCode()) || "PLATFORM_ADMIN".equalsIgnoreCase(role.getCode())) {
                primaryRole = role.getCode();
            }
            if (role.getPermissions() != null) {
                try {
                    List<String> perms = objectMapper.readValue(role.getPermissions(), new TypeReference<List<String>>() {});
                    allPermissions.addAll(perms);
                } catch (Exception ignored) {}
            }
        }

        return new NguoiDungHienTaiDto(
                userId,
                fullName,
                email,
                primaryRole,
                new ArrayList<>(allPermissions),
                tenantName,
                planName
        );
    }

    private String toSlug(String input) {
        String nowhitespace = WHITESPACE.matcher(input.trim()).replaceAll("-");
        String normalized = Normalizer.normalize(nowhitespace, Normalizer.Form.NFD);
        String slug = Pattern.compile("\\p{InCombiningDiacriticalMarks}+").matcher(normalized).replaceAll("");
        slug = slug.replaceAll("đ", "d").replaceAll("Đ", "d");
        slug = NONLATIN.matcher(slug).replaceAll("");
        slug = slug.replaceAll("-+", "-").replaceAll("^-|-$", "").toLowerCase();
        return slug.length() > 50 ? slug.substring(0, 50) : slug;
    }
}
