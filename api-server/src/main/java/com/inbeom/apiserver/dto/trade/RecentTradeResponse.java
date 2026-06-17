package com.inbeom.apiserver.dto.trade;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 홈 화면 알림용 최근 거래내역 (DB trade_history 기반).
 * KIS 라이브 조회({@code /trading/history})와 달리 DB 에서 읽어 빠르고 안정적이다.
 * 프론트가 camelCase 로 읽으므로 기본(camelCase) 직렬화를 사용한다.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RecentTradeResponse {
    private Long id;
    private String stockCode;
    private String stockName;
    private String orderType;     // BUY / SELL
    private String orderStatus;   // PENDING / COMPLETED ...
    private Integer quantity;
    private BigDecimal orderPrice;
    private BigDecimal executedPrice;
    private LocalDateTime orderedAt;
}
