<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/common/AppHeader.vue'
import InvestmentTabs from '@/components/common/InvestmentTabs.vue'
import { tradingApi } from '@/services/api'

const router = useRouter()

const tabs = ref({ main: 'stocks', sub: 'domestic' })
const loading = ref(false)
const errorMessage = ref('')

// 거래 내역 데이터 (API에서 가져옴)
const history = ref([])

// 미체결/예약 주문 데이터
const orders = ref({
  pending: [],
  reserved: []
})

// 요약 데이터 (템플릿 구조에 맞게 수정)
const summary = ref({
  buy: { amount: 0, name: '', symbol: '' },
  sell: { amount: 0, name: '', symbol: '' },
  other: { amount: 0, label: '배당금' }
})

// Load trade history
const loadHistory = async () => {
  try {
    loading.value = true
    errorMessage.value = ''
    const response = await tradingApi.getHistory()

    if (response.data) {
      // TradeHistory 엔티티를 UI 형식으로 변환
      history.value = response.data.map(trade => ({
        id: trade.id,
        symbol: trade.stockCode,
        name: trade.stockName,
        type: trade.orderType.toLowerCase(),  // BUY -> buy, SELL -> sell
        quantity: trade.quantity,
        price: trade.executedPrice || trade.orderPrice,
        amount: (trade.executedPrice || trade.orderPrice) * trade.quantity,
        date: new Date(trade.orderedAt).toLocaleDateString('ko-KR'),
        time: new Date(trade.orderedAt).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }),
        status: trade.orderStatus,  // PENDING, COMPLETED 등
        currency: '원'
      }))

      // 미체결/예약 주문 필터링
      orders.value.pending = history.value.filter(t => t.status === 'PENDING')
      orders.value.reserved = []  // 예약 주문은 별도 API 필요 시 추가

      // 요약 데이터 계산
      const buyTrades = history.value.filter(t => t.type === 'buy' && t.status === 'COMPLETED')
      const sellTrades = history.value.filter(t => t.type === 'sell' && t.status === 'COMPLETED')

      const totalBuy = buyTrades.reduce((sum, t) => sum + t.amount, 0)
      const totalSell = sellTrades.reduce((sum, t) => sum + t.amount, 0)

      // 가장 많이 매수한 종목
      const buyByStock = {}
      buyTrades.forEach(t => {
        if (!buyByStock[t.symbol]) {
          buyByStock[t.symbol] = { amount: 0, name: t.name, symbol: t.symbol }
        }
        buyByStock[t.symbol].amount += t.amount
      })
      const topBuy = Object.values(buyByStock).sort((a, b) => b.amount - a.amount)[0]

      // 가장 많이 매도한 종목
      const sellByStock = {}
      sellTrades.forEach(t => {
        if (!sellByStock[t.symbol]) {
          sellByStock[t.symbol] = { amount: 0, name: t.name, symbol: t.symbol }
        }
        sellByStock[t.symbol].amount += t.amount
      })
      const topSell = Object.values(sellByStock).sort((a, b) => b.amount - a.amount)[0]

      summary.value.buy = topBuy || { amount: 0, name: '-', symbol: '' }
      summary.value.sell = topSell || { amount: 0, name: '-', symbol: '' }
      summary.value.other = { amount: totalSell - totalBuy, label: '손익' }
    }
  } catch (error) {
    console.error('Failed to load trade history:', error)

    // API 키 에러 처리
    if (error.response?.status === 401 || error.response?.status === 403) {
      errorMessage.value = 'API 키를 확인해주세요'
    } else if (error.code === 'ECONNABORTED' || error.message?.includes('Network') || error.message?.includes('timeout')) {
      errorMessage.value = '네트워크 연결을 확인해주세요'
    } else if (error.response?.data?.message) {
      errorMessage.value = error.response.data.message
    } else {
      errorMessage.value = '거래 내역을 불러오는데 실패했습니다'
    }
  } finally {
    loading.value = false
  }
}

// 컴포넌트 마운트 시 데이터 로드
onMounted(() => {
  loadHistory()
})

const goToTrading = (order) => {
  router.push(`/trading/${order.symbol}`)
}

// 기간 선택 (달력 대신 버튼 방식)
const selectedPeriod = ref('1month')
const periodOptions = [
  { key: '1week', label: '1주일' },
  { key: '1month', label: '1개월' },
  { key: '3months', label: '3개월' },
  { key: '6months', label: '6개월' },
  { key: '1year', label: '1년' }
]

const dateRange = ref({
  start: '2024.08.19',
  end: '2024.11.09'
})

const formatDate = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}.${month}.${day}`
}

const selectPeriod = (key) => {
  selectedPeriod.value = key

  const today = new Date()
  const startDate = new Date()

  // 기간에 따라 시작 날짜 계산
  switch (key) {
    case '1week':
      startDate.setDate(today.getDate() - 7)
      break
    case '1month':
      startDate.setMonth(today.getMonth() - 1)
      break
    case '3months':
      startDate.setMonth(today.getMonth() - 3)
      break
    case '6months':
      startDate.setMonth(today.getMonth() - 6)
      break
    case '1year':
      startDate.setFullYear(today.getFullYear() - 1)
      break
  }

  dateRange.value = {
    start: formatDate(startDate),
    end: formatDate(today)
  }
}

const formatNumber = (num) => {
  return new Intl.NumberFormat('ko-KR').format(num)
}

const getTypeClass = (type) => {
  switch (type) {
    case 'buy': return 'buy'
    case 'sell': return 'sell'
    case 'dividend': return 'dividend'
    default: return ''
  }
}

const getTypeLabel = (type) => {
  switch (type) {
    case 'buy': return '매수'
    case 'sell': return '매도'
    case 'dividend': return '배당'
    default: return ''
  }
}
</script>

<template>
  <div class="transactions-screen">
    <AppHeader title="거래 내역" showIcon icon="news" />

    <div class="content">
      <!-- Tabs -->
      <InvestmentTabs v-model="tabs" />

      <!-- Loading State -->
      <div v-if="loading" class="state-container">
        <div class="spinner"></div>
        <p class="state-message">거래 내역을 불러오는 중...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="errorMessage" class="state-container error-state">
        <div class="error-icon">⚠️</div>
        <p class="error-message">{{ errorMessage }}</p>
        <div class="error-actions">
          <button @click="router.push('/profile')" class="action-button primary">
            내 정보로 이동
          </button>
          <button @click="loadHistory()" class="action-button secondary">
            다시 시도
          </button>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else-if="history.length === 0" class="state-container empty-state">
        <div class="empty-icon">📊</div>
        <p class="empty-message">거래 내역이 없습니다</p>
        <p class="empty-submessage">첫 거래를 시작해보세요</p>
      </div>

      <!-- Normal Content -->
      <template v-else>

      <!-- Pending/Reserved Orders Section -->
      <section class="pending-section">
        <h3 class="section-title">미체결 / 예약 주문</h3>
        <div class="order-list">
          <div
            v-for="(order, idx) in [...orders.pending.map(o => ({...o, label: '미체결'})), ...orders.reserved.map(o => ({...o, label: '예약'}))]"
            :key="'order-'+idx"
            class="order-item"
            @click="goToTrading(order)"
          >
            <span class="order-label">{{ order.label }}</span>
            <div class="order-info">
              <span :class="['order-type', order.type]">{{ getTypeLabel(order.type) }}</span>
              <span class="order-name">{{ order.name }}</span>
            </div>
            <span class="order-price">{{ formatNumber(order.price) }}{{ order.currency }}</span>
          </div>
        </div>
      </section>

      <!-- Period Transaction History Section -->
      <section class="period-section">
        <h3 class="section-title">기간 거래 내역</h3>

        <!-- Period Selection Buttons -->
        <div class="period-selector">
          <button
            v-for="option in periodOptions"
            :key="option.key"
            :class="['period-btn', { active: selectedPeriod === option.key }]"
            @click="selectPeriod(option.key)"
          >
            {{ option.label }}
          </button>
        </div>

        <div class="date-range">
          {{ dateRange.start }} - {{ dateRange.end }}
        </div>

        <!-- Summary -->
        <div class="summary-container">
          <div class="summary-card">
            <div class="summary-item">
              <span class="summary-type buy">매수</span>
              <span class="summary-amount">{{ formatNumber(summary.buy.amount) }}</span>
              <span class="summary-detail">{{ summary.buy.name }} ({{ summary.buy.symbol }})</span>
            </div>
            <div class="summary-item">
              <span class="summary-type sell">매도</span>
              <span class="summary-amount">{{ formatNumber(summary.sell.amount) }}</span>
              <span class="summary-detail">{{ summary.sell.name }} ({{ summary.sell.symbol }})</span>
            </div>
            <div class="summary-item">
              <span class="summary-type other">기타</span>
              <span class="summary-amount">+{{ formatNumber(summary.other.amount) }}</span>
              <span class="summary-detail">{{ summary.other.label }}</span>
            </div>
          </div>
        </div>

        <!-- History List -->
        <div class="history-list">
          <div v-for="(item, idx) in history" :key="idx" class="history-item">
            <span :class="['history-type', item.type]">{{ getTypeLabel(item.type) }}</span>
            <span class="history-name">{{ item.name || item.label }}</span>
            <span class="history-amount">{{ formatNumber(item.amount) }}{{ item.currency }}</span>
          </div>
        </div>
      </section>
      </template>
    </div>

    <!-- Spacer for bottom nav -->
    <div class="bottom-spacer"></div>
  </div>
</template>

<style scoped>
.transactions-screen {
  min-height: 100vh;
  background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
  padding-bottom: var(--bottom-nav-height);
}

.content {
  padding: 0 var(--spacing-lg) var(--spacing-lg);
}

/* State Container (Loading, Error, Empty) */
.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: var(--spacing-3xl) var(--spacing-xl);
  text-align: center;
}

/* Loading State */
.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(139, 92, 246, 0.2);
  border-top-color: #8B5CF6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: var(--spacing-lg);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.state-message {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0;
}

/* Error State */
.error-state {
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: 16px;
}

.error-icon {
  font-size: 64px;
  margin-bottom: var(--spacing-lg);
}

.error-message {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: #EF4444;
  margin: 0 0 var(--spacing-xl) 0;
}

.error-actions {
  display: flex;
  gap: var(--spacing-md);
  flex-direction: column;
  width: 100%;
  max-width: 280px;
}

.action-button {
  padding: var(--spacing-md) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all 0.2s;
}

.action-button.primary {
  background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%);
  color: var(--color-text-inverse);
}

.action-button.primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
}

.action-button.secondary {
  background: rgba(255, 255, 255, 0.1);
  color: var(--color-text-primary);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.action-button.secondary:hover {
  background: rgba(255, 255, 255, 0.15);
}

/* Empty State */
.empty-state {
  background: rgba(139, 92, 246, 0.05);
  border: 1px solid rgba(139, 92, 246, 0.1);
  border-radius: 16px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: var(--spacing-lg);
}

.empty-message {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs) 0;
}

.empty-submessage {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin: 0;
}

/* Pending Orders Section */
.pending-section {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.pending-section .section-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
}

.order-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
  padding-right: 4px;
}

.order-list::-webkit-scrollbar {
  width: 4px;
}

.order-list::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.order-list::-webkit-scrollbar-thumb {
  background: rgba(139, 92, 246, 0.5);
  border-radius: 2px;
}

.order-list::-webkit-scrollbar-thumb:hover {
  background: rgba(139, 92, 246, 0.7);
}

.order-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  transition: all 0.2s;
  cursor: pointer;
}

.order-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(139, 92, 246, 0.3);
  transform: translateX(2px);
}

.order-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  min-width: 40px;
}

.order-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.order-type {
  padding: 4px 8px;
  border-radius: 4px;
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

.order-name {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.order-price {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

/* Period Transaction Section */
.period-section {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: var(--spacing-lg);
}

.period-section .section-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-md);
}

/* Period Selector */
.period-selector {
  display: flex;
  gap: 6px;
  margin-bottom: var(--spacing-md);
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.period-selector::-webkit-scrollbar {
  display: none;
}

.period-btn {
  flex-shrink: 0;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.period-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
}

.period-btn.active {
  background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%);
  border-color: #8B5CF6;
  color: var(--color-text-inverse);
  font-weight: var(--font-weight-medium);
}

.date-range {
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  padding: 10px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  margin-bottom: var(--spacing-lg);
}

/* Summary Container */
.summary-container {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(124, 58, 237, 0.1) 100%);
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 12px;
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.summary-card {
  display: flex;
  justify-content: space-around;
  gap: 8px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
  min-width: 0;
}

.summary-type {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: var(--font-weight-medium);
  white-space: nowrap;
}

.summary-type.buy {
  background: #F97316;
  color: var(--color-text-inverse);
}

.summary-type.sell {
  background: var(--color-secondary);
  color: var(--color-text-inverse);
}

.summary-type.other {
  background: rgba(255, 255, 255, 0.1);
  color: var(--color-text-secondary);
}

.summary-amount {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.summary-detail {
  font-size: 10px;
  color: var(--color-text-tertiary);
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* History List */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
  padding-right: 4px;
}

.history-list::-webkit-scrollbar {
  width: 4px;
}

.history-list::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

.history-list::-webkit-scrollbar-thumb {
  background: rgba(139, 92, 246, 0.5);
  border-radius: 2px;
}

.history-list::-webkit-scrollbar-thumb:hover {
  background: rgba(139, 92, 246, 0.7);
}

.history-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  transition: all 0.2s;
  flex-shrink: 0;
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(139, 92, 246, 0.3);
}

.history-type {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  min-width: 40px;
  text-align: center;
}

.history-type.sell {
  background: var(--color-secondary);
  color: var(--color-text-inverse);
}

.history-type.buy {
  background: #F97316;
  color: var(--color-text-inverse);
}

.history-type.dividend {
  background: rgba(255, 255, 255, 0.1);
  color: var(--color-text-secondary);
}

.history-name {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.history-amount {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.bottom-spacer {
  height: var(--bottom-nav-height);
}
</style>
