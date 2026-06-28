package com.inbeom.apiserver.repository;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * trade_execution_plan 조회 (멀티유저 봇 실행 기록).
 *
 * <p>거래내역 화면의 "AI 매매" 배지를 위해, 해당 사용자의 봇 실행 주문번호(KIS ODNO)
 * 집합을 제공한다. KIS 거래내역의 주문번호와 대조해 봇 주문 여부를 판별한다.
 */
@Repository
public class TradeExecutionPlanRepository {

    private final JdbcTemplate jdbcTemplate;

    public TradeExecutionPlanRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /**
     * 해당 사용자의 봇 실행 주문번호(ODNO) 집합.
     * order_no 가 기록된 행만(= KIS 가 접수해 주문번호가 부여된 봇 주문) 포함한다.
     */
    public Set<String> findExecutedOrderNos(Long userId) {
        String sql = """
            SELECT order_no
            FROM trade_execution_plan
            WHERE user_id = ?
                AND order_no IS NOT NULL
            """;
        List<String> rows = jdbcTemplate.queryForList(sql, String.class, userId);
        return new HashSet<>(rows);
    }
}
