package com.inbeom.apiserver.dto.trade;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class HoldingResponse {

    private String stockCode;           // 종목코드
    private String stockName;           // 종목명
    private Integer holdingQuantity;    // 보유수량
    private Integer availableQuantity;  // 매도가능수량
    private BigDecimal averagePrice;    // 매입평균가
    private BigDecimal currentPrice;    // 현재가
    private BigDecimal evaluationAmount;  // 평가금액
    private BigDecimal profitLoss;      // 평가손익
    private BigDecimal profitLossRate;  // 평가손익율(%)
    private BigDecimal purchaseAmount;  // 매입금액
}
