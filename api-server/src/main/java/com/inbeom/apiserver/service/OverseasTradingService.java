package com.inbeom.apiserver.service;

import com.inbeom.apiserver.client.KisApiClient;
import com.inbeom.apiserver.domain.User;
import com.inbeom.apiserver.dto.overseas.OverseasBalanceResponse;
import com.inbeom.apiserver.dto.overseas.OverseasOrderRequest;
import com.inbeom.apiserver.repository.UserRepository;
import com.inbeom.apiserver.service.KisAuthService.KisCredentials;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 해외주식(미국) 잔고/매수/매도 서비스.
 *
 * <p>잔고/매매는 mock 도메인 + 사용자 DB 키(path A, {@link KisAuthService}) 흐름이다
 * ({@link TradingService} 패턴 미러). 해외 TR 은 모의 V변형 상수를 직접 전송하며
 * {@link KisApiClient#convertTrId}에 의존하지 않는다(VTTS/VTTT 는 변환 대상이 아님).
 *
 * <p>모의 해외매매 미지원·rt_cd != 0·예외 시 절대 예외를 전파하지 않는다:
 * 잔고는 빈 목록 + notice, 주문은 {@code {success:false, notice:"..."}} 로 graceful degrade 한다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OverseasTradingService {

    private final KisAuthService kisAuthService;
    private final KisApiClient kisApiClient;
    private final UserRepository userRepository;

    // 해외 TR (모의 V변형 — convertTrId 미적용 대상이므로 상수로 직접 확정)
    private static final String TR_BALANCE = "VTTS3012R";   // 해외주식 잔고 (모의)
    private static final String TR_BUY = "VTTT1002U";       // 미국 매수 주문 (모의)
    private static final String TR_SELL = "VTTT1006U";      // 미국 매도 주문 (모의)

    private static final String BALANCE_ENDPOINT = "/uapi/overseas-stock/v1/trading/inquire-balance";
    private static final String ORDER_ENDPOINT = "/uapi/overseas-stock/v1/trading/order";

    private static final String NOTICE_BALANCE_FAILED = "해외 잔고를 불러오지 못했습니다";
    private static final String NOTICE_ORDER_FAILED = "해외 주문에 실패했습니다 (모의투자 해외매매 미지원일 수 있습니다)";

    /**
     * 해외주식 잔고 조회 (VTTS3012R, 모의). 미국 3거래소(NASD/NYSE/AMEX)를 순회하며 보유종목을 합산한다.
     * 미지원/실패/예외 시 빈 목록 + notice 로 degrade(예외 전파 금지).
     */
    @SuppressWarnings("unchecked")
    public OverseasBalanceResponse getBalance(Long userId) {
        try {
            User user = userRepository.findById(userId).orElse(null);
            if (user == null || user.getKisAccount() == null) {
                log.warn("Overseas balance: no KIS account for userId={}", userId);
                return emptyBalance(NOTICE_BALANCE_FAILED);
            }

            Long kisAccountId = user.getKisAccount().getId();
            String kisToken = kisAuthService.getKisAccessToken(kisAccountId);
            KisCredentials credentials = kisAuthService.getKisCredentials(kisAccountId);

            List<OverseasBalanceResponse.OverseasHolding> holdings = new ArrayList<>();
            BigDecimal totalEval = BigDecimal.ZERO;
            BigDecimal totalPurchase = BigDecimal.ZERO;
            BigDecimal totalProfitLoss = BigDecimal.ZERO;
            boolean anyOk = false;

            for (OverseasExchange ex : OverseasExchange.values()) {
                Map<String, String> queryParams = new LinkedHashMap<>();
                queryParams.put("CANO", credentials.accountNumber());
                queryParams.put("ACNT_PRDT_CD", credentials.accountProductCode());
                queryParams.put("OVRS_EXCG_CD", ex.balanceCode());
                queryParams.put("TR_CRCY_CD", ex.currency());
                queryParams.put("CTX_AREA_FK200", "");
                queryParams.put("CTX_AREA_NK200", "");

                Map<String, Object> body;
                try {
                    ResponseEntity<Map> response = kisApiClient.get(
                            BALANCE_ENDPOINT,
                            TR_BALANCE,
                            kisToken,
                            credentials.appKey(),
                            credentials.appSecret(),
                            queryParams,
                            Map.class
                    );
                    body = response.getBody();
                } catch (Exception e) {
                    log.warn("Overseas balance call failed for userId={} excd={}: {}",
                            userId, ex.balanceCode(), e.getMessage());
                    continue;
                }

                if (!isRtOk(body)) {
                    log.warn("Overseas balance rt_cd!=0 for userId={} excd={}: {}",
                            userId, ex.balanceCode(), body != null ? body.get("msg1") : "null body");
                    continue;
                }
                anyOk = true;

                Object output1 = body.get("output1");
                if (output1 instanceof List) {
                    for (Object row : (List<Object>) output1) {
                        if (!(row instanceof Map)) {
                            continue;
                        }
                        Map<String, Object> item = (Map<String, Object>) row;
                        OverseasBalanceResponse.OverseasHolding holding = mapHolding(item);
                        // 보유수량 0 인 종목은 제외(잔여 노출 방지)
                        if (holding.getQuantity() != null && holding.getQuantity() > 0) {
                            holdings.add(holding);
                            totalPurchase = totalPurchase.add(
                                    parseBigDecimalSafely(asString(item.get("frcr_pchs_amt1"))));
                            totalEval = totalEval.add(
                                    parseBigDecimalSafely(asString(item.get("ovrs_stck_evlu_amt"))));
                            totalProfitLoss = totalProfitLoss.add(
                                    holding.getEvalProfitLoss() != null
                                            ? holding.getEvalProfitLoss() : BigDecimal.ZERO);
                        }
                    }
                }

                // output2(요약)에 통화별 평가/손익이 있으면 우선 누적 시도 (단일 거래소 응답 기준)
                Object output2 = body.get("output2");
                Map<String, Object> summary = firstMap(output2);
                if (summary != null) {
                    BigDecimal sumEval = parseBigDecimalSafely(asString(summary.get("tot_evlu_pfls_amt")));
                    // output2 의 합계 필드는 응답에 따라 비어있을 수 있어 보유종목 합을 신뢰값으로 둔다.
                    log.debug("Overseas balance summary excd={} tot_evlu_pfls_amt={}", ex.balanceCode(), sumEval);
                }
            }

            if (!anyOk) {
                return emptyBalance(NOTICE_BALANCE_FAILED);
            }

            return OverseasBalanceResponse.builder()
                    .holdings(holdings)
                    .totalEval(totalEval)
                    .totalPurchase(totalPurchase)
                    .totalProfitLoss(totalProfitLoss)
                    .currency("USD")
                    .notice(null)
                    .build();
        } catch (Exception e) {
            log.warn("Overseas balance failed for userId={}: {}", userId, e.getMessage());
            return emptyBalance(NOTICE_BALANCE_FAILED);
        }
    }

    /**
     * 해외주식 매수 (VTTT1002U, 모의). 지정가(ORD_DVSN="00")만. 실패 시 {@code {success:false, notice}}.
     */
    public Map<String, Object> buy(Long userId, OverseasOrderRequest request) {
        return order(userId, request, true);
    }

    /**
     * 해외주식 매도 (VTTT1006U, 모의). 지정가(ORD_DVSN="00")만. 실패 시 {@code {success:false, notice}}.
     */
    public Map<String, Object> sell(Long userId, OverseasOrderRequest request) {
        return order(userId, request, false);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> order(Long userId, OverseasOrderRequest request, boolean isBuy) {
        try {
            BigDecimal price = request.getPrice();
            if (price == null || price.compareTo(BigDecimal.ZERO) <= 0) {
                // 모의 해외 주문은 지정가 전용 → 단가 필수
                return orderFailure("해외 주문은 지정가만 지원합니다 (단가 필수)");
            }

            User user = userRepository.findById(userId).orElse(null);
            if (user == null || user.getKisAccount() == null) {
                log.warn("Overseas order: no KIS account for userId={}", userId);
                return orderFailure(NOTICE_ORDER_FAILED);
            }

            Long kisAccountId = user.getKisAccount().getId();
            String kisToken = kisAuthService.getKisAccessToken(kisAccountId);
            KisCredentials credentials = kisAuthService.getKisCredentials(kisAccountId);

            OverseasExchange ex = OverseasExchange.fromCode(request.getExchange());

            Map<String, Object> requestBody = new HashMap<>();
            requestBody.put("CANO", credentials.accountNumber());
            requestBody.put("ACNT_PRDT_CD", credentials.accountProductCode());
            requestBody.put("OVRS_EXCG_CD", ex.balanceCode());
            requestBody.put("PDNO", request.getSymbol());
            requestBody.put("ORD_QTY", String.valueOf(request.getQuantity()));
            requestBody.put("OVRS_ORD_UNPR", price.toPlainString());
            requestBody.put("CTAC_TLNO", "");
            requestBody.put("MGCO_APTM_ODNO", "");
            requestBody.put("SLL_TYPE", isBuy ? "" : "00");
            requestBody.put("ORD_SVR_DVSN_CD", "0");
            requestBody.put("ORD_DVSN", "00");  // 지정가 전용

            String trId = isBuy ? TR_BUY : TR_SELL;

            Map<String, Object> body;
            try {
                ResponseEntity<Map> response = kisApiClient.post(
                        ORDER_ENDPOINT,
                        trId,
                        kisToken,
                        credentials.appKey(),
                        credentials.appSecret(),
                        requestBody,
                        Map.class
                );
                body = response.getBody();
            } catch (Exception e) {
                log.warn("Overseas {} order call failed for userId={} symbol={}: {}",
                        isBuy ? "buy" : "sell", userId, request.getSymbol(), e.getMessage());
                return orderFailure(NOTICE_ORDER_FAILED);
            }

            if (!isRtOk(body)) {
                String msg = body != null ? String.valueOf(body.get("msg1")) : "null body";
                log.warn("Overseas {} order rt_cd!=0 for userId={} symbol={}: {}",
                        isBuy ? "buy" : "sell", userId, request.getSymbol(), msg);
                return orderFailure(NOTICE_ORDER_FAILED);
            }

            String orderNumber = null;
            Object output = body.get("output");
            if (output instanceof Map) {
                orderNumber = asString(((Map<String, Object>) output).get("ODNO"));
            }

            log.info("Overseas {} order executed for userId={}, symbol={}, qty={}, orderNumber={}",
                    isBuy ? "buy" : "sell", userId, request.getSymbol(), request.getQuantity(), orderNumber);

            Map<String, Object> result = new HashMap<>();
            result.put("success", true);
            result.put("orderNumber", orderNumber);
            result.put("symbol", request.getSymbol());
            result.put("exchange", ex.balanceCode());
            result.put("quantity", request.getQuantity());
            result.put("price", price);
            result.put("orderType", isBuy ? "BUY" : "SELL");
            return result;
        } catch (Exception e) {
            log.warn("Overseas order failed for userId={}: {}", userId, e.getMessage());
            return orderFailure(NOTICE_ORDER_FAILED);
        }
    }

    private Map<String, Object> orderFailure(String notice) {
        Map<String, Object> result = new HashMap<>();
        result.put("success", false);
        result.put("notice", notice);
        return result;
    }

    private OverseasBalanceResponse emptyBalance(String notice) {
        return OverseasBalanceResponse.builder()
                .holdings(new ArrayList<>())
                .totalEval(BigDecimal.ZERO)
                .totalPurchase(BigDecimal.ZERO)
                .totalProfitLoss(BigDecimal.ZERO)
                .currency("USD")
                .notice(notice)
                .build();
    }

    private OverseasBalanceResponse.OverseasHolding mapHolding(Map<String, Object> item) {
        return OverseasBalanceResponse.OverseasHolding.builder()
                .symbol(asString(item.get("ovrs_pdno")))
                .name(asString(item.get("ovrs_item_name")))
                .quantity(parseIntSafely(asString(item.get("ovrs_cblc_qty"))))
                .orderableQty(parseIntSafely(asString(item.get("ord_psbl_qty"))))
                .avgPrice(parseBigDecimalSafely(asString(item.get("pchs_avg_pric"))))
                .currentPrice(parseBigDecimalSafely(asString(item.get("now_pric2"))))
                .evalProfitLoss(parseBigDecimalSafely(asString(item.get("frcr_evlu_pfls_amt"))))
                .profitLossRate(parseBigDecimalSafely(asString(item.get("evlu_pfls_rt"))))
                .build();
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> firstMap(Object output) {
        if (output instanceof Map) {
            return (Map<String, Object>) output;
        }
        if (output instanceof List) {
            List<Object> list = (List<Object>) output;
            if (!list.isEmpty() && list.get(0) instanceof Map) {
                return (Map<String, Object>) list.get(0);
            }
        }
        return null;
    }

    private boolean isRtOk(Map<String, Object> body) {
        return body != null && "0".equals(String.valueOf(body.get("rt_cd")));
    }

    private String asString(Object value) {
        if (value == null) {
            return null;
        }
        String s = String.valueOf(value).trim();
        return s.isEmpty() ? null : s;
    }

    private int parseIntSafely(String value) {
        if (value == null || value.trim().isEmpty()) {
            return 0;
        }
        try {
            String cleaned = value.trim().replace(",", "");
            if (cleaned.contains(".")) {
                return (int) Double.parseDouble(cleaned);
            }
            return Integer.parseInt(cleaned);
        } catch (NumberFormatException e) {
            log.warn("Failed to parse int: {}", value);
            return 0;
        }
    }

    private BigDecimal parseBigDecimalSafely(String value) {
        if (value == null || value.trim().isEmpty()) {
            return BigDecimal.ZERO;
        }
        try {
            return new BigDecimal(value.trim().replace(",", ""));
        } catch (NumberFormatException e) {
            log.warn("Failed to parse BigDecimal: {}", value);
            return BigDecimal.ZERO;
        }
    }
}
