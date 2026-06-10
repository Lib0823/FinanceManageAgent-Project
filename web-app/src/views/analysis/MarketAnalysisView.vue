<script setup>
import { ref, computed, onMounted } from 'vue'
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

// KOSPI 정보
const kospiInfo = ref({
  index: null,
  change_rate: null,
  volume: null
})

// 시장 수급 정보 (합계)
const supplyDemand = ref({
  foreign_net_buy: null,
  institutional_net_buy: null
})

// 30종목 히트맵 통계
const heatmapStats = ref({
  totalStocks: 30,
  buyCandidate: 0,
  sellCandidate: 0,
  neutral: 0
})

// 히트맵 상세 데이터 (백엔드에서 scaler_score DESC 정렬됨)
const heatmapData = ref([])

// 백엔드가 제공하는 summary (옵셔널)
const heatmapSummary = ref(null)

// 클라이언트에서 계산한 인사이트 (summary fallback)
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

// 시장 전반 감성분석 데이터 (snake_case 통일)
const marketSentiment = ref({
  score: 0,
  label: '중립',
  distribution: {
    positive: { count: 0, percent: 0, color: '#f87171' },
    neutral: { count: 0, percent: 0, color: '#4a5568' },
    negative: { count: 0, percent: 0, color: '#60a5fa' }
  },
  time_range: '전날 18:00 — 당일 08:50',
  sources: '한경 · 매경 · 연합'
})

// Top 10 종목 (실제 히트맵 매트릭스 표시용)
const topHeatmapStocks = computed(() => heatmapData.value.slice(0, 10))

// 히트맵 매트릭스의 피처 컬럼 정의
const heatmapFeatures = [
  { key: 'foreign_net_buy', label: '외국인', format: 'money' },
  { key: 'institutional_net_buy', label: '기관', format: 'money' },
  { key: 'sentiment_score', label: '감성', format: 'decimal' },
  { key: 'price_trend', label: '추세', format: 'percent' },
  { key: 'vol_avg_multiple', label: '거래량', format: 'multiple' }
]

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
    const dateObj = new Date(latestDate + 'T00:00:00')
    analysisDateStr.value = `${dateObj.getFullYear()}.${String(dateObj.getMonth() + 1).padStart(2, '0')}.${String(dateObj.getDate()).padStart(2, '0')}`

    // 2. Fetch all market data in parallel using the latest date
    const [summaryResponse, sentimentResponse, decisionsResponse, heatmapResponse] = await Promise.all([
      marketAnalysisApi.getSummary(latestDate),
      marketAnalysisApi.getSentiment(latestDate),
      marketAnalysisApi.getDecisions(latestDate),
      marketAnalysisApi.getHeatmap(latestDate)
    ])

    // Process summary data (KOSPI + statistics + supply_demand)
    if (summaryResponse && summaryResponse.data) {
      const summary = summaryResponse.data

      // KOSPI 정보
      if (summary.kospi) {
        kospiInfo.value = {
          index: summary.kospi.index ?? null,
          change_rate: summary.kospi.change_rate ?? null,
          volume: summary.kospi.volume ?? null
        }
      }

      // 통계 정보
      if (summary.statistics) {
        heatmapStats.value = {
          totalStocks: summary.statistics.total ?? 30,
          buyCandidate: summary.statistics.buy_candidate ?? 0,
          sellCandidate: summary.statistics.sell_candidate ?? 0,
          neutral: summary.statistics.neutral ?? 0
        }
      }

      // 수급 정보
      if (summary.supply_demand) {
        supplyDemand.value = {
          foreign_net_buy: summary.supply_demand.foreign_net_buy ?? null,
          institutional_net_buy: summary.supply_demand.institutional_net_buy ?? null
        }
      }
    } else {
      console.warn('Market summary data is empty for date:', latestDate)
    }

    // Process heatmap data
    if (heatmapResponse && heatmapResponse.data && heatmapResponse.data.stocks) {
      const stocks = heatmapResponse.data.stocks
      heatmapData.value = stocks

      // 백엔드 summary 활용 (옵셔널)
      heatmapSummary.value = heatmapResponse.data.summary || null

      // Calculate insights (fallback when summary missing)
      if (stocks.length > 0) {
        const totalForeignNetBuy = stocks.reduce((sum, s) => sum + (s.foreign_net_buy || 0), 0)
        const totalInstitutionalNetBuy = stocks.reduce((sum, s) => sum + (s.institutional_net_buy || 0), 0)
        const totalSentiment = stocks.reduce((sum, s) => sum + (s.sentiment_score || 0), 0)

        heatmapInsights.value.avgForeignNetBuy = Math.round(totalForeignNetBuy / stocks.length)
        heatmapInsights.value.avgInstitutionalNetBuy = Math.round(totalInstitutionalNetBuy / stocks.length)
        heatmapInsights.value.avgSentiment = Number((totalSentiment / stocks.length).toFixed(2))

        // Find top stock by combined positive factors
        let topStock = stocks[0]
        let maxScore = 0

        stocks.forEach(stock => {
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

    // Process sentiment data (snake_case preserved as-is)
    if (sentimentResponse && sentimentResponse.data) {
      const sentiment = sentimentResponse.data
      marketSentiment.value = {
        score: sentiment.score ?? 0,
        label: sentiment.label ?? '중립',
        distribution: sentiment.distribution ?? marketSentiment.value.distribution,
        time_range: sentiment.time_range ?? '전날 18:00 — 당일 08:50',
        sources: sentiment.sources ?? '한경 · 매경 · 연합'
      }
    }

    // Process decisions data
    if (decisionsResponse && decisionsResponse.data) {
      const decisions = decisionsResponse.data

      const hasBuyData = (decisions.buy_top3 || []).some(s => s.stock_code !== null)
      const hasSellData = (decisions.sell_top3 || []).some(s => s.stock_code !== null)

      if (!hasBuyData && !hasSellData) {
        console.warn('AI trade decisions are empty for date:', latestDate)
      }

      buyTop3.value = (decisions.buy_top3 || []).map(stock => ({
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

      sellTop3.value = (decisions.sell_top3 || []).map(stock => ({
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
  if (num === null || num === undefined) return '—'
  if (num === 0) return '0'
  const absNum = Math.abs(num)
  if (absNum >= 100000000) {
    return `${(num / 100000000).toFixed(1)}억`
  } else if (absNum >= 10000) {
    return `${(num / 10000).toFixed(1)}만`
  }
  return num.toLocaleString()
}

const formatKospiIndex = (value) => {
  if (!Number.isFinite(value)) return '—'
  return value.toLocaleString('ko-KR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

const formatVolume = (value) => {
  if (value === null || value === undefined) return '—'
  const absNum = Math.abs(value)
  if (absNum >= 100000000) {
    return `${(value / 100000000).toFixed(1)}억`
  } else if (absNum >= 10000) {
    return `${(value / 10000).toFixed(1)}만`
  }
  return value.toLocaleString()
}

// 히트맵 셀 색상 계산
const getFeatureColor = (value, feature) => {
  if (value === null || value === undefined || isNaN(value)) {
    return 'rgba(128,128,128,0.1)'
  }

  let normalized
  if (feature === 'foreign_net_buy' || feature === 'institutional_net_buy') {
    normalized = Math.tanh(value / 100000000)
  } else if (feature === 'sentiment_score') {
    normalized = Math.max(-1, Math.min(1, value))
  } else if (feature === 'price_trend' || feature === 'volume_trend') {
    normalized = Math.tanh(value * 10)
  } else if (feature === 'vol_avg_multiple') {
    normalized = Math.tanh((value - 1) * 2)
  } else if (feature === 'morning_return') {
    normalized = Math.tanh(value / 3)
  } else {
    normalized = 0
  }

  const intensity = Math.min(Math.abs(normalized), 1) * 0.7 + 0.1
  if (normalized > 0) {
    return `rgba(248, 113, 113, ${intensity})`
  }
  return `rgba(96, 165, 250, ${intensity})`
}

// 히트맵 셀 표시 텍스트 포맷
const formatCellValue = (value, format) => {
  if (value === null || value === undefined || isNaN(value)) return '—'

  if (format === 'money') {
    const absNum = Math.abs(value)
    if (absNum >= 100000000) {
      return `${value > 0 ? '+' : ''}${(value / 100000000).toFixed(1)}억`
    } else if (absNum >= 10000) {
      return `${value > 0 ? '+' : ''}${(value / 10000).toFixed(0)}만`
    }
    return value.toLocaleString()
  } else if (format === 'decimal') {
    return value.toFixed(2)
  } else if (format === 'percent') {
    return `${value > 0 ? '+' : ''}${(value * 100).toFixed(1)}%`
  } else if (format === 'multiple') {
    return `${value.toFixed(2)}x`
  }
  return String(value)
}

// 표시용 인사이트 (백엔드 summary 우선, fallback은 클라이언트 계산)
const displayInsights = computed(() => {
  if (heatmapSummary.value) {
    return {
      avgForeignNetBuy: heatmapSummary.value.avg_foreign_net_buy ?? 0,
      avgInstitutionalNetBuy: heatmapSummary.value.avg_institutional_net_buy ?? 0,
      avgSentiment: Number((heatmapSummary.value.avg_sentiment_score ?? 0).toFixed(2)),
      positiveSentimentCount: heatmapSummary.value.positive_sentiment_count ?? null,
      negativeSentimentCount: heatmapSummary.value.negative_sentiment_count ?? null,
      positiveTrendCount: heatmapSummary.value.positive_trend_count ?? null,
      topStock: {
        name: heatmapSummary.value.top_stock?.stock_name ?? '',
        score: heatmapSummary.value.top_stock?.positive_features ?? 0
      },
      source: 'backend'
    }
  }
  return {
    avgForeignNetBuy: heatmapInsights.value.avgForeignNetBuy,
    avgInstitutionalNetBuy: heatmapInsights.value.avgInstitutionalNetBuy,
    avgSentiment: heatmapInsights.value.avgSentiment,
    positiveSentimentCount: null,
    negativeSentimentCount: null,
    positiveTrendCount: null,
    topStock: heatmapInsights.value.topStock,
    source: 'client'
  }
})

const hasHeatmapData = computed(() => heatmapData.value.length > 0)

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

    <!-- 로딩 / 에러 / 빈 데이터 처리 -->
    <div v-if="loading" class="state-wrapper">
      <div class="state-message">분석 데이터를 불러오는 중...</div>
    </div>

    <div v-else-if="error" class="state-wrapper">
      <div class="state-message error">{{ error }}</div>
    </div>

    <div v-else class="content">
      <!-- ⓘ KOSPI 시장 개요 -->
      <div class="analysis-section">
        <div class="section-label">KOSPI 시장 개요</div>
        <div class="section-card">
          <div class="kospi-block">
            <div class="kospi-main">
              <div class="kospi-label">KOSPI 지수</div>
              <div class="kospi-value">{{ formatKospiIndex(kospiInfo.index) }}</div>
              <div
                v-if="Number.isFinite(kospiInfo.change_rate)"
                :class="['kospi-change', kospiInfo.change_rate >= 0 ? 'up' : 'dn']"
              >
                {{ kospiInfo.change_rate > 0 ? '+' : '' }}{{ kospiInfo.change_rate.toFixed(2) }}%
              </div>
            </div>

            <div class="kospi-side">
              <div class="kospi-side-row">
                <span class="side-label">거래량</span>
                <span class="side-value">{{ formatVolume(kospiInfo.volume) }}</span>
              </div>
              <div class="kospi-side-row">
                <span class="side-label">외국인 순매수</span>
                <span
                  :class="['side-value', supplyDemand.foreign_net_buy === null ? '' : supplyDemand.foreign_net_buy >= 0 ? 'up' : 'dn']"
                >
                  {{ supplyDemand.foreign_net_buy === null ? '—' : (supplyDemand.foreign_net_buy > 0 ? '+' : '') + formatNumber(supplyDemand.foreign_net_buy) + '원' }}
                </span>
              </div>
              <div class="kospi-side-row">
                <span class="side-label">기관 순매수</span>
                <span
                  :class="['side-value', supplyDemand.institutional_net_buy === null ? '' : supplyDemand.institutional_net_buy >= 0 ? 'up' : 'dn']"
                >
                  {{ supplyDemand.institutional_net_buy === null ? '—' : (supplyDemand.institutional_net_buy > 0 ? '+' : '') + formatNumber(supplyDemand.institutional_net_buy) + '원' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ① 30종목 피처 히트맵 -->
      <div class="analysis-section">
        <div class="section-label">30종목 피처 히트맵</div>
        <div class="section-card">
          <div v-if="!hasHeatmapData" class="empty-block">
            분석 데이터가 없습니다
          </div>

          <template v-else>
            <!-- 실제 히트맵 매트릭스 (Top 10 × 5 피처) -->
            <div class="heatmap-section">
              <div class="heatmap-header-bar">
                <span class="heatmap-title">상위 10종목 × 5개 피처</span>
                <span class="heatmap-legend">
                  <span class="legend-chip up"></span> 양호
                  <span class="legend-chip dn"></span> 부진
                </span>
              </div>

              <div class="heatmap-matrix">
                <!-- Header row -->
                <div class="heatmap-header">종목</div>
                <div
                  v-for="feature in heatmapFeatures"
                  :key="feature.key"
                  class="heatmap-header"
                >
                  {{ feature.label }}
                </div>

                <!-- Stock rows -->
                <template v-for="stock in topHeatmapStocks" :key="stock.stock_code">
                  <div class="heatmap-stock-name" :title="stock.stock_name">
                    {{ stock.stock_name }}
                  </div>
                  <div
                    v-for="feature in heatmapFeatures"
                    :key="`${stock.stock_code}-${feature.key}`"
                    class="heatmap-cell"
                    :style="{ background: getFeatureColor(stock[feature.key], feature.key) }"
                  >
                    {{ formatCellValue(stock[feature.key], feature.format) }}
                  </div>
                </template>
              </div>
            </div>
          </template>

          <!-- 통계 그리드 -->
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

          <!-- 인사이트 (백엔드 summary 또는 클라이언트 계산) -->
          <div class="insights-section">
            <div class="insight-row">
              <span class="insight-label">평균 외국인 순매수</span>
              <span :class="['insight-value', displayInsights.avgForeignNetBuy > 0 ? 'up' : displayInsights.avgForeignNetBuy < 0 ? 'dn' : '']">
                {{ displayInsights.avgForeignNetBuy > 0 ? '+' : '' }}{{ formatNumber(displayInsights.avgForeignNetBuy) }}원
              </span>
            </div>
            <div class="insight-row">
              <span class="insight-label">평균 기관 순매수</span>
              <span :class="['insight-value', displayInsights.avgInstitutionalNetBuy > 0 ? 'up' : displayInsights.avgInstitutionalNetBuy < 0 ? 'dn' : '']">
                {{ displayInsights.avgInstitutionalNetBuy > 0 ? '+' : '' }}{{ formatNumber(displayInsights.avgInstitutionalNetBuy) }}원
              </span>
            </div>
            <div class="insight-row">
              <span class="insight-label">평균 감성 점수</span>
              <span :class="['insight-value', displayInsights.avgSentiment > 0 ? 'up' : displayInsights.avgSentiment < 0 ? 'dn' : '']">
                {{ displayInsights.avgSentiment > 0 ? '+' : '' }}{{ displayInsights.avgSentiment }}
              </span>
            </div>
            <div
              v-if="displayInsights.positiveSentimentCount !== null"
              class="insight-row"
            >
              <span class="insight-label">긍정/부정 감성 종목</span>
              <span class="insight-value">
                <span class="up">{{ displayInsights.positiveSentimentCount }}</span>
                /
                <span class="dn">{{ displayInsights.negativeSentimentCount }}</span>
              </span>
            </div>
            <div
              v-if="displayInsights.positiveTrendCount !== null"
              class="insight-row"
            >
              <span class="insight-label">상승 추세 종목</span>
              <span class="insight-value up">{{ displayInsights.positiveTrendCount }}개</span>
            </div>
            <div class="insight-row highlight">
              <span class="insight-label">최고 점수 종목</span>
              <span class="insight-value highlight">
                {{ displayInsights.topStock.name || '분석중' }}
                <span v-if="displayInsights.topStock.score" class="highlight-score">
                  ({{ displayInsights.topStock.score }}/5)
                </span>
              </span>
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
              :class="['stock-row', { empty: stock.isEmpty }]"
            >
              <div class="rank-badge buy">{{ stock.rank ?? '—' }}</div>
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
                {{ stock.score !== null && stock.score !== undefined ? stock.score : '—' }}
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
              <div class="rank-badge sell">{{ stock.rank ?? '—' }}</div>
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
                {{ stock.score !== null && stock.score !== undefined ? stock.score : '—' }}
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
                <div class="info-value">{{ marketSentiment.time_range }}</div>
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

/* State Wrapper */
.state-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: var(--spacing-lg);
}

.state-message {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.state-message.error {
  color: #f87171;
}

.empty-block {
  padding: 40px 16px;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 12px;
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

/* KOSPI Block */
.kospi-block {
  padding: var(--spacing-md);
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: var(--spacing-md);
  align-items: center;
}

.kospi-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kospi-label {
  font-size: 9.5px;
  color: var(--color-text-tertiary);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.kospi-value {
  font-size: 26px;
  font-weight: var(--font-weight-bold);
  font-family: 'DM Mono', monospace;
  color: var(--color-text-primary);
  line-height: 1.1;
  margin-top: 4px;
}

.kospi-change {
  font-size: 12px;
  font-weight: var(--font-weight-semibold);
  font-family: 'DM Mono', monospace;
  margin-top: 2px;
}

.kospi-change.up { color: #f87171; }
.kospi-change.dn { color: #60a5fa; }

.kospi-side {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: var(--spacing-md);
  border-left: 1px solid var(--color-border);
}

.kospi-side-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
}

.side-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
}

.side-value {
  font-size: 11px;
  font-weight: var(--font-weight-semibold);
  font-family: 'DM Mono', monospace;
  color: var(--color-text-primary);
}

.side-value.up { color: #f87171; }
.side-value.dn { color: #60a5fa; }

/* Heatmap Section */
.heatmap-section {
  padding: var(--spacing-md);
}

.heatmap-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.heatmap-title {
  font-size: 10.5px;
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-semibold);
}

.heatmap-legend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 9px;
  color: var(--color-text-tertiary);
  font-family: 'DM Mono', monospace;
}

.legend-chip {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  margin-left: 4px;
}

.legend-chip.up { background: rgba(248, 113, 113, 0.65); }
.legend-chip.dn { background: rgba(96, 165, 250, 0.65); }

.heatmap-matrix {
  display: grid;
  grid-template-columns: 70px repeat(5, 1fr);
  gap: 2px;
  font-size: 9px;
}

.heatmap-cell {
  padding: 6px 4px;
  text-align: center;
  border-radius: 3px;
  font-family: 'DM Mono', monospace;
  font-size: 9px;
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  min-height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.heatmap-header {
  font-weight: 600;
  color: var(--color-text-tertiary);
  padding: 4px 2px;
  font-size: 9.5px;
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.heatmap-stock-name {
  font-size: 10px;
  font-weight: 500;
  padding: 4px 2px;
  text-align: left;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  padding: 0 var(--spacing-md) var(--spacing-sm);
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

.highlight-score {
  font-size: 10px;
  color: var(--color-text-tertiary);
  margin-left: 4px;
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
