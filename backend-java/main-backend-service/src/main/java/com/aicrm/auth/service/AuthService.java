package com.aicrm.auth.service;

import com.aicrm.auth.dto.request.LoginRequest;
import com.aicrm.auth.dto.request.RegisterRequest;
import com.aicrm.auth.dto.response.CurrentUserResponse;
import com.aicrm.auth.dto.response.LoginResponse;
import com.aicrm.auth.security.UserPrincipal;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
public class AuthService {

    @Autowired
    private JwtService jwtService;

    @Autowired
    private CustomUserDetailsService userDetailsService;

    @Autowired
    private PasswordEncoder passwordEncoder;

    public LoginResponse login(LoginRequest request) {
        var userDetails = (UserPrincipal) userDetailsService.loadUserByUsername(request.getEmail());

        if (!passwordEncoder.matches(request.getPassword(), userDetails.getPassword())) {
            throw new RuntimeException("Invalid username or password");
        }

        String token = jwtService.generateToken(userDetails.getEmail(), userDetails.getRole());

        return LoginResponse.builder()
                .accessToken(token)
                .refreshToken("mock-refresh-token")
                .tokenType("Bearer")
                .user(CurrentUserResponse.builder()
                        .id(userDetails.getId())
                        .email(userDetails.getEmail())
                        .fullName(userDetails.getFullName())
                        .role(userDetails.getRole())
                        .businessId(userDetails.getBusinessId())
                        .build())
                .build();
    }

    public void register(RegisterRequest request) {
        // Encode password and persist User and Business entities.
    }
}
