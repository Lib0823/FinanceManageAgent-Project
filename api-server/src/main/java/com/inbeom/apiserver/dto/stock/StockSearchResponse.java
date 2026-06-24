package com.inbeom.apiserver.dto.stock;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 종목 검색 결과 항목 (검색 화면 - SearchView).
 * GET /stocks/search?q=
 *
 * stock_master 카탈로그에서 코드 prefix / 종목명 부분일치로 조회한다.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StockSearchResponse {

    @JsonProperty("stock_code")
    private String stockCode;

    @JsonProperty("stock_name")
    private String stockName;

    @JsonProperty("market")
    private String market;
}
