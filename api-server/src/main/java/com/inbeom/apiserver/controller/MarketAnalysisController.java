package com.inbeom.apiserver.controller;

import com.inbeom.apiserver.dto.common.ApiResponse;
import com.inbeom.apiserver.dto.market.*;
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

        LocalDate targetDate = marketAnalysisService.resolveDate(date);
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

        LocalDate targetDate = marketAnalysisService.resolveDate(date);
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

        LocalDate targetDate = marketAnalysisService.resolveDate(date);
        MarketDecisionsResponse response = marketAnalysisService.getMarketDecisions(targetDate);

        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * 최신 분석 날짜 조회
     * GET /api/market/latest-date
     */
    @GetMapping("/latest-date")
    public ResponseEntity<ApiResponse<LatestDateResponse>> getLatestAnalysisDate() {
        log.info("GET /api/market/latest-date");

        LatestDateResponse response = marketAnalysisService.getLatestAnalysisDate();

        return ResponseEntity.ok(ApiResponse.success(response));
    }

    /**
     * 30종목 히트맵 데이터 조회
     * GET /api/market/heatmap?date=2025-05-27
     */
    @GetMapping("/heatmap")
    public ResponseEntity<ApiResponse<MarketHeatmapResponse>> getHeatmapData(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate date
    ) {
        log.info("GET /api/market/heatmap - date: {}", date);

        LocalDate targetDate = marketAnalysisService.resolveDate(date);
        MarketHeatmapResponse response = marketAnalysisService.getHeatmapData(targetDate);

        return ResponseEntity.ok(ApiResponse.success(response));
    }
}
