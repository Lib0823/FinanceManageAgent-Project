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
                @SuppressWarnings("unchecked")
                Map<String, Object> distMap = (Map<String, Object>) sentiment.get("distribution");
                distribution = distMap;

                BigDecimal raw = toBigDecimal(sentiment.get("sentiment_score"));
                if (raw != null) {
                    sentimentScore = raw;
                } else {
                    // Fallback: 시장 전반 sentiment 행이 없으면 종목별 평균을 사용
                    BigDecimal avgFromStocks = toBigDecimal(distMap != null ? distMap.get("avg_sentiment") : null);
                    sentimentScore = avgFromStocks != null ? avgFromStocks : BigDecimal.ZERO;
                }
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
            // anchor price(yhat_d1) 집계: uncertainty_pct = avg_uncertainty / avg_anchor_price * 100 계산용
            BigDecimal sumAnchorPrice = BigDecimal.ZERO;
            int anchorPriceCount = 0;

            for (Map<String, Object> row : heatmapData) {
                // 5일 예상 수익률 % = (yhat_d5 - yhat_d1) / yhat_d1 * 100
                // yhat_d1, yhat_d5는 사용자 응답에 직접 노출하지 않고 변환값만 expected_return_5d로 노출
                BigDecimal yhatD1 = toBigDecimal(row.get("yhat_d1"));
                BigDecimal yhatD5 = toBigDecimal(row.get("yhat_d5"));
                BigDecimal expectedReturn5d = null;
                if (yhatD1 != null && yhatD5 != null && yhatD1.compareTo(BigDecimal.ZERO) > 0) {
                    expectedReturn5d = yhatD5.subtract(yhatD1)
                            .divide(yhatD1, 6, RoundingMode.HALF_UP)
                            .multiply(BigDecimal.valueOf(100))
                            .setScale(2, RoundingMode.HALF_UP);
                }

                if (yhatD1 != null && yhatD1.compareTo(BigDecimal.ZERO) > 0) {
                    sumAnchorPrice = sumAnchorPrice.add(yhatD1);
                    anchorPriceCount++;
                }

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
                        .expectedReturn5d(expectedReturn5d)
                        .yhatD1(yhatD1)
                        .yhatD2(toBigDecimal(row.get("yhat_d2")))
                        .yhatD3(toBigDecimal(row.get("yhat_d3")))
                        .yhatD4(toBigDecimal(row.get("yhat_d4")))
                        .yhatD5(yhatD5)
                        .yhatUpperD5(toBigDecimal(row.get("yhat_upper_d5")))
                        .yhatLowerD5(toBigDecimal(row.get("yhat_lower_d5")))
                        .build());
            }

            MarketHeatmapResponse.HeatmapSummary summary =
                    buildHeatmapSummary(stocks, sumAnchorPrice, anchorPriceCount);

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
     * 단일 종목 AI 분석 요약 조회 (Bot 화면 보유 종목 카드용).
     * - 데이터 소스: stock_filter_score / news_analysis / prophet_forecast / stock_financial
     *   (ai_trade_decision 은 TOP3 6종목만 존재하므로 사용하지 않음)
     * - date 가 null 이면 해당 종목의 "가장 최근 분석일"로 fallback (보유 종목이 당일 Top30에서
     *   탈락해도 직전 분석일 데이터를 보여주기 위함). 분석 이력이 전혀 없으면 has_analysis=false.
     * - 응답: 한두 문장 headline + color-coded 핵심 지표(metrics).
     */
    @Transactional(readOnly = true)
    public StockAnalysisResponse getStockAnalysis(String stockCode, LocalDate date) {
        try {
            // 종목별 날짜 해석: 명시된 date 우선, 없으면 해당 종목 최신 분석일로 fallback
            LocalDate targetDate = (date != null)
                    ? date
                    : marketAnalysisRepository.getLatestStockScoreDate(stockCode);

            Map<String, Object> features = (targetDate != null)
                    ? marketAnalysisRepository.getStockFeatures(stockCode, targetDate)
                    : null;

            // 분석 이력이 전혀 없는 종목 (분석 유니버스 미포함)
            if (features == null) {
                return StockAnalysisResponse.builder()
                        .stockCode(stockCode)
                        .stockName(null)
                        .analysisDate(targetDate)
                        .hasAnalysis(false)
                        .headline("이 종목은 분석 대상(상위 30종목)에 포함된 적이 없어 분석 데이터가 없습니다.")
                        .metrics(new ArrayList<>())
                        .foreignNetBuy(null)
                        .institutionalNetBuy(null)
                        .sentimentScore(null)
                        .newsCount(null)
                        .expectedReturn5d(null)
                        .per(null)
                        .roe(null)
                        .operatingMargin(null)
                        .build();
            }

            String stockName = (String) features.get("stock_name");
            Long foreignNetBuy = toLong(features.get("foreign_net_buy"));
            Long institutionalNetBuy = toLong(features.get("institutional_net_buy"));
            BigDecimal volAvgMultiple = toBigDecimal(features.get("vol_avg_multiple"));
            BigDecimal sentimentScore = toBigDecimal(features.get("sentiment_score"));
            Integer newsCount = features.get("news_count") != null ? toInt(features.get("news_count")) : null;
            BigDecimal priceTrend = toBigDecimal(features.get("price_trend"));
            BigDecimal per = toBigDecimal(features.get("per"));
            BigDecimal roe = toBigDecimal(features.get("roe"));
            BigDecimal operatingMargin = toBigDecimal(features.get("operating_margin"));

            // 5일 예상 수익률 % = (yhat_d5 - yhat_d1) / yhat_d1 * 100 (히트맵과 동일 공식)
            BigDecimal yhatD1 = toBigDecimal(features.get("yhat_d1"));
            BigDecimal yhatD5 = toBigDecimal(features.get("yhat_d5"));
            BigDecimal expectedReturn5d = null;
            if (yhatD1 != null && yhatD5 != null && yhatD1.compareTo(BigDecimal.ZERO) > 0) {
                expectedReturn5d = yhatD5.subtract(yhatD1)
                        .divide(yhatD1, 6, RoundingMode.HALF_UP)
                        .multiply(BigDecimal.valueOf(100))
                        .setScale(2, RoundingMode.HALF_UP);
            }

            String headline = buildHeadline(
                    foreignNetBuy, institutionalNetBuy,
                    expectedReturn5d, priceTrend, sentimentScore);

            List<StockAnalysisResponse.Metric> metrics = buildMetrics(
                    foreignNetBuy, institutionalNetBuy,
                    expectedReturn5d, volAvgMultiple,
                    sentimentScore, roe);

            return StockAnalysisResponse.builder()
                    .stockCode(stockCode)
                    .stockName(stockName)
                    .analysisDate(targetDate)
                    .hasAnalysis(true)
                    .headline(headline)
                    .metrics(metrics)
                    .foreignNetBuy(foreignNetBuy)
                    .institutionalNetBuy(institutionalNetBuy)
                    .sentimentScore(sentimentScore)
                    .newsCount(newsCount)
                    .expectedReturn5d(expectedReturn5d)
                    .per(per)
                    .roe(roe)
                    .operatingMargin(operatingMargin)
                    .build();
        } catch (Exception e) {
            log.error("Failed to get stock analysis for stockCode: {}, date: {}", stockCode, date, e);
            throw new RuntimeException("Failed to get stock analysis", e);
        }
    }

    /**
     * 단일 종목 AI 분석 상세 조회 (종목 상세 화면 AI 분석 탭용).
     * - 데이터 소스: stock_filter_score / news_analysis(종목) / prophet_forecast / stock_financial
     *   + 시장 감성/분포는 getMarketSentiment(targetDate) 재사용
     * - date 가 null 이면 해당 종목의 "가장 최근 분석일"로 fallback (getStockAnalysis 와 동일 패턴).
     *   분석 이력이 전혀 없으면 has_analysis=false, 3개 섹션(quant/sentiment/timeseries)은 null.
     * - 응답: 정량(quant) / 감성(sentiment) / 시계열(timeseries) 3개 섹션.
     */
    @Transactional(readOnly = true)
    public StockDetailAnalysisResponse getStockDetailAnalysis(String stockCode, LocalDate date) {
        try {
            // 종목별 날짜 해석: 명시된 date 우선, 없으면 해당 종목 최신 분석일로 fallback
            LocalDate targetDate = (date != null)
                    ? date
                    : marketAnalysisRepository.getLatestStockScoreDate(stockCode);

            Map<String, Object> features = (targetDate != null)
                    ? marketAnalysisRepository.getStockDetailFeatures(stockCode, targetDate)
                    : null;

            // 분석 이력이 전혀 없는 종목 (분석 유니버스 미포함)
            if (features == null) {
                return StockDetailAnalysisResponse.builder()
                        .stockCode(stockCode)
                        .stockName(null)
                        .analysisDate(targetDate)
                        .hasAnalysis(false)
                        .quant(null)
                        .sentiment(null)
                        .timeseries(null)
                        .build();
            }

            String stockName = (String) features.get("stock_name");

            // ── 정량(quant) 섹션 ─────────────────────────────────────────
            StockDetailAnalysisResponse.Quant quant = StockDetailAnalysisResponse.Quant.builder()
                    .foreignNetBuy(toLong(features.get("foreign_net_buy")))
                    .institutionalNetBuy(toLong(features.get("institutional_net_buy")))
                    .morningReturn(toBigDecimal(features.get("morning_return")))
                    .closePosition(toBigDecimal(features.get("close_position")))
                    .volAvgMultiple(toBigDecimal(features.get("vol_avg_multiple")))
                    .priceVolatility(toBigDecimal(features.get("price_volatility")))
                    .per(toBigDecimal(features.get("per")))
                    .roe(toBigDecimal(features.get("roe")))
                    .operatingMargin(toBigDecimal(features.get("operating_margin")))
                    .build();

            // ── 감성(sentiment) 섹션 ──────────────────────────────────────
            // 종목별 감성은 features 행에서, 시장 전반/분포는 getMarketSentiment 재사용
            BigDecimal stockSentimentScore = toBigDecimal(features.get("sentiment_score"));
            Integer stockNewsCount = features.get("news_count") != null
                    ? toInt(features.get("news_count"))
                    : null;

            // 시장 전반 감성은 비치명적: 실패해도 종목 상세 응답은 정상 반환
            BigDecimal marketSentimentScore = null;
            StockDetailAnalysisResponse.Sentiment.Distribution marketDistribution = null;
            Integer marketNewsCount = null;

            try {
                MarketSentimentResponse marketSentiment = getMarketSentiment(targetDate);

                marketSentimentScore = marketSentiment.getScore();

                MarketSentimentResponse.Distribution dist = marketSentiment.getDistribution();
                if (dist != null) {
                    int positiveCount = dist.getPositive() != null ? toInt(dist.getPositive().getCount()) : 0;
                    int neutralCount = dist.getNeutral() != null ? toInt(dist.getNeutral().getCount()) : 0;
                    int negativeCount = dist.getNegative() != null ? toInt(dist.getNegative().getCount()) : 0;
                    int totalCount = positiveCount + neutralCount + negativeCount;

                    marketDistribution = StockDetailAnalysisResponse.Sentiment.Distribution.builder()
                            .positiveCount(positiveCount)
                            .neutralCount(neutralCount)
                            .negativeCount(negativeCount)
                            .positivePercent(calculatePercent(positiveCount, totalCount))
                            .neutralPercent(calculatePercent(neutralCount, totalCount))
                            .negativePercent(calculatePercent(negativeCount, totalCount))
                            .build();

                    // 시장 뉴스 건수는 별도 컬럼이 없어 분포 합계(total)로 대체, 분포 없으면 null
                    marketNewsCount = totalCount > 0 ? totalCount : null;
                }
            } catch (Exception e) {
                log.warn("시장 감성 조회 실패, 시장 필드는 null 처리하고 계속 진행: stockCode={}, date={}, error={}",
                        stockCode, targetDate, e.getMessage());
            }

            StockDetailAnalysisResponse.Sentiment sentiment = StockDetailAnalysisResponse.Sentiment.builder()
                    .stockSentimentScore(stockSentimentScore)
                    .stockNewsCount(stockNewsCount)
                    .marketSentimentScore(marketSentimentScore)
                    .marketNewsCount(marketNewsCount)
                    .marketDistribution(marketDistribution)
                    .timeRange("전날 18:00 — 당일 08:50")
                    .marketSources("한경 · 매경 · 연합")
                    .build();

            // ── 시계열(timeseries) 섹션 ───────────────────────────────────
            List<StockDetailAnalysisResponse.Timeseries.Forecast> forecasts = new ArrayList<>();
            for (int d = 1; d <= 5; d++) {
                BigDecimal yhat = toBigDecimal(features.get("yhat_d" + d));
                // yhat_dN 이 없는 날짜는 제외 (데이터가 있는 D+N 항목만 포함)
                if (yhat == null) {
                    continue;
                }
                StockDetailAnalysisResponse.Timeseries.Forecast forecast = buildForecast(
                        d,
                        yhat,
                        toBigDecimal(features.get("yhat_upper_d" + d)),
                        toBigDecimal(features.get("yhat_lower_d" + d)));
                forecasts.add(forecast);
            }

            StockDetailAnalysisResponse.Timeseries timeseries = StockDetailAnalysisResponse.Timeseries.builder()
                    .priceTrend(toBigDecimal(features.get("price_trend")))
                    .volumeTrend(toBigDecimal(features.get("volume_trend")))
                    .priceUncertainty(toBigDecimal(features.get("price_uncertainty")))
                    .trainingDays(120)
                    .forecasts(forecasts)
                    .build();

            return StockDetailAnalysisResponse.builder()
                    .stockCode(stockCode)
                    .stockName(stockName)
                    .analysisDate(targetDate)
                    .hasAnalysis(true)
                    .quant(quant)
                    .sentiment(sentiment)
                    .timeseries(timeseries)
                    .build();
        } catch (Exception e) {
            log.error("Failed to get stock detail analysis for stockCode: {}, date: {}", stockCode, date, e);
            throw new RuntimeException("Failed to get stock detail analysis", e);
        }
    }

    /**
     * D+N 예측 1건 구성.
     * uncertainty_pct = (yhat_upper - yhat_lower) / yhat * 100 (소수 1자리).
     * yhat 이 null 이거나 <= 0 이면, 또는 상·하한 중 하나라도 null 이면 uncertainty_pct 는 null.
     */
    private StockDetailAnalysisResponse.Timeseries.Forecast buildForecast(
            int day, BigDecimal yhat, BigDecimal yhatUpper, BigDecimal yhatLower) {

        BigDecimal uncertaintyPct = null;
        if (yhat != null && yhat.compareTo(BigDecimal.ZERO) > 0
                && yhatUpper != null && yhatLower != null) {
            uncertaintyPct = yhatUpper.subtract(yhatLower)
                    .divide(yhat, 6, RoundingMode.HALF_UP)
                    .multiply(BigDecimal.valueOf(100))
                    .setScale(1, RoundingMode.HALF_UP);
        }

        return StockDetailAnalysisResponse.Timeseries.Forecast.builder()
                .day("D+" + day)
                .yhat(yhat)
                .yhatUpper(yhatUpper)
                .yhatLower(yhatLower)
                .uncertaintyPct(uncertaintyPct)
                .build();
    }

    /**
     * 한두 문장 자연어 요약 구성. 수급 → 5일 예측 → 감성 순으로 데이터가 있는 절만 연결한다.
     */
    private String buildHeadline(
            Long foreignNetBuy, Long institutionalNetBuy,
            BigDecimal expectedReturn5d, BigDecimal priceTrend,
            BigDecimal sentimentScore) {

        List<String> clauses = new ArrayList<>();

        // 수급
        boolean fPos = foreignNetBuy != null && foreignNetBuy > 0;
        boolean fNeg = foreignNetBuy != null && foreignNetBuy < 0;
        boolean iPos = institutionalNetBuy != null && institutionalNetBuy > 0;
        boolean iNeg = institutionalNetBuy != null && institutionalNetBuy < 0;
        if (fPos && iPos) {
            clauses.add("외국인·기관 동반 순매수");
        } else if (fNeg && iNeg) {
            clauses.add("외국인·기관 동반 순매도");
        } else if (foreignNetBuy != null || institutionalNetBuy != null) {
            if (fPos) clauses.add("외국인 순매수 우위");
            else if (iPos) clauses.add("기관 순매수 우위");
            else if (fNeg || iNeg) clauses.add("수급 매도 우위");
            else clauses.add("수급 보합");
        }

        // 5일 예측
        if (expectedReturn5d != null) {
            String trend = expectedReturn5d.compareTo(BigDecimal.ZERO) > 0 ? "상승"
                    : expectedReturn5d.compareTo(BigDecimal.ZERO) < 0 ? "하락" : "보합";
            String sign = expectedReturn5d.compareTo(BigDecimal.ZERO) >= 0 ? "+" : "";
            clauses.add("5일 예측 " + sign
                    + expectedReturn5d.setScale(1, RoundingMode.HALF_UP).toPlainString() + "% " + trend);
        } else if (priceTrend != null && priceTrend.compareTo(BigDecimal.ZERO) != 0) {
            clauses.add(priceTrend.compareTo(BigDecimal.ZERO) > 0 ? "단기 상승 추세" : "단기 하락 추세");
        }

        // 감성
        if (sentimentScore != null) {
            clauses.add("감성 " + sentimentLabel(sentimentScore));
        }

        if (clauses.isEmpty()) {
            return "수급 외 지표 데이터가 제한적입니다.";
        }
        return String.join(" · ", clauses) + ".";
    }

    /**
     * color-coded 핵심 지표 구성 (프론트 미니 표). 데이터가 있는 항목만 3~5개.
     * tone: positive(빨강) / negative(파랑) / neutral(회색)
     */
    private List<StockAnalysisResponse.Metric> buildMetrics(
            Long foreignNetBuy, Long institutionalNetBuy,
            BigDecimal expectedReturn5d, BigDecimal volAvgMultiple,
            BigDecimal sentimentScore, BigDecimal roe) {

        List<StockAnalysisResponse.Metric> metrics = new ArrayList<>();

        if (foreignNetBuy != null) {
            metrics.add(buildMetric("외국인", formatMoney(foreignNetBuy), signTone(foreignNetBuy)));
        }
        if (institutionalNetBuy != null) {
            metrics.add(buildMetric("기관", formatMoney(institutionalNetBuy), signTone(institutionalNetBuy)));
        }

        // 5일 예측 우선, 없으면 거래량 배율로 대체
        if (expectedReturn5d != null) {
            String sign = expectedReturn5d.compareTo(BigDecimal.ZERO) >= 0 ? "+" : "";
            String value = sign + expectedReturn5d.setScale(1, RoundingMode.HALF_UP).toPlainString() + "%";
            metrics.add(buildMetric("5일 예측", value, signTone(expectedReturn5d.signum())));
        } else if (volAvgMultiple != null) {
            String value = volAvgMultiple.setScale(2, RoundingMode.HALF_UP).toPlainString() + "배";
            String tone = volAvgMultiple.compareTo(BigDecimal.valueOf(1.5)) > 0 ? "positive" : "neutral";
            metrics.add(buildMetric("거래량", value, tone));
        }

        if (sentimentScore != null) {
            String label = sentimentLabel(sentimentScore);
            String tone = sentimentScore.compareTo(BigDecimal.valueOf(0.3)) >= 0 ? "positive"
                    : sentimentScore.compareTo(BigDecimal.valueOf(-0.3)) <= 0 ? "negative" : "neutral";
            metrics.add(buildMetric("뉴스 감성", label, tone));
        }

        if (roe != null) {
            String value = roe.setScale(1, RoundingMode.HALF_UP).toPlainString() + "%";
            String tone = roe.compareTo(BigDecimal.valueOf(15)) > 0 ? "positive" : "neutral";
            metrics.add(buildMetric("ROE", value, tone));
        }

        return metrics;
    }

    private StockAnalysisResponse.Metric buildMetric(String label, String value, String tone) {
        return StockAnalysisResponse.Metric.builder()
                .label(label)
                .value(value)
                .tone(tone)
                .build();
    }

    /** 감성 점수 → 라벨 (≥0.3 긍정 / ≤-0.3 부정 / 그 외 중립) */
    private String sentimentLabel(BigDecimal score) {
        if (score == null) return "중립";
        if (score.compareTo(BigDecimal.valueOf(0.3)) >= 0) return "긍정";
        if (score.compareTo(BigDecimal.valueOf(-0.3)) <= 0) return "부정";
        return "중립";
    }

    /** 부호 → tone (양수=positive/빨강, 음수=negative/파랑, 0=neutral) */
    private String signTone(long value) {
        if (value > 0) return "positive";
        if (value < 0) return "negative";
        return "neutral";
    }

    private String signTone(int signum) {
        if (signum > 0) return "positive";
        if (signum < 0) return "negative";
        return "neutral";
    }

    /**
     * 금액 포맷터.
     * - |v| >= 1조 → "조" 단위 (소수 1자리)
     * - |v| >= 1억 → "억" 단위 (소수 1자리)
     * - 그 외      → 천단위 콤마 원본
     * 부호(+/−) 접두, 0이면 "0".
     */
    private String formatMoney(long value) {
        if (value == 0) {
            return "0";
        }
        String sign = value > 0 ? "+" : "−";
        long abs = Math.abs(value);

        final long JO = 1_0000_0000_0000L;  // 1조
        final long EOK = 1_0000_0000L;       // 1억

        if (abs >= JO) {
            BigDecimal v = BigDecimal.valueOf(abs)
                    .divide(BigDecimal.valueOf(JO), 1, RoundingMode.HALF_UP);
            return sign + v.toPlainString() + "조";
        } else if (abs >= EOK) {
            BigDecimal v = BigDecimal.valueOf(abs)
                    .divide(BigDecimal.valueOf(EOK), 1, RoundingMode.HALF_UP);
            return sign + v.toPlainString() + "억";
        } else {
            return sign + String.format("%,d", abs);
        }
    }

    /**
     * 히트맵 종목 리스트로부터 요약 통계 생성
     * - 양/음 카운트, 평균, top stock 계산
     * - ForecastOutlook: expected_return_5d 기반 (yhat_d1/yhat_d5)로 재정의, uncertainty_pct 임계값 사용
     * - FinancialHealth: DART 데이터 없으면 null 반환
     *
     * @param stocks            row → DTO 변환된 종목 리스트
     * @param sumAnchorPrice    yhat_d1 합계 (uncertainty_pct 분모용)
     * @param anchorPriceCount  yhat_d1 표본 수
     */
    private MarketHeatmapResponse.HeatmapSummary buildHeatmapSummary(
            List<MarketHeatmapResponse.StockFeatures> stocks,
            BigDecimal sumAnchorPrice,
            int anchorPriceCount) {

        if (stocks == null || stocks.isEmpty()) {
            // BUG-1/BUG-4 fix: 빈 stocks 케이스에서도 4개 신규/기존 객체를 모두 빌드하여
            // "데이터 부재(필드만 null)" 케이스와 응답 형태 일관성 유지.
            // 각 builder 메서드는 zero/empty 입력에 대해 안전하게 빈 객체를 반환함.
            MarketHeatmapResponse.ForecastOutlook emptyOutlook = buildForecastOutlook(
                    0, 0,
                    BigDecimal.ZERO, 0,
                    BigDecimal.ZERO, 0,
                    BigDecimal.ZERO, 0,
                    BigDecimal.ZERO, 0,
                    BigDecimal.ZERO, 0,
                    null);
            MarketHeatmapResponse.FinancialHealth emptyHealth = buildFinancialHealth(
                    0,
                    null, 0,
                    BigDecimal.ZERO, 0,
                    BigDecimal.ZERO, 0,
                    0, 0, 0,
                    0, 0);
            MarketHeatmapResponse.SmartMoneyFlow emptyFlow =
                    buildSmartMoneyFlow(java.util.Collections.emptyList());
            MarketHeatmapResponse.MarketForecastTrend emptyTrend =
                    buildMarketForecastTrend(java.util.Collections.emptyList());

            return MarketHeatmapResponse.HeatmapSummary.builder()
                    .avgForeignNetBuy(0L)
                    .avgInstitutionalNetBuy(0L)
                    .avgSentimentScore(BigDecimal.ZERO)
                    .positiveSentimentCount(0)
                    .negativeSentimentCount(0)
                    .positiveTrendCount(0)
                    .topStock(null)
                    .forecastOutlook(emptyOutlook)
                    .financialHealth(emptyHealth)
                    .smartMoneyFlow(emptyFlow)
                    .marketForecastTrend(emptyTrend)
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

        // ForecastOutlook 누적기 — expected_return_5d 기반 재정의
        int risingCount = 0;
        int fallingCount = 0;
        BigDecimal sumPriceTrend = BigDecimal.ZERO;
        BigDecimal sumVolumeTrend = BigDecimal.ZERO;
        BigDecimal sumUncertainty = BigDecimal.ZERO;
        BigDecimal sumExpectedReturn = BigDecimal.ZERO;
        int priceTrendCount = 0;
        int volumeTrendCount = 0;
        int uncertaintyCount = 0;
        int expectedReturnCount = 0;
        MarketHeatmapResponse.OutlookStock topOutlook = null;
        BigDecimal maxExpectedReturn = null;

        // FinancialHealth 누적기
        // PER은 소수 고PER 종목이 평균을 크게 왜곡하므로 중앙값(median)으로 대표값을 산출한다.
        List<BigDecimal> perValues = new ArrayList<>();
        BigDecimal sumRoe = BigDecimal.ZERO;
        BigDecimal sumMargin = BigDecimal.ZERO;
        int perCount = 0;
        int roeCount = 0;
        int marginCount = 0;
        int undervaluedCount = 0;
        int highRoeCount = 0;
        int highMarginCount = 0;
        int excellentCount = 0;
        int withDartCount = 0;

        for (MarketHeatmapResponse.StockFeatures s : stocks) {
            if (s.getForeignNetBuy() != null) {
                // Long overflow 가드 (현실 데이터 범위에서는 안전하지만 명시적 체크)
                if (Math.abs(foreignSum) > Long.MAX_VALUE / 2) {
                    log.warn("Approaching long overflow in foreign net buy sum: {}", foreignSum);
                } else {
                    foreignSum += s.getForeignNetBuy();
                    foreignCount++;
                }
            }
            if (s.getInstitutionalNetBuy() != null) {
                if (Math.abs(institutionalSum) > Long.MAX_VALUE / 2) {
                    log.warn("Approaching long overflow in institutional net buy sum: {}", institutionalSum);
                } else {
                    institutionalSum += s.getInstitutionalNetBuy();
                    institutionalCount++;
                }
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
            // positive_trend_count: expected_return_5d 기준 (없으면 priceTrend fallback)
            BigDecimal trendSource = s.getExpectedReturn5d() != null ? s.getExpectedReturn5d() : s.getPriceTrend();
            if (trendSource != null && trendSource.compareTo(BigDecimal.ZERO) > 0) {
                positiveTrendCount++;
            }

            // top stock 계산: 5개 핵심 피처 중 양수 개수
            int positiveFeatures = 0;
            if (s.getForeignNetBuy() != null && s.getForeignNetBuy() > 0) positiveFeatures++;
            if (s.getInstitutionalNetBuy() != null && s.getInstitutionalNetBuy() > 0) positiveFeatures++;
            if (s.getSentimentScore() != null && s.getSentimentScore().compareTo(BigDecimal.ZERO) > 0) positiveFeatures++;
            if (trendSource != null && trendSource.compareTo(BigDecimal.ZERO) > 0) positiveFeatures++;
            if (s.getMorningReturn() != null && s.getMorningReturn().compareTo(BigDecimal.ZERO) > 0) positiveFeatures++;

            if (positiveFeatures > maxPositiveFeatures) {
                maxPositiveFeatures = positiveFeatures;
                topStock = MarketHeatmapResponse.TopStock.builder()
                        .stockCode(s.getStockCode())
                        .stockName(s.getStockName())
                        .positiveFeatures(positiveFeatures)
                        .build();
            }

            // ForecastOutlook 집계: rising/falling 및 topOutlook은 expected_return_5d 기준
            if (s.getExpectedReturn5d() != null) {
                int cmp = s.getExpectedReturn5d().compareTo(BigDecimal.ZERO);
                if (cmp > 0) risingCount++;
                else if (cmp < 0) fallingCount++;
                sumExpectedReturn = sumExpectedReturn.add(s.getExpectedReturn5d());
                expectedReturnCount++;
                if (maxExpectedReturn == null || s.getExpectedReturn5d().compareTo(maxExpectedReturn) > 0) {
                    maxExpectedReturn = s.getExpectedReturn5d();
                    topOutlook = MarketHeatmapResponse.OutlookStock.builder()
                            .stockCode(s.getStockCode())
                            .stockName(s.getStockName())
                            .priceTrend(s.getPriceTrend())            // 호환성 유지 (raw 슬로프)
                            .expectedReturn5d(s.getExpectedReturn5d()) // 사용자 표시용
                            .build();
                }
            }
            // 슬로프 기반 avg_price_trend는 호환성 위해 계속 집계 (사용자 표시 안 함)
            if (s.getPriceTrend() != null) {
                sumPriceTrend = sumPriceTrend.add(s.getPriceTrend());
                priceTrendCount++;
            }
            if (s.getVolumeTrend() != null) {
                sumVolumeTrend = sumVolumeTrend.add(s.getVolumeTrend());
                volumeTrendCount++;
            }
            if (s.getPriceUncertainty() != null) {
                sumUncertainty = sumUncertainty.add(s.getPriceUncertainty());
                uncertaintyCount++;
            }

            // FinancialHealth 집계
            boolean hasAnyDart = s.getPer() != null || s.getRoe() != null || s.getOperatingMargin() != null;
            if (hasAnyDart) withDartCount++;

            boolean isUnderval = false;
            boolean isHighRoe = false;
            boolean isHighMargin = false;

            // 음수 PER(적자기업)은 "저평가"가 아니라 손실 신호이므로 평균/저평가 집계에서 제외.
            // 평균 PER이 적자기업의 큰 음수값으로 왜곡되는 문제를 방지한다.
            if (s.getPer() != null && s.getPer().compareTo(BigDecimal.ZERO) > 0) {
                perValues.add(s.getPer());
                perCount++;
                if (s.getPer().compareTo(BigDecimal.valueOf(15)) < 0) {
                    undervaluedCount++;
                    isUnderval = true;
                }
            }
            if (s.getRoe() != null) {
                sumRoe = sumRoe.add(s.getRoe());
                roeCount++;
                if (s.getRoe().compareTo(BigDecimal.valueOf(15)) > 0) {
                    highRoeCount++;
                    isHighRoe = true;
                }
            }
            if (s.getOperatingMargin() != null) {
                sumMargin = sumMargin.add(s.getOperatingMargin());
                marginCount++;
                if (s.getOperatingMargin().compareTo(BigDecimal.valueOf(10)) > 0) {
                    highMarginCount++;
                    isHighMargin = true;
                }
            }

            // 펀더멘탈 우수: 저평가(PER<15)·고ROE(>15%)·고마진(>10%) 3개 중 2개 이상 충족.
            // 3개 동시 충족(AND)은 실제 종목 유니버스에서 거의 0이라 의미가 없어 2-of-3으로 완화.
            int qualityHits = (isUnderval ? 1 : 0) + (isHighRoe ? 1 : 0) + (isHighMargin ? 1 : 0);
            if (qualityHits >= 2) {
                excellentCount++;
            }
        }

        Long avgForeign = foreignCount > 0 ? foreignSum / foreignCount : 0L;
        Long avgInstitutional = institutionalCount > 0 ? institutionalSum / institutionalCount : 0L;
        BigDecimal avgSentiment = sentimentCount > 0
                ? sentimentSum.divide(BigDecimal.valueOf(sentimentCount), 4, RoundingMode.HALF_UP)
                : BigDecimal.ZERO;

        MarketHeatmapResponse.ForecastOutlook outlook = buildForecastOutlook(
                risingCount, fallingCount,
                sumPriceTrend, priceTrendCount,
                sumVolumeTrend, volumeTrendCount,
                sumUncertainty, uncertaintyCount,
                sumExpectedReturn, expectedReturnCount,
                sumAnchorPrice, anchorPriceCount,
                topOutlook);

        BigDecimal medianPer = median(perValues);
        MarketHeatmapResponse.FinancialHealth health = buildFinancialHealth(
                stocks.size(),
                medianPer, perCount,
                sumRoe, roeCount,
                sumMargin, marginCount,
                undervaluedCount, highRoeCount, highMarginCount,
                excellentCount, withDartCount);

        MarketHeatmapResponse.SmartMoneyFlow smartMoneyFlow = buildSmartMoneyFlow(stocks);
        MarketHeatmapResponse.MarketForecastTrend marketForecastTrend = buildMarketForecastTrend(stocks);

        return MarketHeatmapResponse.HeatmapSummary.builder()
                .avgForeignNetBuy(avgForeign)
                .avgInstitutionalNetBuy(avgInstitutional)
                .avgSentimentScore(avgSentiment)
                .positiveSentimentCount(positiveSentimentCount)
                .negativeSentimentCount(negativeSentimentCount)
                .positiveTrendCount(positiveTrendCount)
                .topStock(topStock)
                .forecastOutlook(outlook)
                .financialHealth(health)
                .smartMoneyFlow(smartMoneyFlow)
                .marketForecastTrend(marketForecastTrend)
                .build();
    }

    /**
     * ForecastOutlook 빌더 — 모든 케이스에서 객체를 반환 (필드 단위로 null/0 허용).
     * 프론트는 내부 필드가 null이면 "—"로 표시.
     *
     * 핵심 변경:
     * - 사용자 표시값은 expected_return_5d 평균 (avg_expected_return_5d %)
     * - uncertainty_level은 avg_uncertainty_pct (가격 대비 비율) 기준으로 분류
     *   - < 2%   → 낮음
     *   - < 5%   → 보통
     *   - 그 외  → 높음
     * - 기존 avg_price_trend (슬로프, 원/day)는 호환성 위해 채우되 표시 권장 안 함
     */
    private MarketHeatmapResponse.ForecastOutlook buildForecastOutlook(
            int risingCount, int fallingCount,
            BigDecimal sumPriceTrend, int priceTrendCount,
            BigDecimal sumVolumeTrend, int volumeTrendCount,
            BigDecimal sumUncertainty, int uncertaintyCount,
            BigDecimal sumExpectedReturn, int expectedReturnCount,
            BigDecimal sumAnchorPrice, int anchorPriceCount,
            MarketHeatmapResponse.OutlookStock topOutlook) {

        BigDecimal avgPriceTrend = priceTrendCount > 0
                ? sumPriceTrend.divide(BigDecimal.valueOf(priceTrendCount), 4, RoundingMode.HALF_UP)
                : null;
        BigDecimal avgVolumeTrend = volumeTrendCount > 0
                ? sumVolumeTrend.divide(BigDecimal.valueOf(volumeTrendCount), 4, RoundingMode.HALF_UP)
                : null;
        BigDecimal avgUncertainty = uncertaintyCount > 0
                ? sumUncertainty.divide(BigDecimal.valueOf(uncertaintyCount), 2, RoundingMode.HALF_UP)
                : null;
        BigDecimal avgExpectedReturn = expectedReturnCount > 0
                ? sumExpectedReturn.divide(BigDecimal.valueOf(expectedReturnCount), 2, RoundingMode.HALF_UP)
                : null;

        // 평균 불확실성 % = avg_uncertainty / avg_anchor_price * 100
        BigDecimal avgUncertaintyPct = null;
        if (avgUncertainty != null && anchorPriceCount > 0
                && sumAnchorPrice.compareTo(BigDecimal.ZERO) > 0) {
            BigDecimal avgAnchor = sumAnchorPrice.divide(
                    BigDecimal.valueOf(anchorPriceCount), 4, RoundingMode.HALF_UP);
            if (avgAnchor.compareTo(BigDecimal.ZERO) > 0) {
                avgUncertaintyPct = avgUncertainty
                        .divide(avgAnchor, 6, RoundingMode.HALF_UP)
                        .multiply(BigDecimal.valueOf(100))
                        .setScale(2, RoundingMode.HALF_UP);
            }
        }

        // 비율 기반 임계값 (가격 대비) — 기존 절대값 1000/5000 폐기
        String uncertaintyLevel = null;
        if (avgUncertaintyPct != null) {
            double pct = avgUncertaintyPct.doubleValue();
            if (pct < 2.0) uncertaintyLevel = "낮음";
            else if (pct < 5.0) uncertaintyLevel = "보통";
            else uncertaintyLevel = "높음";
        }

        return MarketHeatmapResponse.ForecastOutlook.builder()
                .risingCount(risingCount)
                .fallingCount(fallingCount)
                .avgPriceTrend(avgPriceTrend)           // 호환성 유지 (raw 슬로프)
                .avgVolumeTrend(avgVolumeTrend)
                .avgUncertainty(avgUncertainty)
                .avgUncertaintyPct(avgUncertaintyPct)   // 신규: 비율 (%)
                .avgExpectedReturn5d(avgExpectedReturn) // 신규: 사용자 표시용 평균 수익률 (%)
                .uncertaintyLevel(uncertaintyLevel)
                .topOutlookStock(topOutlook)
                .build();
    }

    /**
     * FinancialHealth 빌더 — 모든 케이스에서 객체를 반환 (필드 단위로 null/0 허용).
     * 프론트는 내부 필드가 null이면 "—"로 표시.
     * - 평균 카운트가 0이면 해당 평균 필드는 null
     * - 카운트 자체는 0 그대로 노출
     * - data_coverage 도 0 가능 (이전에는 < 10이면 섹션 자체 숨김이었으나 이제 노출)
     */
    private MarketHeatmapResponse.FinancialHealth buildFinancialHealth(
            int totalStocks,
            BigDecimal medianPer, int perCount,
            BigDecimal sumRoe, int roeCount,
            BigDecimal sumMargin, int marginCount,
            int undervaluedCount, int highRoeCount, int highMarginCount,
            int excellentCount, int withDartCount) {

        int dataCoverage = totalStocks > 0 ? (withDartCount * 100 / totalStocks) : 0;

        // avgPer 필드에는 (평균이 아닌) 양수 PER의 중앙값을 담는다 — 고PER 이상치 왜곡 방지.
        BigDecimal avgPer = (perCount > 0) ? medianPer : null;
        BigDecimal avgRoe = roeCount > 0
                ? sumRoe.divide(BigDecimal.valueOf(roeCount), 2, RoundingMode.HALF_UP)
                : null;
        BigDecimal avgMargin = marginCount > 0
                ? sumMargin.divide(BigDecimal.valueOf(marginCount), 2, RoundingMode.HALF_UP)
                : null;

        return MarketHeatmapResponse.FinancialHealth.builder()
                .avgPer(avgPer)
                .avgRoe(avgRoe)
                .avgOperatingMargin(avgMargin)
                .undervaluedCount(undervaluedCount)
                .highRoeCount(highRoeCount)
                .highMarginCount(highMarginCount)
                .excellentCount(excellentCount)
                .dataCoverage(dataCoverage)
                .build();
    }

    /**
     * 수급 매트릭스 (스마트머니 4분면) 계산.
     * - Q1: foreign+ inst+ → both_buy
     * - Q2: foreign+ inst- → foreign_only_buy (디커플링 A)
     * - Q3: foreign- inst- → both_sell
     * - Q4: foreign- inst+ → institutional_only_buy (디커플링 B)
     * - 0 (= 매수도 매도도 아님)은 buy 판정에서 제외 (fnb > 0 / inb > 0 strict)
     * - consensus_pct = (Q1 + Q3) / total * 100  (외국인-기관 의견 일치 비율)
     * - dominant_signal: Q1 가장 우세 & Q1 > Q2+Q4 → BOTH_BUY
     *                    Q3 가장 우세 & Q3 > Q2+Q4 → BOTH_SELL
     *                    그 외 → MIXED
     * - smart_money_top_stock: Q1 종목 중 combined_net_buy(=fnb+inb) 최대값
     *
     * 모든 케이스에서 객체 반환 (작업 1 정책에 따라). 데이터 0건이면 필드만 null/0.
     */
    private MarketHeatmapResponse.SmartMoneyFlow buildSmartMoneyFlow(
            List<MarketHeatmapResponse.StockFeatures> stocks) {

        int q1 = 0;  // both_buy
        int q2 = 0;  // foreign_only_buy
        int q3 = 0;  // both_sell
        int q4 = 0;  // institutional_only_buy
        int activeStocks = 0;  // BUG-3 fix: fnb != 0 또는 inb != 0 인 종목 카운트 (실제 매매 활동)
        MarketHeatmapResponse.SmartMoneyStock topQ1 = null;
        Long maxCombined = null;

        for (MarketHeatmapResponse.StockFeatures s : stocks) {
            Long fnb = s.getForeignNetBuy();
            Long inb = s.getInstitutionalNetBuy();
            if (fnb == null || inb == null) continue;

            // BUG-3 fix: 외국인/기관 중 하나라도 0이 아닌 종목은 "활동 있음"으로 분류
            if (fnb != 0 || inb != 0) activeStocks++;

            boolean fBuy = fnb > 0;
            boolean iBuy = inb > 0;

            if (fBuy && iBuy) {
                q1++;
                long combined = fnb + inb;
                if (maxCombined == null || combined > maxCombined) {
                    maxCombined = combined;
                    topQ1 = MarketHeatmapResponse.SmartMoneyStock.builder()
                            .stockCode(s.getStockCode())
                            .stockName(s.getStockName())
                            .combinedNetBuy(combined)
                            .build();
                }
            } else if (fBuy && !iBuy) {
                q2++;
            } else if (!fBuy && !iBuy) {
                q3++;
            } else {
                q4++;
            }
        }

        int total = q1 + q2 + q3 + q4;
        Integer consensusPct = total > 0 ? ((q1 + q3) * 100 / total) : null;

        // BUG-3 fix: activeStocks가 0이면 모든 종목 fnb=0 && inb=0 인 케이스 (활동 부재).
        // 이 경우 strict >0 정책상 모두 Q3로 분류되어 "BOTH_SELL"로 오분류되는 문제 방지.
        // 의미있는 매매 신호로 볼 수 없으므로 signal = null 처리.
        String signal;
        if (total == 0 || activeStocks == 0) {
            signal = null;
        } else if (q1 > q3 && q1 > q2 + q4) {
            signal = "BOTH_BUY";
        } else if (q3 > q1 && q3 > q2 + q4) {
            signal = "BOTH_SELL";
        } else {
            signal = "MIXED";
        }

        return MarketHeatmapResponse.SmartMoneyFlow.builder()
                .bothBuyCount(q1)
                .foreignOnlyBuyCount(q2)
                .bothSellCount(q3)
                .institutionalOnlyBuyCount(q4)
                .consensusPct(consensusPct)
                .dominantSignal(signal)
                .smartMoneyTopStock(topQ1)
                .build();
    }

    /**
     * D+1 ~ D+5 시장 평균 예측 추이 계산.
     * - 각 종목의 yhat_d1 을 기준점(0%)으로 yhat_dN 의 변동률(%) 계산
     *   pct(dN) = (yhat_dN - yhat_d1) / yhat_d1 * 100
     * - 모든 종목의 같은 D일자 변동률을 평균하여 시장 평균 추이를 구성
     * - d5_upper_pct / d5_lower_pct: 신뢰구간(yhat_upper_d5 / yhat_lower_d5)도 동일 변환
     * - trend_direction: D+5 평균 변동률 기준
     *   > +1.0%  → 상승세
     *   < -1.0% → 하락세
     *   그 외   → 횡보
     *
     * 모든 케이스에서 객체 반환 (작업 1 정책). 데이터 0건이면 dataCount=0, 나머지 null.
     */
    private MarketHeatmapResponse.MarketForecastTrend buildMarketForecastTrend(
            List<MarketHeatmapResponse.StockFeatures> stocks) {

        BigDecimal sumD2Pct = BigDecimal.ZERO;
        BigDecimal sumD3Pct = BigDecimal.ZERO;
        BigDecimal sumD4Pct = BigDecimal.ZERO;
        BigDecimal sumD5Pct = BigDecimal.ZERO;
        BigDecimal sumD5UpperPct = BigDecimal.ZERO;
        BigDecimal sumD5LowerPct = BigDecimal.ZERO;
        int count = 0;
        int upperCount = 0;
        int lowerCount = 0;

        for (MarketHeatmapResponse.StockFeatures s : stocks) {
            BigDecimal d1 = s.getYhatD1();
            if (d1 == null || d1.compareTo(BigDecimal.ZERO) <= 0) continue;

            BigDecimal d2 = s.getYhatD2();
            BigDecimal d3 = s.getYhatD3();
            BigDecimal d4 = s.getYhatD4();
            BigDecimal d5 = s.getYhatD5();

            // D+2 ~ D+5 모두 있는 종목만 평균에 포함 (부분 결손 종목은 스킵하여 안정성 확보)
            if (d2 == null || d3 == null || d4 == null || d5 == null) continue;

            // BUG-2 fix: percentChange가 null을 반환할 수 있으므로 NPE 방지 위해 명시적 체크.
            // 외부 가드(d1 > 0)와 함께 이중 안전망 — 모든 D+N 변동률이 정상 산출된 종목만 누적.
            BigDecimal d2Pct = percentChange(d1, d2);
            BigDecimal d3Pct = percentChange(d1, d3);
            BigDecimal d4Pct = percentChange(d1, d4);
            BigDecimal d5Pct = percentChange(d1, d5);
            if (d2Pct == null || d3Pct == null || d4Pct == null || d5Pct == null) continue;

            sumD2Pct = sumD2Pct.add(d2Pct);
            sumD3Pct = sumD3Pct.add(d3Pct);
            sumD4Pct = sumD4Pct.add(d4Pct);
            sumD5Pct = sumD5Pct.add(d5Pct);
            count++;

            BigDecimal upper = s.getYhatUpperD5();
            BigDecimal lower = s.getYhatLowerD5();
            if (upper != null) {
                BigDecimal upperPct = percentChange(d1, upper);
                if (upperPct != null) {
                    sumD5UpperPct = sumD5UpperPct.add(upperPct);
                    upperCount++;
                }
            }
            if (lower != null) {
                BigDecimal lowerPct = percentChange(d1, lower);
                if (lowerPct != null) {
                    sumD5LowerPct = sumD5LowerPct.add(lowerPct);
                    lowerCount++;
                }
            }
        }

        if (count == 0) {
            // 객체는 반환하되 모든 평균 값 null, dataCount=0
            return MarketHeatmapResponse.MarketForecastTrend.builder()
                    .d1ReturnPct(null)
                    .d2ReturnPct(null)
                    .d3ReturnPct(null)
                    .d4ReturnPct(null)
                    .d5ReturnPct(null)
                    .d5UpperPct(null)
                    .d5LowerPct(null)
                    .trendDirection(null)
                    .dataCount(0)
                    .build();
        }

        BigDecimal avgD2 = sumD2Pct.divide(BigDecimal.valueOf(count), 2, RoundingMode.HALF_UP);
        BigDecimal avgD3 = sumD3Pct.divide(BigDecimal.valueOf(count), 2, RoundingMode.HALF_UP);
        BigDecimal avgD4 = sumD4Pct.divide(BigDecimal.valueOf(count), 2, RoundingMode.HALF_UP);
        BigDecimal avgD5 = sumD5Pct.divide(BigDecimal.valueOf(count), 2, RoundingMode.HALF_UP);
        BigDecimal avgD5Upper = upperCount > 0
                ? sumD5UpperPct.divide(BigDecimal.valueOf(upperCount), 2, RoundingMode.HALF_UP)
                : null;
        BigDecimal avgD5Lower = lowerCount > 0
                ? sumD5LowerPct.divide(BigDecimal.valueOf(lowerCount), 2, RoundingMode.HALF_UP)
                : null;

        String direction;
        double d5Val = avgD5.doubleValue();
        if (d5Val > 1.0) direction = "상승세";
        else if (d5Val < -1.0) direction = "하락세";
        else direction = "횡보";

        return MarketHeatmapResponse.MarketForecastTrend.builder()
                .d1ReturnPct(BigDecimal.ZERO)
                .d2ReturnPct(avgD2)
                .d3ReturnPct(avgD3)
                .d4ReturnPct(avgD4)
                .d5ReturnPct(avgD5)
                .d5UpperPct(avgD5Upper)
                .d5LowerPct(avgD5Lower)
                .trendDirection(direction)
                .dataCount(count)
                .build();
    }

    /**
     * 변동률 (%) 계산: (target - base) / base * 100, 소수점 6자리 중간 계산 후 곱셈.
     *
     * BUG-2 fix: 함수 자체에 분모 0/null 가드 추가 (방어 코드).
     * - base/target 이 null 이거나 base <= 0 이면 null 반환
     * - 호출자는 반환값 null 체크 후 누적/집계 처리해야 함
     */
    private BigDecimal percentChange(BigDecimal base, BigDecimal target) {
        if (base == null || target == null || base.signum() <= 0) {
            return null;
        }
        return target.subtract(base)
                .divide(base, 6, RoundingMode.HALF_UP)
                .multiply(BigDecimal.valueOf(100));
    }

    // ============================================================
    // JDBC 결과 안전 캐스팅 헬퍼
    // PostgreSQL NUMERIC → BigDecimal, BIGINT → Long, INT → Integer
    // 드라이버/Aggregate 결과에 따라 Double/BigInteger 등으로 올 수 있어 방어적 변환
    // ============================================================

    /** 값 리스트의 중앙값 (2자리 반올림). 빈/널이면 null. */
    private static BigDecimal median(List<BigDecimal> values) {
        if (values == null || values.isEmpty()) {
            return null;
        }
        List<BigDecimal> sorted = new ArrayList<>(values);
        sorted.sort((a, b) -> a.compareTo(b));
        int n = sorted.size();
        if (n % 2 == 1) {
            return sorted.get(n / 2).setScale(2, RoundingMode.HALF_UP);
        }
        return sorted.get(n / 2 - 1)
                .add(sorted.get(n / 2))
                .divide(BigDecimal.valueOf(2), 2, RoundingMode.HALF_UP);
    }

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
