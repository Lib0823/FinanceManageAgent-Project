package com.inbeom.apiserver.dto.market;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.List;

/**
 * 홈 화면 "주요지수" 위젯용 응답.
 * categories[].items[] 형태로 국내/해외 지수를 묶어 전달한다.
 * (해외 지수는 KIS 권한 확인이 불가하면 category 자체를 생략한다 — 가짜 데이터 금지.)
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class IndicesResponse {

    @JsonProperty("categories")
    private List<IndexCategory> categories;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class IndexCategory {
        @JsonProperty("key")
        private String key;

        @JsonProperty("label")
        private String label;

        @JsonProperty("items")
        private List<IndexItem> items;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class IndexItem {
        @JsonProperty("label")
        private String label;

        @JsonProperty("value")
        private BigDecimal value;

        @JsonProperty("change")
        private BigDecimal change;

        @JsonProperty("change_percent")
        private BigDecimal changePercent;
    }
}
