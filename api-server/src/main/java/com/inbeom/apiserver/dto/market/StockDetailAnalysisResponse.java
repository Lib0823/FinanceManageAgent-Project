package com.inbeom.apiserver.dto.market;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

/**
 * 단일 종목 AI 분석 상세 응답 (종목 상세 화면 AI 분석 탭용)
 * GET /market/stock-detail/{stockCode}
 * - 정량(quant) / 감성(sentiment) / 시계열(timeseries) 3개 섹션 전체 노출
 * - 분석 유니버스(상위 30종목)에 포함된 적이 없으면 has_analysis=false, 3개 섹션은 null
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StockDetailAnalysisResponse {
    @JsonProperty("stock_code")
    private String stockCode;

    @JsonProperty("stock_name")
    private String stockName;

    @JsonProperty("analysis_date")
    private LocalDate analysisDate;

    // 해당 종목의 분석 데이터(stock_filter_score) 존재 여부
    @JsonProperty("has_analysis")
    private Boolean hasAnalysis;

    // 정량 분석 (has_analysis=false 이면 null)
    @JsonProperty("quant")
    private Quant quant;

    // 감성 분석 (has_analysis=false 이면 null)
    @JsonProperty("sentiment")
    private Sentiment sentiment;

    // 시계열 예측 (has_analysis=false 이면 null)
    @JsonProperty("timeseries")
    private Timeseries timeseries;

    /**
     * 정량 분석 섹션 (KIS 4지표 + 보조 2지표 + DART 재무 3지표)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Quant {
        @JsonProperty("foreign_net_buy")
        private Long foreignNetBuy;

        @JsonProperty("institutional_net_buy")
        private Long institutionalNetBuy;

        @JsonProperty("morning_return")
        private BigDecimal morningReturn;

        @JsonProperty("close_position")
        private BigDecimal closePosition;

        @JsonProperty("vol_avg_multiple")
        private BigDecimal volAvgMultiple;

        @JsonProperty("price_volatility")
        private BigDecimal priceVolatility;

        @JsonProperty("per")
        private BigDecimal per;

        @JsonProperty("roe")
        private BigDecimal roe;

        @JsonProperty("operating_margin")
        private BigDecimal operatingMargin;
    }

    /**
     * 감성 분석 섹션 (종목별 + 시장 전반 + 시장 감성 분포)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Sentiment {
        @JsonProperty("stock_sentiment_score")
        private BigDecimal stockSentimentScore;

        @JsonProperty("stock_news_count")
        private Integer stockNewsCount;

        @JsonProperty("market_sentiment_score")
        private BigDecimal marketSentimentScore;

        @JsonProperty("market_news_count")
        private Integer marketNewsCount;

        @JsonProperty("market_distribution")
        private Distribution marketDistribution;

        @JsonProperty("time_range")
        private String timeRange;

        @JsonProperty("market_sources")
        private String marketSources;

        /**
         * 시장 감성 분포 (긍정/중립/부정 카운트 + 비율 %)
         */
        @Data
        @Builder
        @NoArgsConstructor
        @AllArgsConstructor
        public static class Distribution {
            @JsonProperty("positive_count")
            private Integer positiveCount;

            @JsonProperty("neutral_count")
            private Integer neutralCount;

            @JsonProperty("negative_count")
            private Integer negativeCount;

            @JsonProperty("positive_percent")
            private Integer positivePercent;

            @JsonProperty("neutral_percent")
            private Integer neutralPercent;

            @JsonProperty("negative_percent")
            private Integer negativePercent;
        }
    }

    /**
     * 시계열 예측 섹션 (Prophet D+1~D+5 예측)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Timeseries {
        @JsonProperty("price_trend")
        private BigDecimal priceTrend;

        @JsonProperty("volume_trend")
        private BigDecimal volumeTrend;

        @JsonProperty("price_uncertainty")
        private BigDecimal priceUncertainty;

        @JsonProperty("training_days")
        private Integer trainingDays;

        // D+1~D+5 중 yhat 데이터가 있는 항목만 포함
        @JsonProperty("forecasts")
        private List<Forecast> forecasts;

        /**
         * D+N 예측 1건 (예측값 / 상·하한 / 불확실성 %)
         */
        @Data
        @Builder
        @NoArgsConstructor
        @AllArgsConstructor
        public static class Forecast {
            @JsonProperty("day")
            private String day;

            @JsonProperty("yhat")
            private BigDecimal yhat;

            @JsonProperty("yhat_upper")
            private BigDecimal yhatUpper;

            @JsonProperty("yhat_lower")
            private BigDecimal yhatLower;

            // 불확실성 % = (yhat_upper - yhat_lower) / yhat * 100 (소수 1자리)
            @JsonProperty("uncertainty_pct")
            private BigDecimal uncertaintyPct;
        }
    }
}
