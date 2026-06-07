<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/common/AppHeader.vue'
import { marketAnalysisApi } from '@/services/api'

const router = useRouter()

// 분석 날짜
const analysisDate = ref(null)
const analysisDateStr = ref('')

// Loading state
const loading = ref(true)
const error = ref(null)

// TOP3 toggle state
const activeTop3 = ref('buy') // 'buy' or 'sell'

// 30종목 히트맵 데이터
const heatmapStats = ref({
  totalStocks: 30,
  buyCandidate: 0,
  sellCandidate: 0,
  neutral: 0
})

// 히트맵 상세 데이터
const heatmapData = ref([])
const heatmapInsights = ref({
  avgForeignNetBuy: 0,
  avgInstitutionalNetBuy: 0,
  avgSentiment: 0,
  topStock: { name: '', score: 0 }
})

// Gemini AI 매수 TOP3
const buyTop3 = ref([])

// Gemini AI 매도 TOP3
const sellTop3 = ref([])

// 시장 전반 감성분석 데이터
const marketSentiment = ref({
  score: 0,
  label: '중립',
  distribution: {
    positive: { count: 0, percent: 0, color: '#f87171' },
    neutral: { count: 0, percent: 0, color: '#4a5568' },
    negative: { count: 0, percent: 0, color: '#60a5fa' }
  },
  timeRange: '전날 18:00 — 당일 08:50',
  sources: '한경 · 매경 · 연합'
})

// Fetch market data
const fetchMarketData = async () => {
  try {
    loading.value = true
    error.value = null

    // 1. Get latest analysis date first
    const latestDateResponse = await marketAnalysisApi.getLatestDate()
    const latestDate = latestDateResponse.data.latest_date

    if (!latestDate) {
      error.value = '분석 데이터가 없습니다.'
      loading.value = false
      return
    }

    analysisDate.value = latestDate

    // Format date for display (handle ISO date string format)
    const dateObj = new Date(latestDate + 'T00:00:00') // Add time to ensure correct timezone
    analysisDateStr.value = `${dateObj.getFullYear()}.${String(dateObj.getMonth() + 1).padStart(2, '0')}.${String(dateObj.getDate()).padStart(2, '0')}`

    // 2. Fetch all market data in parallel using the latest date
    const [summaryResponse, sentimentResponse, decisionsResponse, heatmapResponse] = await Promise.all([
      marketAnalysisApi.getSummary(latestDate),
      marketAnalysisApi.getSentiment(latestDate),
      marketAnalysisApi.getDecisions(latestDate),
      marketAnalysisApi.getHeatmap(latestDate)
    ])

    // Process summary data
    if (summaryResponse && summaryResponse.data) {
      const summary = summaryResponse.data
      heatmapStats.value = {
        totalStocks: summary.statistics.total || 30,
        buyCandidate: summary.statistics.buy_candidate || 0,
        sellCandidate: summary.statistics.sell_candidate || 0,
        neutral: summary.statistics.neutral || 0
      }
    } else {
      // No summary data available
      console.warn('Market summary data is empty for date:', latestDate)
    }

    // Process heatmap data
    if (heatmapResponse && heatmapResponse.data && heatmapResponse.data.stocks) {
      const stocks = heatmapResponse.data.stocks
      heatmapData.value = stocks

      // Calculate insights
      if (stocks.length > 0) {
        // Average foreign/institutional net buy
        const totalForeignNetBuy = stocks.reduce((sum, s) => sum + (s.foreign_net_buy || 0), 0)
        const totalInstitutionalNetBuy = stocks.reduce((sum, s) => sum + (s.institutional_net_buy || 0), 0)
        const totalSentiment = stocks.reduce((sum, s) => sum + (s.sentiment_score || 0), 0)

        heatmapInsights.value.avgForeignNetBuy = Math.round(totalForeignNetBuy / stocks.length)
        heatmapInsights.value.avgInstitutionalNetBuy = Math.round(totalInstitutionalNetBuy / stocks.length)
        heatmapInsights.value.avgSentiment = (totalSentiment / stocks.length).toFixed(2)

        // Find top stock by combined score (simplified scoring)
        let topStock = stocks[0]
        let maxScore = 0

        stocks.forEach(stock => {
          // Simple scoring: positive factors
          const score = (
            (stock.foreign_net_buy > 0 ? 1 : 0) +
            (stock.institutional_net_buy > 0 ? 1 : 0) +
            (stock.sentiment_score > 0 ? 1 : 0) +
            (stock.price_trend > 0 ? 1 : 0) +
            (stock.volume_trend > 0 ? 1 : 0)
          )

          if (score > maxScore) {
            maxScore = score
            topStock = stock
          }
        })

        heatmapInsights.value.topStock = {
          name: topStock.stock_name,
          score: maxScore
        }
      }
    }

    // Process sentiment data
    if (sentimentResponse && sentimentResponse.data) {
      marketSentiment.value = sentimentResponse.data
    }

    // Process decisions data
    if (decisionsResponse && decisionsResponse.data) {
      const decisions = decisionsResponse.data

      // Check if we have actual decision data
      const hasBuyData = decisions.buy_top3.some(s => s.stock_code !== null)
      const hasSellData = decisions.sell_top3.some(s => s.stock_code !== null)

      if (!hasBuyData && !hasSellData) {
        console.warn('AI trade decisions are empty for date:', latestDate)
      }

      // Map buy TOP3
      buyTop3.value = decisions.buy_top3.map(stock => ({
        rank: stock.rank,
        icon: getStockIcon(stock.stock_name),
        iconBg: getIconBg(stock.rank),
        iconColor: getIconColor(stock.rank),
        name: stock.stock_name,
        reason: stock.reason || '',
        score: stock.score,
        scoreClass: getScoreClass(stock.score),
        isEmpty: !stock.stock_code
      }))

      // Map sell TOP3
      sellTop3.value = decisions.sell_top3.map(stock => ({
        rank: stock.rank,
        icon: getStockIcon(stock.stock_name),
        iconBg: getIconBg(stock.rank),
        iconColor: getIconColor(stock.rank),
        name: stock.stock_name,
        reason: stock.reason || '',
        score: stock.score,
        scoreClass: getScoreClass(stock.score),
        isEmpty: !stock.stock_code
      }))
    }

  } catch (err) {
    console.error('Failed to fetch market data:', err)
    error.value = '시장 데이터를 불러올 수 없습니다.'
  } finally {
    loading.value = false
  }
}

// Helper functions
const getStockIcon = (name) => {
  if (!name || name === '해당 없음') return '—'
  return name.substring(0, 2)
}

const getIconBg = (rank) => {
  const colors = [
    'rgba(248,113,113,.12)',
    'rgba(251,191,36,.12)',
    'rgba(52,211,153,.12)'
  ]
  return colors[rank - 1] || 'var(--color-bg-tertiary)'
}

const getIconColor = (rank) => {
  const colors = ['#f87171', '#fbbf24', '#34d399']
  return colors[rank - 1] || 'var(--color-text-tertiary)'
}

const getScoreClass = (score) => {
  if (!score) return 'empty'
  if (score >= 0.8) return 'up'
  if (score >= 0.6) return 'yw'
  if (score >= 0.4) return 'nt'
  return 'dn'
}

const toggleTop3 = (type) => {
  activeTop3.value = type
}

const formatNumber = (num) => {
  if (num === 0) return '0'
  const absNum = Math.abs(num)
  if (absNum >= 100000000) {
    return `${(num / 100000000).toFixed(1)}억`
  } else if (absNum >= 10000) {
    return `${(num / 10000).toFixed(1)}만`
  }
  return num.toLocaleString()
}

const goBack = () => {
  router.push('/bot')
}

onMounted(() => {
  fetchMarketData()
})
</script>

<template>
  <div class="market-analysis-screen">
    <AppHeader title="종합분석" :showBack="true" @back="goBack">
      <template #right>
        <div class="header-meta">
          <div class="live-dot"></div>
          <div class="header-date">{{ analysisDateStr || '조회중...' }}</div>
        </div>
      </template>
    </AppHeader>

    <div class="content">
      <!-- ① 30종목 피처 히트맵 -->
      <div class="analysis-section">
        <div class="section-label">30종목 피처 히트맵</div>
        <div class="section-card">
          <div class="chart-container">
            <svg class="chart-placeholder" viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">
              <!-- Background grid -->
              <defs>
                <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                  <rect width="40" height="40" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="1"/>
                </pattern>
              </defs>
              <rect width="800" height="400" fill="#141b2b"/>
              <rect width="800" height="400" fill="url(#grid)"/>

              <!-- Heatmap simulation -->
              <g opacity="0.6">
                <rect x="50" y="30" width="700" height="340" fill="none" stroke="rgba(167,139,250,0.2)" stroke-width="1"/>
                <!-- Random colored cells to simulate heatmap -->
                <rect x="100" y="60" width="50" height="30" fill="#f87171" opacity="0.4"/>
                <rect x="200" y="60" width="50" height="30" fill="#60a5fa" opacity="0.3"/>
                <rect x="300" y="60" width="50" height="30" fill="#34d399" opacity="0.5"/>
                <rect x="400" y="60" width="50" height="30" fill="#fbbf24" opacity="0.4"/>
                <rect x="500" y="60" width="50" height="30" fill="#f87171" opacity="0.6"/>
                <rect x="600" y="60" width="50" height="30" fill="#2dd4bf" opacity="0.4"/>

                <rect x="100" y="120" width="50" height="30" fill="#60a5fa" opacity="0.3"/>
                <rect x="200" y="120" width="50" height="30" fill="#f87171" opacity="0.5"/>
                <rect x="300" y="120" width="50" height="30" fill="#fbbf24" opacity="0.4"/>
                <rect x="400" y="120" width="50" height="30" fill="#34d399" opacity="0.6"/>
                <rect x="500" y="120" width="50" height="30" fill="#2dd4bf" opacity="0.5"/>
                <rect x="600" y="120" width="50" height="30" fill="#60a5fa" opacity="0.4"/>

                <rect x="100" y="180" width="50" height="30" fill="#34d399" opacity="0.4"/>
                <rect x="200" y="180" width="50" height="30" fill="#2dd4bf" opacity="0.5"/>
                <rect x="300" y="180" width="50" height="30" fill="#f87171" opacity="0.6"/>
                <rect x="400" y="180" width="50" height="30" fill="#60a5fa" opacity="0.3"/>
                <rect x="500" y="180" width="50" height="30" fill="#fbbf24" opacity="0.4"/>
                <rect x="600" y="180" width="50" height="30" fill="#f87171" opacity="0.5"/>
              </g>

              <!-- Label -->
              <text x="400" y="200" font-family="monospace" font-size="14" fill="#94a3b8" text-anchor="middle" opacity="0.6">
                11개 피처 × 30종목 히트맵
              </text>
            </svg>
            <span class="chart-badge">matplotlib · 11개 피처 × 30종목</span>
          </div>

          <div class="stats-grid">
            <div class="stat-box">
              <div class="stat-label">분석<br>종목</div>
              <div class="stat-value nt">{{ heatmapStats.totalStocks }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">매수<br>후보</div>
              <div class="stat-value up">{{ heatmapStats.buyCandidate }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">매도<br>후보</div>
              <div class="stat-value dn">{{ heatmapStats.sellCandidate }}</div>
            </div>
            <div class="stat-box">
              <div class="stat-label">중립</div>
              <div class="stat-value neutral">{{ heatmapStats.neutral }}</div>
            </div>
          </div>

          <!-- 추가 인사이트 -->
          <div class="insights-section">
            <div class="insight-row">
              <span class="insight-label">평균 외국인 순매수</span>
              <span :class="['insight-value', heatmapInsights.avgForeignNetBuy > 0 ? 'up' : 'dn']">
                {{ heatmapInsights.avgForeignNetBuy > 0 ? '+' : '' }}{{ formatNumber(heatmapInsights.avgForeignNetBuy) }}원
              </span>
            </div>
            <div class="insight-row">
              <span class="insight-label">평균 기관 순매수</span>
              <span :class="['insight-value', heatmapInsights.avgInstitutionalNetBuy > 0 ? 'up' : 'dn']">
                {{ heatmapInsights.avgInstitutionalNetBuy > 0 ? '+' : '' }}{{ formatNumber(heatmapInsights.avgInstitutionalNetBuy) }}원
              </span>
            </div>
            <div class="insight-row">
              <span class="insight-label">평균 감성 점수</span>
              <span :class="['insight-value', heatmapInsights.avgSentiment > 0 ? 'up' : 'dn']">
                {{ heatmapInsights.avgSentiment > 0 ? '+' : '' }}{{ heatmapInsights.avgSentiment }}
              </span>
            </div>
            <div class="insight-row highlight">
              <span class="insight-label">💎 최고 점수 종목</span>
              <span class="insight-value highlight">{{ heatmapInsights.topStock.name || '분석중' }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ② Gemini AI 매매 판단 -->
      <div class="analysis-section">
        <div class="section-label">AI 매매 판단</div>
        <div class="section-card">
          <!-- Toggle Buttons -->
          <div class="top3-toggle">
            <button
              :class="['toggle-btn', 'buy', { active: activeTop3 === 'buy' }]"
              @click="toggleTop3('buy')"
            >
              ▲ 매수 TOP3
            </button>
            <button
              :class="['toggle-btn', 'sell', { active: activeTop3 === 'sell' }]"
              @click="toggleTop3('sell')"
            >
              ▼ 매도 TOP3
            </button>
          </div>

          <!-- Buy TOP3 Panel -->
          <div v-show="activeTop3 === 'buy'" class="top3-panel">
            <div
              v-for="stock in buyTop3"
              :key="stock.rank"
              class="stock-row"
            >
              <div class="rank-badge buy">{{ stock.rank }}</div>
              <div
                class="stock-icon"
                :style="{ background: stock.iconBg, color: stock.iconColor }"
              >
                {{ stock.icon }}
              </div>
              <div class="stock-info">
                <div class="stock-name">{{ stock.name }}</div>
                <div v-if="stock.reason" class="stock-reason">{{ stock.reason }}</div>
              </div>
              <div :class="['stock-score', stock.scoreClass]">
                {{ stock.score }}
              </div>
            </div>
          </div>

          <!-- Sell TOP3 Panel -->
          <div v-show="activeTop3 === 'sell'" class="top3-panel">
            <div
              v-for="stock in sellTop3"
              :key="stock.rank"
              :class="['stock-row', { empty: stock.isEmpty }]"
            >
              <div class="rank-badge sell">{{ stock.rank }}</div>
              <div
                class="stock-icon"
                :style="{ background: stock.iconBg, color: stock.iconColor }"
              >
                {{ stock.icon }}
              </div>
              <div class="stock-info">
                <div class="stock-name">{{ stock.name }}</div>
                <div v-if="stock.reason" class="stock-reason">{{ stock.reason }}</div>
              </div>
              <div :class="['stock-score', stock.scoreClass]">
                {{ stock.score !== null ? stock.score : '—' }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ③ 시장 전반 감성분석 -->
      <div class="analysis-section">
        <div class="section-label">시장 전반 감성분석</div>
        <div class="section-card">
          <div class="sentiment-block">
            <!-- Score Row -->
            <div class="sentiment-header">
              <div>
                <div class="sentiment-source">KR-FinBERT · RSS 피드 기반</div>
                <div class="sentiment-main">
                  <span class="sentiment-value">{{ marketSentiment.score > 0 ? '+' : '' }}{{ marketSentiment.score }}</span>
                  <span class="sentiment-label">시장 감성점수</span>
                </div>
              </div>
              <div class="sentiment-badge">{{ marketSentiment.label }}</div>
            </div>

            <div class="sentiment-divider"></div>

            <!-- Distribution Bar -->
            <div class="distribution-section">
              <div class="distribution-header">
                <span>종목 감성 분포 (30종목)</span>
              </div>
              <div class="distribution-bar">
                <div
                  class="bar-segment positive"
                  :style="{ width: marketSentiment.distribution.positive.percent + '%' }"
                ></div>
                <div
                  class="bar-segment neutral"
                  :style="{ width: marketSentiment.distribution.neutral.percent + '%' }"
                ></div>
                <div
                  class="bar-segment negative"
                  :style="{ width: marketSentiment.distribution.negative.percent + '%' }"
                ></div>
              </div>
              <div class="distribution-labels">
                <span class="label-positive">
                  긍정 {{ marketSentiment.distribution.positive.count }}개 ({{ marketSentiment.distribution.positive.percent }}%)
                </span>
                <span class="label-neutral">
                  중립 {{ marketSentiment.distribution.neutral.count }}개 ({{ marketSentiment.distribution.neutral.percent }}%)
                </span>
                <span class="label-negative">
                  부정 {{ marketSentiment.distribution.negative.count }}개 ({{ marketSentiment.distribution.negative.percent }}%)
                </span>
              </div>
            </div>

            <div class="sentiment-divider"></div>

            <!-- Collection Info -->
            <div class="collection-info">
              <div class="info-item">
                <div class="info-label">수집 범위</div>
                <div class="info-value">{{ marketSentiment.timeRange }}</div>
              </div>
              <div class="info-item align-right">
                <div class="info-label">뉴스 출처</div>
                <div class="info-value">{{ marketSentiment.sources }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Spacer for bottom nav -->
    <div class="bottom-spacer"></div>
  </div>
</template>

<style scoped>
.market-analysis-screen {
  min-height: 100vh;
  background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%);
  padding-bottom: var(--bottom-nav-height);
}

/* Header Override */
.market-analysis-screen :deep(.app-header) {
  background: #0F172A;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-stock-up);
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.8);
  }
}

.header-date {
  font-family: 'DM Mono', monospace;
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  padding: 3px 8px;
  border-radius: 6px;
}

.content {
  padding: var(--spacing-md) var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

/* Section Label */
.section-label {
  font-size: 10.5px;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-tertiary);
  letter-spacing: 0.8px;
  text-transform: uppercase;
  margin-bottom: var(--spacing-sm);
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-label::before {
  content: '';
  display: block;
  width: 2px;
  height: 11px;
  background: var(--color-primary);
  border-radius: 2px;
}

/* Section Card */
.section-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

/* Chart Container */
.chart-container {
  position: relative;
  padding: var(--spacing-md);
}

.chart-placeholder {
  width: 100%;
  display: block;
  border-radius: var(--radius-md);
  background: #141b2b;
  min-height: 180px;
}

.chart-badge {
  position: absolute;
  top: 20px;
  left: 20px;
  font-size: 9px;
  color: var(--color-text-secondary);
  background: rgba(8, 12, 20, 0.8);
  backdrop-filter: blur(8px);
  border: 1px solid var(--color-border);
  padding: 3px 8px;
  border-radius: 6px;
  font-family: 'DM Mono', monospace;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  padding: var(--spacing-md);
  padding-top: var(--spacing-sm);
}

.stat-box {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 8px 4px;
  text-align: center;
}

.stat-label {
  font-size: 8px;
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
  line-height: 1.4;
}

.stat-value {
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  font-family: 'DM Mono', monospace;
}

.stat-value.up { color: #f87171; }
.stat-value.dn { color: #60a5fa; }
.stat-value.nt { color: #2dd4bf; }
.stat-value.neutral { color: var(--color-text-secondary); }

/* Insights Section */
.insights-section {
  padding: var(--spacing-md);
  padding-top: var(--spacing-sm);
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.5) 0%, rgba(30, 41, 59, 0.5) 100%);
  border-top: 1px solid var(--color-border);
}

.insight-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.insight-row:last-child {
  border-bottom: none;
}

.insight-row.highlight {
  background: rgba(167, 139, 250, 0.08);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  margin-top: 4px;
  border-bottom: none;
}

.insight-label {
  font-size: 10.5px;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.insight-value {
  font-size: 11.5px;
  font-weight: var(--font-weight-semibold);
  font-family: 'DM Mono', monospace;
}

.insight-value.up {
  color: #f87171;
}

.insight-value.dn {
  color: #60a5fa;
}

.insight-value.highlight {
  color: var(--color-primary);
  font-size: 12px;
}

/* TOP3 Toggle */
.top3-toggle {
  display: flex;
  gap: 6px;
  padding: var(--spacing-md) var(--spacing-md) 0;
}

.toggle-btn {
  flex: 1;
  text-align: center;
  padding: 7px;
  border-radius: var(--radius-md);
  font-size: 11.5px;
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}

.toggle-btn.buy {
  background: rgba(248, 113, 113, 0.1);
  color: #f87171;
  border-color: rgba(248, 113, 113, 0.15);
}

.toggle-btn.sell {
  background: rgba(96, 165, 250, 0.1);
  color: #60a5fa;
  border-color: rgba(96, 165, 250, 0.15);
}

.toggle-btn.buy.active {
  background: rgba(248, 113, 113, 0.2);
  border-color: rgba(248, 113, 113, 0.4);
  box-shadow: 0 0 12px rgba(248, 113, 113, 0.15);
}

.toggle-btn.sell.active {
  background: rgba(96, 165, 250, 0.2);
  border-color: rgba(96, 165, 250, 0.4);
  box-shadow: 0 0 12px rgba(96, 165, 250, 0.15);
}

/* TOP3 Panel */
.top3-panel {
  padding: var(--spacing-sm) var(--spacing-md) var(--spacing-md);
}

.stock-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 9px 0;
  border-bottom: 1px solid var(--color-border);
  transition: opacity 0.2s;
}

.stock-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.stock-row.empty {
  opacity: 0.3;
}

.rank-badge {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: var(--font-weight-bold);
  flex-shrink: 0;
  font-family: 'DM Mono', monospace;
}

.rank-badge.buy {
  background: rgba(248, 113, 113, 0.15);
  color: #f87171;
}

.rank-badge.sell {
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
}

.stock-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: var(--font-weight-bold);
  flex-shrink: 0;
}

.stock-info {
  flex: 1;
  min-width: 0;
}

.stock-name {
  font-size: 12.5px;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.stock-reason {
  font-size: 10px;
  color: var(--color-text-secondary);
  margin-top: 2px;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.stock-score {
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  flex-shrink: 0;
  font-family: 'DM Mono', monospace;
}

.stock-score.up { color: #f87171; }
.stock-score.dn { color: #60a5fa; }
.stock-score.yw { color: #fbbf24; }
.stock-score.nt { color: #2dd4bf; }
.stock-score.empty { color: var(--color-text-tertiary); }

/* Sentiment Block */
.sentiment-block {
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.sentiment-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sentiment-source {
  font-size: 9px;
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
}

.sentiment-main {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.sentiment-value {
  font-size: 28px;
  font-weight: var(--font-weight-bold);
  font-family: 'DM Mono', monospace;
  color: #f87171;
}

.sentiment-label {
  font-size: 11px;
  color: var(--color-text-secondary);
}

.sentiment-badge {
  font-size: 10px;
  background: rgba(52, 211, 153, 0.1);
  color: var(--color-stock-up);
  border: 1px solid rgba(52, 211, 153, 0.2);
  padding: 3px 10px;
  border-radius: 20px;
}

.sentiment-divider {
  height: 1px;
  background: var(--color-border);
  margin: 2px 0;
}

/* Distribution */
.distribution-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.distribution-header {
  font-size: 9px;
  color: var(--color-text-tertiary);
}

.distribution-bar {
  height: 6px;
  background: var(--color-bg-tertiary);
  border-radius: 3px;
  overflow: hidden;
  display: flex;
}

.bar-segment {
  height: 6px;
}

.bar-segment.positive {
  background: #f87171;
  border-radius: 3px 0 0 3px;
}

.bar-segment.neutral {
  background: #4a5568;
}

.bar-segment.negative {
  background: #60a5fa;
  border-radius: 0 3px 3px 0;
}

.distribution-labels {
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  font-family: 'DM Mono', monospace;
  gap: var(--spacing-xs);
}

.label-positive { color: #f87171; }
.label-neutral { color: var(--color-text-tertiary); }
.label-negative { color: #60a5fa; }

/* Collection Info */
.collection-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.info-item.align-right {
  text-align: right;
}

.info-label {
  font-size: 9px;
  color: var(--color-text-tertiary);
}

.info-value {
  font-size: 11px;
  color: var(--color-text-secondary);
}

.bottom-spacer {
  height: var(--bottom-nav-height);
}
</style>
