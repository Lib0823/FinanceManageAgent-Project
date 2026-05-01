package com.inbeom.apiserver.controller;

import com.inbeom.apiserver.dto.auth.*;
import com.inbeom.apiserver.dto.common.ApiResponse;
import com.inbeom.apiserver.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public ApiResponse<LoginResponse> login(@Valid @RequestBody LoginRequest request) {
        try {
            LoginResponse response = authService.login(request);
            return ApiResponse.success("Login successful", response);
        } catch (BadCredentialsException e) {
            return ApiResponse.error("Invalid credentials");
        }
    }

    @PostMapping("/register")
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<RegisterResponse> register(@Valid @RequestBody RegisterRequest request) {
        try {
            RegisterResponse response = authService.register(request);
            return ApiResponse.success("Registration successful", response);
        } catch (IllegalArgumentException e) {
            return ApiResponse.error(e.getMessage());
        }
    }

    @PostMapping("/reset-password")
    public ApiResponse<Void> resetPassword(@Valid @RequestBody ResetPasswordRequest request) {
        try {
            authService.resetPassword(request);
            return ApiResponse.success("Password reset successful", null);
        } catch (IllegalArgumentException e) {
            return ApiResponse.error(e.getMessage());
        }
    }

    @GetMapping("/check-username")
    public ApiResponse<CheckAvailabilityResponse> checkUsername(@RequestParam String username) {
        CheckAvailabilityResponse response = authService.checkUsername(username);
        String message = response.isAvailable() ? "Username is available" : "Username is already taken";
        return ApiResponse.success(message, response);
    }

    @GetMapping("/check-email")
    public ApiResponse<CheckAvailabilityResponse> checkEmail(@RequestParam String email) {
        CheckAvailabilityResponse response = authService.checkEmail(email);
        String message = response.isAvailable() ? "Email is available" : "Email is already taken";
        return ApiResponse.success(message, response);
    }

    @PostMapping("/refresh")
    public ApiResponse<RefreshTokenResponse> refreshToken(@Valid @RequestBody RefreshTokenRequest request) {
        try {
            RefreshTokenResponse response = authService.refreshToken(request);
            return ApiResponse.success("Token refreshed", response);
        } catch (BadCredentialsException e) {
            return ApiResponse.error(e.getMessage());
        }
    }
}
