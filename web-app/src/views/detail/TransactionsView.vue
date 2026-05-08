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

// 요약 데이터
const summary = ref({
  totalBuy: 0,
  totalSell: 0,
  totalProfit: 0,
  count: 0
})

// Load trade history
const loadHistory = async () => {
  try {
    loading.value = true
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
        status: trade.orderStatus  // PENDING, COMPLETED 등
      }))

      // 요약 데이터 계산
      summary.value.count = history.value.length
      summary.value.totalBuy = history.value
        .filter(t => t.type === 'buy')
        .reduce((sum, t) => sum + t.amount, 0)
      summary.value.totalSell = history.value
        .filter(t => t.type === 'sell')
        .reduce((sum, t) => sum + t.amount, 0)
      summary.value.totalProfit = summary.value.totalSell - summary.value.totalBuy
    }
  } catch (error) {
    console.error('Failed to load trade history:', error)
    errorMessage.value = '거래 내역을 불러오는데 실패했습니다'
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
