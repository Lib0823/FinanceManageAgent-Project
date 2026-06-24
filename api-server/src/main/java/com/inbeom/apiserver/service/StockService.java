package com.inbeom.apiserver.service;

import com.inbeom.apiserver.domain.StockMaster;
import com.inbeom.apiserver.dto.stock.OrderbookResponse;
import com.inbeom.apiserver.dto.stock.StockPriceResponse;
import com.inbeom.apiserver.dto.stock.StockSearchResponse;
import com.inbeom.apiserver.repository.StockMasterRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * 종목 검색·현재가 조회 서비스 (검색 화면 - SearchView).
 *
 * <p>검색은 stock_master 카탈로그(코드 prefix / 종목명 부분일치)에서, 현재가는 공용
 * {@link KisQuoteClient} 로 KIS 실전 시세를 조회한다. 시세 비활성/실패 시 가격은 null,
 * notice 로 사유를 노출하며 절대 예외를 전파하지 않는다.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class StockService {

    private final StockMasterRepository stockMasterRepository;
    private final KisQuoteClient kisQuoteClient;

    /**
     * 종목 검색: 코드 prefix 또는 종목명 부분일치(대소문자 무시), 최대 30건.
     * 빈/공백 질의는 빈 리스트.
     */
    @Transactional(readOnly = true)
    public List<StockSearchResponse> searchStocks(String q) {
        if (q == null || q.isBlank()) {
            return Collections.emptyList();
        }
        String term = q.trim();
        List<StockMaster> matches =
                stockMasterRepository.findTop30ByStockCodeStartingWithOrStockNameContainingIgnoreCase(term, term);
        return matches.stream()
                .map(m -> StockSearchResponse.builder()
                        .stockCode(m.getStockCode())
                        .stockName(m.getStockName())
                        .market(m.getMarket())
                        .build())
                .toList();
    }

    /**
     * 종목 현재가 조회. 시세 비활성/실패 시 가격 null + notice.
     * KIS output 매핑: stck_prpr→currentPrice, prdy_vrss→changeAmount, prdy_ctrt→changeRate.
     */
    public StockPriceResponse getPrice(String stockCode) {
        Map<String, Object> price = kisQuoteClient.fetchCurrentPrice(stockCode);
        if (price == null) {
            return StockPriceResponse.builder()
                    .stockCode(stockCode)
                    .notice(kisQuoteClient.getNotice() != null
                            ? kisQuoteClient.getNotice()
                            : KisQuoteClient.NOTICE_KIS_QUOTE)
                    .build();
        }
        return StockPriceResponse.builder()
                .stockCode(stockCode)
                .currentPrice(parseLong(price.get("stck_prpr")))
                .changeAmount(parseLong(price.get("prdy_vrss")))
                .changeRate(parseBigDecimal(price.get("prdy_ctrt")))
                .build();
    }

    /**
     * 종목 호가 조회. 호가(FHKST01010200 output1) + 현재가(FHKST01010100 stck_prpr)를 조합한다.
     * 호가 비활성/실패 시 asks/bids 빈 리스트, currentPrice null, notice 로 사유 노출.
     * KIS output1 매핑: askp{n}/askp_rsqn{n}→asks, bidp{n}/bidp_rsqn{n}→bids (0원 호가 제외).
     */
    public OrderbookResponse getOrderbook(String stockCode) {
        Map<String, Object> orderbook = kisQuoteClient.fetchOrderbook(stockCode);
        if (orderbook == null) {
            return OrderbookResponse.builder()
                    .stockCode(stockCode)
                    .currentPrice(null)
                    .asks(Collections.emptyList())
                    .bids(Collections.emptyList())
                    .notice(kisQuoteClient.getNotice() != null
                            ? kisQuoteClient.getNotice()
                            : KisQuoteClient.NOTICE_KIS_QUOTE)
                    .build();
        }

        Long currentPrice = null;
        Map<String, Object> price = kisQuoteClient.fetchCurrentPrice(stockCode);
        if (price != null) {
            currentPrice = parseLong(price.get("stck_prpr"));
        }

        return OrderbookResponse.builder()
                .stockCode(stockCode)
                .currentPrice(currentPrice)
                .asks(buildLevels(orderbook, "askp", "askp_rsqn"))
                .bids(buildLevels(orderbook, "bidp", "bidp_rsqn"))
                .build();
    }

    /**
     * 1~10단계 호가/잔량을 OrderbookLevel 리스트로 변환. 가격이 null 또는 0인 단계는 제외한다.
     */
    private List<OrderbookResponse.OrderbookLevel> buildLevels(Map<String, Object> output1,
                                                               String priceKeyPrefix,
                                                               String quantityKeyPrefix) {
        List<OrderbookResponse.OrderbookLevel> levels = new ArrayList<>();
        for (int i = 1; i <= 10; i++) {
            Long price = parseLong(output1.get(priceKeyPrefix + i));
            if (price == null || price == 0L) {
                continue;
            }
            Long quantity = parseLong(output1.get(quantityKeyPrefix + i));
            levels.add(OrderbookResponse.OrderbookLevel.builder()
                    .price(price)
                    .quantity(quantity != null ? quantity : 0L)
                    .build());
        }
        return levels;
    }

    private String asString(Object o) {
        if (o == null) {
            return null;
        }
        String s = String.valueOf(o).trim();
        return s.isEmpty() ? null : s;
    }

    private Long parseLong(Object o) {
        String s = asString(o);
        if (s == null) {
            return null;
        }
        try {
            String cleaned = s.replace(",", "");
            if (cleaned.contains(".")) {
                return (long) Double.parseDouble(cleaned);
            }
            return Long.parseLong(cleaned);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private BigDecimal parseBigDecimal(Object o) {
        String s = asString(o);
        if (s == null) {
            return null;
        }
        try {
            return new BigDecimal(s.replace(",", ""));
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
