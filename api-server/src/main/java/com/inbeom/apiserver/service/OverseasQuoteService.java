package com.inbeom.apiserver.service;

import com.inbeom.apiserver.client.KisApiClient;
import com.inbeom.apiserver.dto.overseas.OverseasPriceResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.HashMap;
import java.util.Map;

/**
 * 해외주식(미국) 현재가 조회 서비스.
 *
 * <p>해외 시세(현재가상세 HHDFS76200200 / 현재가 HHDFS00000300)는 모의(openapivts) 도메인에서
 * 제공되지 않으므로, 매매/잔고 흐름과 분리된 실전 시세 도메인 + 실전 quote 자격증명
 * ({@link KisQuoteService}, 설정 kis.quote-*)으로 호출한다. DB 의 모의 키는 이 경로에서 쓰지 않는다.
 *
 * <p>시세 미연동(quote 키 미설정)·해외시세 권한없음·rt_cd != 0·예외 시 절대 예외를 전파하지 않고
 * 가격 필드는 null, {@code notice} 에 안내 메시지를 담아 graceful degrade 한다.
 * ({@link KisQuoteClient} 패턴 미러)
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OverseasQuoteService {

    private final KisQuoteService kisQuoteService;
    private final KisApiClient kisApiClient;

    /**
     * 해외 시세 미연동 시 UI 안내용 메시지.
     */
    public static final String NOTICE_OVERSEAS_QUOTE =
            "해외 시세가 연동되지 않았습니다 (실전 KIS 시세 키 필요)";

    /**
     * 해외 시세 조회 실패 시 UI 안내용 메시지.
     */
    public static final String NOTICE_OVERSEAS_QUOTE_FAILED =
            "해외 시세를 불러오지 못했습니다";

    private static final String PRICE_DETAIL_ENDPOINT = "/uapi/overseas-price/v1/quotations/price-detail";
    private static final String PRICE_DETAIL_TR_ID = "HHDFS76200200";

    /**
     * 해외주식 현재가상세 조회 (HHDFS76200200). 실전 시세 도메인 + 실전 quote 자격증명 사용.
     *
     * @param symbol   종목코드 (예: AAPL)
     * @param exchange 잔고/매매용 거래소코드(NASD/NYSE/AMEX). null/blank 또는 미지원 코드면 NASD 로 처리.
     * @return 가격이 채워진 응답, 또는 미연동/실패 시 가격 null + notice 응답 (절대 예외 전파하지 않음)
     */
    @SuppressWarnings("unchecked")
    public OverseasPriceResponse getPrice(String symbol, String exchange) {
        OverseasExchange ex = OverseasExchange.fromCode(exchange);

        if (!kisQuoteService.isQuoteEnabled()) {
            log.warn("KIS quote credentials not configured; overseas price unavailable for symbol={}", symbol);
            return degraded(symbol, ex, NOTICE_OVERSEAS_QUOTE);
        }

        String token = kisQuoteService.getQuoteAccessToken();
        if (token == null) {
            log.warn("KIS quote token unavailable; overseas price unavailable for symbol={}", symbol);
            return degraded(symbol, ex, NOTICE_OVERSEAS_QUOTE);
        }

        try {
            Map<String, String> params = new HashMap<>();
            params.put("AUTH", "");
            params.put("EXCD", ex.quoteCode());
            params.put("SYMB", symbol);

            ResponseEntity<Map> response = kisApiClient.get(
                    kisQuoteService.getQuoteBaseUrl(),
                    PRICE_DETAIL_ENDPOINT,
                    PRICE_DETAIL_TR_ID,
                    token,
                    kisQuoteService.getQuoteAppKey(),
                    kisQuoteService.getQuoteAppSecret(),
                    params,
                    Map.class
            );

            Map<String, Object> body = response.getBody();
            if (!isRtOk(body)) {
                log.warn("KIS overseas price-detail rt_cd!=0 for symbol={} excd={}: {}",
                        symbol, ex.quoteCode(), body != null ? body.get("msg1") : "null body");
                return degraded(symbol, ex, NOTICE_OVERSEAS_QUOTE_FAILED);
            }

            Object output = body.get("output");
            if (!(output instanceof Map)) {
                log.warn("KIS overseas price-detail missing output for symbol={}", symbol);
                return degraded(symbol, ex, NOTICE_OVERSEAS_QUOTE_FAILED);
            }
            Map<String, Object> out = (Map<String, Object>) output;

            BigDecimal last = parseBigDecimal(asString(out.get("last")));
            // last 가 비어있으면 사실상 데이터가 없는 것으로 보고 degrade 한다.
            if (last == null) {
                log.warn("KIS overseas price-detail empty last for symbol={}", symbol);
                return degraded(symbol, ex, NOTICE_OVERSEAS_QUOTE_FAILED);
            }

            String currency = asString(out.get("curr"));
            BigDecimal base = parseBigDecimal(asString(out.get("base")));
            BigDecimal diff = parseBigDecimal(asString(out.get("diff")));
            BigDecimal rate = parseBigDecimal(asString(out.get("rate")));
            // KIS price-detail 응답이 diff/rate 를 비워 보내는 경우, last/base 로 직접 도출한다.
            if (base != null && base.signum() != 0) {
                if (diff == null) {
                    diff = last.subtract(base);
                }
                if (rate == null) {
                    rate = last.subtract(base)
                            .multiply(BigDecimal.valueOf(100))
                            .divide(base, 2, java.math.RoundingMode.HALF_UP);
                }
            }
            return OverseasPriceResponse.builder()
                    .symbol(symbol)
                    .exchange(ex.balanceCode())
                    .currency(currency != null ? currency : ex.currency())
                    .last(last)
                    .base(base)
                    .diff(diff)
                    .rate(rate)
                    .notice(null)
                    .build();
        } catch (Exception e) {
            log.warn("KIS overseas price-detail call failed for symbol={}: {}", symbol, e.getMessage());
            return degraded(symbol, ex, NOTICE_OVERSEAS_QUOTE_FAILED);
        }
    }

    private OverseasPriceResponse degraded(String symbol, OverseasExchange ex, String notice) {
        return OverseasPriceResponse.builder()
                .symbol(symbol)
                .exchange(ex.balanceCode())
                .currency(ex.currency())
                .last(null)
                .base(null)
                .diff(null)
                .rate(null)
                .notice(notice)
                .build();
    }

    private boolean isRtOk(Map<String, Object> body) {
        return body != null && "0".equals(String.valueOf(body.get("rt_cd")));
    }

    /**
     * KIS output 값(Object)을 trim 된 String 으로 변환. null/공백이면 null.
     */
    private String asString(Object value) {
        if (value == null) {
            return null;
        }
        String s = String.valueOf(value).trim();
        return s.isEmpty() ? null : s;
    }

    /**
     * 콤마 제거 후 BigDecimal 파싱. null/공백/파싱불가 시 null (가격 미존재로 본다).
     */
    private BigDecimal parseBigDecimal(String value) {
        if (value == null) {
            return null;
        }
        try {
            return new BigDecimal(value.replace(",", ""));
        } catch (NumberFormatException e) {
            log.warn("Failed to parse overseas price BigDecimal: {}", value);
            return null;
        }
    }
}
