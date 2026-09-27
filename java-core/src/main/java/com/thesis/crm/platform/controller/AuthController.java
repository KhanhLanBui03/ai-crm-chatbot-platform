package com.thesis.crm.platform.controller;

import com.thesis.crm.common.response.ApiResponse;
import com.thesis.crm.platform.dto.*;
import com.thesis.crm.platform.service.AuthService;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.*;

import java.util.UUID;

@RestController
@RequestMapping("/api/v1")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/auth/send-otp")
    public ResponseEntity<ApiResponse<Void>> sendOtp(@Valid @RequestBody SendOtpRequest request) {
        authService.guiOtp(request);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    @PostMapping("/auth/verify-otp")
    public ResponseEntity<ApiResponse<VerifyOtpResult>> verifyOtp(@Valid @RequestBody VerifyOtpRequest request) {
        VerifyOtpResult result = authService.xacThucOtp(request);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @PostMapping("/auth/register")
    public ResponseEntity<ApiResponse<DangKyResult>> register(@Valid @RequestBody DangKyRequest request) {
        DangKyResult result = authService.dangKy(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(result));
    }

    @PostMapping("/auth/login")
    public ResponseEntity<ApiResponse<KetQuaDangNhap>> login(
            @Valid @RequestBody DangNhapRequest request,
            HttpServletResponse response) {
        KetQuaDangNhap result = authService.dangNhap(request, response);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @PostMapping("/auth/verify-email")
    public ResponseEntity<ApiResponse<Void>> verifyEmail(@RequestBody VerifyEmailRequest request) {
        authService.xacThucThu(request.token());
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    @PostMapping("/auth/resend-verification")
    public ResponseEntity<ApiResponse<Void>> resendVerification(@RequestBody ResendVerificationRequest request) {
        authService.guiLaiThuXacThuc(request.email());
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(ApiResponse.ok(null));
    }

    @PostMapping("/auth/forgot-password")
    public ResponseEntity<ApiResponse<Void>> forgotPassword(@Valid @RequestBody ForgotPasswordRequest request) {
        authService.quenMatKhau(request);
        return ResponseEntity.status(HttpStatus.ACCEPTED).body(ApiResponse.ok(null));
    }

    @PostMapping("/auth/reset-password")
    public ResponseEntity<ApiResponse<Void>> resetPassword(@Valid @RequestBody ResetPasswordRequest request) {
        authService.datLaiMatKhau(request);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    @PostMapping("/auth/refresh")
    public ResponseEntity<ApiResponse<TokenRefreshResult>> refresh(
            @CookieValue(name = "refresh_token", required = false) String refreshToken) {
        TokenRefreshResult result = authService.lamMoiToken(refreshToken);
        return ResponseEntity.ok(ApiResponse.ok(result));
    }

    @PostMapping("/auth/logout")
    public ResponseEntity<ApiResponse<Void>> logout(
            @CookieValue(name = "refresh_token", required = false) String refreshToken,
            HttpServletResponse response) {
        authService.dangXuat(refreshToken, response);
        return ResponseEntity.ok(ApiResponse.ok(null));
    }

    @GetMapping("/me")
    public ResponseEntity<ApiResponse<NguoiDungHienTaiDto>> getMe(@AuthenticationPrincipal Jwt jwt) {
        UUID userId = UUID.fromString(jwt.getSubject());
        NguoiDungHienTaiDto profile = authService.layHoSoCuaToi(userId);
        return ResponseEntity.ok(ApiResponse.ok(profile));
    }
}
