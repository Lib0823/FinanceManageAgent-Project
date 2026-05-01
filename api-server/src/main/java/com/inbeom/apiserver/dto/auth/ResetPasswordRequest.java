package com.inbeom.apiserver.dto.auth;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class ResetPasswordRequest {

    @NotBlank(message = "Username is required")
    private String username;

    @NotBlank(message = "Phone is required")
    @Pattern(regexp = "^010\\d{8}$", message = "Phone must be 11 digits starting with 010")
    private String phone;

    @NotBlank(message = "New password is required")
    @Size(min = 8, message = "Password must be at least 8 characters")
    @Pattern(regexp = "^(?=.*[A-Za-z])(?=.*\\d)(?=.*[@$!%*#?&])[A-Za-z\\d@$!%*#?&]+$",
             message = "Password must contain letters, numbers and special characters")
    private String newPassword;

    @NotBlank(message = "Password confirmation is required")
    private String passwordConfirm;
}
