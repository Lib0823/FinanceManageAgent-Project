package com.inbeom.apiserver.dto.trade;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class BalanceSummaryResponse {

    private List<HoldingResponse> holdings;  // 보유 종목 목록
    private BigDecimal totalEvaluationAmount;  // 총평가금액
    private BigDecimal totalPurchaseAmount;    // 매입금액합계
    private BigDecimal totalProfitLoss;        // 평가손익합계
    private BigDecimal totalProfitLossRate;    // 평가손익율
    private BigDecimal cashBalance;            // 예수금(현금잔고)
}
