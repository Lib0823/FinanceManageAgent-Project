<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/common/AppHeader.vue'
import { mockCompanyInfo } from '@/services/mockData'

const route = useRoute()
const router = useRouter()

const activeTab = ref('ai')
const aiSubTab = ref('quant')
const company = ref(mockCompanyInfo)
const isFavorite = ref(false)

const toggleFavorite = () => {
  isFavorite.value = !isFavorite.value
}

const tabs = [
  { key: 'ai', label: 'AI분석' },
  { key: 'basic', label: '기본정보' },
  { key: 'financial', label: '재무제표' },
  { key: 'disclosure', label: '공시정보' }
]

const aiSubTabs = [
  { key: 'quant', label: '정량분석' },
  { key: 'sentiment', label: '감성분석' },
  { key: 'timeseries', label: '시계열' }
]

const aiAnalysis = ref({
  score: 92,
  rating: 'A+',
  recommendation: '매수',
  reasons: [
    '높은 성장 잠재력과 안정적인 수익 구조',
    '업계 평균 대비 우수한 재무 지표',
    '최근 3개월 긍정적인 시장 반응'
  ],
  strengths: [
    { title: '재무 안정성', score: 95 },
    { title: '성장성', score: 88 },
    { title: '수익성', score: 93 }
  ],
  warnings: [
    '단기 변동성 주의',
    '글로벌 경기 둔화 영향 가능성'
  ]
})

const financialData = ref({
  annual: [
    { year: '2024', revenue: 302840, operatingProfit: 45680, netProfit: 35920, eps: 4850 },
    { year: '2023', revenue: 280150, operatingProfit: 42300, netProfit: 32100, eps: 4320 },
    { year: '2022', revenue: 265800, operatingProfit: 38900, netProfit: 29500, eps: 3980 }
  ],
  ratios: [
    { label: 'ROE', value: 18.5, unit: '%', good: true },
    { label: 'ROA', value: 12.3, unit: '%', good: true },
    { label: 'PER', value: 15.2, unit: '배', good: true },
    { label: 'PBR', value: 2.8, unit: '배', good: true },
    { label: '부채비율', value: 45.6, unit: '%', good: true },
    { label: '유동비율', value: 185.3, unit: '%', good: true }
  ]
})

const disclosures = ref([
  {
    id: 1,
    type: '공정공시',
    title: '2024년 4분기 실적발표 (잠정)',
    date: '2025-01-15',
    important: true
  },
  {
    id: 2,
    type: '주요사항보고',
    title: '자기주식 취득 결정',
    date: '2025-01-10',
    important: false
  },
  {
    id: 3,
    type: '정기공시',
    title: '분기보고서 (2024.09)',
    date: '2024-11-14',
    important: false
  },
  {
    id: 4,
    type: '공정공시',
    title: '신규 사업 진출 계획',
    date: '2024-11-05',
    important: true
  },
  {
    id: 5,
    type: '주요사항보고',
    title: '배당 결정',
    date: '2024-10-28',
    important: false
  },
  {
    id: 6,
    type: '공정공시',
    title: '대규모 설비투자 계획',
    date: '2024-10-15',
    important: true
  }
])

// AI 분석 데이터
const quantAnalysis = ref({
  stats: [
    { label: '외국인\n순매수', value: '+2,840억', class: 'up' },
    { label: '기관\n순매수', value: '+620억', class: 'up' },
    { label: '거래량\n배율', value: '3.2x', class: 'yw' },
    { label: '종가\n위치', value: '0.74', class: 'nt' }
  ],
  kisFeatures: [
    { label: '외국인 순매수', source: 'KIS 수급', value: '+2,840억', percent: 88, class: 'up' },
    { label: '기관 순매수', source: 'KIS 수급', value: '+620억', percent: 42, class: 'yw' },
    { label: '장초반 수익률', source: 'KIS 가격', value: '+0.82%', percent: 60, class: 'nt' },
    { label: '종가 위치', source: 'KIS 가격', value: '0.74', percent: 74, class: 'purple' }
  ],
  dartMetrics: [
    { label: 'PER', value: '38.7', class: 'up' },
    { label: 'ROE (%)', value: '18.5%', class: 'nt' },
    { label: '영업이익률', value: '19.8%', class: 'yw' }
  ]
})

const sentimentAnalysis = ref({
  stockSentiment: { score: 0.44, label: '긍정', newsCount: 5 },
  marketSentiment: { score: 0.28, label: '긍정 우세', newsCount: 24 },
  difference: 0.16,
  stockNewsRange: '전날 18:00 — 당일 08:50',
  marketDistribution: { positive: 57, neutral: 30, negative: 13 },
  marketSources: '한경 · 매경 · 연합뉴스'
})

const timeseriesAnalysis = ref({
  stats: [
    { label: 'price\ntrend', value: '+0.31', class: 'up' },
    { label: 'volume\ntrend', value: '+0.18', class: 'up' },
    { label: 'uncertainty', value: '2.4%', class: 'yw' },
    { label: '학습\n거래일', value: '120일', class: 'nt' }
  ],
  features: [
    { label: '가격 추세', source: 'price_trend', value: '+0.31', percent: 62, class: 'up' },
    { label: '거래량 추세', source: 'vol_trend', value: '+0.18', percent: 36, class: 'yw' },
    { label: '예측 불확실성', source: 'uncertainty', value: '2.4%', percent: 24, class: 'nt' }
  ],
  forecasts: [
    { day: 'D+1', yhat: '178,200', upper: '181,400', lower: '175,100', uncertainty: '1.8%' },
    { day: 'D+2', yhat: '179,800', upper: '184,200', lower: '175,500', uncertainty: '2.1%' },
    { day: 'D+3', yhat: '181,400', upper: '187,800', lower: '175,200', uncertainty: '2.8%' },
    { day: 'D+4', yhat: '182,900', upper: '190,400', lower: '175,600', uncertainty: '2.7%' },
    { day: 'D+5', yhat: '184,500', upper: '193,200', lower: '176,000', uncertainty: '2.9%' }
  ]
})

const formatNumber = (num) => {
  return new Intl.NumberFormat('ko-KR').format(num)
}

const goToNews = () => {
  router.push(`/news?symbol=${company.value.symbol}`)
}

const goToTrade = () => {
  router.push(`/trading/${company.value.symbol}`)
}

onMounted(() => {
  // Fetch company data based on route.params.symbol

  // Check if AI analysis tab should be shown
  if (route.query.showAiAnalysis === 'true') {
    activeTab.value = 'ai'
    // Remove query parameter from URL
    router.replace({ query: {} })
  }
})
</script>

<template>
  <div class="company-detail-screen">
    <AppHeader title="기업 상세 정보" showBack />

    <div class="content">
      <!-- Company Header -->
      <div class="company-header">
        <div class="company-logo">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <line x1="9" y1="9" x2="15" y2="9"/>
            <line x1="9" y1="15" x2="15" y2="15"/>
          </svg>
        </div>
        <div class="company-info">
          <span class="company-name">{{ company.name }}</span>
          <span class="company-symbol">{{ company.symbol }}</span>
        </div>
        <button class="favorite-btn" @click="toggleFavorite">
          <van-icon
            :name="isFavorite ? 'star' : 'star-o'"
            :color="isFavorite ? '#F59E0B' : '#9CA3AF'"
            size="24"
          />
        </button>
      </div>

      <!-- Sub Tabs -->
      <div class="sub-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['sub-tab', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- Basic Info Tab -->
      <div v-if="activeTab === 'basic'" class="tab-content">
        <!-- Score Gauges -->
        <div class="score-grid">
          <div v-for="(score, key) in company.scores" :key="key" class="score-item">
            <div class="gauge">
              <svg viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="45" fill="none" stroke="#E5E7EB" stroke-width="8"/>
                <circle
                  cx="50" cy="50" r="45"
                  fill="none"
                  stroke="#F59E0B"
                  stroke-width="8"
                  :stroke-dasharray="`${score * 2.83} 283`"
                  transform="rotate(-90 50 50)"
                />
              </svg>
              <span class="gauge-label">{{ key.toUpperCase() }}</span>
              <span class="gauge-value">{{ score }}</span>
            </div>
          </div>
        </div>

        <!-- Company Info Card -->
        <div class="info-card">
          <div class="info-row">
            <span class="info-label">기업명</span>
            <span class="info-value">{{ company.nameEn }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">주소</span>
            <span class="info-value">{{ company.address }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">홈페이지</span>
            <a class="info-value link" :href="company.website" target="_blank">{{ company.website }}</a>
          </div>
          <div class="info-row">
            <span class="info-label">섹터</span>
            <span class="info-value">{{ company.sector }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">직원수</span>
            <span class="info-value">{{ formatNumber(company.employees) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">주식수</span>
            <span class="info-value">{{ formatNumber(company.shares) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">재무통화</span>
            <span class="info-value">{{ company.currency }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">시가총액</span>
            <span class="info-value">{{ formatNumber(company.marketCap) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">배당</span>
            <span class="info-value">{{ company.dividend }}</span>
          </div>
          <div class="info-row full">
            <span class="info-label">개요</span>
            <p class="info-desc">{{ company.description }}</p>
          </div>
        </div>
      </div>

      <!-- AI Analysis Tab -->
      <div v-else-if="activeTab === 'ai'" class="tab-content">
        <!-- AI Sub Tabs -->
        <div class="ai-sub-tabs">
          <button
            v-for="subTab in aiSubTabs"
            :key="subTab.key"
            :class="['ai-sub-tab', { active: aiSubTab === subTab.key }]"
            @click="aiSubTab = subTab.key"
          >
            {{ subTab.label }}
          </button>
        </div>

        <!-- 정량분석 -->
        <div v-if="aiSubTab === 'quant'" class="ai-tab-sections">
          <!-- KIS·DART 피처 분포 차트 -->
          <div class="ai-section">
            <div class="section-label">KIS · DART 피처 분포</div>
            <div class="analysis-card">
              <div class="chart-wrapper">
                <div class="chart-placeholder">
                  <svg width="100%" height="170" viewBox="0 0 100 50" preserveAspectRatio="none">
                    <rect x="0" y="30" width="20" height="20" fill="#F87171" opacity="0.3"/>
                    <rect x="25" y="20" width="20" height="30" fill="#60A5FA" opacity="0.3"/>
                    <rect x="50" y="15" width="20" height="35" fill="#34D399" opacity="0.3"/>
                    <rect x="75" y="25" width="20" height="25" fill="#FBBF24" opacity="0.3"/>
                  </svg>
                  <div class="chart-badge">KIS 4개 + DART 3개 피처</div>
                </div>
                <div class="stat-row">
                  <div v-for="(stat, idx) in quantAnalysis.stats" :key="idx" class="stat-item">
                    <div class="stat-label" v-html="stat.label.replace('\n', '<br>')"></div>
                    <div class="stat-value" :class="stat.class">{{ stat.value }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- KIS 피처 상세 -->
          <div class="ai-section">
            <div class="section-label">KIS 피처 상세</div>
            <div class="analysis-card">
              <div class="feature-list">
                <div v-for="(feature, idx) in quantAnalysis.kisFeatures" :key="idx" class="feature-row">
                  <div class="feature-label">{{ feature.label }}</div>
                  <div class="feature-source">{{ feature.source }}</div>
                  <div class="feature-bar-wrap">
                    <div class="feature-bar-track">
                      <div
                        class="feature-bar-fill"
                        :class="feature.class"
                        :style="{ width: `${feature.percent}%` }"
                      ></div>
                    </div>
                  </div>
                  <div class="feature-value" :class="feature.class">{{ feature.value }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- DART 재무지표 -->
          <div class="ai-section">
            <div class="section-label">DART 재무지표</div>
            <div class="analysis-card">
              <div class="card-sublabel">분기 기준 · DART API 공시 데이터</div>
              <div class="metrics-list">
                <div v-for="(metric, idx) in quantAnalysis.dartMetrics" :key="idx" class="metrics-row">
                  <div class="metrics-label">{{ metric.label }}</div>
                  <div class="metrics-value" :class="metric.class">{{ metric.value }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 감성분석 -->
        <div v-else-if="aiSubTab === 'sentiment'" class="ai-tab-sections">
          <!-- 감성점수 비교 -->
          <div class="ai-section">
            <div class="section-label">감성점수 비교</div>
            <div class="analysis-card">
              <div class="sentiment-compare">
                <div class="sentiment-box">
                  <div class="sentiment-header">종목 감성</div>
                  <div class="sentiment-meta">네이버금융 · {{ sentimentAnalysis.stockSentiment.newsCount }}건</div>
                  <div class="sentiment-score up">{{ sentimentAnalysis.stockSentiment.score > 0 ? '+' : '' }}{{ sentimentAnalysis.stockSentiment.score }}</div>
                  <div class="sentiment-badge positive">{{ sentimentAnalysis.stockSentiment.label }}</div>
                  <div class="sentiment-footer">시간 가중 평균</div>
                </div>
                <div class="sentiment-box">
                  <div class="sentiment-header">시장 전반</div>
                  <div class="sentiment-meta">RSS 피드 · 3개 출처</div>
                  <div class="sentiment-score up">{{ sentimentAnalysis.marketSentiment.score > 0 ? '+' : '' }}{{ sentimentAnalysis.marketSentiment.score }}</div>
                  <div class="sentiment-badge positive">{{ sentimentAnalysis.marketSentiment.label }}</div>
                  <div class="sentiment-footer">시간 가중 평균</div>
                </div>
              </div>
              <div class="sentiment-diff">
                <div class="diff-label">종목 − 시장 전반</div>
                <div class="diff-value">+{{ sentimentAnalysis.difference }} ↑</div>
              </div>
              <div class="diff-desc">시장 평균 대비 긍정 신호 우위</div>
            </div>
          </div>

          <!-- 종목 감성 상세 -->
          <div class="ai-section">
            <div class="section-label">종목 감성 상세</div>
            <div class="analysis-card">
              <div class="card-sublabel">stock_code = 000660 · news_analysis 테이블</div>

              <!-- 감성 척도 바 -->
              <div class="sentiment-scale">
                <div class="scale-labels">
                  <span>-1.0 부정</span>
                  <span>0 중립</span>
                  <span>긍정 +1.0</span>
                </div>
                <div class="scale-bar">
                  <div
                    class="market-marker"
                    :style="{ left: `calc(50% + ${sentimentAnalysis.marketSentiment.score / 2 * 100}%)` }"
                  ></div>
                  <div
                    class="stock-marker"
                    :style="{ left: `calc(50% + ${sentimentAnalysis.stockSentiment.score / 2 * 100}%)` }"
                  ></div>
                </div>
                <div class="scale-legend">
                  <span class="market-legend">▲ 시장 +{{ sentimentAnalysis.marketSentiment.score }}</span>
                  <span class="stock-legend">● 종목 +{{ sentimentAnalysis.stockSentiment.score }}</span>
                </div>
              </div>

              <!-- 수집 메타 -->
              <div class="meta-grid">
                <div class="meta-box">
                  <div class="meta-label">수집 뉴스</div>
                  <div class="meta-value">{{ sentimentAnalysis.stockSentiment.newsCount }}건</div>
                </div>
                <div class="meta-box">
                  <div class="meta-label">수집 범위</div>
                  <div class="meta-value-multi">{{ sentimentAnalysis.stockNewsRange }}</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 시장 전반 감성 상세 -->
          <div class="ai-section">
            <div class="section-label">시장 전반 감성 상세</div>
            <div class="analysis-card">
              <div class="card-sublabel">stock_code = NULL · RSS 피드 · {{ sentimentAnalysis.marketSources }}</div>

              <!-- 긍정/중립/부정 분포 바 -->
              <div class="distribution-section">
                <div class="distribution-label">코스피 100 기준 종목 분포</div>
                <div class="distribution-bar">
                  <div class="dist-positive" :style="{ flex: sentimentAnalysis.marketDistribution.positive }"></div>
                  <div class="dist-neutral" :style="{ flex: sentimentAnalysis.marketDistribution.neutral }"></div>
                  <div class="dist-negative" :style="{ flex: sentimentAnalysis.marketDistribution.negative }"></div>
                </div>
                <div class="distribution-legend">
                  <span class="legend-positive">긍정 17개 ({{ sentimentAnalysis.marketDistribution.positive }}%)</span>
                  <span class="legend-neutral">중립 9개 ({{ sentimentAnalysis.marketDistribution.neutral }}%)</span>
                  <span class="legend-negative">부정 4개 ({{ sentimentAnalysis.marketDistribution.negative }}%)</span>
                </div>
              </div>

              <!-- 수집 메타 -->
              <div class="meta-grid">
                <div class="meta-box">
                  <div class="meta-label">분석 뉴스</div>
                  <div class="meta-value">{{ sentimentAnalysis.marketSentiment.newsCount }}건</div>
                </div>
                <div class="meta-box">
                  <div class="meta-label">출처</div>
                  <div class="meta-value-multi">{{ sentimentAnalysis.marketSources }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 시계열 -->
        <div v-else-if="aiSubTab === 'timeseries'" class="ai-tab-sections">
          <!-- Prophet 예측 차트 -->
          <div class="ai-section">
            <div class="section-label">Prophet D+1~D+5 가격 예측</div>
            <div class="analysis-card">
              <div class="chart-wrapper">
                <div class="chart-placeholder">
                  <svg width="100%" height="170" viewBox="0 0 100 50" preserveAspectRatio="none">
                    <polyline
                      points="0,40 20,35 40,30 60,25 80,20 100,15"
                      fill="none"
                      stroke="#60A5FA"
                      stroke-width="0.5"
                      opacity="0.5"
                    />
                    <polyline
                      points="0,30 20,28 40,26 60,24 80,22 100,20"
                      fill="none"
                      stroke="#F87171"
                      stroke-width="1"
                    />
                  </svg>
                  <div class="chart-badge">Prophet · 120거래일 기반 · 신뢰구간 포함</div>
                </div>
                <div class="stat-row">
                  <div v-for="(stat, idx) in timeseriesAnalysis.stats" :key="idx" class="stat-item">
                    <div class="stat-label" v-html="stat.label.replace('\n', '<br>')"></div>
                    <div class="stat-value" :class="stat.class">{{ stat.value }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 예측 피처 상세 -->
          <div class="ai-section">
            <div class="section-label">예측 피처 상세</div>
            <div class="analysis-card">
              <div class="card-sublabel">D+1~D+5 선형회귀 기울기 · Gemini 입력 피처</div>
              <div class="feature-list">
                <div v-for="(feature, idx) in timeseriesAnalysis.features" :key="idx" class="feature-row">
                  <div class="feature-label">{{ feature.label }}</div>
                  <div class="feature-source">{{ feature.source }}</div>
                  <div class="feature-bar-wrap">
                    <div class="feature-bar-track">
                      <div
                        class="feature-bar-fill"
                        :class="feature.class"
                        :style="{ width: `${feature.percent}%` }"
                      ></div>
                    </div>
                  </div>
                  <div class="feature-value" :class="feature.class">{{ feature.value }}</div>
                </div>
              </div>

              <!-- 방향 요약 -->
              <div class="trend-summary">
                <div class="trend-summary-label">종합 추세 판단</div>
                <div class="trend-cards">
                  <div class="trend-card">
                    <div class="trend-emoji">📈</div>
                    <div class="trend-label">가격</div>
                    <div class="trend-value up">상승</div>
                  </div>
                  <div class="trend-card">
                    <div class="trend-emoji">📈</div>
                    <div class="trend-label">거래량</div>
                    <div class="trend-value up">증가</div>
                  </div>
                  <div class="trend-card">
                    <div class="trend-emoji">🎯</div>
                    <div class="trend-label">신뢰도</div>
                    <div class="trend-value nt">양호</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 예측 구간 정보 -->
          <div class="ai-section">
            <div class="section-label">예측 구간 정보</div>
            <div class="analysis-card">
              <div class="card-sublabel">(yhat_upper − yhat_lower) / yhat 평균 · 값이 클수록 신뢰도 낮음</div>

              <!-- D+1~D+5 예측값 테이블 -->
              <div class="forecast-table">
                <div class="forecast-header">
                  <div class="forecast-cell">일자</div>
                  <div class="forecast-cell">yhat</div>
                  <div class="forecast-cell">yhat_upper</div>
                  <div class="forecast-cell">yhat_lower</div>
                  <div class="forecast-cell">불확실성</div>
                </div>
                <div v-for="(forecast, idx) in timeseriesAnalysis.forecasts" :key="idx" class="forecast-row">
                  <div class="forecast-cell day">{{ forecast.day }}</div>
                  <div class="forecast-cell">{{ forecast.yhat }}</div>
                  <div class="forecast-cell up">{{ forecast.upper }}</div>
                  <div class="forecast-cell dn">{{ forecast.lower }}</div>
                  <div class="forecast-cell nt">{{ forecast.uncertainty }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Financial Tab -->
      <div v-else-if="activeTab === 'financial'" class="tab-content">
        <div class="financial-content">
          <!-- Financial Ratios -->
          <div class="financial-section">
            <h4 class="section-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
              </svg>
              주요 재무비율
            </h4>
            <div class="ratios-grid">
              <div v-for="(ratio, index) in financialData.ratios" :key="index" class="ratio-card">
                <div class="ratio-label">{{ ratio.label }}</div>
                <div class="ratio-value" :class="{ good: ratio.good }">
                  {{ ratio.value }}{{ ratio.unit }}
                </div>
              </div>
            </div>
          </div>

          <!-- Annual Financial Data -->
          <div class="financial-section">
            <h4 class="section-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
              연간 실적 (단위: 억원)
            </h4>
            <div class="financial-table">
              <div class="table-header">
                <div class="table-cell">연도</div>
                <div class="table-cell">매출액</div>
                <div class="table-cell">영업이익</div>
                <div class="table-cell">순이익</div>
                <div class="table-cell">EPS</div>
              </div>
              <div v-for="data in financialData.annual" :key="data.year" class="table-row">
                <div class="table-cell year">{{ data.year }}</div>
                <div class="table-cell">{{ formatNumber(data.revenue) }}</div>
                <div class="table-cell">{{ formatNumber(data.operatingProfit) }}</div>
                <div class="table-cell">{{ formatNumber(data.netProfit) }}</div>
                <div class="table-cell">{{ formatNumber(data.eps) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Disclosure Tab -->
      <div v-else-if="activeTab === 'disclosure'" class="tab-content">
        <div class="disclosure-content">
          <div class="disclosure-section">
            <h4 class="section-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              최근 공시
            </h4>
            <div class="disclosure-list">
              <div
                v-for="disclosure in disclosures"
                :key="disclosure.id"
                class="disclosure-item"
                :class="{ important: disclosure.important }"
              >
                <div class="disclosure-header">
                  <span class="disclosure-type">{{ disclosure.type }}</span>
                  <span class="disclosure-date">{{ disclosure.date }}</span>
                </div>
                <div class="disclosure-title">
                  <svg v-if="disclosure.important" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" class="important-icon">
                    <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                  </svg>
                  {{ disclosure.title }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Other tabs placeholder -->
      <div v-else class="tab-content">
        <div class="empty-tab">
          <p>{{ tabs.find(t => t.key === activeTab)?.label }} 정보를 불러오는 중...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.company-detail-screen {
  min-height: 100vh;
  background: var(--color-bg-primary);
}

.content {
  padding: 0 var(--spacing-lg) var(--spacing-lg);
}

.company-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.company-logo {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.company-logo svg {
  color: var(--color-text-tertiary);
}

.company-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.company-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.company-symbol {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.sub-tabs {
  display: flex;
  gap: 0;
  margin-bottom: var(--spacing-xl);
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-lg);
  padding: 4px;
}

.sub-tab {
  flex: 1;
  padding: var(--spacing-sm) var(--spacing-xs);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.3s ease;
  font-weight: var(--font-weight-medium);
}

.sub-tab.active {
  background: var(--color-primary);
  color: var(--color-text-inverse);
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
}

.favorite-btn {
  background: none;
  border: none;
  padding: var(--spacing-xs);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.score-grid {
  display: flex;
  justify-content: space-around;
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-lg);
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.05) 0%, rgba(124, 58, 237, 0.05) 100%);
  border-radius: var(--radius-lg);
}

.score-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-xs);
}

.gauge {
  position: relative;
  width: 70px;
  height: 70px;
}

.gauge svg {
  width: 100%;
  height: 100%;
}

.gauge-label {
  position: absolute;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  color: var(--color-text-tertiary);
  font-weight: var(--font-weight-medium);
  text-transform: uppercase;
}

.gauge-value {
  position: absolute;
  bottom: 18px;
  left: 50%;
  transform: translateX(-50%);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.info-card {
  background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
  border-radius: var(--radius-xl);
  padding: var(--spacing-xl);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md) 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  gap: var(--spacing-md);
}

.info-row.full {
  flex-direction: column;
  align-items: flex-start;
  gap: var(--spacing-sm);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  flex-shrink: 0;
  min-width: 80px;
}

.info-value {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  text-align: right;
  flex: 1;
  word-break: break-all;
}

.info-value.link {
  color: #A78BFA;
  text-decoration: none;
  transition: color 0.3s ease;
}

.info-value.link:hover {
  color: #7C3AED;
}

.info-desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  width: 100%;
}

.empty-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--color-text-tertiary);
}

.action-buttons {
  display: flex;
  gap: var(--spacing-md);
  margin-top: var(--spacing-2xl);
}

.action-btn {
  flex: 1;
  padding: var(--spacing-md) var(--spacing-lg);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3);
}

.action-btn:active {
  transform: translateY(0);
}

.action-btn.news {
  background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
  color: var(--color-text-inverse);
}

.action-btn.trade {
  background: linear-gradient(135deg, #10B981 0%, #059669 100%);
  color: var(--color-text-inverse);
}

/* AI Analysis Tab */
.ai-analysis-content {
  padding-bottom: var(--spacing-lg);
}

.ai-compact-header {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-lg);
  background: linear-gradient(135deg, rgba(79, 70, 229, 0.08) 0%, rgba(124, 58, 237, 0.08) 100%);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(79, 70, 229, 0.2);
}

.ai-score-compact {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

.score-circle-small {
  position: relative;
  width: 80px;
  height: 80px;
  flex-shrink: 0;
}

.score-circle-small svg {
  width: 100%;
  height: 100%;
  transform: scaleX(-1);
}

.score-content-small {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.score-value-small {
  display: block;
  font-size: 24px;
  font-weight: var(--font-weight-bold);
  color: #F9FAFB;
  line-height: 1;
}

.ai-info-compact {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  min-width: 0;
}

.ai-header-inline {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.ai-header-inline svg {
  flex-shrink: 0;
}

.ai-title-compact {
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-bold);
  color: #F9FAFB;
  margin: 0;
}

.badges-row {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.rating-badge-small {
  padding: 4px var(--spacing-md);
  background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  color: #fff;
  box-shadow: 0 2px 6px rgba(79, 70, 229, 0.3);
}

.recommendation-badge-small {
  padding: 4px var(--spacing-md);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.recommendation-badge-small.매수 {
  background: linear-gradient(135deg, #10B981 0%, #059669 100%);
  color: #fff;
}

.recommendation-badge-small.보유 {
  background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
  color: #fff;
}

.recommendation-badge-small.매도 {
  background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);
  color: #fff;
}

.ai-disclaimer {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  background: rgba(255, 255, 255, 0.02);
  border-radius: var(--radius-md);
  border: 1px solid rgba(255, 255, 255, 0.05);
  margin-top: var(--spacing-xl);
}

.ai-disclaimer svg {
  color: var(--color-text-tertiary);
  flex-shrink: 0;
  margin-top: 2px;
}

.ai-disclaimer p {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: var(--color-text-tertiary);
  opacity: 0.8;
}

.analysis-section {
  margin-bottom: var(--spacing-xl);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  color: #F9FAFB;
  margin-bottom: var(--spacing-md);
}

.section-title svg {
  color: #A78BFA;
}

.section-title.warning svg {
  color: #F59E0B;
}

.reason-list,
.warning-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.reason-list li,
.warning-list li {
  padding-left: var(--spacing-lg);
  position: relative;
  font-size: var(--font-size-sm);
  color: #D1D5DB;
  line-height: 1.5;
}

.reason-list li::before {
  content: '✓';
  position: absolute;
  left: 0;
  color: #10B981;
  font-weight: var(--font-weight-bold);
}

.warning-list li::before {
  content: '⚠';
  position: absolute;
  left: 0;
  color: #F59E0B;
}

.strength-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.strength-item {
  background: rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
}

.strength-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
}

.strength-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: #F9FAFB;
}

.strength-score {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  color: #A78BFA;
}

.strength-bar {
  height: 6px;
  background: #374151;
  border-radius: var(--radius-full);
  overflow: hidden;
}

.strength-progress {
  height: 100%;
  background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 100%);
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

/* Financial Tab */
.financial-content {
  padding-bottom: var(--spacing-lg);
}

.financial-section {
  margin-bottom: var(--spacing-xl);
}

.ratios-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-md);
}

.ratio-card {
  background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md);
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.3s ease;
}

.ratio-card:hover {
  transform: translateY(-2px);
  border-color: rgba(79, 70, 229, 0.3);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
}

.ratio-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xs);
  font-weight: var(--font-weight-medium);
}

.ratio-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.ratio-value.good {
  background: linear-gradient(135deg, #10B981 0%, #059669 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.financial-table {
  background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.table-header {
  display: grid;
  grid-template-columns: 1fr 1.2fr 1.2fr 1.2fr 1fr;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  background: rgba(79, 70, 229, 0.1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.table-row {
  display: grid;
  grid-template-columns: 1fr 1.2fr 1.2fr 1.2fr 1fr;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  transition: background 0.3s ease;
}

.table-row:last-child {
  border-bottom: none;
}

.table-row:hover {
  background: rgba(79, 70, 229, 0.05);
}

.table-cell {
  font-size: var(--font-size-xs);
  color: var(--color-text-primary);
  text-align: right;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.table-header .table-cell {
  color: #A78BFA;
  font-weight: var(--font-weight-semibold);
  text-align: right;
}

.table-cell.year {
  font-weight: var(--font-weight-bold);
  color: #A78BFA;
  justify-content: flex-start;
  text-align: left;
}

.table-header .table-cell:first-child {
  justify-content: flex-start;
  text-align: left;
}

/* Disclosure Tab */
.disclosure-content {
  padding-bottom: var(--spacing-lg);
}

.disclosure-section {
  margin-bottom: var(--spacing-xl);
}

.disclosure-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.disclosure-item {
  background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md);
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.3s ease;
  cursor: pointer;
}

.disclosure-item:hover {
  transform: translateY(-1px);
  border-color: rgba(79, 70, 229, 0.3);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
}

.disclosure-item.important {
  border-color: rgba(245, 158, 11, 0.3);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.05) 0%, rgba(217, 119, 6, 0.05) 100%);
}

.disclosure-item.important:hover {
  border-color: rgba(245, 158, 11, 0.5);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2);
}

.disclosure-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xs);
}

.disclosure-type {
  font-size: var(--font-size-xs);
  color: #A78BFA;
  font-weight: var(--font-weight-semibold);
  padding: 2px var(--spacing-sm);
  background: rgba(79, 70, 229, 0.2);
  border-radius: var(--radius-sm);
}

.disclosure-item.important .disclosure-type {
  color: #F59E0B;
  background: rgba(245, 158, 11, 0.2);
}

.disclosure-date {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.disclosure-title {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  line-height: 1.4;
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-xs);
}

.important-icon {
  color: #F59E0B;
  flex-shrink: 0;
  margin-top: 2px;
}

/* AI Analysis Tab Styles */
.ai-sub-tabs {
  display: flex;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-lg);
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-lg);
  padding: 4px;
}

.ai-sub-tab {
  flex: 1;
  padding: var(--spacing-sm) var(--spacing-xs);
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: var(--font-weight-medium);
}

.ai-sub-tab.active {
  background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.3);
}

.ai-tab-sections {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.ai-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.section-label {
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.section-label::before {
  content: '';
  width: 2px;
  height: 10px;
  background: #A78BFA;
  border-radius: 2px;
}

.analysis-card {
  background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md);
}

.card-sublabel {
  font-size: 9px;
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-md);
}

.chart-wrapper {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.chart-placeholder {
  position: relative;
  width: 100%;
  background: rgba(20, 27, 43, 0.5);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.chart-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  font-size: 9px;
  color: var(--color-text-secondary);
  background: rgba(8, 12, 20, 0.8);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-family: 'SF Mono', monospace;
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}

.stat-item {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) 4px;
  text-align: center;
}

.stat-label {
  font-size: 7.5px;
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
  line-height: 1.4;
}

.stat-value {
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  font-family: 'SF Mono', monospace;
}

.stat-value.up { color: #F87171; }
.stat-value.dn { color: #60A5FA; }
.stat-value.nt { color: #2DD4BF; }
.stat-value.yw { color: #FBBF24; }

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.feature-row {
  display: flex;
  align-items: center;
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  gap: var(--spacing-xs);
}

.feature-row:last-child {
  border-bottom: none;
}

.feature-label {
  font-size: 10px;
  color: var(--color-text-secondary);
  width: 100px;
  flex-shrink: 0;
}

.feature-source {
  font-size: 9px;
  color: var(--color-text-tertiary);
  width: 50px;
  flex-shrink: 0;
}

.feature-bar-wrap {
  flex: 1;
  margin: 0 var(--spacing-xs);
}

.feature-bar-track {
  height: 5px;
  background: rgba(55, 65, 81, 0.5);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.feature-bar-fill {
  height: 5px;
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

.feature-bar-fill.up { background: #F87171; }
.feature-bar-fill.dn { background: #60A5FA; }
.feature-bar-fill.nt { background: #2DD4BF; }
.feature-bar-fill.yw { background: #FBBF24; }
.feature-bar-fill.purple { background: #A78BFA; }

.feature-value {
  font-size: 11px;
  font-weight: var(--font-weight-bold);
  font-family: 'SF Mono', monospace;
  width: 50px;
  text-align: right;
  flex-shrink: 0;
}

.feature-value.up { color: #F87171; }
.feature-value.dn { color: #60A5FA; }
.feature-value.nt { color: #2DD4BF; }
.feature-value.yw { color: #FBBF24; }
.feature-value.purple { color: #A78BFA; }

.metrics-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.metrics-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.metrics-row:last-child {
  border-bottom: none;
}

.metrics-label {
  font-size: 10px;
  color: var(--color-text-secondary);
}

.metrics-value {
  font-size: 13px;
  font-weight: var(--font-weight-bold);
  font-family: 'SF Mono', monospace;
}

.metrics-value.up { color: #F87171; }
.metrics-value.dn { color: #60A5FA; }
.metrics-value.nt { color: #2DD4BF; }
.metrics-value.yw { color: #FBBF24; }

/* 감성분석 스타일 */
.sentiment-compare {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sentiment-box {
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: center;
}

.sentiment-box:first-child {
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}

.sentiment-header {
  font-size: 9px;
  color: var(--color-text-tertiary);
}

.sentiment-meta {
  font-size: 9px;
  color: var(--color-text-tertiary);
}

.sentiment-score {
  font-size: 26px;
  font-weight: var(--font-weight-bold);
  font-family: 'SF Mono', monospace;
  line-height: 1;
  margin: 4px 0;
}

.sentiment-score.up { color: #F87171; }

.sentiment-badge {
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: 10px;
  font-weight: var(--font-weight-semibold);
}

.sentiment-badge.positive {
  background: rgba(248, 113, 113, 0.12);
  color: #F87171;
  border: 1px solid rgba(248, 113, 113, 0.2);
}

.sentiment-footer {
  font-size: 9px;
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

.sentiment-diff {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  background: rgba(30, 41, 59, 0.5);
  margin-top: var(--spacing-md);
  border-radius: var(--radius-md);
}

.diff-label {
  font-size: 9px;
  color: var(--color-text-tertiary);
}

.diff-value {
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  font-family: 'SF Mono', monospace;
  color: #F87171;
}

.diff-desc {
  font-size: 10px;
  color: var(--color-text-secondary);
  margin-top: var(--spacing-sm);
}

.sentiment-scale {
  margin-bottom: var(--spacing-md);
}

.scale-labels {
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  color: var(--color-text-tertiary);
  margin-bottom: 6px;
}

.scale-bar {
  position: relative;
  height: 10px;
  background: linear-gradient(to right, #60A5FA, rgba(55, 65, 81, 0.5) 50%, #F87171);
  border-radius: var(--radius-full);
}

.market-marker {
  position: absolute;
  top: -3px;
  transform: translateX(-50%);
  width: 2px;
  height: 16px;
  background: #FBBF24;
  border-radius: 1px;
}

.stock-marker {
  position: absolute;
  top: -5px;
  transform: translateX(-50%);
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #F87171;
  border: 2px solid #1E293B;
  box-shadow: 0 0 8px rgba(248, 113, 113, 0.5);
}

.scale-legend {
  display: flex;
  justify-content: space-between;
  font-size: 8.5px;
  margin-top: 6px;
  font-family: 'SF Mono', monospace;
}

.market-legend {
  color: #FBBF24;
}

.stock-legend {
  color: #F87171;
}

.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-xs);
}

.meta-box {
  background: rgba(30, 41, 59, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm);
}

.meta-label {
  font-size: 9px;
  color: var(--color-text-tertiary);
  margin-bottom: 3px;
}

.meta-value {
  font-size: 15px;
  font-weight: var(--font-weight-bold);
  font-family: 'SF Mono', monospace;
  color: var(--color-text-primary);
}

.meta-value-multi {
  font-size: 10px;
  color: var(--color-text-secondary);
  line-height: 1.4;
  margin-top: 2px;
}

.distribution-section {
  margin-bottom: var(--spacing-md);
}

.distribution-label {
  font-size: 9px;
  color: var(--color-text-tertiary);
  margin-bottom: 6px;
}

.distribution-bar {
  display: flex;
  height: 8px;
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.dist-positive {
  background: #F87171;
  border-radius: 3px 0 0 3px;
}

.dist-neutral {
  background: #4A5568;
}

.dist-negative {
  background: #60A5FA;
  border-radius: 0 3px 3px 0;
}

.distribution-legend {
  display: flex;
  justify-content: space-between;
  font-size: 9px;
  margin-top: 5px;
  font-family: 'SF Mono', monospace;
}

.legend-positive { color: #F87171; }
.legend-neutral { color: #4A5568; }
.legend-negative { color: #60A5FA; }

/* 시계열 스타일 */
.trend-summary {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.trend-summary-label {
  font-size: 9px;
  color: var(--color-text-tertiary);
  margin-bottom: var(--spacing-sm);
}

.trend-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-xs);
}

.trend-card {
  background: rgba(248, 113, 113, 0.08);
  border: 1px solid rgba(248, 113, 113, 0.2);
  border-radius: var(--radius-md);
  padding: var(--spacing-sm);
  text-align: center;
}

.trend-card:last-child {
  background: rgba(52, 211, 153, 0.08);
  border: 1px solid rgba(52, 211, 153, 0.2);
}

.trend-emoji {
  font-size: 18px;
  margin-bottom: 4px;
}

.trend-label {
  font-size: 9px;
  color: var(--color-text-tertiary);
}

.trend-value {
  font-size: 12px;
  font-weight: var(--font-weight-bold);
  margin-top: 2px;
}

.trend-value.up { color: #F87171; }
.trend-value.nt { color: #2DD4BF; }

.forecast-table {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.forecast-header {
  display: flex;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 9px;
  color: var(--color-text-tertiary);
}

.forecast-row {
  display: flex;
  padding: 7px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 11px;
  font-family: 'SF Mono', monospace;
}

.forecast-row:last-child {
  border-bottom: none;
}

.forecast-cell {
  flex: 1;
  text-align: right;
  color: var(--color-text-primary);
}

.forecast-cell:first-child {
  text-align: left;
}

.forecast-cell.day {
  color: var(--color-text-tertiary);
}

.forecast-cell.up { color: #F87171; }
.forecast-cell.dn { color: #60A5FA; }
.forecast-cell.nt { color: #2DD4BF; }
</style>
