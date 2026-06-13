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

    @JsonProperty("summary")
    private HeatmapSummary summary;

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
        // price_trend: ai-agent에서 저장한 원/day 단위 슬로프 (사용자 표시 부적합, 호환성 위해 유지)
        @JsonProperty("price_trend")
        private BigDecimal priceTrend;

        @JsonProperty("volume_trend")
        private BigDecimal volumeTrend;

        @JsonProperty("price_uncertainty")
        private BigDecimal priceUncertainty;

        // 5일 예상 수익률 % — yhat_d1, yhat_d5 기반 계산값 (사용자 표시용)
        // 공식: (yhat_d5 - yhat_d1) / yhat_d1 * 100
        @JsonProperty("expected_return_5d")
        private BigDecimal expectedReturn5d;

        // Prophet raw 예측치 (D+1 ~ D+5) — 시장 평균 예측 추이 계산용 노출
        @JsonProperty("yhat_d1")
        private BigDecimal yhatD1;

        @JsonProperty("yhat_d2")
        private BigDecimal yhatD2;

        @JsonProperty("yhat_d3")
        private BigDecimal yhatD3;

        @JsonProperty("yhat_d4")
        private BigDecimal yhatD4;

        @JsonProperty("yhat_d5")
        private BigDecimal yhatD5;

        @JsonProperty("yhat_upper_d5")
        private BigDecimal yhatUpperD5;

        @JsonProperty("yhat_lower_d5")
        private BigDecimal yhatLowerD5;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class HeatmapSummary {
        @JsonProperty("avg_foreign_net_buy")
        private Long avgForeignNetBuy;

        @JsonProperty("avg_institutional_net_buy")
        private Long avgInstitutionalNetBuy;

        @JsonProperty("avg_sentiment_score")
        private BigDecimal avgSentimentScore;

        @JsonProperty("positive_sentiment_count")
        private Integer positiveSentimentCount;

        @JsonProperty("negative_sentiment_count")
        private Integer negativeSentimentCount;

        @JsonProperty("positive_trend_count")
        private Integer positiveTrendCount;

        @JsonProperty("top_stock")
        private TopStock topStock;

        // 신규: 5일 예측 전망 (Prophet 데이터 기반)
        @JsonProperty("forecast_outlook")
        private ForecastOutlook forecastOutlook;

        // 신규: 펀더멘탈 분석 (DART 데이터 기반)
        @JsonProperty("financial_health")
        private FinancialHealth financialHealth;

        // 신규: 수급 매트릭스 (스마트머니 4분면)
        @JsonProperty("smart_money_flow")
        private SmartMoneyFlow smartMoneyFlow;

        // 신규: D+1 ~ D+5 시장 평균 예측 추이
        @JsonProperty("market_forecast_trend")
        private MarketForecastTrend marketForecastTrend;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class TopStock {
        @JsonProperty("stock_code")
        private String stockCode;

        @JsonProperty("stock_name")
        private String stockName;

        @JsonProperty("positive_features")
        private Integer positiveFeatures;
    }

    /**
     * 5일 예측 전망 (Prophet 데이터 기반)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class ForecastOutlook {
        @JsonProperty("rising_count")
        private Integer risingCount;

        @JsonProperty("falling_count")
        private Integer fallingCount;

        // 기존 슬로프 기반 평균 (원/day) — 더 이상 사용자 표시 권장 안 함, 호환성 유지
        @JsonProperty("avg_price_trend")
        private BigDecimal avgPriceTrend;

        @JsonProperty("avg_volume_trend")
        private BigDecimal avgVolumeTrend;

        @JsonProperty("avg_uncertainty")
        private BigDecimal avgUncertainty;

        // 신규: 평균 불확실성 (가격 대비 비율 %) — uncertainty_level 산출 기준
        @JsonProperty("avg_uncertainty_pct")
        private BigDecimal avgUncertaintyPct;

        // 신규: 5일 평균 예상 수익률 % (사용자 표시용)
        @JsonProperty("avg_expected_return_5d")
        private BigDecimal avgExpectedReturn5d;

        @JsonProperty("uncertainty_level")
        private String uncertaintyLevel;

        @JsonProperty("top_outlook_stock")
        private OutlookStock topOutlookStock;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class OutlookStock {
        @JsonProperty("stock_code")
        private String stockCode;

        @JsonProperty("stock_name")
        private String stockName;

        // 기존: 슬로프 (호환성 유지)
        @JsonProperty("price_trend")
        private BigDecimal priceTrend;

        // 신규: 5일 예상 수익률 % (사용자 표시용)
        @JsonProperty("expected_return_5d")
        private BigDecimal expectedReturn5d;
    }

    /**
     * 펀더멘탈 분석 (DART 데이터 기반)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class FinancialHealth {
        @JsonProperty("avg_per")
        private BigDecimal avgPer;

        @JsonProperty("avg_roe")
        private BigDecimal avgRoe;

        @JsonProperty("avg_operating_margin")
        private BigDecimal avgOperatingMargin;

        @JsonProperty("undervalued_count")
        private Integer undervaluedCount;

        @JsonProperty("high_roe_count")
        private Integer highRoeCount;

        @JsonProperty("high_margin_count")
        private Integer highMarginCount;

        @JsonProperty("excellent_count")
        private Integer excellentCount;

        @JsonProperty("data_coverage")
        private Integer dataCoverage;
    }

    /**
     * 수급 매트릭스 (스마트머니 4분면)
     * - Q1: 외국인+ 기관+ (동반 매수)
     * - Q2: 외국인+ 기관- (디커플링 A)
     * - Q3: 외국인- 기관- (동반 매도)
     * - Q4: 외국인- 기관+ (디커플링 B)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SmartMoneyFlow {
        @JsonProperty("both_buy_count")
        private Integer bothBuyCount;

        @JsonProperty("foreign_only_buy_count")
        private Integer foreignOnlyBuyCount;

        @JsonProperty("both_sell_count")
        private Integer bothSellCount;

        @JsonProperty("institutional_only_buy_count")
        private Integer institutionalOnlyBuyCount;

        // (Q1 + Q3) / total * 100 — 외국인-기관 의견 일치도
        @JsonProperty("consensus_pct")
        private Integer consensusPct;

        // "BOTH_BUY" / "BOTH_SELL" / "MIXED"
        @JsonProperty("dominant_signal")
        private String dominantSignal;

        @JsonProperty("smart_money_top_stock")
        private SmartMoneyStock smartMoneyTopStock;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SmartMoneyStock {
        @JsonProperty("stock_code")
        private String stockCode;

        @JsonProperty("stock_name")
        private String stockName;

        // foreign_net_buy + institutional_net_buy
        @JsonProperty("combined_net_buy")
        private Long combinedNetBuy;
    }

    /**
     * D+1 ~ D+5 시장 평균 예측 추이
     * - 각 종목의 yhat_d1 을 기준점(0%)으로 yhat_dN 의 변동률(%)을 계산한 뒤 종목 평균
     * - d5_upper_pct / d5_lower_pct: yhat_upper_d5 / yhat_lower_d5 기준 신뢰구간 (%)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class MarketForecastTrend {
        @JsonProperty("d1_return_pct")
        private BigDecimal d1ReturnPct;

        @JsonProperty("d2_return_pct")
        private BigDecimal d2ReturnPct;

        @JsonProperty("d3_return_pct")
        private BigDecimal d3ReturnPct;

        @JsonProperty("d4_return_pct")
        private BigDecimal d4ReturnPct;

        @JsonProperty("d5_return_pct")
        private BigDecimal d5ReturnPct;

        @JsonProperty("d5_upper_pct")
        private BigDecimal d5UpperPct;

        @JsonProperty("d5_lower_pct")
        private BigDecimal d5LowerPct;

        // "상승세" / "하락세" / "횡보"
        @JsonProperty("trend_direction")
        private String trendDirection;

        @JsonProperty("data_count")
        private Integer dataCount;
    }
}
