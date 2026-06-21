package com.inbeom.apiserver.controller;

import com.inbeom.apiserver.dto.common.ApiResponse;
import com.inbeom.apiserver.dto.company.BasicInfoResponse;
import com.inbeom.apiserver.dto.company.DisclosuresResponse;
import com.inbeom.apiserver.dto.company.FinancialsResponse;
import com.inbeom.apiserver.service.CompanyInfoService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * 종목 상세 화면 탭(기본정보/재무제표/공시정보)용 컨트롤러.
 * KIS Open API(시세/재무) + DART Open API(회사개황/공시) 조합.
 *
 * 단일 사용자(MVP)·읽기 전용이며 인증을 요구하지 않는다 (SecurityConfig 에서 /company/** permitAll).
 * 외부 API 실패는 서비스 계층에서 null 필드로 degrade 되며 항상 200 + ApiResponse.success 를 반환한다.
 */
@Slf4j
@RestController
@RequestMapping("/company")
@RequiredArgsConstructor
public class CompanyController {

    private final CompanyInfoService companyInfoService;

    /**
     * 종목 기본정보 (현재가/시총/PER·PBR/52주/회사개황)
     * GET /api/company/{stockCode}/basic-info
     */
    @GetMapping("/{stockCode}/basic-info")
    public ResponseEntity<ApiResponse<BasicInfoResponse>> getBasicInfo(
            @PathVariable String stockCode
    ) {
        log.info("GET /api/company/{}/basic-info", stockCode);
        BasicInfoResponse response = companyInfoService.getBasicInfo(stockCode);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * 종목 재무제표 (연간 손익 + 주요 재무비율)
     * GET /api/company/{stockCode}/financials
     */
    @GetMapping("/{stockCode}/financials")
    public ResponseEntity<ApiResponse<FinancialsResponse>> getFinancials(
            @PathVariable String stockCode
    ) {
        log.info("GET /api/company/{}/financials", stockCode);
        FinancialsResponse response = companyInfoService.getFinancials(stockCode);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * 종목 공시정보 (최근 ~6개월, 최대 20건)
     * GET /api/company/{stockCode}/disclosures
     */
    @GetMapping("/{stockCode}/disclosures")
    public ResponseEntity<ApiResponse<DisclosuresResponse>> getDisclosures(
            @PathVariable String stockCode
    ) {
        log.info("GET /api/company/{}/disclosures", stockCode);
        DisclosuresResponse response = companyInfoService.getDisclosures(stockCode);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
