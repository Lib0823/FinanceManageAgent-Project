/**
 * Realtime WebSocket service (Phase 1: 실시간 호가 + 체결가)
 *
 * 네이티브 WebSocket 싱글톤. 브라우저는 KIS에 직접 붙지 못하므로 Spring 브리지
 * `/ws/realtime`에 JWT 핸드셰이크로 연결하고, 서버가 단일 상향 KIS 연결을
 * 심볼 ref-count로 멀티플렉싱한다. (신규 의존성 0 — 네이티브 WebSocket 사용)
 *
 * 프로토콜 (서버 RealtimeWebSocketHandler와 합의):
 *  - 구독:  client → server  {action:'subscribe',   market, symbol, type, exchange}
 *  - 해제:  client → server  {action:'unsubscribe', market, symbol, type, exchange}
 *  - 데이터: server → client  {type:'quote'|'tick', market, symbol, ...}
 *  - 상태:  server → client  {type:'status', state:'disabled'|'reconnecting'|..., notice}
 *
 *  - market : 'KR' | 'US'
 *  - type   : 'orderbook' | 'tick'
 *  - exchange : (US 전용) OverseasExchange enum 값. KR이면 무시/생략.
 *
 * Graceful degrade: 연결 실패/서버 disabled 상태에서도 절대 throw 하지 않는다.
 * 구독자 콜백은 데이터 프레임만, 상태 변화는 onStatus 리스너로 전달한다.
 */

const RECONNECT_BASE_MS = 1000
const RECONNECT_MAX_MS = 30000

/**
 * 연결 상태 (store와 동일 enum)
 * connecting | open | reconnecting | disabled | closed
 */
function deriveWsUrl() {
  const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:7070/api'
  // http(s)://host:port/api → ws(s)://host:port/ws/realtime
  // baseURL에서 컨텍스트 경로(/api 등)는 떼고 호스트만 사용한다.
  let origin
  try {
    const u = new URL(base, window.location.origin)
    origin = `${u.protocol}//${u.host}`
  } catch {
    origin = base.replace(/\/api\/?$/, '')
  }
  const wsOrigin = origin.replace(/^http/, 'ws')
  return `${wsOrigin}/ws/realtime`
}

/** 구독 dedupe 키. (서버 SubKey와 무관 — 클라이언트 측 콜백 라우팅용) */
function subKey(market, symbol, type) {
  return `${market}:${symbol}:${type}`
}

/** 메시지 라우팅 키. 서버가 status 프레임에는 symbol을 안 줄 수 있으므로 분리. */
function routeKey(market, symbol, type) {
  return `${market}:${symbol}:${type}`
}

class RealtimeClient {
  constructor() {
    this.ws = null
    this.url = null
    this.state = 'closed'

    // subKey → { market, symbol, type, exchange, refCount, callbacks:Set<fn> }
    this.subscriptions = new Map()
    // 상태 변화 리스너 Set<fn(state, notice)>
    this.statusListeners = new Set()

    this.reconnectAttempts = 0
    this.reconnectTimer = null
    this.intentionalClose = false
  }

  /** 현재 토큰 (localStorage accessToken). store와 동일 소스. */
  _token() {
    return localStorage.getItem('accessToken') || ''
  }

  _setState(state, notice) {
    this.state = state
    for (const fn of this.statusListeners) {
      try {
        fn(state, notice)
      } catch (e) {
        console.error('[realtime] status listener error:', e)
      }
    }
  }

  /** 상태 변화 구독. 해제 함수 반환. */
  onStatus(fn) {
    this.statusListeners.add(fn)
    // 현재 상태를 즉시 한 번 통지
    try {
      fn(this.state)
    } catch (e) {
      console.error('[realtime] status listener error:', e)
    }
    return () => this.statusListeners.delete(fn)
  }

  /** 연결 (멱등). 토큰 없으면 연결 시도하지 않고 disabled 처리. */
  connect() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    const token = this._token()
    if (!token) {
      // 인증 토큰이 없으면 브리지에 붙을 수 없다 → degrade.
      this._setState('disabled', '인증 토큰이 없어 실시간 연결을 사용할 수 없습니다.')
      return
    }

    this.intentionalClose = false
    this.url = deriveWsUrl()

    let socket
    try {
      socket = new WebSocket(`${this.url}?token=${encodeURIComponent(token)}`)
    } catch (e) {
      // 생성 자체 실패 → 절대 throw 하지 않고 재연결 스케줄.
      console.error('[realtime] WebSocket 생성 실패:', e)
      this._scheduleReconnect()
      return
    }

    this.ws = socket
    this._setState(this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting')

    socket.onopen = () => {
      this.reconnectAttempts = 0
      this._setState('open')
      // 재연결 시 기존 모든 구독 재등록.
      this._resubscribeAll()
    }

    socket.onmessage = (event) => {
      this._handleMessage(event.data)
    }

    socket.onerror = (event) => {
      // onclose가 뒤따라 오므로 여기서는 로깅만.
      console.error('[realtime] WebSocket error:', event)
    }

    socket.onclose = () => {
      this.ws = null
      if (this.intentionalClose) {
        this._setState('closed')
        return
      }
      this._scheduleReconnect()
    }
  }

  _scheduleReconnect() {
    if (this.intentionalClose) return
    if (this.reconnectTimer) return
    // 재등록할 구독이 하나도 없으면 굳이 재연결하지 않는다.
    if (this.subscriptions.size === 0) {
      this._setState('closed')
      return
    }

    const attempt = this.reconnectAttempts
    const backoff = Math.min(RECONNECT_BASE_MS * 2 ** attempt, RECONNECT_MAX_MS)
    const jitter = Math.floor(Math.random() * 1000)
    const delay = backoff + jitter

    this._setState('reconnecting')
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.reconnectAttempts += 1
      this.connect()
    }, delay)
  }

  _handleMessage(raw) {
    let msg
    try {
      msg = typeof raw === 'string' ? JSON.parse(raw) : raw
    } catch {
      // 프레임 파싱 실패는 무시 (브리지는 JSON만 보냄).
      return
    }
    if (!msg || typeof msg !== 'object') return

    if (msg.type === 'status') {
      // 서버 측 degrade/reconnect 통지.
      this._setState(msg.state || this.state, msg.notice)
      return
    }

    // 데이터 프레임 라우팅: type(quote→orderbook / tick) + symbol.
    // 서버 quote 프레임 type은 'quote'지만 클라이언트 구독 type은 'orderbook'.
    const subType = msg.type === 'quote' ? 'orderbook' : msg.type
    if (!subType || msg.symbol == null) return

    const market = msg.market || 'KR'
    const key = routeKey(market, msg.symbol, subType)
    const sub = this.subscriptions.get(key)
    if (!sub) return

    for (const cb of sub.callbacks) {
      try {
        cb(msg)
      } catch (e) {
        console.error('[realtime] subscriber callback error:', e)
      }
    }
  }

  /**
   * 구독. dedupe + refCount.
   * @param {string} market 'KR' | 'US'
   * @param {string} symbol 종목 코드 / 심볼
   * @param {string} type   'orderbook' | 'tick'
   * @param {string|null} exchange US 전용 거래소 코드 (KR이면 null)
   * @param {function} cb    데이터 프레임 콜백 (msg) => void
   * @returns {function} 해제 함수
   */
  subscribe(market, symbol, type, exchange, cb) {
    const key = subKey(market, symbol, type)
    let sub = this.subscriptions.get(key)

    if (!sub) {
      sub = {
        market,
        symbol,
        type,
        exchange: exchange || null,
        refCount: 0,
        callbacks: new Set()
      }
      this.subscriptions.set(key, sub)
    }

    if (typeof cb === 'function') {
      sub.callbacks.add(cb)
    }
    sub.refCount += 1

    // 첫 ref면 서버에 등록 프레임 전송 (이미 연결돼 있을 때).
    if (sub.refCount === 1) {
      this._sendSubscribe(sub)
    }

    // 연결이 없으면 시작.
    this.connect()

    return () => this.unsubscribe(market, symbol, type, cb)
  }

  /** 구독 해제. refCount 0 도달 시 서버에 해제 프레임 전송. */
  unsubscribe(market, symbol, type, cb) {
    const key = subKey(market, symbol, type)
    const sub = this.subscriptions.get(key)
    if (!sub) return

    if (typeof cb === 'function') {
      sub.callbacks.delete(cb)
    }
    sub.refCount = Math.max(0, sub.refCount - 1)

    if (sub.refCount === 0) {
      this._sendUnsubscribe(sub)
      this.subscriptions.delete(key)
    }
  }

  _sendSubscribe(sub) {
    this._send({
      action: 'subscribe',
      market: sub.market,
      symbol: sub.symbol,
      type: sub.type,
      exchange: sub.exchange
    })
  }

  _sendUnsubscribe(sub) {
    this._send({
      action: 'unsubscribe',
      market: sub.market,
      symbol: sub.symbol,
      type: sub.type,
      exchange: sub.exchange
    })
  }

  _send(obj) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      // 아직 연결 전이면 onopen의 _resubscribeAll에서 일괄 전송됨.
      return
    }
    try {
      this.ws.send(JSON.stringify(obj))
    } catch (e) {
      console.error('[realtime] send 실패:', e)
    }
  }

  _resubscribeAll() {
    for (const sub of this.subscriptions.values()) {
      if (sub.refCount > 0) {
        this._sendSubscribe(sub)
      }
    }
  }

  /** 전체 종료 (의도적). 모든 구독/타이머 정리. */
  disconnect() {
    this.intentionalClose = true
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.subscriptions.clear()
    if (this.ws) {
      try {
        this.ws.close()
      } catch {
        // ignore
      }
      this.ws = null
    }
    this._setState('closed')
  }
}

// 싱글톤
const realtimeClient = new RealtimeClient()

export default realtimeClient
