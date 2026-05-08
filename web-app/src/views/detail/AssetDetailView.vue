<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppHeader from '@/components/common/AppHeader.vue'
import AssetTabs from '@/components/common/AssetTabs.vue'
import { assetApi } from '@/services/api'
import { mockStocks } from '@/services/mockData'

const router = useRouter()
const route = useRoute()

const tabs = ref({ main: 'stocks', sub: 'domestic' })
const loading = ref(false)
const errorMessage = ref('')

// 국내 주식 데이터 (API에서 가져옴)
const domesticStocks = ref([])

// 해외 주식 데이터 (Mock - KIS API는 국내 주식만 지원)
const overseasStocks = ref(mockStocks)

// 현재 선택된 탭에 따른 주식 데이터
const currentStocks = computed(() => {
  return tabs.value.sub === 'domestic' ? domesticStocks.value : overseasStocks.value
})

// 현금 데이터 (API에서 가져옴)
const cashDetail = ref({
  krw: {
    availableForOrder: 0,
    availableForWithdrawal: 0
  },
  usd: {
    amount: 0,
    availableForOrder: 0,
    availableForWithdrawal: 0,
    exchangeRate: 1350
  }
})

// Load holdings (보유 주식)
const loadHoldings = async () => {
  try {
    loading.value = true
    const response = await assetApi.getHoldings()

    // KIS API 응답 구조에 맞춰 파싱
    if (response.data?.output1) {
      domesticStocks.value = response.data.output1.map(stock => ({
        symbol: stock.pdno,  // 종목코드
        name: stock.prdt_name,  // 종목명
        nameEn: stock.prdt_name,
        currentPrice: parseInt(stock.prpr),  // 현재가
        quantity: parseInt(stock.hldg_qty),  // 보유수량
        avgPrice: parseInt(stock.pchs_avg_pric),  // 평균매입가
        purchasePrice: parseInt(stock.pchs_amt),  // 매입금액
        profit: parseInt(stock.evlu_pfls_amt),  // 평가손익금액
        profitPercent: parseFloat(stock.evlu_pfls_rt),  // 평가손익율
        logo: ''
      }))
    }
  } catch (error) {
    console.error('Failed to load holdings:', error)
    errorMessage.value = '보유 주식 정보를 불러오는데 실패했습니다'
  } finally {
    loading.value = false
  }
}

// Load balance (잔고)
const loadBalance = async () => {
  try {
    const response = await assetApi.getBalance()

    // KIS API 응답 구조에 맞춰 파싱
    if (response.data?.balance?.output2) {
      const balanceData = response.data.balance.output2[0]
      cashDetail.value.krw.availableForOrder = parseInt(balanceData.ord_psbl_cash || 0)  // 주문가능현금
      cashDetail.value.krw.availableForWithdrawal = parseInt(balanceData.wdrw_psbl_tot_amt || 0)  // 출금가능금액
    }
  } catch (error) {
    console.error('Failed to load balance:', error)
  }
}

// URL 쿼리에서 초기 탭 설정 및 데이터 로드
onMounted(async () => {
  if (route.query.main) {
    tabs.value.main = route.query.main
    if (route.query.sub) {
      tabs.value.sub = route.query.sub
    }
  }

  // Load data
  await Promise.all([loadHoldings(), loadBalance()])
})

// USD를 원화로 환산
const usdToKrw = computed(() => {
  return cashDetail.value.usd.amount * cashDetail.value.usd.exchangeRate
})

const formatNumber = (num) => {
  return new Intl.NumberFormat('ko-KR').format(num)
}

const goToNews = (stock) => {
  router.push(`/news?symbol=${stock.symbol}`)
}

const goToTrade = (stock) => {
  router.push(`/trading/${stock.symbol}`)
}

const goToInfo = (stock) => {
  router.push(`/company/${stock.symbol}`)
}

const goToTransfer = () => {
  router.push('/transfer')
}
</script>

<template>
  <div class="asset-detail-screen">
    <AppHeader title="자산 상세 정보" showBack />

    <div class="content">
      <!-- Tabs -->
      <AssetTabs v-model="tabs" :showSubTabs="tabs.main === 'stocks'" />

      <!-- 현금 화면 -->
      <div v-if="tabs.main === 'cash'" class="cash-section">
        <!-- KRW Card -->
        <div class="cash-card">
          <div class="cash-header">
            <h3 class="cash-title">KRW</h3>
            <span class="cash-total">{{ formatNumber(cashDetail.krw.availableForOrder) }}원</span>
          </div>
          <div class="cash-details">
            <div class="cash-detail-item">
              <span class="detail-label">주문가능금</span>
              <span class="detail-value">{{ formatNumber(cashDetail.krw.availableForOrder) }}원</span>
            </div>
            <div class="cash-detail-item">
              <span class="detail-label">출금가능금</span>
              <span class="detail-value">{{ formatNumber(cashDetail.krw.availableForWithdrawal) }}원</span>
            </div>
          </div>
        </div>

        <!-- USD Card -->
        <div class="cash-card">
          <div class="cash-header">
            <h3 class="cash-title">USD</h3>
            <div class="cash-total-group">
              <span class="cash-total">${{ formatNumber(cashDetail.usd.amount) }}</span>
              <span class="cash-total-krw">({{ formatNumber(usdToKrw) }}원)</span>
            </div>
          </div>
          <div class="cash-details">
            <div class="cash-detail-item">
              <span class="detail-label">주문가능금</span>
              <span class="detail-value">${{ formatNumber(cashDetail.usd.availableForOrder) }}</span>
            </div>
            <div class="cash-detail-item">
              <span class="detail-label">출금가능금</span>
              <span class="detail-value">${{ formatNumber(cashDetail.usd.availableForWithdrawal) }}</span>
            </div>
          </div>
        </div>

        <!-- 계좌이체 버튼 -->
        <button class="transfer-btn" @click="goToTransfer">
          <span>계좌이체</span>
          <van-icon name="arrow" />
        </button>
      </div>

      <!-- 주식 화면 -->
      <div v-if="tabs.main === 'stocks'">
        <!-- Summary Card -->
        <div class="summary-card">
          <div class="summary-header">
            <h3 class="summary-title">{{ tabs.sub === 'domestic' ? '국내' : '해외' }} 주식</h3>
            <div class="profit-badge">
              <span class="profit-icon">{{ stockDetail[tabs.sub].profitPercent >= 0 ? '▲' : '▼' }}</span>
              <span class="profit-percent">{{ stockDetail[tabs.sub].profitPercent }}%</span>
            </div>
          </div>

          <div class="summary-main">
            <div class="main-info">
              <span class="main-label">총평가금액</span>
              <span class="main-value">{{ formatNumber(stockDetail[tabs.sub].totalValuation) }}<span class="unit">원</span></span>
            </div>
            <div class="profit-info">
              <span class="profit-label">총평가손익</span>
              <span class="profit-value positive">{{ formatNumber(stockDetail[tabs.sub].totalProfit) }}원</span>
            </div>
          </div>

          <div class="summary-details">
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">D+2예수금</span>
                <span class="detail-value">{{ formatNumber(stockDetail[tabs.sub].d2Deposit) }}원</span>
              </div>
              <div class="detail-divider"></div>
              <div class="detail-item">
                <span class="detail-label">총매입금액</span>
                <span class="detail-value">{{ formatNumber(stockDetail[tabs.sub].totalPurchase) }}원</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Stock List -->
        <div class="stock-list">
          <div v-for="stock in currentStocks" :key="stock.symbol" class="stock-card-enhanced">
            <!-- Stock Info Header -->
            <div class="stock-header">
              <div class="stock-logo">
                <img v-if="stock.logo" :src="stock.logo" :alt="stock.name" />
                <div v-else class="logo-placeholder">{{ stock.symbol?.charAt(0) }}</div>
              </div>
              <div class="stock-info">
                <div class="stock-name-row">
                  <span class="stock-name">{{ stock.name }}</span>
                  <span class="stock-symbol">{{ stock.symbol }}</span>
                </div>
                <div class="stock-price-row">
                  <span class="current-price">₩{{ formatNumber(stock.currentPrice) }}</span>
                  <span class="profit-badge" :class="stock.profitPercent >= 0 ? 'positive' : 'negative'">
                    {{ stock.profitPercent >= 0 ? '+' : '' }}{{ stock.profitPercent }}%
                  </span>
                </div>
              </div>
            </div>

            <!-- Stock Details -->
            <div class="stock-details">
              <div class="detail-item">
                <span class="detail-label">평가금액</span>
                <span class="detail-value">{{ formatNumber(stock.purchasePrice) }}원</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">평가손익</span>
                <span class="detail-value profit" :class="stock.profit >= 0 ? 'positive' : 'negative'">
                  {{ stock.profit >= 0 ? '+' : '' }}{{ formatNumber(stock.profit) }}원
                </span>
              </div>
              <div class="detail-item">
                <span class="detail-label">매도 가능 수량</span>
                <span class="detail-value">{{ formatNumber(stock.quantity) }}주</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">평균단가</span>
                <span class="detail-value">{{ formatNumber(stock.avgPrice) }}원</span>
              </div>
            </div>

            <!-- Action Buttons -->
            <div class="action-buttons">
              <button class="action-btn news-btn" @click="goToNews(stock)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" stroke="currentColor" stroke-width="2"/>
                </svg>
                뉴스
              </button>
              <button class="action-btn trade-btn" @click="goToTrade(stock)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                거래
              </button>
              <button class="action-btn info-btn" @click="goToInfo(stock)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                  <path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                정보
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.asset-detail-screen {
  min-height: 100vh;
  background: var(--color-bg-primary);
}

.content {
  padding: 0 var(--spacing-lg) var(--spacing-lg);
}

.summary-card {
  background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
  border-radius: var(--radius-xl);
  padding: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

/* 헤더 영역 */
.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.summary-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin: 0;
}

.profit-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(16, 185, 129, 0.25) 100%);
  padding: 6px 14px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.profit-icon {
  font-size: var(--font-size-sm);
  color: var(--color-stock-up);
}

.profit-percent {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-bold);
  color: var(--color-stock-up);
}

/* 메인 정보 영역 */
.summary-main {
  margin-bottom: var(--spacing-lg);
}

.main-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-md);
}

.main-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.main-value {
  font-size: 32px;
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: 1.2;
}

.unit {
  font-size: 20px;
  color: var(--color-text-secondary);
  margin-left: 4px;
}

.profit-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  background: rgba(16, 185, 129, 0.1);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-stock-up);
}

.profit-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.profit-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
}

.profit-value.positive {
  color: var(--color-stock-up);
}

/* 상세 정보 영역 */
.summary-details {
  background: rgba(255, 255, 255, 0.03);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
}

.detail-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.detail-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.detail-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.detail-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.detail-divider {
  width: 1px;
  height: 40px;
  background: rgba(255, 255, 255, 0.1);
}

.stock-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* Enhanced Stock Card */
.stock-card-enhanced {
  background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
  border-radius: var(--radius-xl);
  padding: var(--spacing-lg);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

/* Stock Header */
.stock-header {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.stock-logo {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-bg-secondary);
  flex-shrink: 0;
}

.stock-logo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.logo-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #10B981 0%, #059669 100%);
  color: white;
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
}

.stock-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.stock-name-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.stock-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.stock-symbol {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
}

.stock-price-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.current-price {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.profit-badge {
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
}

.profit-badge.positive {
  background: rgba(16, 185, 129, 0.2);
  color: var(--color-stock-up);
}

.profit-badge.negative {
  background: rgba(239, 68, 68, 0.2);
  color: var(--color-stock-down);
}

/* Stock Details */
.stock-details {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: rgba(255, 255, 255, 0.03);
  border-radius: var(--radius-md);
}

.stock-card-enhanced .detail-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xxs);
}

.stock-card-enhanced .detail-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.stock-card-enhanced .detail-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.stock-card-enhanced .detail-value.profit.positive {
  color: var(--color-stock-up);
}

.stock-card-enhanced .detail-value.profit.negative {
  color: var(--color-stock-down);
}

/* Action Buttons */
.action-buttons {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-sm);
  margin-top: var(--spacing-xs);
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-sm);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--color-bg-highlight);
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.action-btn:active {
  transform: scale(0.98);
}

/* 현금 섹션 */
.cash-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.cash-card {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-xl);
  padding: var(--spacing-lg);
}

.cash-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--color-border);
}

.cash-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.cash-total {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.cash-total-group {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--spacing-xxs);
}

.cash-total-krw {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.cash-details {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.cash-detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) 0;
}

.detail-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.detail-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.transfer-btn {
  width: 100%;
  padding: var(--spacing-md);
  background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-inverse);
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--spacing-sm);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
  transition: all 0.2s ease;
}

.transfer-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(245, 158, 11, 0.4);
}

.transfer-btn:active {
  transform: translateY(0);
}
</style>
