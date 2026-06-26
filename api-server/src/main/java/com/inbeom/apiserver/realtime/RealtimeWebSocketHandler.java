package com.inbeom.apiserver.realtime;

import com.inbeom.apiserver.service.KisQuoteService;
import com.inbeom.apiserver.service.OverseasExchange;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/**
 * 브라우저 ↔ 서버 실시간 핸들러 ({@code /ws/realtime}).
 *
 * <p>inbound 메시지(JSON): {@code {"action":"subscribe|unsubscribe","market":"KR|US",
 * "symbol":"005930|AAPL","type":"orderbook|tick","exchange":"NAS|NYS|AMS"}}.
 * → {@link RealtimeTr} 해석 후 {@link SubscriptionManager} subscribe/unsubscribe.
 *
 * <p>연결 직후, 시세 비활성(quote disabled)이면 즉시 {@code {type:status,state:disabled,notice}} 를
 * 보내 프론트가 REST 스냅샷을 유지하도록 한다(graceful degrade). 연결 종료 시 세션의 모든 구독 해제.
 */
@Slf4j
@RequiredArgsConstructor
public class RealtimeWebSocketHandler extends TextWebSocketHandler {

    /** 시세 미연동 안내 (KisQuoteClient.NOTICE_KIS_QUOTE 와 동일 문구). */
    public static final String NOTICE_QUOTE_DISABLED =
            "실시간 시세가 연동되지 않았습니다 (실전 KIS 키 필요)";

    private final SubscriptionManager subscriptionManager;
    private final KisQuoteService kisQuoteService;
    private final ObjectMapper objectMapper;

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        log.debug("[realtime] client connected: session={}", session.getId());
        if (!kisQuoteService.isQuoteEnabled()) {
            // 상향 시세 비활성 → 브라우저는 기존 REST 스냅샷 유지.
            subscriptionManager.sendStatus(session, "disabled", NOTICE_QUOTE_DISABLED);
        } else {
            subscriptionManager.sendStatus(session, "open", null);
        }
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        String payload = message.getPayload();
        if (payload == null || payload.isBlank()) {
            return;
        }
        try {
            JsonNode node = objectMapper.readTree(payload);
            String action = text(node, "action");
            String market = text(node, "market");
            String symbol = text(node, "symbol");
            String type = text(node, "type");
            String exchange = text(node, "exchange");

            if (action == null || symbol == null || symbol.isBlank()) {
                subscriptionManager.sendStatus(session, "error", "action/symbol 누락");
                return;
            }

            RealtimeTr tr = RealtimeTr.resolve(market, type);
            if (tr == null) {
                subscriptionManager.sendStatus(session, "error",
                        "지원하지 않는 market/type: " + market + "/" + type);
                return;
            }

            SubKey key = toSubKey(tr, symbol, exchange);

            switch (action.trim().toLowerCase()) {
                case "subscribe" -> {
                    boolean ok = subscriptionManager.subscribe(session, key);
                    if (ok) {
                        subscriptionManager.sendStatus(session, "subscribed", null);
                    }
                }
                case "unsubscribe" -> {
                    subscriptionManager.unsubscribe(session, key);
                    subscriptionManager.sendStatus(session, "unsubscribed", null);
                }
                default -> subscriptionManager.sendStatus(session, "error",
                        "알 수 없는 action: " + action);
            }
        } catch (Exception e) {
            log.debug("[realtime] inbound message error: {}", e.getMessage());
            subscriptionManager.sendStatus(session, "error", "잘못된 메시지 형식");
        }
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) {
        log.debug("[realtime] client transport error session={}: {}", session.getId(), exception.getMessage());
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        subscriptionManager.removeSession(session);
        log.debug("[realtime] client disconnected: session={} status={}", session.getId(), status.getCode());
    }

    /**
     * (TR, symbol, exchange) → SubKey. 국내는 tr_key=symbol, 미국은 {@link OverseasTrKey} 포맷.
     */
    private SubKey toSubKey(RealtimeTr tr, String symbol, String exchange) {
        String sym = symbol.trim().toUpperCase();
        if (tr.market() == RealtimeTr.Market.US) {
            OverseasExchange ex = OverseasExchange.fromCode(exchange);
            String trKey = OverseasTrKey.build(ex, sym);
            return new SubKey(tr, sym, trKey);
        }
        // 국내: 종목코드 원본(대문자 변환 무의미하지만 일관성 유지)을 tr_key 로.
        return new SubKey(tr, symbol.trim(), symbol.trim());
    }

    private String text(JsonNode node, String field) {
        JsonNode v = node.get(field);
        return (v == null || v.isNull()) ? null : v.asString();
    }
}
