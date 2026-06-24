<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/common/AppHeader.vue'
import { stockApi, tradingApi } from '@/services/api'

const route = useRoute()
const router = useRouter()

const symbol = ref(route.params.symbol || '005930')  // Default to Samsung Electronics
const stockName = ref(route.query.name || '삼성전자')  // Stock name
const activeTab = ref('buy')
const loading = ref(false)
const errorMessage = ref('')

const orderForm = ref({
  type: 'market',
  time: '09:00 ~ 15:30',
  quantity: 1,
  maxQuantity: 100,
  price: 71500,
  maxPrice: 1000000
})

// 실시간 시세
const currentPrice = ref(null)
const changeRate = ref(null)
const changeAmount = ref(null)
const priceNotice = ref(null)

// 호가 (order book)
const orderbookAsks = ref([]) // 매도호가 (높은 가격), 위쪽
const orderbookBids = ref([]) // 매수호가, 아래쪽
const orderbookNotice = ref(null)

// 주문 가능 정보
const orderableNotice = ref(null)

const formatNumber = (num) => {
  return new Intl.NumberFormat('ko-KR').format(Math.round(Number(num) || 0))
}

// 총 금액: 가격 * 수량 (가격·수량 양쪽에 반응)
const totalAmount = computed(() => {
  const price = Number(orderForm.value.price) || 0
  const quantity = Number(orderForm.value.quantity) || 0
  return price * quantity
})

// 현재 일시 (ko-KR)
const currentDateTime = computed(() => {
  const now = new Date()
  const date = now.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  })
  const time = now.toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit'
  })
  return `${date} / ${time}`
})

// 호가창에 표시할 행 (매도 위, 매수 아래)
const orderbookRows = computed(() => {
  const asks = orderbookAsks.value.map((row) => ({ ...row, side: 'ask' }))
  const bids = orderbookBids.value.map((row) => ({ ...row, side: 'bid' }))
  return [...asks, ...bids]
})

// currentPrice 에 가장 가까운 행 highlight 판단
const nearestPrice = computed(() => {
  const base = Number(currentPrice.value)
  if (!base) return null
  let best = null
  let bestDiff = Infinity
  for (const row of orderbookRows.value) {
    const diff = Math.abs(Number(row.price) - base)
    if (diff < bestDiff) {
      bestDiff = diff
      best = row.price
    }
  }
  return best
})

const selectPrice = (price) => {
  if (!price) return
  orderForm.value.price = price
}

// 호가 데이터 없을 때 currentPrice 기준 ±5틱 사다리 생성 (fallback)
const buildFallbackLadder = (base) => {
  const center = Number(base)
  if (!center) {
    orderbookAsks.value = []
    orderbookBids.value = []
    return
  }
  const tick = estimateTick(center)
  const asks = []
  const bids = []
  for (let i = 5; i >= 1; i--) {
    asks.push({ price: center + tick * i, quantity: null })
  }
  for (let i = 1; i <= 5; i++) {
    bids.push({ price: Math.max(center - tick * i, tick), quantity: null })
  }
  orderbookAsks.value = asks
  orderbookBids.value = bids
}

// KRX 호가 단위 근사
const estimateTick = (price) => {
  if (price < 2000) return 1
  if (price < 5000) return 5
  if (price < 20000) return 10
  if (price < 50000) return 50
  if (price < 200000) return 100
  if (price < 500000) return 500
  return 1000
}

const loadPrice = async () => {
  try {
    const response = await stockApi.getPrice(symbol.value)
    const data = response?.data || {}
    if (data.notice) {
      priceNotice.value = data.notice
    } else {
      priceNotice.value = null
    }
    if (data.currentPrice != null) {
      currentPrice.value = Number(data.currentPrice)
      changeAmount.value = data.changeAmount != null ? Number(data.changeAmount) : null
      changeRate.value = data.changeRate != null ? Number(data.changeRate) : null
      // 실제 현재가를 주문 가격 기본값으로 (수동 변경 전)
      orderForm.value.price = Number(data.currentPrice)
    }
  } catch (error) {
    console.error('Failed to load price:', error)
    priceNotice.value = '시세 미연동'
  }
}

const loadOrderbook = async () => {
  try {
    const response = await stockApi.getOrderbook(symbol.value)
    const data = response?.data || {}
    const asks = Array.isArray(data.asks) ? data.asks.filter((r) => r && r.price) : []
    const bids = Array.isArray(data.bids) ? data.bids.filter((r) => r && r.price) : []

    if (data.notice || (asks.length === 0 && bids.length === 0)) {
      orderbookNotice.value = data.notice || '호가 미연동'
      buildFallbackLadder(currentPrice.value)
      return
    }

    orderbookNotice.value = null
    // asks: 매도호가 높은가격 순 (내림차순) → 위쪽
    orderbookAsks.value = [...asks].sort((a, b) => Number(b.price) - Number(a.price))
    // bids: 매수호가 높은가격 순 (내림차순) → 아래쪽 상단부터
    orderbookBids.value = [...bids].sort((a, b) => Number(b.price) - Number(a.price))
  } catch (error) {
    console.error('Failed to load orderbook:', error)
    orderbookNotice.value = '호가 미연동'
    buildFallbackLadder(currentPrice.value)
  }
}

const loadOrderable = async () => {
  try {
    const price = Number(orderForm.value.price) || Number(currentPrice.value) || 0
    const response = await tradingApi.getOrderable(symbol.value, price)
    const data = response?.data || {}
    if (data.notice) {
      orderableNotice.value = data.notice
      return
    }
    orderableNotice.value = null
    if (data.maxBuyQuantity != null) {
      orderForm.value.maxQuantity = Number(data.maxBuyQuantity)
    }
    if (data.orderableCash != null) {
      orderForm.value.maxPrice = Number(data.orderableCash)
    }
  } catch (error) {
    console.error('Failed to load orderable:', error)
    orderableNotice.value = '주문가능 미연동'
  }
}

// "최대" 선택 시 수량을 주문가능 최대로
const setMaxQuantity = (event) => {
  if (event.target.checked) {
    orderForm.value.quantity = orderForm.value.maxQuantity
  }
}

const loadMarketData = async () => {
  await loadPrice()
  await Promise.all([loadOrderbook(), loadOrderable()])
}

const placeOrder = async () => {
  if (loading.value) return

  try {
    loading.value = true
    errorMessage.value = ''

    const orderData = {
      stockCode: symbol.value,
      stockName: stockName.value,
      quantity: parseInt(orderForm.value.quantity),
      price: orderForm.value.price
    }

    if (activeTab.value === 'buy') {
      await tradingApi.buy(orderData)
    } else {
      await tradingApi.sell(orderData)
    }

    // Success
    alert(`${activeTab.value === 'buy' ? '매수' : '매도'} 주문이 완료되었습니다.`)

    // Redirect to transactions page
    router.push('/transactions')
  } catch (error) {
    console.error('Order failed:', error)
    errorMessage.value = error.response?.data?.message || '주문 실행에 실패했습니다'
    alert(errorMessage.value)
  } finally {
    loading.value = false
  }
}

// 미체결 주문 (실데이터: /trading/pending-orders → daily-ccld 필터)
const pendingOrders = ref([])

const loadPendingOrders = async () => {
  try {
    const response = await tradingApi.getPendingOrders()
    const list = Array.isArray(response?.data) ? response.data : []
    pendingOrders.value = list.map((order) => ({
      type: (order.orderType || '').toLowerCase() === 'sell' ? 'sell' : 'buy',
      name: order.stockName || order.stockCode || '',
      symbol: order.stockCode || '',
      price: Number(order.orderPrice) || 0,
      currency: '원'
    }))
  } catch (error) {
    console.error('Failed to load pending orders:', error)
    pendingOrders.value = []
  }
}

onMounted(() => {
  loadPendingOrders()
  loadMarketData()
})

// 종목 변경 시 시세/호가/주문가능 재조회
watch(symbol, () => {
  loadMarketData()
})

// 가격 변경 시 주문가능 수량/금액 갱신
let orderablePriceTimer = null
watch(
  () => orderForm.value.price,
  () => {
    if (orderablePriceTimer) clearTimeout(orderablePriceTimer)
    orderablePriceTimer = setTimeout(() => {
      loadOrderable()
    }, 300)
  }
)

// 예약 주문은 미지원 (추후 지원) → 항상 빈 배열
const filteredOrders = computed(() => ({
  pending: pendingOrders.value,
  reserved: []
}))
</script>

<template>
  <div class="trading-screen">
    <AppHeader title="실시간 매매" showBack />

    <div class="content">
      <!-- Stock Header -->
      <div class="stock-header">
        <h2 class="stock-name">{{ stockName }}({{ symbol }})</h2>
        <div v-if="currentPrice != null" class="stock-price-row">
          <span class="stock-current-price">{{ formatNumber(currentPrice) }}원</span>
          <span
            v-if="changeRate != null"
            :class="['stock-change', changeRate >= 0 ? 'up' : 'down']"
          >
            {{ changeRate >= 0 ? '▲' : '▼' }}
            <template v-if="changeAmount != null">{{ formatNumber(Math.abs(changeAmount)) }}</template>
            ({{ changeRate >= 0 ? '+' : '' }}{{ changeRate.toFixed(2) }}%)
          </span>
        </div>
        <p v-if="priceNotice" class="notice-text">{{ priceNotice }}</p>
        <div class="stock-tags">
          <span class="tag">국내</span>
          <span class="tag">KOSPI</span>
        </div>
      </div>

      <!-- Orders Section -->
      <div class="orders-section">
        <div class="order-group" v-if="filteredOrders.pending.length > 0">
          <h3 class="order-title">미체결</h3>
          <div class="order-list">
            <div v-for="(order, idx) in filteredOrders.pending" :key="idx" class="order-item">
              <span :class="['order-type', order.type]">{{ order.type === 'sell' ? '매도' : '매수' }}</span>
              <span class="order-symbol">{{ order.name }}({{ order.symbol }})</span>
              <span class="order-price">{{ formatNumber(order.price) }}{{ order.currency }}</span>
            </div>
          </div>
        </div>

        <div class="order-group">
          <h3 class="order-title">예약 주문 (추후 지원)</h3>
          <div class="no-orders">
            <p>예약 주문 기능은 추후 지원될 예정입니다.</p>
          </div>
        </div>

        <div v-if="filteredOrders.pending.length === 0" class="no-orders">
          <p>현재 미체결 주문이 없습니다.</p>
        </div>
      </div>

      <!-- Trading Form -->
      <div class="trading-form">
        <!-- Price List (Order Book) -->
        <div class="price-list">
          <div
            v-for="(row, idx) in orderbookRows"
            :key="`${row.side}-${row.price}-${idx}`"
            :class="[
              'price-item',
              row.side,
              { highlight: nearestPrice != null && row.price === nearestPrice }
            ]"
            @click="selectPrice(row.price)"
          >
            <span class="price-item-price">{{ formatNumber(row.price) }}</span>
            <span v-if="row.quantity != null" class="price-item-qty">{{ formatNumber(row.quantity) }}</span>
          </div>
          <div v-if="orderbookRows.length === 0" class="price-item empty">호가 없음</div>
          <p v-if="orderbookNotice" class="notice-text orderbook-notice">{{ orderbookNotice }}</p>
        </div>

        <!-- Order Form -->
        <div class="order-form">
          <!-- Buy/Sell Tabs -->
          <div class="form-tabs">
            <button
              :class="['form-tab', { active: activeTab === 'buy' }]"
              @click="activeTab = 'buy'"
            >
              매수
            </button>
            <button
              :class="['form-tab', { active: activeTab === 'sell' }]"
              @click="activeTab = 'sell'"
            >
              매도
            </button>
          </div>

          <!-- Form Fields -->
          <div class="form-fields">
            <div class="form-row">
              <span class="form-label">구분</span>
              <span class="form-value">정규장 (지정가)</span>
            </div>
            <div class="form-row">
              <span class="form-label">시간</span>
              <span class="form-value">{{ orderForm.time }}</span>
            </div>
            <div class="form-row">
              <span class="form-label">수량</span>
              <div class="form-input-group">
                <input type="text" v-model="orderForm.quantity" class="form-input" />
                <span class="form-hint">
                  주문 가능 {{ formatNumber(orderForm.maxQuantity) }}주
                </span>
                <label class="checkbox-small">
                  <input type="checkbox" @change="setMaxQuantity" /> 최대
                </label>
              </div>
            </div>
            <div class="form-row">
              <span class="form-label">가격</span>
              <div class="form-input-group">
                <input type="text" v-model="orderForm.price" class="form-input" />
                <span class="form-hint">주문 가능 {{ formatNumber(orderForm.maxPrice) }}원</span>
              </div>
            </div>
            <p v-if="orderableNotice" class="notice-text">{{ orderableNotice }}</p>
            <div class="form-row total">
              <span class="form-label">총 {{ activeTab === 'buy' ? '매수' : '매도' }} 금액</span>
              <span class="form-total">{{ formatNumber(totalAmount) }}원</span>
            </div>

            <!-- Date Time -->
            <div class="datetime-row">
              <span class="calendar-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
                  <path d="M16 2V6M8 2V6M3 10H21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </span>
              <span class="datetime-value">{{ currentDateTime }}</span>
            </div>
          </div>

          <!-- Submit Button -->
          <button
            :class="['submit-btn', activeTab]"
            @click="placeOrder"
          >
            {{ activeTab === 'buy' ? '매수' : '매도' }} 주문
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trading-screen {
  min-height: 100vh;
  background: var(--color-bg-primary);
}

.content {
  padding: 0 var(--spacing-lg) var(--spacing-lg);
}

.stock-header {
  margin-bottom: var(--spacing-lg);
}

.stock-name {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.stock-price-row {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.stock-current-price {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.stock-change {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
}

.stock-change.up {
  color: var(--color-stock-up);
}

.stock-change.down {
  color: var(--color-stock-down);
}

.notice-text {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-sm);
}

.orderbook-notice {
  text-align: center;
}

.stock-tags {
  display: flex;
  gap: var(--spacing-sm);
}

.tag {
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--color-bg-highlight);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  color: var(--color-primary);
}

.orders-section {
  margin-bottom: var(--spacing-lg);
}

.order-group {
  margin-bottom: var(--spacing-md);
}

.order-title {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-sm);
}

.order-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.order-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-sm);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

.order-type {
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.order-type.sell {
  background: var(--color-secondary);
  color: var(--color-text-inverse);
}

.order-type.buy {
  background: #F97316;
  color: var(--color-text-inverse);
}

.order-symbol {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.order-price {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.no-orders {
  padding: var(--spacing-lg);
  text-align: center;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.trading-form {
  display: flex;
  gap: var(--spacing-md);
}

.price-list {
  flex: 0 0 100px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.price-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  padding: var(--spacing-sm);
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
  cursor: pointer;
}

/* 매도호가 (asks) → 위쪽, 파란색 */
.price-item.ask {
  background: #DBEAFE;
  color: var(--color-stock-down);
}

/* 매수호가 (bids) → 아래쪽, 빨간색 */
.price-item.bid {
  background: #FEE2E2;
  color: var(--color-stock-up);
}

.price-item.empty {
  background: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
  cursor: default;
}

.price-item-price {
  font-size: var(--font-size-sm);
}

.price-item-qty {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.price-item.highlight {
  font-weight: var(--font-weight-bold);
  outline: 2px solid var(--color-primary);
  outline-offset: -2px;
}

.order-form {
  flex: 1;
}

.form-tabs {
  display: flex;
  margin-bottom: var(--spacing-md);
}

.form-tab {
  flex: 1;
  padding: var(--spacing-sm);
  border: none;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}

.form-tab.active {
  color: var(--color-text-inverse);
}

.form-tab:first-child.active {
  background: #F97316;
}

.form-tab:last-child.active {
  background: var(--color-secondary);
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.form-row {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-sm);
}

.form-row.total {
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border-light);
}

.form-label {
  width: 50px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.form-value {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.form-input-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.form-input {
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-sm);
}

.form-hint {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.checkbox-small {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.checkbox-small input {
  width: 14px;
  height: 14px;
}

.form-total {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-stock-up);
}

.datetime-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--color-bg-highlight);
  border-radius: var(--radius-md);
}

.calendar-icon {
  color: var(--color-text-secondary);
}

.datetime-value {
  font-size: var(--font-size-sm);
  color: var(--color-primary);
}

.submit-btn {
  width: 100%;
  padding: var(--spacing-md);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-inverse);
  cursor: pointer;
  margin-top: var(--spacing-md);
}

.submit-btn.buy {
  background: #F97316;
}

.submit-btn.sell {
  background: var(--color-secondary);
}
</style>
