package com.inbeom.apiserver.service;

import com.inbeom.apiserver.client.KisApiClient;
import com.inbeom.apiserver.domain.User;
import com.inbeom.apiserver.dto.kis.KisBalanceResponse;
import com.inbeom.apiserver.dto.kis.KisDailyCcldResponse;
import com.inbeom.apiserver.dto.trade.BalanceSummaryResponse;
import com.inbeom.apiserver.dto.trade.HoldingResponse;
import com.inbeom.apiserver.dto.trade.TradeHistoryResponse;
import com.inbeom.apiserver.exception.UserNotFoundException;
import com.inbeom.apiserver.repository.UserRepository;
import com.inbeom.apiserver.service.KisAuthService.KisCredentials;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class TradingService {

    private final KisAuthService kisAuthService;
    private final KisApiClient kisApiClient;
    private final UserRepository userRepository;

    /**
     * Execute buy order via KIS API (VTTC0802U)
     * Note: Trade history is fetched from KIS API directly, not stored in DB
     */
    public Map<String, Object> executeBuy(Long userId, Long kisAccountId, String stockCode, String stockName,
                                           Integer quantity, BigDecimal orderPrice) {
        // 1. Get KIS credentials and token
        String kisToken = kisAuthService.getKisAccessToken(kisAccountId);
        KisCredentials credentials = kisAuthService.getKisCredentials(kisAccountId);

        // 2. Build request body
        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("CANO", credentials.accountNumber());
        requestBody.put("ACNT_PRDT_CD", credentials.accountProductCode());
        requestBody.put("PDNO", stockCode);
        requestBody.put("ORD_DVSN", "01"); // 시장가
        requestBody.put("ORD_QTY", String.valueOf(quantity));
        requestBody.put("ORD_UNPR", "0"); // 시장가는 0

        // 3. Call KIS API
        ResponseEntity<Map> response = kisApiClient.post(
                "/uapi/domestic-stock/v1/trading/order-cash",
                "VTTC0802U",
                kisToken,
                credentials.appKey(),
                credentials.appSecret(),
                requestBody,
                Map.class
        );

        log.info("Buy order executed for userId={}, stockCode={}, quantity={}, orderNumber={}",
                userId, stockCode, quantity, extractOrderNumber(response.getBody()));

        return response.getBody();
    }

    /**
     * Execute sell order via KIS API (VTTC0801U)
     * Note: Trade history is fetched from KIS API directly, not stored in DB
     */
    public Map<String, Object> executeSell(Long userId, Long kisAccountId, String stockCode, String stockName,
                                            Integer quantity, BigDecimal orderPrice) {
        String kisToken = kisAuthService.getKisAccessToken(kisAccountId);
        KisCredentials credentials = kisAuthService.getKisCredentials(kisAccountId);

        Map<String, Object> requestBody = new HashMap<>();
        requestBody.put("CANO", credentials.accountNumber());
        requestBody.put("ACNT_PRDT_CD", credentials.accountProductCode());
        requestBody.put("PDNO", stockCode);
        requestBody.put("ORD_DVSN", "01");
        requestBody.put("ORD_QTY", String.valueOf(quantity));
        requestBody.put("ORD_UNPR", "0");

        ResponseEntity<Map> response = kisApiClient.post(
                "/uapi/domestic-stock/v1/trading/order-cash",
                "VTTC0801U",
                kisToken,
                credentials.appKey(),
                credentials.appSecret(),
                requestBody,
                Map.class
        );

        log.info("Sell order executed for userId={}, stockCode={}, quantity={}, orderNumber={}",
                userId, stockCode, quantity, extractOrderNumber(response.getBody()));

        return response.getBody();
    }

    /**
     * Get trade history from KIS API (VTTC0081R)
     * 최근 3개월 거래내역 조회
     */
    public List<TradeHistoryResponse> getTradeHistory(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException(userId));

        // 1. Get KIS account from user
        Long kisAccountId = user.getKisAccount().getId();

        // 2. Get KIS credentials and token
        String kisToken = kisAuthService.getKisAccessToken(kisAccountId);
        KisCredentials credentials = kisAuthService.getKisCredentials(kisAccountId);

        // 3. Build query parameters for last 3 months
        LocalDate endDate = LocalDate.now();
        LocalDate startDate = endDate.minusMonths(3);
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd");

        Map<String, String> queryParams = new HashMap<>();
        queryParams.put("CANO", credentials.accountNumber());
        queryParams.put("ACNT_PRDT_CD", credentials.accountProductCode());
        queryParams.put("INQR_STRT_DT", startDate.format(formatter));
        queryParams.put("INQR_END_DT", endDate.format(formatter));
        queryParams.put("SLL_BUY_DVSN_CD", "00");  // 00: 전체, 01: 매도, 02: 매수
        queryParams.put("INQR_DVSN", "00");  // 00: 역순
        queryParams.put("PDNO", "");  // 전체 종목
        queryParams.put("CCLD_DVSN", "00");  // 00: 전체
        queryParams.put("ORD_GNO_BRNO", "");
        queryParams.put("ODNO", "");
        queryParams.put("INQR_DVSN_3", "00");
        queryParams.put("INQR_DVSN_1", "");
        queryParams.put("CTX_AREA_FK100", "");
        queryParams.put("CTX_AREA_NK100", "");

        // 4. Call KIS API
        ResponseEntity<KisDailyCcldResponse> response = kisApiClient.get(
                "/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
                "VTTC0081R",  // 주식일별주문체결조회 (모의투자)
                kisToken,
                credentials.appKey(),
                credentials.appSecret(),
                queryParams,
                KisDailyCcldResponse.class
        );

        // 5. Map KIS response to TradeHistoryResponse
        if (response.getBody() == null || response.getBody().getOutput1() == null) {
            log.warn("Empty trade history response from KIS API for userId={}", userId);
            return new ArrayList<>();
        }

        return response.getBody().getOutput1().stream()
                .map(this::mapToTradeHistoryResponse)
                .collect(Collectors.toList());
    }

    /**
     * Map KIS DailyCcldItem to TradeHistoryResponse
     */
    private TradeHistoryResponse mapToTradeHistoryResponse(KisDailyCcldResponse.DailyCcldItem item) {
        // Parse date and time
        DateTimeFormatter dateFormatter = DateTimeFormatter.ofPattern("yyyyMMdd");
        DateTimeFormatter timeFormatter = DateTimeFormatter.ofPattern("HHmmss");
        DateTimeFormatter dateDisplayFormatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
        DateTimeFormatter timeDisplayFormatter = DateTimeFormatter.ofPattern("HH:mm:ss");

        LocalDate orderDate = LocalDate.parse(item.getOrdDt(), dateFormatter);
        LocalDateTime orderedAt;

        if (item.getOrdTmd() != null && !item.getOrdTmd().isEmpty()) {
            String ordTmd = item.getOrdTmd().length() == 6 ? item.getOrdTmd() : String.format("%06d", Integer.parseInt(item.getOrdTmd()));
            orderedAt = LocalDateTime.of(
                    orderDate,
                    java.time.LocalTime.parse(ordTmd, timeFormatter)
            );
        } else {
            orderedAt = orderDate.atStartOfDay();
        }

        // Determine order type: 01=매도(SELL), 02=매수(BUY)
        String orderType = "02".equals(item.getSllBuyDvsnCd()) ? "BUY" : "SELL";

        // Determine order status based on execution
        String orderStatus;
        int totalQty = parseIntSafely(item.getTotCcldQty());
        int orderQty = parseIntSafely(item.getOrdQty());
        boolean isCancelled = "Y".equals(item.getCnclYn());

        if (isCancelled) {
            orderStatus = "CANCELLED";
        } else if (totalQty == 0) {
            orderStatus = "PENDING";
        } else if (totalQty < orderQty) {
            orderStatus = "PARTIAL";
        } else {
            orderStatus = "COMPLETED";
        }

        return TradeHistoryResponse.builder()
                .id(item.getOdno())
                .stockCode(item.getPdno())
                .stockName(item.getPrdtName())
                .orderType(orderType)
                .orderStatus(orderStatus)
                .quantity(orderQty)
                .orderPrice(parseBigDecimalSafely(item.getOrdUnpr()))
                .executedPrice(parseBigDecimalSafely(item.getAvgPrvs()))
                .executedQuantity(totalQty)
                .orderedAt(orderedAt)
                .orderDate(orderDate.format(dateDisplayFormatter))
                .orderTime(orderedAt.toLocalTime().format(timeDisplayFormatter))
                .build();
    }

    /**
     * Safely parse String to Integer
     */
    private int parseIntSafely(String value) {
        if (value == null || value.trim().isEmpty()) {
            return 0;
        }
        try {
            return Integer.parseInt(value.trim());
        } catch (NumberFormatException e) {
            log.warn("Failed to parse int: {}", value);
            return 0;
        }
    }

    /**
     * Safely parse String to BigDecimal
     */
    private BigDecimal parseBigDecimalSafely(String value) {
        if (value == null || value.trim().isEmpty()) {
            return BigDecimal.ZERO;
        }
        try {
            return new BigDecimal(value.trim());
        } catch (NumberFormatException e) {
            log.warn("Failed to parse BigDecimal: {}", value);
            return BigDecimal.ZERO;
        }
    }

    private String extractOrderNumber(Map<String, Object> kisResponse) {
        if (kisResponse != null && kisResponse.containsKey("output")) {
            Map<String, Object> output = (Map<String, Object>) kisResponse.get("output");
            return (String) output.get("ODNO");
        }
        return null;
    }

    /**
     * Get holdings (보유 종목 조회) from KIS API (VTTC8434R)
     */
    public BalanceSummaryResponse getHoldings(Long userId) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new UserNotFoundException(userId));

        // 1. Get KIS account from user
        Long kisAccountId = user.getKisAccount().getId();

        // 2. Get KIS credentials and token
        String kisToken = kisAuthService.getKisAccessToken(kisAccountId);
        KisCredentials credentials = kisAuthService.getKisCredentials(kisAccountId);

        // 3. Build query parameters
        Map<String, String> queryParams = new HashMap<>();
        queryParams.put("CANO", credentials.accountNumber());
        queryParams.put("ACNT_PRDT_CD", credentials.accountProductCode());
        queryParams.put("AFHR_FLPR_YN", "N");  // 시간외단일가여부
        queryParams.put("OFL_YN", "");  // 오프라인여부
        queryParams.put("INQR_DVSN", "02");  // 조회구분: 01-대출일별, 02-종목별
        queryParams.put("UNPR_DVSN", "01");  // 단가구분: 01-기본값
        queryParams.put("FUND_STTL_ICLD_YN", "N");  // 펀드결제분포함여부
        queryParams.put("FNCG_AMT_AUTO_RDPT_YN", "N");  // 융자금액자동상환여부
        queryParams.put("PRCS_DVSN", "01");  // 처리구분: 00-전일, 01-당일
        queryParams.put("CTX_AREA_FK100", "");  // 연속조회검색조건100
        queryParams.put("CTX_AREA_NK100", "");  // 연속조회키100

        // 4. Call KIS API
        ResponseEntity<KisBalanceResponse> response = kisApiClient.get(
                "/uapi/domestic-stock/v1/trading/inquire-balance",
                "VTTC8434R",  // 주식잔고조회 (모의투자)
                kisToken,
                credentials.appKey(),
                credentials.appSecret(),
                queryParams,
                KisBalanceResponse.class
        );

        // 5. Map KIS response to BalanceSummaryResponse
        if (response.getBody() == null) {
            log.warn("Empty balance response from KIS API for userId={}", userId);
            return BalanceSummaryResponse.builder()
                    .holdings(new ArrayList<>())
                    .totalEvaluationAmount(BigDecimal.ZERO)
                    .totalPurchaseAmount(BigDecimal.ZERO)
                    .totalProfitLoss(BigDecimal.ZERO)
                    .totalProfitLossRate(BigDecimal.ZERO)
                    .cashBalance(BigDecimal.ZERO)
                    .build();
        }

        KisBalanceResponse body = response.getBody();

        // Map output1 (holdings)
        List<HoldingResponse> holdings = new ArrayList<>();
        if (body.getOutput1() != null && !body.getOutput1().isEmpty()) {
            holdings = body.getOutput1().stream()
                    .map(this::mapToHoldingResponse)
                    .collect(Collectors.toList());
        }

        // Map output2 (summary)
        KisBalanceResponse.Output2 summary = body.getOutput2() != null && !body.getOutput2().isEmpty()
                ? body.getOutput2().get(0)
                : new KisBalanceResponse.Output2();

        // Calculate totals from holdings if Output2 fields are null
        BigDecimal totalEvaluationAmount = parseBigDecimalSafely(summary.getTotEvluAmt());
        BigDecimal totalPurchaseAmount = parseBigDecimalSafely(summary.getPchsAmtSmtl());
        BigDecimal totalProfitLoss = parseBigDecimalSafely(summary.getEvluPflsSmtl());
        BigDecimal totalProfitLossRate = parseBigDecimalSafely(summary.getEvluPflsRt());
        BigDecimal cashBalance = parseBigDecimalSafely(summary.getDncaTotAmt());

        // If Output2 fields are zero/null, calculate from holdings
        if ((totalPurchaseAmount == null || totalPurchaseAmount.compareTo(BigDecimal.ZERO) == 0) && !holdings.isEmpty()) {
            log.info("Output2 summary fields are null/zero, calculating from holdings");

            // Calculate sums from holdings
            totalPurchaseAmount = holdings.stream()
                    .map(HoldingResponse::getPurchaseAmount)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);

            totalProfitLoss = holdings.stream()
                    .map(HoldingResponse::getProfitLoss)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);

            totalEvaluationAmount = holdings.stream()
                    .map(HoldingResponse::getEvaluationAmount)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);

            // Calculate profit/loss rate: (totalProfitLoss / totalPurchaseAmount) * 100
            if (totalPurchaseAmount.compareTo(BigDecimal.ZERO) > 0) {
                totalProfitLossRate = totalProfitLoss
                        .divide(totalPurchaseAmount, 4, RoundingMode.HALF_UP)
                        .multiply(new BigDecimal("100"));
            } else {
                totalProfitLossRate = BigDecimal.ZERO;
            }
        }

        log.info("Final Balance Summary - TotalEvaluation: {}, TotalPurchase: {}, TotalProfitLoss: {}, ProfitRate: {}%, Cash: {}",
                totalEvaluationAmount, totalPurchaseAmount, totalProfitLoss, totalProfitLossRate, cashBalance);

        return BalanceSummaryResponse.builder()
                .holdings(holdings)
                .totalEvaluationAmount(totalEvaluationAmount)
                .totalPurchaseAmount(totalPurchaseAmount)
                .totalProfitLoss(totalProfitLoss)
                .totalProfitLossRate(totalProfitLossRate)
                .cashBalance(cashBalance)
                .build();
    }

    /**
     * Map KIS Output1 to HoldingResponse
     */
    private HoldingResponse mapToHoldingResponse(KisBalanceResponse.Output1 item) {
        return HoldingResponse.builder()
                .stockCode(item.getPdno())
                .stockName(item.getPrdtName())
                .holdingQuantity(parseIntSafely(item.getHldgQty()))
                .availableQuantity(parseIntSafely(item.getOrdPsblQty()))
                .averagePrice(parseBigDecimalSafely(item.getPchsAvgPric()))
                .currentPrice(parseBigDecimalSafely(item.getPrpr()))
                .evaluationAmount(parseBigDecimalSafely(item.getEvluAmt()))
                .profitLoss(parseBigDecimalSafely(item.getEvluPflsAmt()))
                .profitLossRate(parseBigDecimalSafely(item.getEvluPflsRt()))
                .purchaseAmount(parseBigDecimalSafely(item.getPchsAmt()))
                .build();
    }
}
