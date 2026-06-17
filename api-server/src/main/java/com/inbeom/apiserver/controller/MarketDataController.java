package com.inbeom.apiserver.controller;

import com.inbeom.apiserver.dto.common.ApiResponse;
import com.inbeom.apiserver.dto.market.ExchangeRateResponse;
import com.inbeom.apiserver.dto.market.IndicesResponse;
import com.inbeom.apiserver.dto.market.NewsItemResponse;
import com.inbeom.apiserver.service.MarketDataService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 홈 화면 위젯(주요지수 / 환율 / 속보)용 읽기 전용 시장 데이터 엔드포인트.
 *
 * <p>모두 항상 200 + ApiResponse.success 로 응답하며, 외부 소스 실패 시
 * 부분/빈 데이터로 degrade 한다(서비스 레이어에서 source 별 try/catch).
 */
@Slf4j
@RestController
@RequestMapping("/market")
@RequiredArgsConstructor
public class MarketDataController {

    private final MarketDataService marketDataService;

    /**
     * 주요지수 (국내 KIS 지수). 해외는 KIS 권한 미확인으로 생략될 수 있음.
     * GET /api/market/indices
     */
    @GetMapping("/indices")
    public ResponseEntity<ApiResponse<IndicesResponse>> getIndices() {
        log.info("GET /api/market/indices");
        IndicesResponse response = marketDataService.getIndices();
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * 환율 (frankfurter.app / ECB). USD·JPY(100엔)·EUR·CNY.
     * GET /api/market/exchange-rates
     */
    @GetMapping("/exchange-rates")
    public ResponseEntity<ApiResponse<List<ExchangeRateResponse>>> getExchangeRates() {
        log.info("GET /api/market/exchange-rates");
        List<ExchangeRateResponse> response = marketDataService.getExchangeRates();
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * 속보 (경제 RSS: 한국경제/매일경제/연합뉴스). 최신 ~8건.
     * GET /api/market/news
     */
    @GetMapping("/news")
    public ResponseEntity<ApiResponse<List<NewsItemResponse>>> getNews() {
        log.info("GET /api/market/news");
        List<NewsItemResponse> response = marketDataService.getNews();
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
