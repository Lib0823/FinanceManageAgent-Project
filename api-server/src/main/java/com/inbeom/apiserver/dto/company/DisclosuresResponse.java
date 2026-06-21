package com.inbeom.apiserver.dto.company;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 종목 공시정보 응답 (종목 상세 화면 - 공시정보 탭)
 * GET /company/{stockCode}/disclosures
 *
 * DART 공시검색(list.json) 기반 최근 ~6개월, 최대 20건 (최신순).
 * DART 비활성/실패/데이터없음(status 013) 시 빈 리스트로 degrade.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DisclosuresResponse {

    @JsonProperty("stock_code")
    private String stockCode;

    @JsonProperty("disclosures")
    private List<Disclosure> disclosures;

    // DART 공시 미연동 시 UI 안내용 메시지 (정상이면 null)
    @JsonProperty("notice")
    private String notice;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class Disclosure {
        // 접수번호 (rcept_no)
        @JsonProperty("id")
        private String id;

        // 카테고리 (report_nm 에서 추출: 정기공시/주요사항/공정공시/기타 등)
        @JsonProperty("type")
        private String type;

        // 보고서명 (report_nm)
        @JsonProperty("title")
        private String title;

        // 접수일 (YYYY-MM-DD, rcept_dt 변환)
        @JsonProperty("date")
        private String date;

        // 중요 공시 여부 (제목 휴리스틱)
        @JsonProperty("important")
        private Boolean important;
    }
}
