# CLAUDE.md - AI Agent Module

This file provides guidance to Claude Code when working with the AI Agent pipeline module.

## Module Overview

Python-based FastAPI service that orchestrates the daily AI-powered stock analysis pipeline. Runs scheduled at 08:50 KST weekdays via APScheduler, processes KOSPI top 100 stocks, filters to top 30 using ML scoring, performs 3-way analysis (quantitative/sentiment/time-series), and sends buy/sell decisions to Spring Boot API-Server for KIS order execution.

**Role in System:**
- Autonomous daily pipeline execution (no manual trigger)
- ML-based stock filtering and feature engineering
- Multi-domain analysis orchestration (quant/sentiment/time-series)
- Gemini AI decision generation
- Trading signal transmission to API-Server

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (async/await) |
| ML/Data | pandas, NumPy, scikit-learn (StandardScaler) |
| Time-Series | Prophet (Meta/Facebook) |
| NLP | transformers (KR-FinBERT for Korean financial sentiment) |
| AI Decision | Gemini API (free tier, 1 call/day) |
| Scheduling | APScheduler (cron expression: weekdays 08:50 KST) |
| Visualization | matplotlib + NanumGothic font (Korean text rendering) |
| HTTP Client | aiohttp (async KIS API calls) |
| Database | PostgreSQL (via psycopg2 or SQLAlchemy) |

## Pipeline Architecture

### Daily Execution Flow (08:50 KST Weekdays)
```
APScheduler Trigger (08:50)
  ↓
1. Stock Filtering (KOSPI 100 → Top 30)
   - KIS API: 외국인/기관 순매수, 거래량, 변동성
   - StandardScaler 정규화 → 가중합산 스코어
   - Top 30 선정 (+ 보유 종목 무조건 포함)
  ↓
2. Data Collection (asyncio parallel, rate limit: 5 req/sec)
   - KIS API: 분봉, 일봉, 수급 데이터 (120거래일)
   - DART DB: 분기 재무지표 (PER, ROE, 영업이익률)
   - News: RSS 피드 (시장 전반) + 네이버 크롤링 (종목별)
  ↓
3. 3-Way Analysis
   ├─ Quantitative (7 features)
   │   KIS: morning_return, close_position, foreign_net_buy, institutional_net_buy
   │   DART: per, roe, operating_margin
   ├─ Sentiment (1 feature)
   │   KR-FinBERT → sentiment_score (-1.0 ~ 1.0)
   └─ Time-Series (3 features)
       Prophet (120-day train) → D+1~D+5 trends
       prophet_price_trend, prophet_volume_trend, prophet_price_uncertainty
  ↓
4. Chart Generation (matplotlib → /static/charts/)
   - heatmap_today.png (11 features × 30 stocks)
   - quant_features_today.png (수급/거래량 bars)
   - sentiment_today.png (감성 점수 by stock)
   - prophet_forecast_today.png (TOP3 예측 + confidence intervals)
  ↓
5. Gemini AI Decision (11 features → JSON)
   - TOP3 매수 종목 + 매수 이유
   - TOP3 매도 종목 + 매도 이유
   - DB 저장: ai_trade_decision 테이블
  ↓
6. Trade Execution (if is_active=true)
   - POST to Spring Boot /api/trading/execute
   - KIS API 주문 실행 (모의투자 환경)
```

## Directory Structure (Planned)

```
ai-agent/
├── CLAUDE.md                   # This file
├── main.py                     # FastAPI app + APScheduler setup
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container build
├── .env.example                # Environment variables template
│
├── pipeline/
│   ├── __init__.py
│   ├── scheduler.py            # APScheduler cron configuration
│   └── orchestrator.py         # Daily pipeline orchestration logic
│
├── analysis/
│   ├── __init__.py
│   ├── filter.py               # Stage 1: KOSPI 100 → Top 30 scoring
│   ├── quantitative.py         # Stage 2-1: 7 features from KIS/DART
│   ├── sentiment.py            # Stage 2-2: KR-FinBERT sentiment analysis
│   └── timeseries.py           # Stage 2-3: Prophet forecasting
│
├── collectors/
│   ├── __init__.py
│   ├── kis_client.py           # KIS API async client (rate limit handling)
│   ├── dart_client.py          # DART API client (quarterly financials)
│   └── news_collector.py       # RSS feed parser + Naver Finance crawler
│
├── models/
│   ├── __init__.py
│   ├── kr_finbert.py           # KR-FinBERT model loader and inference
│   └── prophet_trainer.py      # Prophet model training and prediction
│
├── ai/
│   ├── __init__.py
│   ├── gemini_client.py        # Gemini API client
│   └── decision_generator.py   # 11-feature → Gemini prompt → JSON parsing
│
├── charts/
│   ├── __init__.py
│   └── generator.py            # Matplotlib chart generation (4 PNGs)
│
├── database/
│   ├── __init__.py
│   ├── models.py               # SQLAlchemy models
│   └── repository.py           # DB CRUD operations
│
├── config/
│   ├── __init__.py
│   ├── settings.py             # Environment variable management (pydantic)
│   └── constants.py            # KOSPI 100 stock codes, weights, thresholds
│
├── utils/
│   ├── __init__.py
│   ├── preprocessing.py        # Text cleaning, outlier removal
│   └── validation.py           # Data quality checks
│
├── static/
│   └── charts/                 # Daily chart output (overwritten)
│       ├── heatmap_today.png
│       ├── quant_features_today.png
│       ├── sentiment_today.png
│       └── prophet_forecast_today.png
│
└── tests/
    ├── __init__.py
    ├── test_filter.py
    ├── test_quantitative.py
    ├── test_sentiment.py
    └── test_timeseries.py
```

## Stage 1: Stock Filtering (KOSPI 100 → Top 30)

### Purpose
Filter KOSPI top 100 stocks to 30 candidates for detailed analysis using ML-based scoring.

### Data Collection
| Indicator | Source | API Call |
|-----------|--------|----------|
| 외국인 순매수 | KIS API | FHKST01010900 (수급 데이터) |
| 기관 순매수 | KIS API | FHKST01010900 (동일 호출) |
| 거래량 배율 | KIS API | 일봉 조회 (20일 평균 대비 전날 거래량) |
| 가격 변동성 | KIS API | 일봉 조회 ((고가-저가)/저가) |

**API Call Volume:** 100 stocks × 2 calls = 200 calls (~40 seconds @ 5 req/sec)

### Scoring Algorithm
```python
# StandardScaler normalization (매일 새로 fit)
scaler = StandardScaler()
normalized = scaler.fit_transform(df[['foreign_net_buy_abs', 'institution_net_buy_abs',
                                       'volume_ratio', 'price_volatility']])

# Weighted sum scoring
score = (normalized[:, 0] * 0.3 +  # 외국인 순매수 (절대값)
         normalized[:, 1] * 0.3 +  # 기관 순매수 (절대값)
         normalized[:, 2] * 0.3 +  # 거래량 배율
         normalized[:, 3] * 0.1)   # 가격 변동성

# Select top 30 + always include holdings
top_30 = df.nlargest(30, 'score')
final_30 = top_30.union(holdings)  # Ensure holdings are in final 30
```

### Database Storage
**Table:** `stock_filter_score`
```sql
CREATE TABLE stock_filter_score (
    stock_code VARCHAR(10),
    trade_date DATE,
    foreign_net_buy BIGINT,
    institution_net_buy BIGINT,
    volume_ratio DECIMAL,
    price_volatility DECIMAL,
    final_score DECIMAL,
    is_selected BOOLEAN,
    PRIMARY KEY (stock_code, trade_date)
);
```

### Design Decisions
| Decision | Rationale |
|----------|-----------|
| 절대값 정규화 (수급) | 매수세/매도세 모두 "강한 움직임"으로 포착 |
| 매일 새로 fit | 당일 100개 종목 기준 상대 비교 (어제 기준 아님) |
| 보유 종목 무조건 포함 | 매도 분석 가능하도록 보장 |
| 가중치 (0.3/0.3/0.3/0.1) | 수급+거래량 동등 비중, 변동성은 보조 |

## Stage 2-1: Quantitative Analysis (7 Features)

### KIS-Based Features (4)
| Feature | Source | Calculation | Interpretation |
|---------|--------|-------------|----------------|
| `morning_return` | 전날 분봉 | (10시 종가 - 시가) / 시가 × 100 | 양수: 매수세, 음수: 매도 압력 |
| `close_position` | 전날 일봉 | (종가-저가)/(고가-저가) | 1에 가까울수록 강세 마감 |
| `foreign_net_buy` | 수급 데이터 | 원화 순매수 금액 (raw) | 양수: 순매수, 음수: 순매도 |
| `institutional_net_buy` | 수급 데이터 | 원화 순매수 금액 (raw) | 양수: 순매수, 음수: 순매도 |

### DART-Based Features (3)
| Feature | Source | Update Frequency | Interpretation |
|---------|--------|------------------|----------------|
| `per` | DART 분기 재무제표 | Quarterly | 낮을수록 저평가 신호 |
| `roe` | DART 분기 재무제표 | Quarterly | 높을수록 수익 창출력 우수 |
| `operating_margin` | DART 분기 재무제표 | Quarterly | 높을수록 본업 수익성 안정 |

### Data Collection Strategy
```python
# KIS API (asyncio parallel with rate limiting)
async def collect_stock_data(stock_codes: list[str]):
    semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_kis_data(session, code, semaphore) for code in stock_codes]
        results = await asyncio.gather(*tasks)

    return results

# DART DB (Query only, no API call)
def get_dart_financials(stock_codes: list[str]) -> pd.DataFrame:
    query = """
        SELECT stock_code, per, roe, operating_margin
        FROM stock_financial
        WHERE stock_code IN %(codes)s
        AND base_date = (SELECT MAX(base_date) FROM stock_financial)
    """
    return pd.read_sql(query, conn, params={'codes': tuple(stock_codes)})
```

### Database Storage
**Table:** `stock_financial`
```sql
CREATE TABLE stock_financial (
    stock_code VARCHAR(10),
    base_date DATE,
    per DECIMAL,
    roe DECIMAL,
    operating_margin DECIMAL,
    PRIMARY KEY (stock_code, base_date)
);
```

## Stage 2-2: Sentiment Analysis (1 Feature)

### Two-Track Architecture
| Track | Target | Output | Usage |
|-------|--------|--------|-------|
| Track 1 | 시장 전반 뉴스 (RSS) | 시장 감성점수 | Vue3 대시보드 시각화 |
| Track 2 | 종목별 뉴스 (크롤링) | `sentiment_score` | Gemini 입력 피처 |

### Track 1: Market Sentiment (RSS Feed)
```python
import feedparser
from datetime import datetime, timedelta

RSS_SOURCES = [
    'https://www.hankyung.com/feed/finance',
    'https://www.mk.co.kr/rss/30000001/',
    'https://www.yonhapnewstv.co.kr/browse/economy/rss'
]

def collect_market_news(cutoff_time: datetime):
    articles = []
    for rss_url in RSS_SOURCES:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            pub_time = datetime(*entry.published_parsed[:6])
            if pub_time >= cutoff_time:  # 전날 18:00 이후
                articles.append({
                    'title': entry.title,
                    'summary': entry.summary[:200],  # 본문 앞 200자
                    'published': pub_time
                })

    # Remove duplicates by title prefix (first 20 chars)
    articles = remove_duplicates(articles, key=lambda x: x['title'][:20])
    return articles
```

### Track 2: Stock-Specific Sentiment (Web Scraping)
```python
from bs4 import BeautifulSoup
import aiohttp

async def collect_stock_news(stock_code: str, max_articles: int = 5):
    url = f'http://finance.naver.com/item/news_news.nhn?code={stock_code}&page=1'

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()

    soup = BeautifulSoup(html, 'html.parser')
    articles = []

    for item in soup.select('.tb_cont tr')[:max_articles]:
        title = item.select_one('.title').text.strip()
        link = item.select_one('.title a')['href']
        date = parse_date(item.select_one('.date').text)

        # Fetch full article content
        content = await fetch_article_content(link)

        articles.append({
            'title': title,
            'content': content[:200],  # 본문 앞 200자
            'published': date
        })

    return articles
```

### KR-FinBERT Inference
```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class KRFinBERTAnalyzer:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained('snunlp/KR-FinBert-SC')
        self.model = AutoModelForSequenceClassification.from_pretrained('snunlp/KR-FinBert-SC')
        self.model.eval()

    def analyze(self, text: str) -> float:
        """
        Returns sentiment score: -1.0 (negative) to 1.0 (positive)
        """
        # Tokenize: 제목 + 본문 앞 200자
        inputs = self.tokenizer(text, return_tensors='pt',
                                max_length=512, truncation=True)

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=1)

        # probs: [negative, neutral, positive]
        score = probs[0][2].item() - probs[0][0].item()  # P(positive) - P(negative)
        return score

    def analyze_multiple(self, articles: list[dict]) -> float:
        """
        Time-weighted average for stock-specific news (Track 2)
        """
        scores = [self.analyze(f"{a['title']} {a['content']}") for a in articles]

        # Linear decay weights: [5, 4, 3, 2, 1] for 5 articles (newest first)
        weights = list(range(len(scores), 0, -1))
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)

        return weighted_score
```

### Database Storage
**Table:** `news_analysis`
```sql
CREATE TABLE news_analysis (
    stock_code VARCHAR(10),      -- NULL for market-wide (Track 1)
    analysis_date DATE,
    sentiment_score DECIMAL(5, 4),  -- Range: -1.0000 to 1.0000
    news_count INT,
    PRIMARY KEY (stock_code, analysis_date)
);
```

## Stage 2-3: Time-Series Analysis (3 Features)

### Prophet Training Strategy
```python
from prophet import Prophet
import pandas as pd
from sklearn.linear_model import LinearRegression

class StockProphetAnalyzer:
    def __init__(self, lookback_days: int = 120):
        self.lookback_days = lookback_days

    def prepare_data(self, stock_code: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetch 120-day historical data from KIS API (no DB storage)
        """
        # Fetch daily OHLCV for 120 trading days
        df_price = fetch_kis_daily_ohlcv(stock_code, days=120)

        # Fetch minute data to calculate buy ratio
        df_minute = fetch_kis_minute_data(stock_code, days=120)
        df_buy_ratio = calculate_daily_buy_ratio(df_minute)

        # Prophet format: columns must be 'ds' (date) and 'y' (value)
        price_series = pd.DataFrame({
            'ds': df_price['trade_date'],
            'y': df_price['close_price']
        })

        volume_series = pd.DataFrame({
            'ds': df_buy_ratio['trade_date'],
            'y': df_buy_ratio['buy_ratio']  # 매수체결량 / 총거래량
        })

        return price_series, volume_series

    def train_and_forecast(self, df: pd.DataFrame, periods: int = 5) -> dict:
        """
        Train Prophet and forecast D+1 to D+5
        """
        # Train model
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=False  # 120 days insufficient for yearly
        )
        model.fit(df)

        # Forecast next 5 trading days
        future = model.make_future_dataframe(periods=periods, freq='B')  # Business days
        forecast = model.predict(future)

        # Extract D+1 to D+5 predictions
        future_forecast = forecast.tail(periods)

        return {
            'yhat': future_forecast['yhat'].values,
            'yhat_lower': future_forecast['yhat_lower'].values,
            'yhat_upper': future_forecast['yhat_upper'].values
        }

    def calculate_trend(self, yhat: np.ndarray) -> float:
        """
        Linear regression slope of D+1 to D+5 yhat
        """
        X = np.arange(len(yhat)).reshape(-1, 1)
        y = yhat.reshape(-1, 1)

        model = LinearRegression()
        model.fit(X, y)

        return model.coef_[0][0]  # Slope

    def calculate_uncertainty(self, yhat_lower: np.ndarray, yhat_upper: np.ndarray) -> float:
        """
        Average confidence interval width for D+1 to D+5
        """
        interval_widths = yhat_upper - yhat_lower
        return np.mean(interval_widths)

    def analyze_stock(self, stock_code: str) -> dict:
        """
        Full analysis: returns 3 features
        """
        price_series, volume_series = self.prepare_data(stock_code)

        # Price forecast
        price_forecast = self.train_and_forecast(price_series)
        prophet_price_trend = self.calculate_trend(price_forecast['yhat'])
        prophet_price_uncertainty = self.calculate_uncertainty(
            price_forecast['yhat_lower'],
            price_forecast['yhat_upper']
        )

        # Volume (buy ratio) forecast
        volume_forecast = self.train_and_forecast(volume_series)
        prophet_volume_trend = self.calculate_trend(volume_forecast['yhat'])

        return {
            'prophet_price_trend': prophet_price_trend,
            'prophet_volume_trend': prophet_volume_trend,
            'prophet_price_uncertainty': prophet_price_uncertainty
        }
```

### Feature Definitions
| Feature | Calculation | Interpretation |
|---------|-------------|----------------|
| `prophet_price_trend` | Linear slope of D+1~D+5 price yhat | 양수: 상승 기조, 음수: 하락 기조 |
| `prophet_volume_trend` | Linear slope of D+1~D+5 buy ratio yhat | 양수: 매수세 강화, 음수: 매도세 강화 |
| `prophet_price_uncertainty` | Mean(yhat_upper - yhat_lower) for D+1~D+5 | 클수록 예측 불확실성 높음 |

### Design Decisions
| Decision | Rationale |
|----------|-----------|
| No DB storage | 매일 종목 변경으로 누적 학습 실익 없음 |
| 120-day training | 주간/월간 계절성 학습 가능한 균형점 |
| 5-day forecast | 단일 하루보다 추세 방향 파악에 유효 |
| Buy ratio vs volume | 방향성 확보 (매수 주도 vs 매도 주도) |
| Slope extraction | 5개 예측값을 하나의 방향성 피처로 압축 |

## Stage 3: Chart Generation (matplotlib)

### Chart Specifications
```python
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# Korean font setup (REQUIRED in Docker container)
font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
font_prop = fm.FontProperties(fname=font_path)
plt.rcParams['font.family'] = font_prop.get_name()
plt.rcParams['axes.unicode_minus'] = False

class ChartGenerator:
    def __init__(self, output_dir: str = './static/charts'):
        self.output_dir = output_dir

    def generate_heatmap(self, features_df: pd.DataFrame):
        """
        11 features × 30 stocks heatmap
        """
        fig, ax = plt.subplots(figsize=(14, 10))

        # Normalize features for visualization
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        features_normalized = scaler.fit_transform(features_df)

        im = ax.imshow(features_normalized.T, cmap='RdYlGn', aspect='auto')

        # Axis labels
        ax.set_xticks(range(len(features_df)))
        ax.set_xticklabels(features_df.index, rotation=45, ha='right')
        ax.set_yticks(range(len(features_df.columns)))
        ax.set_yticklabels(features_df.columns)

        plt.colorbar(im, ax=ax, label='Normalized Score')
        plt.title('종목별 11개 피처 히트맵', fontproperties=font_prop, fontsize=16)
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/heatmap_today.png', dpi=150)
        plt.close()

    def generate_quant_features(self, quant_df: pd.DataFrame):
        """
        Foreign/institutional net buy + volume bars
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        x = range(len(quant_df))
        width = 0.35

        ax.bar([i - width/2 for i in x], quant_df['foreign_net_buy'],
               width, label='외국인 순매수')
        ax.bar([i + width/2 for i in x], quant_df['institutional_net_buy'],
               width, label='기관 순매수')

        ax.set_xlabel('종목', fontproperties=font_prop)
        ax.set_ylabel('순매수 금액 (원)', fontproperties=font_prop)
        ax.set_title('종목별 수급 현황', fontproperties=font_prop, fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(quant_df.index, rotation=45, ha='right')
        ax.legend(prop=font_prop)

        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/quant_features_today.png', dpi=150)
        plt.close()

    def generate_sentiment_chart(self, sentiment_df: pd.DataFrame):
        """
        Sentiment scores by stock (horizontal bar chart)
        """
        fig, ax = plt.subplots(figsize=(10, 12))

        colors = ['green' if s > 0 else 'red' for s in sentiment_df['sentiment_score']]

        ax.barh(range(len(sentiment_df)), sentiment_df['sentiment_score'], color=colors)
        ax.set_yticks(range(len(sentiment_df)))
        ax.set_yticklabels(sentiment_df.index)
        ax.set_xlabel('감성 점수 (-1.0 ~ 1.0)', fontproperties=font_prop)
        ax.set_title('종목별 뉴스 감성 분석', fontproperties=font_prop, fontsize=14)
        ax.axvline(0, color='black', linewidth=0.8, linestyle='--')

        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/sentiment_today.png', dpi=150)
        plt.close()

    def generate_prophet_forecast(self, top3_forecasts: dict):
        """
        TOP3 buy predictions with confidence intervals
        """
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))

        for i, (stock_code, forecast) in enumerate(top3_forecasts.items()):
            ax = axes[i]

            days = range(1, 6)  # D+1 to D+5
            ax.plot(days, forecast['yhat'], 'b-', label='예측 가격')
            ax.fill_between(days, forecast['yhat_lower'], forecast['yhat_upper'],
                            alpha=0.3, label='신뢰구간')

            ax.set_title(f'{stock_code} 향후 5일 예측', fontproperties=font_prop)
            ax.set_xlabel('예측 일수 (D+N)', fontproperties=font_prop)
            ax.set_ylabel('가격', fontproperties=font_prop)
            ax.legend(prop=font_prop)
            ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/prophet_forecast_today.png', dpi=150)
        plt.close()
```

### File Management
- **Location:** `/static/charts/`
- **Overwrite Strategy:** Daily charts overwrite previous day (no versioning)
- **Naming Convention:** `{chart_type}_today.png`
- **Served by:** FastAPI static file mount (`app.mount('/static', StaticFiles(directory='static'), name='static')`)

## Stage 4: Gemini AI Decision

### Feature Context Assembly
```python
def build_gemini_context(stock_code: str, features: dict) -> str:
    """
    Assemble 11-feature context for Gemini prompt
    """
    context = f"""
종목: {stock_code}

[정량 분석 - KIS 기반]
- 장초반 수익률: {features['morning_return']:.2f}%
- 종가 위치 (고저 범위 내): {features['close_position']:.2f}
- 외국인 순매수: {features['foreign_net_buy']:,}원
- 기관 순매수: {features['institutional_net_buy']:,}원

[정량 분석 - DART 기반]
- PER: {features['per'] if features['per'] else '적자 또는 결측'}
- ROE: {features['roe']:.2f}%
- 영업이익률: {features['operating_margin']:.2f}%

[감성 분석]
- 뉴스 감성 점수: {features['sentiment_score']:.2f} (범위: -1.0 ~ 1.0)

[시계열 예측]
- 가격 추세 (D+1~D+5): {features['prophet_price_trend']:.4f} (양수: 상승, 음수: 하락)
- 거래량 추세 (매수 비율): {features['prophet_volume_trend']:.4f} (양수: 매수세 강화)
- 가격 예측 불확실성: {features['prophet_price_uncertainty']:.2f}
"""
    return context

def generate_gemini_prompt(contexts: list[str]) -> str:
    """
    Generate Gemini prompt with all 30 stock contexts
    """
    prompt = f"""
당신은 한국 주식 시장의 AI 트레이딩 어드바이저입니다.
아래 30개 종목의 11개 피처를 분석하여 매수/매도 결정을 내려주세요.

## 분석 종목 (30개)
{''.join(contexts)}

## 판단 기준
1. **수급 흐름**: 외국인·기관 순매수가 동시에 양수면 강한 매수 신호
2. **가격 모멘텀**: morning_return, close_position이 높으면 단기 강세
3. **펀더멘탈**: PER 낮고 ROE·영업이익률 높으면 중장기 매력
4. **뉴스 심리**: sentiment_score가 0.5 이상이면 호재 집중
5. **추세 방향**: prophet_price_trend 양수이고 prophet_volume_trend도 양수면 상승 기조
6. **불확실성**: prophet_price_uncertainty가 크면 판단 보류 고려

## 출력 형식 (JSON)
{{
  "buy_top3": [
    {{"stock_code": "005930", "reason": "외국인·기관 동시 순매수 + 가격 상승 추세 + 긍정 뉴스"}},
    {{"stock_code": "000660", "reason": "..."}},
    {{"stock_code": "051910", "reason": "..."}}
  ],
  "sell_top3": [
    {{"stock_code": "005380", "reason": "외국인·기관 동시 순매도 + 가격 하락 추세 + 부정 뉴스"}},
    {{"stock_code": "035420", "reason": "..."}},
    {{"stock_code": "068270", "reason": "..."}}
  ]
}}

**중요**: 반드시 JSON 형식으로만 답변하고, 설명은 reason 필드에 포함하세요.
"""
    return prompt
```

### Gemini API Client
```python
import google.generativeai as genai
import json

class GeminiDecisionGenerator:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def generate_decision(self, prompt: str) -> dict:
        """
        Call Gemini API (1 call/day limit for free tier)
        """
        response = self.model.generate_content(prompt)

        # Parse JSON from response
        try:
            # Extract JSON from response text (may contain markdown code blocks)
            text = response.text
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]

            decision = json.loads(text.strip())
            return decision

        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini response is not valid JSON: {e}\nResponse: {response.text}")

    def save_decision(self, decision: dict, trade_date: str):
        """
        Save to ai_trade_decision table
        """
        records = []

        for item in decision['buy_top3']:
            records.append({
                'stock_code': item['stock_code'],
                'trade_date': trade_date,
                'decision_type': 'BUY',
                'reason': item['reason'],
                'rank': decision['buy_top3'].index(item) + 1
            })

        for item in decision['sell_top3']:
            records.append({
                'stock_code': item['stock_code'],
                'trade_date': trade_date,
                'decision_type': 'SELL',
                'reason': item['reason'],
                'rank': decision['sell_top3'].index(item) + 1
            })

        # Insert to DB
        df = pd.DataFrame(records)
        df.to_sql('ai_trade_decision', conn, if_exists='append', index=False)
```

### Database Storage
**Table:** `ai_trade_decision`
```sql
CREATE TABLE ai_trade_decision (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    decision_type VARCHAR(4) NOT NULL,  -- 'BUY' or 'SELL'
    reason TEXT NOT NULL,
    rank INT NOT NULL,                  -- 1, 2, 3 for TOP3
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Stage 5: Trade Execution

### Spring Boot API Integration
```python
import aiohttp

class TradeExecutor:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url

    async def check_auto_trading_enabled(self, user_id: int) -> bool:
        """
        Check user_trade_config.is_active flag
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.api_base_url}/api/config/{user_id}') as resp:
                config = await resp.json()
                return config.get('is_active', False)

    async def execute_trades(self, decisions: dict):
        """
        POST to Spring Boot /api/trading/execute
        """
        # Check if auto-trading is enabled
        if not await self.check_auto_trading_enabled(user_id=1):  # MVP: single user
            print("[Trade Execution] Auto-trading is disabled. Skipping execution.")
            return

        # Prepare trade requests
        trade_requests = []

        for item in decisions['buy_top3']:
            trade_requests.append({
                'stock_code': item['stock_code'],
                'side': 'BUY',
                'quantity': 1,  # MVP: 1주 단위 주문
                'price': 0,     # 시장가
                'reason': item['reason']
            })

        for item in decisions['sell_top3']:
            # Check holdings first
            holdings = await self.get_holdings(item['stock_code'])
            if holdings > 0:
                trade_requests.append({
                    'stock_code': item['stock_code'],
                    'side': 'SELL',
                    'quantity': holdings,  # 보유 수량 전부 매도
                    'price': 0,
                    'reason': item['reason']
                })

        # Execute trades via Spring Boot API
        async with aiohttp.ClientSession() as session:
            for req in trade_requests:
                async with session.post(f'{self.api_base_url}/api/trading/execute',
                                       json=req) as resp:
                    result = await resp.json()
                    print(f"[Trade Execution] {req['side']} {req['stock_code']}: {result}")

    async def get_holdings(self, stock_code: str) -> int:
        """
        Get current holdings for stock_code
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{self.api_base_url}/api/assets/holdings') as resp:
                holdings = await resp.json()
                for h in holdings:
                    if h['stock_code'] == stock_code:
                        return h['quantity']
                return 0
```

## KIS API Integration

### Authentication (KIS_API_GUIDE.md 참고)
```python
import aiohttp
import asyncio
from datetime import datetime, timedelta

class KISClient:
    def __init__(self, app_key: str, app_secret: str, mode: str = 'VIRTUAL'):
        self.app_key = app_key
        self.app_secret = app_secret
        self.mode = mode  # 'VIRTUAL' or 'REAL'
        self.base_url = 'https://openapi.koreainvestment.com:9443'
        self.access_token = None
        self.token_expires_at = None

    async def get_access_token(self) -> str:
        """
        OAuth token (24-hour cache)
        """
        if self.access_token and datetime.now() < self.token_expires_at:
            return self.access_token

        url = f'{self.base_url}/oauth2/tokenP'
        data = {
            'grant_type': 'client_credentials',
            'appkey': self.app_key,
            'appsecret': self.app_secret
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as resp:
                result = await resp.json()
                self.access_token = result['access_token']
                self.token_expires_at = datetime.now() + timedelta(hours=24)
                return self.access_token

    def convert_tr_id(self, base_tr_id: str) -> str:
        """
        Auto-convert TR_ID based on mode (VIRTUAL/REAL)
        VTTC8434R (VIRTUAL) → TTTC8434R (REAL)
        """
        if base_tr_id.startswith('VTTC') and self.mode == 'REAL':
            return 'TTTC' + base_tr_id[4:]
        elif base_tr_id.startswith('TTTC') and self.mode == 'VIRTUAL':
            return 'VTTC' + base_tr_id[4:]
        return base_tr_id

    async def request(self, method: str, endpoint: str, tr_id: str, params: dict = None):
        """
        Generic KIS API request with rate limiting
        """
        token = await self.get_access_token()
        tr_id_converted = self.convert_tr_id(tr_id)

        headers = {
            'authorization': f'Bearer {token}',
            'appkey': self.app_key,
            'appsecret': self.app_secret,
            'tr_id': tr_id_converted,
            'custtype': 'P'
        }

        url = f'{self.base_url}{endpoint}'

        async with aiohttp.ClientSession() as session:
            if method == 'GET':
                async with session.get(url, headers=headers, params=params) as resp:
                    return await resp.json()
            elif method == 'POST':
                async with session.post(url, headers=headers, json=params) as resp:
                    return await resp.json()

    async def get_daily_ohlcv(self, stock_code: str, days: int = 120) -> pd.DataFrame:
        """
        일봉 조회 (120거래일)
        """
        endpoint = '/uapi/domestic-stock/v1/quotations/inquire-daily-price'
        tr_id = 'FHKST01010400'

        params = {
            'FID_COND_MRKT_DIV_CODE': 'J',
            'FID_INPUT_ISCD': stock_code,
            'FID_PERIOD_DIV_CODE': 'D',
            'FID_ORG_ADJ_PRC': '0'
        }

        result = await self.request('GET', endpoint, tr_id, params)

        # Parse response
        ohlcv_list = result['output'][:days]
        df = pd.DataFrame(ohlcv_list)
        df.columns = ['trade_date', 'open', 'high', 'low', 'close', 'volume']

        return df

    async def get_supply_demand(self, stock_code: str) -> dict:
        """
        외국인·기관 순매수 (FHKST01010900)
        """
        endpoint = '/uapi/domestic-stock/v1/quotations/inquire-investor'
        tr_id = 'FHKST01010900'

        params = {
            'FID_COND_MRKT_DIV_CODE': 'J',
            'FID_INPUT_ISCD': stock_code
        }

        result = await self.request('GET', endpoint, tr_id, params)

        return {
            'foreign_net_buy': int(result['output']['stck_frgn_ntby_amt']),
            'institutional_net_buy': int(result['output']['stck_orgn_ntby_amt'])
        }

    async def get_minute_data(self, stock_code: str, date: str) -> pd.DataFrame:
        """
        분봉 조회 (09:00~10:00 for morning_return calculation)
        """
        endpoint = '/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice'
        tr_id = 'FHKST01010600'

        params = {
            'FID_COND_MRKT_DIV_CODE': 'J',
            'FID_INPUT_ISCD': stock_code,
            'FID_INPUT_DATE_1': date,
            'FID_INPUT_HOUR_1': '0900',
            'FID_INPUT_HOUR_2': '1000'
        }

        result = await self.request('GET', endpoint, tr_id, params)

        df = pd.DataFrame(result['output'])
        return df

# Rate limiting with asyncio.Semaphore
async def fetch_all_stocks_parallel(stock_codes: list[str], kis_client: KISClient):
    """
    Fetch data for all stocks with rate limiting (5 req/sec)
    """
    semaphore = asyncio.Semaphore(5)

    async def fetch_with_semaphore(stock_code: str):
        async with semaphore:
            data = await kis_client.get_supply_demand(stock_code)
            await asyncio.sleep(0.2)  # 5 req/sec = 0.2s interval
            return stock_code, data

    tasks = [fetch_with_semaphore(code) for code in stock_codes]
    results = await asyncio.gather(*tasks)

    return dict(results)
```

### API Call Summary
| Operation | TR_ID (모의) | TR_ID (실전) | Calls/Stock | Total Calls (100 stocks) |
|-----------|-------------|-------------|-------------|--------------------------|
| 잔고 조회 | VTTC8434R | TTTC8434R | - | 1 (전체 잔고) |
| 수급 데이터 | FHKST01010900 | - | 1 | 100 |
| 일봉 조회 | FHKST01010400 | - | 1 | 100 |
| 분봉 조회 | FHKST01010600 | - | 1 | 30 (Top 30만) |
| **Stage 1 합계** | - | - | - | **~200** |
| **Stage 2 합계** | - | - | - | **~30** |

**Rate Limiting:** 초당 5건 제한 → asyncio.Semaphore(5) + 0.2초 간격

## Database Schema

### Tables Used by AI Agent
```sql
-- Stage 1 output
CREATE TABLE stock_filter_score (
    stock_code VARCHAR(10),
    trade_date DATE,
    foreign_net_buy BIGINT,
    institution_net_buy BIGINT,
    volume_ratio DECIMAL,
    price_volatility DECIMAL,
    final_score DECIMAL,
    is_selected BOOLEAN,
    PRIMARY KEY (stock_code, trade_date)
);

-- Stage 2-1 input (DART data)
CREATE TABLE stock_financial (
    stock_code VARCHAR(10),
    base_date DATE,
    per DECIMAL,
    roe DECIMAL,
    operating_margin DECIMAL,
    PRIMARY KEY (stock_code, base_date)
);

-- Stage 2-2 output
CREATE TABLE news_analysis (
    stock_code VARCHAR(10),
    analysis_date DATE,
    sentiment_score DECIMAL(5, 4),
    news_count INT,
    PRIMARY KEY (stock_code, analysis_date)
);

-- Stage 4 output
CREATE TABLE ai_trade_decision (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    trade_date DATE NOT NULL,
    decision_type VARCHAR(4) NOT NULL,
    reason TEXT NOT NULL,
    rank INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User config (read by Stage 5)
CREATE TABLE user_trade_config (
    user_id INT PRIMARY KEY REFERENCES users(id),
    is_active BOOLEAN DEFAULT FALSE,  -- Auto-trading enabled
    max_investment_per_stock BIGINT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Trade execution history (written by api-server)
CREATE TABLE trade_history (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    stock_code VARCHAR(10),
    trade_type VARCHAR(4),
    quantity INT,
    price BIGINT,
    executed_at TIMESTAMP DEFAULT NOW()
);
```

## Configuration Management

### Environment Variables
```bash
# .env
# Python Environment
PYTHONPATH=/app

# KIS API (모의투자)
KIS_MODE=VIRTUAL
KIS_APP_KEY=PS모의투자용키32자리문자열
KIS_APP_SECRET=모의투자용시크릿32자리문자열

# DART API
DART_API_KEY=your_dart_api_key

# Gemini API (free tier)
GEMINI_API_KEY=your_gemini_api_key

# Database
DB_HOST=postgres
DB_PORT=5432
DB_NAME=financemanage
DB_USER=postgres
DB_PASSWORD=yourpassword

# API Server
API_SERVER_URL=http://api-server:8080

# Scheduler
PIPELINE_CRON=50 8 * * 1-5  # Weekdays 08:50 KST
PIPELINE_TIMEZONE=Asia/Seoul

# Chart Output
CHART_OUTPUT_DIR=/app/static/charts

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/pipeline.log
```

### Constants (config/constants.py)
```python
# KOSPI 100 stock codes (hardcoded)
KOSPI_100 = [
    '005930',  # 삼성전자
    '000660',  # SK하이닉스
    '051910',  # LG화학
    # ... 97 more stocks
]

# Feature weights
FILTER_WEIGHTS = {
    'foreign_net_buy': 0.3,
    'institution_net_buy': 0.3,
    'volume_ratio': 0.3,
    'price_volatility': 0.1
}

# Analysis parameters
LOOKBACK_DAYS = 120  # Prophet training period
FORECAST_DAYS = 5    # D+1 to D+5
TOP_N_STOCKS = 30    # Final analysis candidates
NEWS_PER_STOCK = 5   # Track 2 news collection

# Thresholds
SENTIMENT_POSITIVE_THRESHOLD = 0.5
SENTIMENT_NEGATIVE_THRESHOLD = -0.5
UNCERTAINTY_HIGH_THRESHOLD = 1000  # Prophet confidence interval width
```

## Development Commands

### Local Development
```bash
cd ai-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Trigger pipeline manually (for testing)
curl -X POST http://localhost:8000/api/pipeline/trigger

# Check pipeline status
curl http://localhost:8000/api/pipeline/status

# View generated charts
curl http://localhost:8000/static/charts/heatmap_today.png
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific stage tests
pytest tests/test_filter.py -v
pytest tests/test_sentiment.py -v

# Test with coverage
pytest --cov=. --cov-report=html

# Test KIS API integration (requires API key)
pytest tests/test_kis_client.py --kis-api-key=$KIS_APP_KEY
```

### Docker
```bash
# Build image
docker build -t ai-agent:latest .

# Run container
docker run -d \
  --name ai-agent \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/static/charts:/app/static/charts \
  ai-agent:latest

# View logs
docker logs -f ai-agent

# Execute pipeline manually
docker exec ai-agent python -m pipeline.orchestrator
```

## Important Design Decisions

### Data Flow
| Decision | Rationale |
|----------|-----------|
| No time-series DB storage | 매일 종목 변경으로 누적 실익 없음, 파이프라인 실행 시 KIS API 직접 조회 |
| Features as variables (not DB) | Gemini 프롬프트에 직접 전달하므로 중간 저장 불필요 |
| Daily StandardScaler fit | 당일 100개 종목 기준 상대 비교 (어제 기준 아님) |
| 보유 종목 무조건 포함 | 매도 분석 가능하도록 top 30 선정 시 강제 포함 |
| Chart overwrite (no versioning) | 대시보드는 최신 차트만 표시, 히스토리 관리 불필요 |

### Performance
| Optimization | Implementation |
|--------------|----------------|
| Async KIS API calls | aiohttp + asyncio.Semaphore(5) for rate limiting |
| Parallel Prophet training | ThreadPoolExecutor for CPU-bound operations |
| No DB round-trips | All features computed in memory, single batch insert |
| Model non-persistence | Prophet 모델 저장 없음, 매일 새로 fit (종목 변경 대응) |

### Error Handling
| Scenario | Handling Strategy |
|----------|-------------------|
| KIS API rate limit | Retry with exponential backoff (3 attempts) |
| Prophet training failure | Skip stock, log warning, continue pipeline |
| Gemini API failure | Save empty decision, send alert, retry next day |
| DB connection loss | Retry with connection pool, fail pipeline if persistent |
| News parsing error | Skip article, log warning, continue with available data |

### Monitoring
| Metric | Alert Threshold |
|--------|-----------------|
| Pipeline execution time | > 10 minutes |
| KIS API error rate | > 10% |
| Prophet training failures | > 5 stocks |
| Gemini API call failure | Immediate alert |
| Chart generation failure | Immediate alert |

## Critical Dependencies

### Python Packages (requirements.txt)
```txt
# Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
apscheduler==3.10.4

# Async HTTP
aiohttp==3.9.1

# Data Science
pandas==2.2.0
numpy==1.26.3
scikit-learn==1.4.0

# ML/Time-Series
prophet==1.1.5
pystan==3.9.0  # Prophet dependency

# NLP
transformers==4.37.0
torch==2.1.2  # For KR-FinBERT

# Visualization
matplotlib==3.8.2

# Web Scraping
beautifulsoup4==4.12.3
feedparser==6.0.11

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.25

# AI
google-generativeai==0.3.2

# Utils
python-dotenv==1.0.0
pydantic==2.5.3
pydantic-settings==2.1.0
```

### System Dependencies (Dockerfile)
```dockerfile
FROM python:3.11-slim

# Install NanumGothic font for matplotlib Korean text
RUN apt-get update && \
    apt-get install -y fonts-nanum && \
    fc-cache -fv && \
    rm -rf /var/lib/apt/lists/*

# Install system dependencies for Prophet (Stan compiler)
RUN apt-get update && \
    apt-get install -y build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Common Issues

#### Prophet Installation Failure
```bash
# Issue: pystan compilation error
# Solution: Install build tools
sudo apt-get install build-essential
pip install pystan==3.9.0
pip install prophet==1.1.5
```

#### KR-FinBERT Model Download Slow
```bash
# Issue: Hugging Face model download timeout
# Solution: Pre-download in Dockerfile or use cached model
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    AutoTokenizer.from_pretrained('snunlp/KR-FinBert-SC'); \
    AutoModelForSequenceClassification.from_pretrained('snunlp/KR-FinBert-SC')"
```

#### Korean Font Not Rendering
```bash
# Issue: matplotlib charts show squares instead of Korean text
# Solution: Verify NanumGothic installation
fc-list | grep Nanum  # Should show font path
python -c "import matplotlib.font_manager as fm; print([f.name for f in fm.fontManager.ttflist if 'Nanum' in f.name])"
```

#### KIS API 401 Unauthorized
```bash
# Issue: Access token expired or invalid
# Solution: Check environment variables and mode (VIRTUAL vs REAL)
echo $KIS_MODE  # Must match API key type
echo $KIS_APP_KEY | head -c 2  # Should be "PS" for mock trading
```

#### Pipeline Not Triggering
```bash
# Issue: APScheduler cron not firing
# Solution: Check timezone and cron expression
# Verify: 50 8 * * 1-5 = 08:50 weekdays (Monday=1, Friday=5)
# Test manually:
curl -X POST http://localhost:8000/api/pipeline/trigger
```

## Security Considerations

### API Key Management
- **Never commit** `.env` file to Git
- Use `.env.example` with placeholder values
- Store production keys in secure vault (AWS Secrets Manager, etc.)
- Rotate KIS API keys quarterly

### Database Access
- Use read-only credentials for DART DB queries
- Encrypt sensitive user data (KIS account credentials in `user_kis_account` table)
- Implement connection pooling with max connections limit

### External API Calls
- Always use HTTPS for KIS/DART/Gemini API calls
- Validate SSL certificates
- Implement request timeout (30 seconds default)
- Log API errors without exposing keys

## Future Enhancements

### Phase 2 Considerations
| Feature | Current Limitation | Enhancement Path |
|---------|-------------------|------------------|
| Multi-user support | Single user (MVP) | Add user_id to pipeline context, parallel execution per user |
| Real-time triggers | Daily 08:50 only | Intraday pipeline for market hours monitoring |
| Advanced ML | RandomForest removed | Implement ensemble models (XGBoost, LightGBM) |
| Backtesting | None | Historical simulation with performance metrics |
| Risk management | 1-share orders | Position sizing, stop-loss, portfolio allocation |

### Scalability
- **Horizontal scaling:** Run multiple pipeline instances with distributed task queue (Celery + Redis)
- **Database optimization:** Partition tables by date, add indexes on stock_code + trade_date
- **Caching layer:** Redis for KIS API responses, Prophet forecasts
- **Async everywhere:** Replace blocking DB calls with asyncpg

---

**Document Version:** 1.0
**Last Updated:** 2025-05-19
**Maintainer:** AI Agent Development Team
**Status:** 🚧 Development (module not yet implemented)
