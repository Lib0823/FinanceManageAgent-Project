package com.inbeom.apiserver.dto.company;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

/**
 * 종목 기본정보 응답 (종목 상세 화면 - 기본정보 탭)
 * GET /company/{stockCode}/basic-info
 *
 * KIS 주식현재가 시세(FHKST01010100) + DART 회사개황(company.json) 조합.
 * KIS/DART 호출 실패 시 해당 필드는 null 로 degrade 한다.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BasicInfoResponse {

    @JsonProperty("stock_code")
    private String stockCode;

    @JsonProperty("stock_name")
    private String stockName;

    @JsonProperty("stock_name_en")
    private String stockNameEn;

    // 현재가 (원)
    @JsonProperty("current_price")
    private Long currentPrice;

    // 전일 대비 등락률 (%)
    @JsonProperty("change_rate")
    private BigDecimal changeRate;

    // 시가총액 (원 단위 = hts_avls 억원 * 100,000,000)
    @JsonProperty("market_cap")
    private Long marketCap;

    // 상장 주식수
    @JsonProperty("listed_shares")
    private Long listedShares;

    // 업종명 (KIS bstp_kor_isnm | DART induty | null)
    @JsonProperty("sector")
    private String sector;

    @JsonProperty("per")
    private BigDecimal per;

    @JsonProperty("pbr")
    private BigDecimal pbr;

    @JsonProperty("eps")
    private BigDecimal eps;

    @JsonProperty("bps")
    private BigDecimal bps;

    // 52주 최고/최저가 (원)
    @JsonProperty("week52_high")
    private Long week52High;

    @JsonProperty("week52_low")
    private Long week52Low;

    // DART 회사개황
    @JsonProperty("address")
    private String address;

    @JsonProperty("homepage")
    private String homepage;

    @JsonProperty("ceo_name")
    private String ceoName;

    // 설립일 (YYYYMMDD, DART est_dt)
    @JsonProperty("established_date")
    private String establishedDate;

    // DART 회사개황 조회 성공 여부
    @JsonProperty("has_dart_profile")
    private Boolean hasDartProfile;

    // 일부/전체 데이터 미연동 시 UI 안내용 메시지 (모두 정상이면 null)
    @JsonProperty("notice")
    private String notice;
}
