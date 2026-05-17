package com.inbeom.apiserver.dto.kis;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KisTokenRequest {

    @JsonProperty("grant_type")
    private String grantType;

    @JsonProperty("appkey")
    private String appKey;

    @JsonProperty("appsecret")
    private String appSecret;
}
