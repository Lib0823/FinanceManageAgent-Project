package com.inbeom.apiserver.dto.market;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.Map;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MarketSentimentResponse {
    @JsonProperty("score")
    private BigDecimal score;

    @JsonProperty("label")
    private String label;

    @JsonProperty("distribution")
    private Distribution distribution;

    @JsonProperty("time_range")
    private String timeRange;

    @JsonProperty("sources")
    private String sources;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Distribution {
        @JsonProperty("positive")
        private CategoryInfo positive;

        @JsonProperty("neutral")
        private CategoryInfo neutral;

        @JsonProperty("negative")
        private CategoryInfo negative;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CategoryInfo {
        @JsonProperty("count")
        private Integer count;

        @JsonProperty("percent")
        private Integer percent;

        @JsonProperty("color")
        private String color;
    }
}
