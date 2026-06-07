package com.inbeom.apiserver.client;

import com.inbeom.apiserver.service.KisAuthService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class KisApiClient {

    private final RestTemplate restTemplate = new RestTemplate();

    @Value("${kis.base-url}")
    private String kisBaseUrl;

    /**
     * Check if current KIS API is real trading mode
     * - Virtual trading: openapivts.koreainvestment.com
     * - Real trading: openapi.koreainvestment.com
     */
    private boolean isRealTrading() {
        return kisBaseUrl != null && kisBaseUrl.contains("openapi.koreainvestment.com");
    }

    /**
     * Convert TR_ID based on KIS base URL
     * - Virtual trading (openapivts): VTTC* (모의투자)
     * - Real trading (openapi): TTTC* (실전투자)
     *
     * @param baseTrId Base TR_ID (e.g., "VTTC8434R")
     * @return Converted TR_ID based on base URL
     */
    public String convertTrId(String baseTrId) {
        if (baseTrId == null || baseTrId.length() < 4) {
            return baseTrId;
        }

        String suffix = baseTrId.substring(4); // "8434R" 부분
        String prefix = isRealTrading() ? "TTTC" : "VTTC";

        return prefix + suffix;
    }

    /**
     * Call KIS API with authentication headers
     * TR_ID는 base URL에 따라 자동 변환됩니다 (VTTC ↔ TTTC)
     */
    public <T> ResponseEntity<T> callKisApi(
            String endpoint,
            HttpMethod method,
            String trId,
            String kisToken,
            String appKey,
            String appSecret,
            Object requestBody,
            Class<T> responseType
    ) {
        String url = kisBaseUrl + endpoint;

        // TR_ID 자동 변환 (Virtual → VTTC*, Real → TTTC*)
        String convertedTrId = convertTrId(trId);
        String mode = isRealTrading() ? "REAL" : "VIRTUAL";
        log.debug("TR_ID conversion: {} → {} (mode: {})", trId, convertedTrId, mode);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("authorization", "Bearer " + kisToken);
        headers.set("appkey", appKey);
        headers.set("appsecret", appSecret);
        headers.set("tr_id", convertedTrId);  // 변환된 TR_ID 사용
        headers.set("custtype", "P");

        HttpEntity<?> request = new HttpEntity<>(requestBody, headers);

        try {
            ResponseEntity<T> response = restTemplate.exchange(url, method, request, responseType);
            log.debug("KIS API call success: {} {}, status={}", method, endpoint, response.getStatusCode());
            return response;
        } catch (Exception e) {
            log.error("KIS API call failed: {} {}", method, endpoint, e);
            throw new RuntimeException("KIS API call failed: " + e.getMessage(), e);
        }
    }

    /**
     * GET request to KIS API
     */
    public <T> ResponseEntity<T> get(
            String endpoint,
            String trId,
            String kisToken,
            String appKey,
            String appSecret,
            Map<String, String> queryParams,
            Class<T> responseType
    ) {
        // Build query string
        StringBuilder urlBuilder = new StringBuilder(endpoint);
        if (queryParams != null && !queryParams.isEmpty()) {
            urlBuilder.append("?");
            queryParams.forEach((key, value) ->
                    urlBuilder.append(key).append("=").append(value).append("&")
            );
            urlBuilder.setLength(urlBuilder.length() - 1); // Remove last &
        }

        return callKisApi(urlBuilder.toString(), HttpMethod.GET, trId, kisToken, appKey, appSecret, null, responseType);
    }

    /**
     * POST request to KIS API
     */
    public <T> ResponseEntity<T> post(
            String endpoint,
            String trId,
            String kisToken,
            String appKey,
            String appSecret,
            Object requestBody,
            Class<T> responseType
    ) {
        return callKisApi(endpoint, HttpMethod.POST, trId, kisToken, appKey, appSecret, requestBody, responseType);
    }
}
