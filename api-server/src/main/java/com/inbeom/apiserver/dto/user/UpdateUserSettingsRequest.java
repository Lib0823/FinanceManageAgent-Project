package com.inbeom.apiserver.dto.user;

import tools.jackson.databind.JsonNode;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UpdateUserSettingsRequest {

    private JsonNode assetOrder;

    @NotNull(message = "다크 모드 설정은 필수입니다")
    private Boolean darkMode;

    @NotNull(message = "자동 로그인 설정은 필수입니다")
    private Boolean autoLogin;

    private JsonNode notifications;
}
