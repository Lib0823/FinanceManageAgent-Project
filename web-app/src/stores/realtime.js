import { defineStore } from 'pinia'
import { ref } from 'vue'
import realtimeClient from '@/services/realtime'

/**
 * Realtime store (Phase 1: 실시간 호가 + 체결가)
 *
 * 뷰는 이 store를 통해서만 구독한다 (services/realtime.js를 직접 만지지 않음).
 * store는 심볼별 최신 quote(호가) / tick(체결가)을 보관하고, 연결 상태를
 * connectionState로 노출한다. 뷰는 store의 ref를 watch 하거나 구독 콜백을
 * 받아 자체 ref를 갱신한다.
 *
 * Graceful degrade: connectionState가 'disabled'/'reconnecting'/'closed'일 때
 * 뷰는 기존 REST 스냅샷을 유지한다 (store는 강제로 데이터를 지우지 않음).
 *
 * REST DTO 호환 (프론트가 동일 렌더 경로 재사용):
 *  - quote.asks / quote.bids : [{ price, quantity }]
 *  - tick.currentPrice / changeAmount / changeRate / volume / accVolume
 */
export const useRealtimeStore = defineStore('realtime', () => {
  // connecting | open | reconnecting | disabled | closed
  const connectionState = ref('closed')
  // 서버/클라이언트가 전달한 degrade 안내 문구
  const notice = ref(null)

  // 심볼별 최신 데이터. 키 = `${market}:${symbol}`
  // quotes: { asks, bids, ts }
  const quotes = ref({})
  // ticks: { currentPrice, changeAmount, changeRate, volume, accVolume, ts }
  const ticks = ref({})

  // 상태 리스너 등록 (1회). client 싱글톤이라 store도 싱글톤이지만 방어.
  let statusUnsub = null
  function ensureStatusListener() {
    if (statusUnsub) return
    statusUnsub = realtimeClient.onStatus((state, msg) => {
      connectionState.value = state
      if (msg != null) {
        notice.value = msg
      } else if (state === 'open') {
        notice.value = null
      }
    })
  }

  function dataKey(market, symbol) {
    return `${market}:${symbol}`
  }

  /**
   * 호가 구독. 뷰는 반환된 해제 함수를 onBeforeUnmount/watch에서 호출한다.
   * @param {string} market 'KR' | 'US'
   * @param {string} symbol
   * @param {string|null} exchange US 전용 거래소 코드
   * @param {function} [cb] (quote) => void 선택 콜백 (store 갱신과 별개로 뷰 직접 처리용)
   * @returns {function} 해제 함수
   */
  function subscribeOrderbook(market, symbol, exchange, cb) {
    ensureStatusListener()
    const key = dataKey(market, symbol)
    const handler = (msg) => {
      quotes.value = {
        ...quotes.value,
        [key]: {
          asks: Array.isArray(msg.asks) ? msg.asks : [],
          bids: Array.isArray(msg.bids) ? msg.bids : [],
          ts: msg.ts ?? Date.now()
        }
      }
      if (typeof cb === 'function') cb(msg)
    }
    return realtimeClient.subscribe(market, symbol, 'orderbook', exchange || null, handler)
  }

  /**
   * 체결가(tick) 구독.
   * @returns {function} 해제 함수
   */
  function subscribeTick(market, symbol, exchange, cb) {
    ensureStatusListener()
    const key = dataKey(market, symbol)
    const handler = (msg) => {
      const prev = ticks.value[key] || {}
      ticks.value = {
        ...ticks.value,
        [key]: {
          currentPrice: msg.currentPrice ?? msg.price ?? prev.currentPrice ?? null,
          changeAmount: msg.changeAmount ?? prev.changeAmount ?? null,
          changeRate: msg.changeRate ?? prev.changeRate ?? null,
          volume: msg.volume ?? prev.volume ?? null,
          accVolume: msg.accVolume ?? prev.accVolume ?? null,
          ts: msg.ts ?? Date.now()
        }
      }
      if (typeof cb === 'function') cb(msg)
    }
    return realtimeClient.subscribe(market, symbol, 'tick', exchange || null, handler)
  }

  /** 심볼별 최신 호가 조회 (없으면 null). */
  function getQuote(market, symbol) {
    return quotes.value[dataKey(market, symbol)] || null
  }

  /** 심볼별 최신 체결가 조회 (없으면 null). */
  function getTick(market, symbol) {
    return ticks.value[dataKey(market, symbol)] || null
  }

  return {
    // State
    connectionState,
    notice,
    quotes,
    ticks,

    // Actions
    subscribeOrderbook,
    subscribeTick,

    // Getters
    getQuote,
    getTick
  }
})
