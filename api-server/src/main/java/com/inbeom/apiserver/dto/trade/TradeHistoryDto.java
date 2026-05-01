package com.inbeom.apiserver.dto.trade;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class TradeHistoryDto {

    private Long id;
    private String stockCode;
    private String stockName;
    private String orderType;
    private Integer quantity;
    private BigDecimal price;
    private LocalDateTime executedAt;
    private String kisOrderNo;

    public static class Response {
        @Getter
        @NoArgsConstructor
        @AllArgsConstructor
        @Builder
        public static class Summary {
            private Long id;
            private String stockCode;
            private String stockName;
            private String orderType;
            private Integer quantity;
            private BigDecimal price;
            private BigDecimal totalAmount;
            private LocalDateTime executedAt;
        }
    }
}
