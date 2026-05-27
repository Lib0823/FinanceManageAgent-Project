package com.inbeom.apiserver.controller;

import com.inbeom.apiserver.dto.common.ApiResponse;
import com.inbeom.apiserver.dto.market.MarketDecisionsResponse;
import com.inbeom.apiserver.dto.market.MarketSentimentResponse;
import com.inbeom.apiserver.dto.market.MarketSummaryResponse;
import com.inbeom.apiserver.service.MarketAnalysisService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;

@Slf4j
@RestController
@RequestMapping("/market")
@RequiredArgsConstructor
public class MarketAnalysisController {

    private final MarketAnalysisService marketAnalysisService;

    /**
     * 시장 전체 요약 데이터 조회
     * GET /api/market/summary?date=2025-05-27
     */
    @GetMapping("/summary")
    public ResponseEntity<ApiResponse<MarketSummaryResponse>> getMarketSummary(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date
    ) {
        log.info("GET /api/market/summary - date: {}", date);

        LocalDate targetDate = date != null ? date : LocalDate.now();
        MarketSummaryResponse response = marketAnalysisService.getMarketSummary(targetDate);

        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * 시장 감성 분석 데이터 조회
     * GET /api/market/sentiment?date=2025-05-27
     */
    @GetMapping("/sentiment")
    public ResponseEntity<ApiResponse<MarketSentimentResponse>> getMarketSentiment(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date
    ) {
        log.info("GET /api/market/sentiment - date: {}", date);

        LocalDate targetDate = date != null ? date : LocalDate.now();
        MarketSentimentResponse response = marketAnalysisService.getMarketSentiment(targetDate);

        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * AI 매매 결정 TOP3 조회
     * GET /api/market/decisions?date=2025-05-27
     */
    @GetMapping("/decisions")
    public ResponseEntity<ApiResponse<MarketDecisionsResponse>> getMarketDecisions(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date
    ) {
        log.info("GET /api/market/decisions - date: {}", date);

        LocalDate targetDate = date != null ? date : LocalDate.now();
        MarketDecisionsResponse response = marketAnalysisService.getMarketDecisions(targetDate);

        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
