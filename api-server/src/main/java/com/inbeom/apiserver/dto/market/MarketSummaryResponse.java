package com.inbeom.apiserver.dto.market;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MarketSummaryResponse {
    @JsonProperty("date")
    private LocalDate date;

    @JsonProperty("kospi")
    private KospiInfo kospi;

    @JsonProperty("statistics")
    private StockStatistics statistics;

    @JsonProperty("supply_demand")
    private SupplyDemand supplyDemand;

    @JsonProperty("market_sentiment")
    private BigDecimal marketSentiment;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class KospiInfo {
        @JsonProperty("index")
        private BigDecimal index;

        @JsonProperty("change_rate")
        private BigDecimal changeRate;

        @JsonProperty("volume")
        private Long volume;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class StockStatistics {
        @JsonProperty("total")
        private Integer total;

        @JsonProperty("rising")
        private Integer rising;

        @JsonProperty("falling")
        private Integer falling;

        @JsonProperty("unchanged")
        private Integer unchanged;

        @JsonProperty("buy_candidate")
        private Integer buyCandidate;

        @JsonProperty("sell_candidate")
        private Integer sellCandidate;

        @JsonProperty("neutral")
        private Integer neutral;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class SupplyDemand {
        @JsonProperty("foreign_net_buy")
        private Long foreignNetBuy;

        @JsonProperty("institutional_net_buy")
        private Long institutionalNetBuy;
    }
}
