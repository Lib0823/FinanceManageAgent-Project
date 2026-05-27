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
                COUNT(*) FILTER (WHERE atd.decision = 'buy') as buy_candidate,
                COUNT(*) FILTER (WHERE atd.decision = 'sell') as sell_candidate,
                COUNT(*) FILTER (WHERE atd.decision IS NULL OR atd.decision = 'hold') as neutral
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
        // 시장 전체 감성 점수 조회 (stock_code IS NULL)
        String sentimentSql = """
            SELECT sentiment_score
            FROM news_analysis
            WHERE analysis_date = ?
                AND stock_code IS NULL
            """;

        List<BigDecimal> sentimentResults = jdbcTemplate.queryForList(sentimentSql, BigDecimal.class, date);
        if (sentimentResults.isEmpty()) {
            return null;
        }
        BigDecimal sentimentScore = sentimentResults.get(0);

        // 종목별 감성 분포 조회
        String distributionSql = """
            SELECT
                COUNT(*) FILTER (WHERE na.sentiment_score >= 0.3) as positive_count,
                COUNT(*) FILTER (WHERE na.sentiment_score BETWEEN -0.3 AND 0.3) as neutral_count,
                COUNT(*) FILTER (WHERE na.sentiment_score <= -0.3) as negative_count,
                COUNT(*) as total_count
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

        Map<String, Object> result = new HashMap<>();
        result.put("sentiment_score", sentimentScore);
        result.put("distribution", distribution);

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
                AND atd.decision = ?
            ORDER BY atd.rank ASC
            LIMIT 3
            """;

        return jdbcTemplate.queryForList(sql, date, decisionType);
    }
}
