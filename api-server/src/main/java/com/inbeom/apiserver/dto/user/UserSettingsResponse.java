package com.inbeom.apiserver.dto.user;

import tools.jackson.databind.JsonNode;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserSettingsResponse {

    private JsonNode assetOrder;
    private Boolean darkMode;
    private Boolean autoLogin;
    private JsonNode notifications;
}
