package com.inbeom.apiserver.dto.market;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MarketHeatmapResponse {
    @JsonProperty("date")
    private LocalDate date;

    @JsonProperty("stocks")
    private List<StockFeatures> stocks;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class StockFeatures {
        @JsonProperty("stock_code")
        private String stockCode;

        @JsonProperty("stock_name")
        private String stockName;

        // Stage 1 필터링 지표
        @JsonProperty("foreign_net_buy")
        private Long foreignNetBuy;

        @JsonProperty("institutional_net_buy")
        private Long institutionalNetBuy;

        @JsonProperty("vol_avg_multiple")
        private BigDecimal volAvgMultiple;

        @JsonProperty("price_volatility")
        private BigDecimal priceVolatility;

        // Stage 2-1 정량 지표
        @JsonProperty("morning_return")
        private BigDecimal morningReturn;

        @JsonProperty("close_position")
        private BigDecimal closePosition;

        // DART 재무 지표
        @JsonProperty("per")
        private BigDecimal per;

        @JsonProperty("roe")
        private BigDecimal roe;

        @JsonProperty("operating_margin")
        private BigDecimal operatingMargin;

        // Stage 2-2 감성 지표
        @JsonProperty("sentiment_score")
        private BigDecimal sentimentScore;

        // Stage 2-3 시계열 지표
        @JsonProperty("price_trend")
        private BigDecimal priceTrend;

        @JsonProperty("volume_trend")
        private BigDecimal volumeTrend;

        @JsonProperty("price_uncertainty")
        private BigDecimal priceUncertainty;
    }
}
