package com.inbeom.apiserver.service;

import com.inbeom.apiserver.dto.market.*;
import com.inbeom.apiserver.repository.MarketAnalysisRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class MarketAnalysisService {

    private final MarketAnalysisRepository marketAnalysisRepository;

    /**
     * 시장 전체 요약 데이터 조회
     */
    @Transactional(readOnly = true)
    public MarketSummaryResponse getMarketSummary(LocalDate date) {
        try {
            Map<String, Object> summary = marketAnalysisRepository.getMarketSummary(date);

            // No data available for this date
            if (summary == null) {
                log.info("No market summary data found for date: {}", date);
                return null;
            }

            Map<String, Object> statistics = marketAnalysisRepository.getStockStatistics(date);

            return MarketSummaryResponse.builder()
                    .date(date)
                    .kospi(MarketSummaryResponse.KospiInfo.builder()
                            .index((BigDecimal) summary.get("kospi_index"))
                            .changeRate((BigDecimal) summary.get("kospi_change_rate"))
                            .volume((Long) summary.get("kospi_volume"))
                            .build())
                    .statistics(MarketSummaryResponse.StockStatistics.builder()
                            .total(((Number) summary.get("total_stocks")).intValue())
                            .rising(((Number) summary.get("rising_stocks")).intValue())
                            .falling(((Number) summary.get("falling_stocks")).intValue())
                            .unchanged(((Number) summary.get("unchanged_stocks")).intValue())
                            .buyCandidate(((Number) statistics.get("buy_candidate")).intValue())
                            .sellCandidate(((Number) statistics.get("sell_candidate")).intValue())
                            .neutral(((Number) statistics.get("neutral")).intValue())
                            .build())
                    .supplyDemand(MarketSummaryResponse.SupplyDemand.builder()
                            .foreignNetBuy((Long) summary.get("total_foreign_net_buy"))
                            .institutionalNetBuy((Long) summary.get("total_institutional_net_buy"))
                            .build())
                    .marketSentiment((BigDecimal) summary.get("market_sentiment_score"))
                    .build();
        } catch (Exception e) {
            log.error("Failed to get market summary for date: {}", date, e);
            throw new RuntimeException("Failed to get market summary", e);
        }
    }

    /**
     * 시장 감성 분석 데이터 조회
     */
    @Transactional(readOnly = true)
    public MarketSentimentResponse getMarketSentiment(LocalDate date) {
        try {
            Map<String, Object> sentiment = marketAnalysisRepository.getMarketSentiment(date);

            // No data available for this date
            if (sentiment == null) {
                log.info("No market sentiment data found for date: {}", date);
                return null;
            }

            BigDecimal sentimentScore = (BigDecimal) sentiment.get("sentiment_score");

            @SuppressWarnings("unchecked")
            Map<String, Object> distribution = (Map<String, Object>) sentiment.get("distribution");

            int totalCount = ((Number) distribution.get("total_count")).intValue();
            int positiveCount = ((Number) distribution.get("positive_count")).intValue();
            int neutralCount = ((Number) distribution.get("neutral_count")).intValue();
            int negativeCount = ((Number) distribution.get("negative_count")).intValue();

            int positivePercent = calculatePercent(positiveCount, totalCount);
            int neutralPercent = calculatePercent(neutralCount, totalCount);
            int negativePercent = calculatePercent(negativeCount, totalCount);

            String label = getSentimentLabel(sentimentScore);

            return MarketSentimentResponse.builder()
                    .score(sentimentScore)
                    .label(label)
                    .distribution(MarketSentimentResponse.Distribution.builder()
                            .positive(MarketSentimentResponse.CategoryInfo.builder()
                                    .count(positiveCount)
                                    .percent(positivePercent)
                                    .color("#f87171")
                                    .build())
                            .neutral(MarketSentimentResponse.CategoryInfo.builder()
                                    .count(neutralCount)
                                    .percent(neutralPercent)
                                    .color("#4a5568")
                                    .build())
                            .negative(MarketSentimentResponse.CategoryInfo.builder()
                                    .count(negativeCount)
                                    .percent(negativePercent)
                                    .color("#60a5fa")
                                    .build())
                            .build())
                    .timeRange("전날 18:00 — 당일 08:50")
                    .sources("한경 · 매경 · 연합")
                    .build();
        } catch (Exception e) {
            log.error("Failed to get market sentiment for date: {}", date, e);
            throw new RuntimeException("Failed to get market sentiment", e);
        }
    }

    /**
     * AI 매매 결정 TOP3 조회
     */
    @Transactional(readOnly = true)
    public MarketDecisionsResponse getMarketDecisions(LocalDate date) {
        try {
            List<Map<String, Object>> buyDecisions = marketAnalysisRepository.getDecisionTop3(date, "buy");
            List<Map<String, Object>> sellDecisions = marketAnalysisRepository.getDecisionTop3(date, "sell");

            List<MarketDecisionsResponse.DecisionStock> buyTop3 = mapDecisionStocks(buyDecisions);
            List<MarketDecisionsResponse.DecisionStock> sellTop3 = mapDecisionStocks(sellDecisions);

            // Fill empty slots if less than 3
            while (buyTop3.size() < 3) {
                buyTop3.add(createEmptyDecisionStock(buyTop3.size() + 1));
            }
            while (sellTop3.size() < 3) {
                sellTop3.add(createEmptyDecisionStock(sellTop3.size() + 1));
            }

            return MarketDecisionsResponse.builder()
                    .buyTop3(buyTop3)
                    .sellTop3(sellTop3)
                    .build();
        } catch (Exception e) {
            log.error("Failed to get market decisions for date: {}", date, e);
            throw new RuntimeException("Failed to get market decisions", e);
        }
    }

    private List<MarketDecisionsResponse.DecisionStock> mapDecisionStocks(List<Map<String, Object>> decisions) {
        List<MarketDecisionsResponse.DecisionStock> stocks = new ArrayList<>();

        for (Map<String, Object> decision : decisions) {
            BigDecimal score = decision.get("confidence_score") != null
                    ? (BigDecimal) decision.get("confidence_score")
                    : BigDecimal.ZERO;

            stocks.add(MarketDecisionsResponse.DecisionStock.builder()
                    .rank(((Number) decision.get("rank")).intValue())
                    .stockCode((String) decision.get("stock_code"))
                    .stockName((String) decision.get("stock_name"))
                    .reason((String) decision.get("reason"))
                    .score(score)
                    .currentPrice((Long) decision.get("current_price"))
                    .changeRate((BigDecimal) decision.get("change_rate"))
                    .build());
        }

        return stocks;
    }

    private MarketDecisionsResponse.DecisionStock createEmptyDecisionStock(int rank) {
        return MarketDecisionsResponse.DecisionStock.builder()
                .rank(rank)
                .stockCode(null)
                .stockName("해당 없음")
                .reason("")
                .score(null)
                .currentPrice(null)
                .changeRate(null)
                .build();
    }

    private int calculatePercent(int count, int total) {
        if (total == 0) {
            return 0;
        }
        return BigDecimal.valueOf(count)
                .multiply(BigDecimal.valueOf(100))
                .divide(BigDecimal.valueOf(total), 0, RoundingMode.HALF_UP)
                .intValue();
    }

    private String getSentimentLabel(BigDecimal score) {
        if (score.compareTo(BigDecimal.valueOf(0.3)) >= 0) {
            return "긍정 우세";
        } else if (score.compareTo(BigDecimal.valueOf(-0.3)) <= 0) {
            return "부정 우세";
        } else {
            return "중립";
        }
    }

    /**
     * 최신 분석 날짜 조회
     */
    @Transactional(readOnly = true)
    public LatestDateResponse getLatestAnalysisDate() {
        try {
            LocalDate latestDate = marketAnalysisRepository.getLatestAnalysisDate();
            return LatestDateResponse.builder()
                    .latestDate(latestDate)
                    .build();
        } catch (Exception e) {
            log.error("Failed to get latest analysis date", e);
            throw new RuntimeException("Failed to get latest analysis date", e);
        }
    }

    /**
     * 30종목 히트맵 데이터 조회
     */
    @Transactional(readOnly = true)
    public MarketHeatmapResponse getHeatmapData(LocalDate date) {
        try {
            List<Map<String, Object>> heatmapData = marketAnalysisRepository.getHeatmapData(date);

            List<MarketHeatmapResponse.StockFeatures> stocks = new ArrayList<>();
            for (Map<String, Object> row : heatmapData) {
                stocks.add(MarketHeatmapResponse.StockFeatures.builder()
                        .stockCode((String) row.get("stock_code"))
                        .stockName((String) row.get("stock_name"))
                        .foreignNetBuy((Long) row.get("foreign_net_buy"))
                        .institutionalNetBuy((Long) row.get("institutional_net_buy"))
                        .volAvgMultiple((BigDecimal) row.get("vol_avg_multiple"))
                        .priceVolatility((BigDecimal) row.get("price_volatility"))
                        .morningReturn((BigDecimal) row.get("morning_return"))
                        .closePosition((BigDecimal) row.get("close_position"))
                        .per((BigDecimal) row.get("per"))
                        .roe((BigDecimal) row.get("roe"))
                        .operatingMargin((BigDecimal) row.get("operating_margin"))
                        .sentimentScore((BigDecimal) row.get("sentiment_score"))
                        .priceTrend((BigDecimal) row.get("price_trend"))
                        .volumeTrend((BigDecimal) row.get("volume_trend"))
                        .priceUncertainty((BigDecimal) row.get("price_uncertainty"))
                        .build());
            }

            return MarketHeatmapResponse.builder()
                    .date(date)
                    .stocks(stocks)
                    .build();
        } catch (Exception e) {
            log.error("Failed to get heatmap data for date: {}", date, e);
            throw new RuntimeException("Failed to get heatmap data", e);
        }
    }
}
