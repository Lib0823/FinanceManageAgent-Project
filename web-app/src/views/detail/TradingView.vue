<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/common/AppHeader.vue'
import { tradingApi } from '@/services/api'

const route = useRoute()
const router = useRouter()

const symbol = ref(route.params.symbol || '005930')  // Default to Samsung Electronics
const stockName = ref('삼성전자')  // Stock name
const activeTab = ref('buy')
const loading = ref(false)
const errorMessage = ref('')

const orderForm = ref({
  type: 'market',
  time: '09:00 ~ 15:30',
  quantity: 1,
  maxQuantity: 100,
  price: 71500,
  maxPrice: 1000000,
  totalAmount: 71500
})

const priceList = [
  90000, 85000, 80000, 75000, 71500, 70000, 65000, 60000, 55000, 50000
]

const formatNumber = (num) => {
  return new Intl.NumberFormat('ko-KR').format(num)
}

const selectPrice = (price) => {
  orderForm.value.price = price
  orderForm.value.totalAmount = price * orderForm.value.quantity
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

    let response
    if (activeTab.value === 'buy') {
      response = await tradingApi.buy(orderData)
    } else {
      response = await tradingApi.sell(orderData)
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

// Mock orders for display (실제로는 API에서 가져와야 하지만 MVP에서는 생략)
const filteredOrders = computed(() => ({
  pending: [],
  reserved: []
}))
</script>

<template>
  <div class="trading-screen">
    <AppHeader title="실시간 매매" showBack />

    <div class="content">
      <!-- Stock Header -->
      <div class="stock-header">
        <h2 class="stock-name">{{ symbol }}(AMZN)</h2>
        <div class="stock-tags">
          <span class="tag">나스닥</span>
          <span class="tag">도소매업</span>
          <span class="tag">홀짝</span>
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

        <div class="order-group" v-if="filteredOrders.reserved.length > 0">
          <h3 class="order-title">예약 주문</h3>
          <div class="order-list">
            <div v-for="(order, idx) in filteredOrders.reserved" :key="idx" class="order-item">
              <span :class="['order-type', order.type]">{{ order.type === 'sell' ? '매도' : '매수' }}</span>
              <span class="order-symbol">{{ order.name }}({{ order.symbol }})</span>
              <span class="order-price">{{ formatNumber(order.price) }}{{ order.currency }}</span>
            </div>
          </div>
        </div>

        <div v-if="filteredOrders.pending.length === 0 && filteredOrders.reserved.length === 0" class="no-orders">
          <p>현재 {{ symbol }} 종목에 대한 미체결 및 예약 주문이 없습니다.</p>
        </div>
      </div>

      <!-- Trading Form -->
      <div class="trading-form">
        <!-- Price List (Order Book) -->
        <div class="price-list">
          <div
            v-for="price in priceList"
            :key="price"
            :class="['price-item', { highlight: price === 400000 }]"
            @click="selectPrice(price)"
          >
            {{ formatNumber(price) }}
          </div>
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
                <span class="form-hint">주문 가능 {{ orderForm.maxQuantity }}주</span>
                <label class="checkbox-small">
                  <input type="checkbox" /> 최대
                </label>
              </div>
            </div>
            <div class="form-row">
              <span class="form-label">가격</span>
              <div class="form-input-group">
                <input type="text" v-model="orderForm.price" class="form-input" />
                <span class="form-hint">주문 가능 {{ formatNumber(orderForm.maxPrice) }}원</span>
                <label class="checkbox-small">
                  <input type="checkbox" /> 최대
                </label>
              </div>
            </div>
            <div class="form-row total">
              <span class="form-label">총 매수 금액</span>
              <span class="form-total">{{ formatNumber(orderForm.totalAmount) }}원</span>
            </div>

            <!-- Date Time -->
            <div class="datetime-row">
              <span class="calendar-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="4" width="18" height="18" rx="2" stroke="currentColor" stroke-width="2"/>
                  <path d="M16 2V6M8 2V6M3 10H21" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </span>
              <span class="datetime-value">2024, 10, 26 / 10:25</span>
            </div>
          </div>

          <!-- Submit Button -->
          <button
            :class="['submit-btn', activeTab]"
            @click="placeOrder"
          >
            예약 {{ activeTab === 'buy' ? '매수' : '매도' }} 주문
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
  padding: var(--spacing-sm);
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
  cursor: pointer;
}

.price-item:nth-child(-n+5) {
  background: #DBEAFE;
  color: var(--color-stock-down);
}

.price-item:nth-child(n+6) {
  background: #FEE2E2;
  color: var(--color-stock-up);
}

.price-item.highlight {
  font-weight: var(--font-weight-bold);
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
