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
 * 단일 종목 AI 분석 요약 응답 (Bot 화면 보유 종목 카드용)
 * GET /market/stock-analysis/{stockCode}
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StockAnalysisResponse {
    @JsonProperty("stock_code")
    private String stockCode;

    @JsonProperty("stock_name")
    private String stockName;

    @JsonProperty("analysis_date")
    private LocalDate analysisDate;

    // 해당 종목의 분석 데이터(stock_filter_score) 존재 여부
    @JsonProperty("has_analysis")
    private Boolean hasAnalysis;

    // 한두 문장 자연어 요약 (프론트 상단 표시)
    @JsonProperty("headline")
    private String headline;

    // 프론트 표시용 핵심 지표 (color-coded 미니 표) — 데이터가 있는 항목만 포함
    @JsonProperty("metrics")
    private List<Metric> metrics;

    // raw 큐레이션 피처 (프론트 유연성 위해 함께 노출)
    @JsonProperty("foreign_net_buy")
    private Long foreignNetBuy;

    @JsonProperty("institutional_net_buy")
    private Long institutionalNetBuy;

    @JsonProperty("sentiment_score")
    private BigDecimal sentimentScore;

    @JsonProperty("news_count")
    private Integer newsCount;

    // 5일 예상 수익률 % — (yhat_d5 - yhat_d1) / yhat_d1 * 100
    @JsonProperty("expected_return_5d")
    private BigDecimal expectedReturn5d;

    @JsonProperty("per")
    private BigDecimal per;

    @JsonProperty("roe")
    private BigDecimal roe;

    @JsonProperty("operating_margin")
    private BigDecimal operatingMargin;

    /**
     * 핵심 지표 1개 (라벨 / 표시값 / 색상 톤)
     * tone: "positive"(상승·순매수, 빨강) / "negative"(하락·순매도, 파랑) / "neutral"(회색)
     */
    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Metric {
        @JsonProperty("label")
        private String label;

        @JsonProperty("value")
        private String value;

        @JsonProperty("tone")
        private String tone;
    }
}
