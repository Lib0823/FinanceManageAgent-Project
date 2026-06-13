package com.inbeom.apiserver.repository;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Repository
public class MarketAnalysisRepository {

    private final JdbcTemplate jdbcTemplate;

    public MarketAnalysisRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /**
     * 시장 전체 요약 데이터 조회
     */
    public Map<String, Object> getMarketSummary(LocalDate date) {
        String sql = """
            SELECT
                summary_date,
                kospi_index,
                kospi_change_rate,
                kospi_volume,
                total_stocks,
                rising_stocks,
                falling_stocks,
                unchanged_stocks,
                total_foreign_net_buy,
                total_institutional_net_buy,
                market_sentiment_score
            FROM market_daily_summary
            WHERE summary_date = ?
            """;

        List<Map<String, Object>> results = jdbcTemplate.queryForList(sql, date);
        return results.isEmpty() ? null : results.get(0);
    }

    /**
     * 30종목 통계 조회 (매수/매도/중립 후보)
     */
    public Map<String, Object> getStockStatistics(LocalDate date) {
        String sql = """
            SELECT
                COUNT(*) FILTER (WHERE is_selected = true) as total_stocks,
                COUNT(*) FILTER (WHERE LOWER(atd.decision) = 'buy') as buy_candidate,
                COUNT(*) FILTER (WHERE LOWER(atd.decision) = 'sell') as sell_candidate,
                COUNT(*) FILTER (WHERE atd.decision IS NULL OR LOWER(atd.decision) = 'hold') as neutral
            FROM stock_filter_score sfs
            LEFT JOIN ai_trade_decision atd
                ON sfs.stock_code = atd.stock_code
                AND sfs.score_date = atd.decision_date
            WHERE sfs.score_date = ?
                AND sfs.is_selected = true
            """;

        return jdbcTemplate.queryForMap(sql, date);
    }

    /**
     * 시장 감성 분석 데이터 조회
     */
    public Map<String, Object> getMarketSentiment(LocalDate date) {
        // 시장 전체 감성 점수 조회 (stock_code IS NULL) - 없을 수 있음
        String sentimentSql = """
            SELECT sentiment_score
            FROM news_analysis
            WHERE analysis_date = ?
                AND stock_code IS NULL
            """;

        List<BigDecimal> sentimentResults = jdbcTemplate.queryForList(sentimentSql, BigDecimal.class, date);
        BigDecimal sentimentScore = sentimentResults.isEmpty() ? null : sentimentResults.get(0);

        // 종목별 감성 분포 조회 (Top30 종목 기준) - 없을 수 있음
        // avg_sentiment: 시장 전반 sentiment가 NULL일 때 fallback으로 사용
        String distributionSql = """
            SELECT
                COUNT(*) FILTER (WHERE na.sentiment_score >= 0.3) as positive_count,
                COUNT(*) FILTER (WHERE na.sentiment_score BETWEEN -0.3 AND 0.3) as neutral_count,
                COUNT(*) FILTER (WHERE na.sentiment_score <= -0.3) as negative_count,
                COUNT(*) as total_count,
                AVG(na.sentiment_score) as avg_sentiment
            FROM news_analysis na
            JOIN stock_filter_score sfs
                ON na.stock_code = sfs.stock_code
                AND na.analysis_date = sfs.score_date
            WHERE na.analysis_date = ?
                AND sfs.is_selected = true
                AND na.stock_code IS NOT NULL
            """;

        List<Map<String, Object>> distributionResults = jdbcTemplate.queryForList(distributionSql, date);
        Map<String, Object> distribution = distributionResults.isEmpty() ? null : distributionResults.get(0);

        // 분포에 종목이 하나도 없으면 distribution은 비어있는 것으로 간주
        boolean distributionEmpty = distribution == null
                || distribution.get("total_count") == null
                || ((Number) distribution.get("total_count")).intValue() == 0;

        // 시장 전반 감성과 분포 둘 다 없으면 null 반환 (정말 데이터 없음)
        if (sentimentScore == null && distributionEmpty) {
            return null;
        }

        Map<String, Object> result = new HashMap<>();
        result.put("sentiment_score", sentimentScore);  // null 가능
        result.put("distribution", distributionEmpty ? null : distribution);
        return result;
    }

    /**
     * AI 매매 결정 TOP3 조회 (매수/매도)
     */
    public List<Map<String, Object>> getDecisionTop3(LocalDate date, String decisionType) {
        String sql = """
            SELECT
                atd.rank,
                atd.stock_code,
                atd.stock_name,
                atd.reason,
                atd.confidence_score,
                srp.current_price,
                srp.change_rate
            FROM ai_trade_decision atd
            LEFT JOIN stock_realtime_price srp
                ON atd.stock_code = srp.stock_code
            WHERE atd.decision_date = ?
                AND LOWER(atd.decision) = LOWER(?)
            ORDER BY atd.rank ASC
            LIMIT 3
            """;

        return jdbcTemplate.queryForList(sql, date, decisionType);
    }

    /**
     * 최신 분석 날짜 조회
     * 파이프라인 전체 단계(stock_filter_score, ai_trade_decision, news_analysis,
     * prophet_forecast)가 모두 완료된 날짜 중 가장 최신 날짜를 반환한다.
     * 4개 테이블에 동시에 존재하는 날짜만 "완전한 파이프라인"으로 간주하여,
     * Stage-1 필터링만 실행된 미완성 날짜를 제외한다.
     */
    public LocalDate getLatestAnalysisDate() {
        String sql = """
            SELECT MAX(d) as latest_date FROM (
                SELECT DISTINCT score_date AS d FROM stock_filter_score WHERE is_selected = true
                INTERSECT SELECT DISTINCT decision_date FROM ai_trade_decision
                INTERSECT SELECT DISTINCT analysis_date FROM news_analysis WHERE stock_code IS NOT NULL
                INTERSECT SELECT DISTINCT forecast_date FROM prophet_forecast
            ) t
            """;

        List<LocalDate> results = jdbcTemplate.queryForList(sql, LocalDate.class);
        return results.isEmpty() ? null : results.get(0);
    }

    /**
     * 30종목 히트맵 데이터 조회 (11개 피처)
     */
    public List<Map<String, Object>> getHeatmapData(LocalDate date) {
        String sql = """
            SELECT
                sfs.stock_code,
                sfs.stock_name,
                sfs.score_date,
                -- Stage 1 필터링 지표
                sfs.foreign_net_buy,
                sfs.institutional_net_buy,
                sfs.vol_avg_multiple,
                sfs.price_volatility,
                -- Stage 2-1 정량 지표
                sfs.morning_return,
                sfs.close_position,
                -- DART 재무 지표
                sf.per,
                sf.roe,
                sf.operating_margin,
                -- Stage 2-2 감성 지표
                na.sentiment_score,
                -- Stage 2-3 시계열 지표
                pf.price_trend,
                pf.volume_trend,
                pf.price_uncertainty,
                pf.yhat_d1,
                pf.yhat_d2,
                pf.yhat_d3,
                pf.yhat_d4,
                pf.yhat_d5,
                pf.yhat_upper_d5,
                pf.yhat_lower_d5
            FROM stock_filter_score sfs
            LEFT JOIN stock_financial sf
                ON sfs.stock_code = sf.stock_code
                AND sf.base_date = (
                    SELECT MAX(base_date)
                    FROM stock_financial sf2
                    WHERE sf2.stock_code = sfs.stock_code
                )
            LEFT JOIN news_analysis na
                ON sfs.stock_code = na.stock_code
                AND sfs.score_date = na.analysis_date
            LEFT JOIN prophet_forecast pf
                ON sfs.stock_code = pf.stock_code
                AND sfs.score_date = pf.forecast_date
            WHERE sfs.score_date = ?
                AND sfs.is_selected = TRUE
            ORDER BY sfs.scaler_score DESC
            """;

        return jdbcTemplate.queryForList(sql, date);
    }

    /**
     * 단일 종목 큐레이션 피처 조회 (Top30 선정 종목 기준).
     * stock_filter_score(is_selected=true)를 기준으로
     * news_analysis / prophet_forecast / stock_financial(최신 base_date)을 LEFT JOIN.
     * 해당 날짜에 분석 대상이 아니면 null 반환.
     */
    public Map<String, Object> getStockFeatures(String stockCode, LocalDate date) {
        String sql = """
            SELECT
                sfs.stock_name,
                sfs.foreign_net_buy,
                sfs.institutional_net_buy,
                sfs.vol_avg_multiple,
                sfs.morning_return,
                sfs.close_position,
                na.sentiment_score,
                na.news_count,
                pf.price_trend,
                pf.yhat_d1,
                pf.yhat_d5,
                pf.price_uncertainty,
                sf.per,
                sf.roe,
                sf.operating_margin
            FROM stock_filter_score sfs
            LEFT JOIN news_analysis na
                ON sfs.stock_code = na.stock_code
                AND sfs.score_date = na.analysis_date
            LEFT JOIN prophet_forecast pf
                ON sfs.stock_code = pf.stock_code
                AND sfs.score_date = pf.forecast_date
            LEFT JOIN stock_financial sf
                ON sfs.stock_code = sf.stock_code
                AND sf.base_date = (
                    SELECT MAX(base_date)
                    FROM stock_financial sf2
                    WHERE sf2.stock_code = sfs.stock_code
                )
            WHERE sfs.stock_code = ?
                AND sfs.score_date = ?
                AND sfs.is_selected = TRUE
            """;

        List<Map<String, Object>> results = jdbcTemplate.queryForList(sql, stockCode, date);
        return results.isEmpty() ? null : results.get(0);
    }

    /**
     * 단일 종목의 가장 최근 분석 날짜 조회 (is_selected=true 기준).
     * 보유 종목이 당일 Top30에서 탈락해도 직전 분석일 데이터로 fallback 하기 위해 사용.
     * 한 번도 분석 대상에 포함된 적이 없으면 null 반환.
     */
    public LocalDate getLatestStockScoreDate(String stockCode) {
        String sql = """
            SELECT MAX(score_date)
            FROM stock_filter_score
            WHERE stock_code = ?
                AND is_selected = TRUE
            """;

        List<LocalDate> results = jdbcTemplate.queryForList(sql, LocalDate.class, stockCode);
        return results.isEmpty() ? null : results.get(0);
    }
}
