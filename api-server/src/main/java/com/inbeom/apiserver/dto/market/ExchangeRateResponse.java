package com.inbeom.apiserver.dto.market;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

/**
 * 홈 화면 "환율" 위젯용 단일 통화 환율 항목.
 * 환율 데이터는 frankfurter.app (ECB, 무료/키 불필요) 에서 조회한다.
 * JPY 는 100엔 기준으로 환산해 전달한다(others 는 1단위 기준).
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExchangeRateResponse {

    @JsonProperty("currency")
    private String currency;

    @JsonProperty("country")
    private String country;

    @JsonProperty("rate")
    private BigDecimal rate;

    @JsonProperty("change")
    private BigDecimal change;

    @JsonProperty("change_percent")
    private BigDecimal changePercent;

    @JsonProperty("history")
    private List<BigDecimal> history;
}
