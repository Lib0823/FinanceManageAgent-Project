package com.inbeom.apiserver.controller;

import com.inbeom.apiserver.dto.common.ApiResponse;
import com.inbeom.apiserver.dto.trade.BalanceSummaryResponse;
import com.inbeom.apiserver.dto.trade.RecentTradeResponse;
import com.inbeom.apiserver.dto.trade.TradeHistoryResponse;
import com.inbeom.apiserver.dto.trade.TradeRequest;
import com.inbeom.apiserver.service.TradingService;
import com.inbeom.apiserver.util.JwtTokenProvider;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/trading")
@RequiredArgsConstructor
public class TradingController {

    private final TradingService tradingService;
    private final JwtTokenProvider jwtTokenProvider;

    /**
     * POST /api/trading/buy
     * Execute buy order via KIS API
     */
    @PostMapping("/buy")
    public ResponseEntity<ApiResponse<Map<String, Object>>> buy(
            @RequestHeader("Authorization") String authHeader,
            @Valid @RequestBody TradeRequest request
    ) {
        String token = authHeader.substring(7);
        Long userId = jwtTokenProvider.getUserIdFromToken(token);
        Long kisAccountId = jwtTokenProvider.getKisAccountIdFromToken(token);

        Map<String, Object> result = tradingService.executeBuy(
                userId,
                kisAccountId,
                request.getStockCode(),
                request.getStockName(),
                request.getQuantity(),
                request.getPrice()
        );

        return ResponseEntity.ok(
                ApiResponse.success("Buy order executed successfully", result)
        );
    }

    /**
     * POST /api/trading/sell
     * Execute sell order via KIS API
     */
    @PostMapping("/sell")
    public ResponseEntity<ApiResponse<Map<String, Object>>> sell(
            @RequestHeader("Authorization") String authHeader,
            @Valid @RequestBody TradeRequest request
    ) {
        String token = authHeader.substring(7);
        Long userId = jwtTokenProvider.getUserIdFromToken(token);
        Long kisAccountId = jwtTokenProvider.getKisAccountIdFromToken(token);

        Map<String, Object> result = tradingService.executeSell(
                userId,
                kisAccountId,
                request.getStockCode(),
                request.getStockName(),
                request.getQuantity(),
                request.getPrice()
        );

        return ResponseEntity.ok(
                ApiResponse.success("Sell order executed successfully", result)
        );
    }

    /**
     * GET /api/trading/history
     * Get trade history from KIS API (최근 3개월)
     */
    @GetMapping("/history")
    public ResponseEntity<ApiResponse<List<TradeHistoryResponse>>> getHistory(
            @RequestHeader("Authorization") String authHeader
    ) {
        String token = authHeader.substring(7);
        Long userId = jwtTokenProvider.getUserIdFromToken(token);

        List<TradeHistoryResponse> history = tradingService.getTradeHistory(userId);

        return ResponseEntity.ok(
                ApiResponse.success("Trade history retrieved from KIS API successfully", history)
        );
    }

    /**
     * GET /api/trading/recent
     * 홈 화면 알림용 최근 거래내역 (DB trade_history 기반). KIS 라이브가 아니므로 빠르고 안정적이다.
     */
    @GetMapping("/recent")
    public ResponseEntity<ApiResponse<List<RecentTradeResponse>>> getRecentTrades(
            @RequestHeader("Authorization") String authHeader
    ) {
        String token = authHeader.substring(7);
        Long userId = jwtTokenProvider.getUserIdFromToken(token);

        List<RecentTradeResponse> trades = tradingService.getRecentTrades(userId);

        return ResponseEntity.ok(
                ApiResponse.success("Recent trades retrieved successfully", trades)
        );
    }

    /**
     * GET /api/trading/holdings
     * Get current holdings from KIS API (보유 종목 조회)
     */
    @GetMapping("/holdings")
    public ResponseEntity<ApiResponse<BalanceSummaryResponse>> getHoldings(
            @RequestHeader("Authorization") String authHeader
    ) {
        String token = authHeader.substring(7);
        Long userId = jwtTokenProvider.getUserIdFromToken(token);

        BalanceSummaryResponse holdings = tradingService.getHoldings(userId);

        return ResponseEntity.ok(
                ApiResponse.success("Holdings retrieved successfully", holdings)
        );
    }
}
