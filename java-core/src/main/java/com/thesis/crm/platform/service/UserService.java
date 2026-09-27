package com.thesis.crm.platform.service;

import com.thesis.crm.common.exception.AppException;
import com.thesis.crm.common.response.PageResponse;
import com.thesis.crm.platform.dto.InviteUserRequest;
import com.thesis.crm.platform.dto.UpdateUserRequest;
import com.thesis.crm.platform.dto.UserDto;
import com.thesis.crm.platform.entity.*;
import com.thesis.crm.platform.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.security.SecureRandom;
import java.time.Instant;
import java.util.*;

@Service
public class UserService {

    private static final Logger log = LoggerFactory.getLogger(UserService.class);

    private final UserRepository userRepository;
    private final RoleRepository roleRepository;
    private final UserRoleRepository userRoleRepository;
    private final TenantSubscriptionRepository subscriptionRepository;
    private final SubscriptionPlanRepository planRepository;
    private final TenantRepository tenantRepository;
    private final PasswordEncoder passwordEncoder;
    private final EmailService emailService;

    public UserService(
            UserRepository userRepository,
            RoleRepository roleRepository,
            UserRoleRepository userRoleRepository,
            TenantSubscriptionRepository subscriptionRepository,
            SubscriptionPlanRepository planRepository,
            TenantRepository tenantRepository,
            PasswordEncoder passwordEncoder,
            EmailService emailService
    ) {
        this.userRepository = userRepository;
        this.roleRepository = roleRepository;
        this.userRoleRepository = userRoleRepository;
        this.subscriptionRepository = subscriptionRepository;
        this.planRepository = planRepository;
        this.tenantRepository = tenantRepository;
        this.passwordEncoder = passwordEncoder;
        this.emailService = emailService;
    }

    @Transactional(readOnly = true)
    public PageResponse<UserDto> layDanhSachNguoiDung(
            UUID tenantId,
            String q,
            String status,
            String roleCode,
            int page,
            int size,
            String sort
    ) {
        Sort sortObj = Sort.by(Sort.Direction.DESC, "createdAt");
        if (sort != null && !sort.isBlank()) {
            boolean isDesc = sort.startsWith("-");
            String field = isDesc ? sort.substring(1) : sort;
            if ("fullName".equalsIgnoreCase(field)) {
                sortObj = isDesc ? Sort.by(Sort.Direction.DESC, "fullName") : Sort.by(Sort.Direction.ASC, "fullName");
            } else if ("email".equalsIgnoreCase(field)) {
                sortObj = isDesc ? Sort.by(Sort.Direction.DESC, "email") : Sort.by(Sort.Direction.ASC, "email");
            } else if ("status".equalsIgnoreCase(field)) {
                sortObj = isDesc ? Sort.by(Sort.Direction.DESC, "status") : Sort.by(Sort.Direction.ASC, "status");
            } else if ("createdAt".equalsIgnoreCase(field)) {
                sortObj = isDesc ? Sort.by(Sort.Direction.DESC, "createdAt") : Sort.by(Sort.Direction.ASC, "createdAt");
            }
        }

        Pageable pageable = PageRequest.of(Math.max(0, page), Math.max(1, size), sortObj);
        Page<User> usersPage = userRepository.searchUsers(tenantId, q, status, pageable);

        List<UserDto> items = usersPage.getContent().stream()
                .map(this::toDto)
                .filter(u -> roleCode == null || roleCode.isBlank() || roleCode.equalsIgnoreCase(u.roleCode()))
                .toList();

        return PageResponse.of(items, usersPage.getNumber(), usersPage.getSize(), usersPage.getTotalElements());
    }

    @Transactional
    public UserDto moiNguoiDung(UUID tenantId, UUID grantedBy, InviteUserRequest req) {
        String normalizedEmail = req.email().trim().toLowerCase();

        if (userRepository.existsByTenantIdAndEmailIgnoreCaseAndDeletedAtIsNull(tenantId, normalizedEmail)) {
            throw new AppException("Email này đã tồn tại trong doanh nghiệp của bạn.", HttpStatus.CONFLICT);
        }

        // Kiểm tra hạn mức người dùng của gói dịch vụ
        subscriptionRepository.findFirstByTenantIdOrderByCreatedAtDesc(tenantId).ifPresent(sub -> {
            planRepository.findById(sub.getPlanId()).ifPresent(plan -> {
                long currentActive = userRepository.countActiveUsersByTenantId(tenantId);
                if (currentActive >= plan.getMaxUsers()) {
                    throw new AppException(
                            "Đã đạt giới hạn số lượng người dùng tối đa của gói (" + plan.getMaxUsers() + " người). Vui lòng nâng cấp gói dịch vụ.",
                            HttpStatus.PAYMENT_REQUIRED
                    );
                }
            });
        });

        // Tìm vai trò
        String roleCode = req.roleCode() != null ? req.roleCode().trim().toUpperCase() : "AGENT";
        Role role = roleRepository.findByCodeAndTenantIdIsNull(roleCode)
                .orElseThrow(() -> new AppException("Không tìm thấy vai trò: " + roleCode, HttpStatus.BAD_REQUEST));

        // Sinh mật khẩu ngẫu nhiên tạm thời
        String randomPassword = generateSecureRandomPassword();
        String passwordHash = passwordEncoder.encode(randomPassword);

        User user = new User();
        user.setTenantId(tenantId);
        user.setEmail(normalizedEmail);
        user.setFullName(req.fullName() != null && !req.fullName().isBlank() ? req.fullName().trim() : normalizedEmail);
        user.setPasswordHash(passwordHash);
        user.setScope("TENANT");
        user.setStatus("PENDING");
        user.setCreatedAt(Instant.now());
        user.setUpdatedAt(Instant.now());

        User savedUser = userRepository.save(user);

        // Gán vai trò
        UserRole userRole = new UserRole(new UserRoleId(savedUser.getId(), role.getId()), tenantId, grantedBy);
        userRoleRepository.save(userRole);

        // Gửi email lời mời tham gia
        String companyName = tenantRepository.findById(tenantId)
                .map(Tenant::getName)
                .orElse("Doanh nghiệp");

        emailService.guiThuMoiThanhVien(normalizedEmail, savedUser.getFullName(), companyName, role.getName());

        log.info("👤 Đã mời thành viên mới và gửi thư kích hoạt: email={} | role={} | tenantId={}", normalizedEmail, roleCode, tenantId);

        return toDto(savedUser, role.getCode(), role.getName());
    }

    @Transactional(readOnly = true)
    public UserDto layChiTietNguoiDung(UUID tenantId, UUID userId) {
        User user = userRepository.findByIdAndTenantIdAndDeletedAtIsNull(userId, tenantId)
                .orElseThrow(() -> new AppException("Không tìm thấy người dùng.", HttpStatus.NOT_FOUND));
        return toDto(user);
    }

    @Transactional
    public UserDto capNhatNguoiDung(UUID tenantId, UUID userId, UpdateUserRequest req) {
        User user = userRepository.findByIdAndTenantIdAndDeletedAtIsNull(userId, tenantId)
                .orElseThrow(() -> new AppException("Không tìm thấy người dùng.", HttpStatus.NOT_FOUND));

        if (req.fullName() != null && !req.fullName().isBlank()) {
            user.setFullName(req.fullName().trim());
        }

        if (req.status() != null && !req.status().isBlank()) {
            String st = req.status().trim().toUpperCase();
            if (List.of("ACTIVE", "PENDING", "DISABLED").contains(st)) {
                user.setStatus(st);
            }
        }

        user.setUpdatedAt(Instant.now());
        User updatedUser = userRepository.save(user);

        // Cập nhật vai trò nếu có
        if (req.roleCode() != null && !req.roleCode().isBlank()) {
            String roleCode = req.roleCode().trim().toUpperCase();
            Role newRole = roleRepository.findByCodeAndTenantIdIsNull(roleCode)
                    .orElseThrow(() -> new AppException("Không tìm thấy vai trò: " + roleCode, HttpStatus.BAD_REQUEST));

            // Xóa vai trò cũ và gán vai trò mới
            List<Role> currentRoles = roleRepository.findRolesByUserId(userId);
            for (Role r : currentRoles) {
                userRoleRepository.deleteById(new UserRoleId(userId, r.getId()));
            }
            userRoleRepository.save(new UserRole(new UserRoleId(userId, newRole.getId()), tenantId, null));
            return toDto(updatedUser, newRole.getCode(), newRole.getName());
        }

        return toDto(updatedUser);
    }

    @Transactional
    public UserDto voHieuHoaNguoiDung(UUID tenantId, UUID userId) {
        User user = userRepository.findByIdAndTenantIdAndDeletedAtIsNull(userId, tenantId)
                .orElseThrow(() -> new AppException("Không tìm thấy người dùng.", HttpStatus.NOT_FOUND));

        user.setStatus("DISABLED");
        user.setUpdatedAt(Instant.now());
        User saved = userRepository.save(user);
        log.info("⛔ Đã vô hiệu hoá người dùng: id={} | tenantId={}", userId, tenantId);
        return toDto(saved);
    }

    @Transactional
    public UserDto kichHoatNguoiDung(UUID tenantId, UUID userId) {
        User user = userRepository.findByIdAndTenantIdAndDeletedAtIsNull(userId, tenantId)
                .orElseThrow(() -> new AppException("Không tìm thấy người dùng.", HttpStatus.NOT_FOUND));

        user.setStatus("ACTIVE");
        user.setUpdatedAt(Instant.now());
        User saved = userRepository.save(user);
        log.info("✅ Đã kích hoạt lại người dùng: id={} | tenantId={}", userId, tenantId);
        return toDto(saved);
    }

    @Transactional
    public void guiLaiLoiMoi(UUID tenantId, UUID userId) {
        User user = userRepository.findByIdAndTenantIdAndDeletedAtIsNull(userId, tenantId)
                .orElseThrow(() -> new AppException("Không tìm thấy người dùng.", HttpStatus.NOT_FOUND));

        List<Role> roles = roleRepository.findRolesByUserId(userId);
        String roleName = !roles.isEmpty() ? roles.get(0).getName() : "Nhân viên chăm sóc khách hàng";

        String companyName = tenantRepository.findById(tenantId)
                .map(Tenant::getName)
                .orElse("Doanh nghiệp");

        emailService.guiThuMoiThanhVien(user.getEmail(), user.getFullName(), companyName, roleName);

        log.info("📨 Đã gửi lại email kích hoạt cho: email={} | tenantId={}", user.getEmail(), tenantId);
    }

    @Transactional
    public void xoaNguoiDung(UUID tenantId, UUID userId) {
        User user = userRepository.findByIdAndTenantIdAndDeletedAtIsNull(userId, tenantId)
                .orElseThrow(() -> new AppException("Không tìm thấy người dùng.", HttpStatus.NOT_FOUND));

        user.setDeletedAt(Instant.now());
        userRepository.save(user);
        log.info("🗑️ Đã xoá người dùng: id={} | tenantId={}", userId, tenantId);
    }

    private UserDto toDto(User u) {
        List<Role> roles = roleRepository.findRolesByUserId(u.getId());
        String roleCode = !roles.isEmpty() ? roles.get(0).getCode() : "AGENT";
        String roleName = !roles.isEmpty() ? roles.get(0).getName() : "Nhân viên chăm sóc khách hàng";
        return toDto(u, roleCode, roleName);
    }

    private UserDto toDto(User u, String roleCode, String roleName) {
        return new UserDto(
                u.getId(),
                u.getFullName(),
                u.getEmail(),
                roleCode,
                roleName,
                u.getStatus(),
                u.getEmailVerifiedAt(),
                u.getLastLoginAt(),
                0, // số hội thoại đang phụ trách
                u.getCreatedAt()
        );
    }

    private String generateSecureRandomPassword() {
        String chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*";
        SecureRandom random = new SecureRandom();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 12; i++) {
            sb.append(chars.charAt(random.nextInt(chars.length())));
        }
        return sb.toString();
    }
}
