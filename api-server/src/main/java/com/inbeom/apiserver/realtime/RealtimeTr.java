package com.inbeom.apiserver.realtime;

/**
 * Phase 1 실시간 TR 정의 (호가 + 체결가). 모의·실전 동일한 TR_ID 를 쓴다.
 *
 * <p>출처: KIS Developers 실시간시세(WebSocket) 명세.
 * <ul>
 *   <li>국내 호가 10단계: H0STASP0</li>
 *   <li>국내 체결가:      H0STCNT0</li>
 *   <li>미국 호가(1단계): HDFSASP0</li>
 *   <li>미국 체결가:      HDFSCNT0</li>
 * </ul>
 * 체결통보(H0STCNI0/H0GSCNI0, 사용자키 + AES 암호 프레임)는 Phase 2 범위로 제외한다.
 */
public enum RealtimeTr {

    /** 국내 호가 10단계. */
    KR_ASKING("H0STASP0", Market.KR, Kind.ORDERBOOK),
    /** 국내 체결가. */
    KR_TICK("H0STCNT0", Market.KR, Kind.TICK),
    /** 미국 호가(1단계). */
    US_ASKING("HDFSASP0", Market.US, Kind.ORDERBOOK),
    /** 미국 체결가. */
    US_TICK("HDFSCNT0", Market.US, Kind.TICK);

    /** 구독/해제 프레임의 tr_type: 1 = 등록, 2 = 해제. */
    public static final String TR_TYPE_REGISTER = "1";
    public static final String TR_TYPE_UNREGISTER = "2";

    public enum Market { KR, US }

    public enum Kind { ORDERBOOK, TICK }

    private final String trId;
    private final Market market;
    private final Kind kind;

    RealtimeTr(String trId, Market market, Kind kind) {
        this.trId = trId;
        this.market = market;
        this.kind = kind;
    }

    public String trId() {
        return trId;
    }

    public Market market() {
        return market;
    }

    public Kind kind() {
        return kind;
    }

    /**
     * 브라우저 요청(market + type)을 TR 로 해석한다.
     *
     * @param market "KR" | "US" (대소문자 무시)
     * @param type   "orderbook" | "tick" (대소문자 무시)
     * @return 매칭 TR, 알 수 없으면 null
     */
    public static RealtimeTr resolve(String market, String type) {
        if (market == null || type == null) {
            return null;
        }
        Market m;
        try {
            m = Market.valueOf(market.trim().toUpperCase());
        } catch (IllegalArgumentException e) {
            return null;
        }
        Kind k = switch (type.trim().toLowerCase()) {
            case "orderbook", "asking", "quote" -> Kind.ORDERBOOK;
            case "tick", "price", "ccnl" -> Kind.TICK;
            default -> null;
        };
        if (k == null) {
            return null;
        }
        for (RealtimeTr tr : values()) {
            if (tr.market == m && tr.kind == k) {
                return tr;
            }
        }
        return null;
    }

    /**
     * 상향 프레임의 tr_id 로부터 TR 을 역해석한다 (parser 의 fan-out 라우팅용).
     */
    public static RealtimeTr fromTrId(String trId) {
        if (trId == null) {
            return null;
        }
        for (RealtimeTr tr : values()) {
            if (tr.trId.equals(trId)) {
                return tr;
            }
        }
        return null;
    }
}
