package com.inbeom.apiserver.dto.market;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MarketDecisionsResponse {
    @JsonProperty("buy_top3")
    private List<DecisionStock> buyTop3;

    @JsonProperty("sell_top3")
    private List<DecisionStock> sellTop3;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class DecisionStock {
        @JsonProperty("rank")
        private Integer rank;

        @JsonProperty("stock_code")
        private String stockCode;

        @JsonProperty("stock_name")
        private String stockName;

        @JsonProperty("reason")
        private String reason;

        @JsonProperty("score")
        private BigDecimal score;

        @JsonProperty("current_price")
        private Long currentPrice;

        @JsonProperty("change_rate")
        private BigDecimal changeRate;
    }
}
