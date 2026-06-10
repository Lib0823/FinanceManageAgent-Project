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
     * - market_daily_summary 데이터가 없어도 stock_filter_score/ai_trade_decision 기반 통계는 반환
     */
    @Transactional(readOnly = true)
    public MarketSummaryResponse getMarketSummary(LocalDate date) {
        try {
            Map<String, Object> summary = marketAnalysisRepository.getMarketSummary(date);
            Map<String, Object> statistics = marketAnalysisRepository.getStockStatistics(date);

            // KOSPI 정보와 공급/수요는 market_daily_summary가 있을 때만 채움
            MarketSummaryResponse.KospiInfo kospi = null;
            MarketSummaryResponse.SupplyDemand supplyDemand = null;
            BigDecimal marketSentiment = null;

            if (summary != null) {
                kospi = MarketSummaryResponse.KospiInfo.builder()
                        .index(toBigDecimal(summary.get("kospi_index")))
                        .changeRate(toBigDecimal(summary.get("kospi_change_rate")))
                        .volume(toLong(summary.get("kospi_volume")))
                        .build();

                supplyDemand = MarketSummaryResponse.SupplyDemand.builder()
                        .foreignNetBuy(toLong(summary.get("total_foreign_net_buy")))
                        .institutionalNetBuy(toLong(summary.get("total_institutional_net_buy")))
                        .build();

                marketSentiment = toBigDecimal(summary.get("market_sentiment_score"));
            } else {
                log.info("No market_daily_summary data for date: {} - returning partial response", date);
            }

            // statistics는 항상 채움 (summary의 totals를 우선 사용, 없으면 stock_filter_score 기반 total_stocks)
            MarketSummaryResponse.StockStatistics stockStatistics = MarketSummaryResponse.StockStatistics.builder()
                    .total(summary != null
                            ? toInt(summary.get("total_stocks"))
                            : toInt(statistics != null ? statistics.get("total_stocks") : null))
                    .rising(summary != null ? toInt(summary.get("rising_stocks")) : 0)
                    .falling(summary != null ? toInt(summary.get("falling_stocks")) : 0)
                    .unchanged(summary != null ? toInt(summary.get("unchanged_stocks")) : 0)
                    .buyCandidate(toInt(statistics != null ? statistics.get("buy_candidate") : null))
                    .sellCandidate(toInt(statistics != null ? statistics.get("sell_candidate") : null))
                    .neutral(toInt(statistics != null ? statistics.get("neutral") : null))
                    .build();

            return MarketSummaryResponse.builder()
                    .date(date)
                    .kospi(kospi)
                    .statistics(stockStatistics)
                    .supplyDemand(supplyDemand)
                    .marketSentiment(marketSentiment)
                    .build();
        } catch (Exception e) {
            log.error("Failed to get market summary for date: {}", date, e);
            throw new RuntimeException("Failed to get market summary", e);
        }
    }

    /**
     * 시장 감성 분석 데이터 조회
     * - 시장 전반 감성 또는 종목별 분포가 없어도 0/null로 안전하게 응답
     */
    @Transactional(readOnly = true)
    public MarketSentimentResponse getMarketSentiment(LocalDate date) {
        try {
            Map<String, Object> sentiment = marketAnalysisRepository.getMarketSentiment(date);

            BigDecimal sentimentScore = BigDecimal.ZERO;
            Map<String, Object> distribution = null;

            if (sentiment != null) {
                BigDecimal raw = toBigDecimal(sentiment.get("sentiment_score"));
                sentimentScore = raw != null ? raw : BigDecimal.ZERO;

                @SuppressWarnings("unchecked")
                Map<String, Object> distMap = (Map<String, Object>) sentiment.get("distribution");
                distribution = distMap;
            } else {
                log.info("No market sentiment data for date: {} - returning zeroed response", date);
            }

            int totalCount = 0;
            int positiveCount = 0;
            int neutralCount = 0;
            int negativeCount = 0;

            if (distribution != null) {
                totalCount = toInt(distribution.get("total_count"));
                positiveCount = toInt(distribution.get("positive_count"));
                neutralCount = toInt(distribution.get("neutral_count"));
                negativeCount = toInt(distribution.get("negative_count"));
            }

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
            BigDecimal score = toBigDecimal(decision.get("confidence_score"));
            if (score == null) {
                score = BigDecimal.ZERO;
            }

            stocks.add(MarketDecisionsResponse.DecisionStock.builder()
                    .rank(toInt(decision.get("rank")))
                    .stockCode((String) decision.get("stock_code"))
                    .stockName((String) decision.get("stock_name"))
                    .reason((String) decision.get("reason"))
                    .score(score)
                    .currentPrice(toLong(decision.get("current_price")))
                    .changeRate(toBigDecimal(decision.get("change_rate")))
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
        if (score == null) {
            return "중립";
        }
        if (score.compareTo(BigDecimal.valueOf(0.3)) >= 0) {
            return "긍정 우세";
        } else if (score.compareTo(BigDecimal.valueOf(-0.3)) <= 0) {
            return "부정 우세";
        } else {
            return "중립";
        }
    }

    /**
     * 날짜 파라미터 해석: null이면 최신 분석 날짜 사용, 그것도 없으면 오늘.
     * Controller에서 휴장일(주말/공휴일) default가 빈 응답으로 떨어지는 것을 방지.
     */
    @Transactional(readOnly = true)
    public LocalDate resolveDate(LocalDate date) {
        if (date != null) {
            return date;
        }
        LocalDate latest = marketAnalysisRepository.getLatestAnalysisDate();
        return latest != null ? latest : LocalDate.now();
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
     * 30종목 히트맵 데이터 조회 (+ 요약 통계 동봉)
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
                        .foreignNetBuy(toLong(row.get("foreign_net_buy")))
                        .institutionalNetBuy(toLong(row.get("institutional_net_buy")))
                        .volAvgMultiple(toBigDecimal(row.get("vol_avg_multiple")))
                        .priceVolatility(toBigDecimal(row.get("price_volatility")))
                        .morningReturn(toBigDecimal(row.get("morning_return")))
                        .closePosition(toBigDecimal(row.get("close_position")))
                        .per(toBigDecimal(row.get("per")))
                        .roe(toBigDecimal(row.get("roe")))
                        .operatingMargin(toBigDecimal(row.get("operating_margin")))
                        .sentimentScore(toBigDecimal(row.get("sentiment_score")))
                        .priceTrend(toBigDecimal(row.get("price_trend")))
                        .volumeTrend(toBigDecimal(row.get("volume_trend")))
                        .priceUncertainty(toBigDecimal(row.get("price_uncertainty")))
                        .build());
            }

            MarketHeatmapResponse.HeatmapSummary summary = buildHeatmapSummary(stocks);

            return MarketHeatmapResponse.builder()
                    .date(date)
                    .stocks(stocks)
                    .summary(summary)
                    .build();
        } catch (Exception e) {
            log.error("Failed to get heatmap data for date: {}", date, e);
            throw new RuntimeException("Failed to get heatmap data", e);
        }
    }

    /**
     * 히트맵 종목 리스트로부터 요약 통계 생성
     * - 양/음 카운트, 평균, top stock 계산
     */
    private MarketHeatmapResponse.HeatmapSummary buildHeatmapSummary(
            List<MarketHeatmapResponse.StockFeatures> stocks) {

        if (stocks == null || stocks.isEmpty()) {
            return MarketHeatmapResponse.HeatmapSummary.builder()
                    .avgForeignNetBuy(0L)
                    .avgInstitutionalNetBuy(0L)
                    .avgSentimentScore(BigDecimal.ZERO)
                    .positiveSentimentCount(0)
                    .negativeSentimentCount(0)
                    .positiveTrendCount(0)
                    .topStock(null)
                    .build();
        }

        long foreignSum = 0L;
        int foreignCount = 0;
        long institutionalSum = 0L;
        int institutionalCount = 0;
        BigDecimal sentimentSum = BigDecimal.ZERO;
        int sentimentCount = 0;
        int positiveSentimentCount = 0;
        int negativeSentimentCount = 0;
        int positiveTrendCount = 0;

        MarketHeatmapResponse.TopStock topStock = null;
        int maxPositiveFeatures = -1;

        for (MarketHeatmapResponse.StockFeatures s : stocks) {
            if (s.getForeignNetBuy() != null) {
                foreignSum += s.getForeignNetBuy();
                foreignCount++;
            }
            if (s.getInstitutionalNetBuy() != null) {
                institutionalSum += s.getInstitutionalNetBuy();
                institutionalCount++;
            }
            if (s.getSentimentScore() != null) {
                sentimentSum = sentimentSum.add(s.getSentimentScore());
                sentimentCount++;
                if (s.getSentimentScore().compareTo(BigDecimal.ZERO) > 0) {
                    positiveSentimentCount++;
                } else if (s.getSentimentScore().compareTo(BigDecimal.ZERO) < 0) {
                    negativeSentimentCount++;
                }
            }
            if (s.getPriceTrend() != null && s.getPriceTrend().compareTo(BigDecimal.ZERO) > 0) {
                positiveTrendCount++;
            }

            // top stock 계산: 5개 핵심 피처 중 양수 개수
            int positiveFeatures = 0;
            if (s.getForeignNetBuy() != null && s.getForeignNetBuy() > 0) positiveFeatures++;
            if (s.getInstitutionalNetBuy() != null && s.getInstitutionalNetBuy() > 0) positiveFeatures++;
            if (s.getSentimentScore() != null && s.getSentimentScore().compareTo(BigDecimal.ZERO) > 0) positiveFeatures++;
            if (s.getPriceTrend() != null && s.getPriceTrend().compareTo(BigDecimal.ZERO) > 0) positiveFeatures++;
            if (s.getMorningReturn() != null && s.getMorningReturn().compareTo(BigDecimal.ZERO) > 0) positiveFeatures++;

            if (positiveFeatures > maxPositiveFeatures) {
                maxPositiveFeatures = positiveFeatures;
                topStock = MarketHeatmapResponse.TopStock.builder()
                        .stockCode(s.getStockCode())
                        .stockName(s.getStockName())
                        .positiveFeatures(positiveFeatures)
                        .build();
            }
        }

        Long avgForeign = foreignCount > 0 ? foreignSum / foreignCount : 0L;
        Long avgInstitutional = institutionalCount > 0 ? institutionalSum / institutionalCount : 0L;
        BigDecimal avgSentiment = sentimentCount > 0
                ? sentimentSum.divide(BigDecimal.valueOf(sentimentCount), 4, RoundingMode.HALF_UP)
                : BigDecimal.ZERO;

        return MarketHeatmapResponse.HeatmapSummary.builder()
                .avgForeignNetBuy(avgForeign)
                .avgInstitutionalNetBuy(avgInstitutional)
                .avgSentimentScore(avgSentiment)
                .positiveSentimentCount(positiveSentimentCount)
                .negativeSentimentCount(negativeSentimentCount)
                .positiveTrendCount(positiveTrendCount)
                .topStock(topStock)
                .build();
    }

    // ============================================================
    // JDBC 결과 안전 캐스팅 헬퍼
    // PostgreSQL NUMERIC → BigDecimal, BIGINT → Long, INT → Integer
    // 드라이버/Aggregate 결과에 따라 Double/BigInteger 등으로 올 수 있어 방어적 변환
    // ============================================================

    private static BigDecimal toBigDecimal(Object value) {
        if (value == null) return null;
        if (value instanceof BigDecimal) return (BigDecimal) value;
        if (value instanceof Number) return BigDecimal.valueOf(((Number) value).doubleValue());
        try {
            return new BigDecimal(value.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static Long toLong(Object value) {
        if (value == null) return null;
        if (value instanceof Long) return (Long) value;
        if (value instanceof Number) return ((Number) value).longValue();
        try {
            return Long.parseLong(value.toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static Integer toInt(Object value) {
        if (value == null) return 0;
        if (value instanceof Number) return ((Number) value).intValue();
        try {
            return Integer.parseInt(value.toString());
        } catch (NumberFormatException e) {
            return 0;
        }
    }
}
