# 시스템 아키텍처 및 데이터 플로우

> **용도**: AI 자동매매 시스템의 전체 구조 및 6단계 파이프라인 상세 이해
> **대상**: 시스템 아키텍트, Backend/AI 개발자
> **관련 문서**: `API_REFERENCE.md`, `USAGE.md`

---

## 📌 시스템 개요

AI 기반 한국 주식 자동매매 시스템으로, 매일 08:50에 KOSPI 상위 100개 종목을 분석하여 TOP 30을 선정하고, 3가지 분석(정량/감성/시계열)을 통해 Gemini AI가 매수/매도 결정을 내려 KIS API로 자동 실행합니다.

### 핵심 특징
- **일일 자동 실행**: APScheduler로 평일 08:50 자동 파이프라인 실행
- **ML 기반 종목 필터링**: StandardScaler로 KOSPI 100 → TOP 30 선정
- **3-Way 분석**: 정량(7개), 감성(1개), 시계열(3개) 총 11개 피처
- **AI 의사결정**: Gemini API로 매수/매도 TOP3 결정
- **자동 거래 실행**: Spring Boot API Server → KIS 모의투자 API

---

## 🏗️ 시스템 아키텍처

### 전체 구성도

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Vue3 SPA     │────▶│  Spring Boot    │────▶│   PostgreSQL    │
│   (Frontend)    │     │   (API Server)  │     │   (Database)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       ▲                        ▲
         │                       │                        │
         ▼                       │                        │
┌─────────────────┐             │                        │
│  FastAPI Agent  │─────────────┴────────────────────────┘
│   (AI Pipeline) │
└─────────────────┘
         │
         ▼
    ┌─────────┐
    │ KIS API │
    └─────────┘
```

### 컴포넌트별 역할

| 컴포넌트 | 기술 스택 | 역할 |
|---------|---------|------|
| **Vue3 Web App** | Vue 3.5, Vite, Tailwind CSS | 대시보드, 차트 시각화, 설정 관리 |
| **Spring Boot API** | Spring Boot 4.1, JPA | 거래 실행, 사용자 관리, REST API |
| **AI Agent (FastAPI)** | Python 3.11, FastAPI, ML 라이브러리 | 데이터 분석, AI 결정, 파이프라인 실행 |
| **PostgreSQL** | PostgreSQL 16 | 분석 결과, 거래 내역, 사용자 데이터 저장 |
| **KIS API** | 한국투자증권 Open API | 실시간 시세, 수급 데이터, 주문 실행 |
| **DART** | 금융감독원 Open DART | 분기 재무제표 데이터 |

---

## 📊 데이터 파이프라인 (6단계)

### 전체 데이터 플로우

```
[KIS API] ───┐
             │
[DART API] ──┼──▶ [AI Agent Pipeline] ──▶ [PostgreSQL] ──▶ [API Server] ──▶ [Web App]
             │           (6 Stages)
[뉴스 RSS] ──┘
```

### 단계별 개요

| Stage | 입력 | 처리 | 출력 테이블 | 소요시간 |
|-------|------|------|------------|---------|
| **Stage 0** | - | 휴장일 체크 | - | 1초 |
| **Stage 1** | KOSPI 100 종목 | StandardScaler 필터링 | `stock_filter_score` | ~40초 |
| **Stage 2-1** | TOP 30 종목 | 7개 정량 지표 계산 | 메모리 (미저장) | ~10초 |
| **Stage 2-2** | 뉴스 데이터 | KR-FinBERT 감성 분석 | `news_analysis` | ~30초 |
| **Stage 2-3** | 120일 가격 | Prophet 예측 | `prophet_forecast` | ~2분 |
| **Stage 3** | 분석 결과 | matplotlib 차트 | PNG 파일 (4개) | ~10초 |
| **Stage 4** | 11개 피처 | Gemini AI 결정 | `ai_trade_decision` | ~5초 |
| **Stage 5** | AI 결정 | Safety Filter | `safety_filter_result` | ~1초 |
| **Stage 6** | 검증된 결정 | KIS 주문 실행 | `trade_history` | ~3초 |

**총 소요시간**: 약 4~5분 (Stage 2-3 Prophet 학습이 대부분)

---

## 🔍 Stage별 상세 플로우

### Stage 0: 휴장일 체크 (2026-06-01 추가)

**목적**: 파이프라인 실행 전 시장 개장 여부 확인으로 불필요한 API 호출 방지

#### 동작 방식
```python
async def is_market_open(self) -> bool:
    """
    휴장일 체크 2단계:
    1. 주말 체크 (토/일요일)
    2. 실시간 API 테스트 (공휴일 감지)
    """
    # Check 1: Weekend
    kst = pytz.timezone('Asia/Seoul')
    now_kst = datetime.now(kst)

    if now_kst.weekday() >= 5:  # 토요일(5), 일요일(6)
        return False

    # Check 2: Real-time API test (supply/demand API)
    try:
        result = await kis_client.get_supply_demand('005930')  # 삼성전자
        return result is not None
    except RuntimeError as e:
        if '500' in str(e):  # HTTP 500 = 휴장일
            return False
        return False
```

#### 출력
- **개장일**: 파이프라인 계속 진행
- **휴장일**: `{"error": "오늘은 휴장일입니다", "is_holiday": true}` 즉시 리턴

---

### Stage 1: 종목 필터링 (KOSPI 100 → TOP 30)

**목적**: ML 기반 스코어링으로 분석 대상 종목 압축

#### 1.1 데이터 수집
```python
# collectors/kis_client.py
async def collect_supply_demand(stock_codes: list[str]):
    """외국인/기관 순매수 데이터 수집 (asyncio 병렬 처리)"""
    semaphore = asyncio.Semaphore(5)  # Rate limiting: 5 req/sec

    async def fetch_with_limit(code):
        async with semaphore:
            data = await kis_client.get_supply_demand(code)
            await asyncio.sleep(0.2)  # 0.2초 간격 = 5 req/sec
            return code, data

    tasks = [fetch_with_limit(code) for code in stock_codes]
    results = await asyncio.gather(*tasks)
    return dict(results)
```

**API 호출**:
- 수급 데이터: 100 calls (외국인/기관 순매수)
- 일봉 데이터: 100 calls (거래량, 변동성)
- **총 200 calls, 약 40초 소요** (5 req/sec 제한)

#### 1.2 스코어링 알고리즘
```python
# analysis/filter.py
def calculate_filter_score(df: pd.DataFrame) -> pd.DataFrame:
    """StandardScaler 정규화 및 가중합 스코어 계산"""

    # Step 1: 절대값 변환 (매수/매도 모두 강한 신호)
    df['foreign_abs'] = df['foreign_net_buy'].abs()
    df['inst_abs'] = df['institutional_net_buy'].abs()

    # Step 2: StandardScaler 정규화
    scaler = StandardScaler()
    features = ['foreign_abs', 'inst_abs', 'vol_avg_multiple', 'price_volatility']
    normalized = scaler.fit_transform(df[features])

    # Step 3: 가중합 계산
    weights = [0.3, 0.3, 0.3, 0.1]  # 수급(30%) + 수급(30%) + 거래량(30%) + 변동성(10%)
    df['scaler_score'] = np.sum(normalized * weights, axis=1)

    # Step 4: TOP 30 선정 + 보유 종목 무조건 포함
    top_30 = df.nlargest(30, 'scaler_score')
    holdings = get_user_holdings()
    final_stocks = pd.concat([top_30, holdings]).drop_duplicates('stock_code')

    return final_stocks.head(30)
```

#### 1.3 DB 저장
```sql
-- stock_filter_score 테이블
INSERT INTO stock_filter_score (
    stock_code, stock_name, score_date,
    foreign_net_buy, institutional_net_buy,
    vol_avg_multiple, price_volatility,
    scaler_score, is_selected
) VALUES (...);
```

**주요 결정 사항**:
- 절대값 사용: 순매수/순매도 모두 "강한 움직임"으로 포착
- 매일 새로 fit: 당일 100개 종목 기준 상대 비교 (과거 기준 아님)
- 보유 종목 강제 포함: 매도 분석 가능하도록 보장

---

### Stage 2-1: 정량 분석 (7개 피처)

**목적**: KIS API 및 DART 재무제표로 종목별 정량 지표 계산

#### KIS 기반 지표 (4개)
```python
# analysis/quantitative.py
async def calculate_kis_features(stock_code: str, kis_data: dict) -> dict:
    """KIS 데이터로부터 4개 정량 지표 계산"""

    # 1. morning_return: 장초반 수익률 (09:00 ~ 10:00)
    minute_data = kis_data['minute_data']
    open_price = minute_data.iloc[0]['price']
    price_10am = minute_data[minute_data['time'] == '10:00:00']['price'].iloc[0]
    morning_return = (price_10am - open_price) / open_price * 100

    # 2. close_position: 종가 위치 (0~1, 1에 가까울수록 고가 근처 마감)
    daily = kis_data['daily_data']
    close_position = (daily['close'] - daily['low']) / (daily['high'] - daily['low'])

    # 3~4. 수급 데이터는 Stage 1에서 이미 수집됨
    foreign_net_buy = kis_data['foreign_net_buy']
    institutional_net_buy = kis_data['institutional_net_buy']

    return {
        'morning_return': morning_return,
        'close_position': close_position,
        'foreign_net_buy': foreign_net_buy,
        'institutional_net_buy': institutional_net_buy
    }
```

#### DART 기반 지표 (3개)
```python
# collectors/dart_client.py
def get_financial_metrics(stock_codes: list[str]) -> pd.DataFrame:
    """DART DB에서 최신 분기 재무 지표 조회"""
    query = """
        SELECT
            stock_code,
            per,                    -- 주가수익비율
            roe,                    -- 자기자본이익률
            operating_margin,       -- 영업이익률
            debt_ratio,             -- 부채비율
            revenue_growth          -- 매출 성장률
        FROM stock_financial
        WHERE stock_code IN %(codes)s
          AND base_date = (SELECT MAX(base_date) FROM stock_financial)
    """

    with get_db_connection() as conn:
        df = pd.read_sql(query, conn, params={'codes': tuple(stock_codes)})

    return df
```

**데이터 소스**:
- KIS API: 실시간 분봉/일봉 데이터
- DART DB: 분기별 재무제표 (API 아님, DB 조회)

**저장**: 메모리에만 유지 (DB 저장 안함, Gemini 프롬프트 생성 시 사용)

---

### Stage 2-2: 감성 분석 (1개 피처)

**목적**: 뉴스 감성을 KR-FinBERT로 정량화 (-1.0 ~ 1.0)

#### Track 1: 시장 전반 뉴스 (RSS 피드)
```python
# collectors/news_collector.py
async def collect_market_news(self) -> list[dict]:
    """시장 전반 뉴스 수집 (한경, 매경, 연합뉴스 RSS)"""
    all_articles = []

    for feed_url in self.RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        articles = [
            {
                'title': entry.title,
                'summary': entry.summary[:200],
                'published': entry.published_parsed
            }
            for entry in feed.entries[:10]
        ]
        all_articles.extend(articles)

    # 중복 제거 (제목 앞 30자 기준)
    unique = {a['title'][:30]: a for a in all_articles}
    return list(unique.values())
```

#### Track 2: 종목별 뉴스 (네이버 크롤링)
```python
async def collect_stock_news(self, stock_code: str) -> list[dict]:
    """종목별 최근 5개 뉴스 수집"""
    url = f'https://finance.naver.com/item/news_news.nhn?code={stock_code}'

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()

    soup = BeautifulSoup(html, 'html.parser')
    articles = []

    for item in soup.select('.tb_cont tr')[:5]:
        title = item.select_one('.title').text.strip()
        date_text = item.select_one('.date').text

        articles.append({
            'title': title,
            'published': self.parse_date(date_text)
        })

    return articles
```

#### KR-FinBERT 감성 분석
```python
# models/kr_finbert.py
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class KRFinBERTAnalyzer:
    def __init__(self):
        model_name = 'snunlp/KR-FinBert-SC'
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.eval()

    def analyze_sentiment(self, text: str) -> float:
        """텍스트 감성 점수 계산 (-1.0 ~ 1.0)"""
        inputs = self.tokenizer(
            text,
            return_tensors='pt',
            max_length=512,
            truncation=True
        )

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)

        # probs: [negative, neutral, positive]
        sentiment_score = probs[0][2] - probs[0][0]  # positive - negative
        return sentiment_score.item()

    def analyze_articles(self, articles: list[dict]) -> float:
        """여러 기사의 시간 가중 평균 감성 점수"""
        scores = []
        weights = []

        for i, article in enumerate(articles):
            text = f"{article['title']} {article.get('content', '')[:200]}"
            score = self.analyze_sentiment(text)
            scores.append(score)
            weights.append(len(articles) - i)  # 최신 기사에 높은 가중치

        weighted_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        return weighted_score
```

#### DB 저장
```sql
-- news_analysis 테이블
INSERT INTO news_analysis (
    stock_code,          -- NULL = 시장 전반 (Track 1)
    analysis_date,
    sentiment_score,     -- -1.0 ~ 1.0
    news_count
) VALUES (...);
```

---

### Stage 2-3: 시계열 분석 (3개 피처)

**목적**: Prophet으로 D+1~D+5 가격/거래량 추세 예측

#### Prophet 모델 학습
```python
# models/prophet_trainer.py
from prophet import Prophet

class StockProphetAnalyzer:
    def __init__(self, lookback_days: int = 120):
        self.lookback_days = lookback_days

    def prepare_data(self, stock_code: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """120일 가격 데이터 준비 (Prophet 입력 형식)"""
        daily_data = fetch_kis_daily_data(stock_code, 120)

        # 가격 시계열
        price_df = pd.DataFrame({
            'ds': pd.to_datetime(daily_data['trade_date']),
            'y': daily_data['close_price']
        })

        # 거래량 매수 비율 시계열
        volume_df = pd.DataFrame({
            'ds': pd.to_datetime(daily_data['trade_date']),
            'y': daily_data['buy_ratio']  # 매수체결량 / 전체거래량
        })

        return price_df, volume_df

    def train_and_forecast(self, df: pd.DataFrame) -> dict:
        """Prophet 학습 및 D+1~D+5 예측"""
        # 모델 설정
        model = Prophet(
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=False,
            changepoint_prior_scale=0.05
        )

        # 학습
        model.fit(df)

        # 미래 5거래일 예측
        future = model.make_future_dataframe(periods=5, freq='B')  # Business days
        forecast = model.predict(future)

        # D+1 ~ D+5 추출
        future_forecast = forecast.tail(5)

        return {
            'yhat': future_forecast['yhat'].values,
            'yhat_lower': future_forecast['yhat_lower'].values,
            'yhat_upper': future_forecast['yhat_upper'].values
        }
```

#### 피처 계산
```python
# analysis/timeseries.py
from sklearn.linear_model import LinearRegression

def calculate_prophet_features(forecast: dict) -> dict:
    """Prophet 예측으로부터 3개 피처 계산"""

    # 1. 가격 추세 (선형 회귀 기울기)
    X = np.arange(5).reshape(-1, 1)
    y_price = forecast['yhat'].reshape(-1, 1)

    lr_price = LinearRegression()
    lr_price.fit(X, y_price)
    price_trend = lr_price.coef_[0][0]  # 양수: 상승, 음수: 하락

    # 2. 거래량 추세 (매수 비율 기울기)
    y_volume = forecast['volume_yhat'].reshape(-1, 1)
    lr_volume = LinearRegression()
    lr_volume.fit(X, y_volume)
    volume_trend = lr_volume.coef_[0][0]  # 양수: 매수세 강화

    # 3. 가격 불확실성 (신뢰구간 평균 너비)
    uncertainty = np.mean(forecast['yhat_upper'] - forecast['yhat_lower'])

    return {
        'prophet_price_trend': price_trend,
        'prophet_volume_trend': volume_trend,
        'prophet_price_uncertainty': uncertainty
    }
```

#### DB 저장
```sql
-- prophet_forecast 테이블
INSERT INTO prophet_forecast (
    stock_code, forecast_date,
    -- 추세 지표
    price_trend, volume_trend, price_uncertainty,
    -- D+1~D+5 예측값
    yhat_d1, yhat_d2, yhat_d3, yhat_d4, yhat_d5,
    -- 신뢰구간
    yhat_upper_d1, yhat_upper_d5,
    yhat_lower_d1, yhat_lower_d5
) VALUES (...);
```

**설계 결정**:
- 120일 학습: 주간/월간 계절성 학습 가능한 균형점
- 5일 예측: 단일 하루보다 추세 방향 파악에 유효
- Buy ratio 사용: 방향성 확보 (매수 주도 vs 매도 주도)
- Slope 추출: 5개 예측값을 하나의 방향성 피처로 압축

---

### Stage 3: 차트 생성 (matplotlib)

**목적**: 분석 결과를 4개 PNG 차트로 시각화

#### 3.1 히트맵 (11개 피처 × 30종목)
```python
# charts/generator.py
import matplotlib.pyplot as plt
import seaborn as sns

def generate_heatmap(self, data: pd.DataFrame):
    """11개 피처 × 30종목 히트맵"""
    plt.figure(figsize=(14, 10))

    # 데이터 정규화
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    normalized = scaler.fit_transform(data)

    # 히트맵 생성
    sns.heatmap(
        normalized.T,
        xticklabels=data.index,
        yticklabels=data.columns,
        cmap='RdYlGn',
        center=0,
        cbar_kws={'label': '정규화 점수'}
    )

    plt.title('종목별 11개 피처 히트맵', fontsize=16)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig('./static/charts/heatmap_today.png', dpi=150)
    plt.close()
```

#### 3.2 감성 점수 차트
```python
def generate_sentiment_chart(self, sentiments: pd.DataFrame):
    """감성 점수 수평 막대 차트"""
    plt.figure(figsize=(10, 12))

    colors = ['green' if s > 0 else 'red' for s in sentiments['sentiment_score']]

    plt.barh(
        range(len(sentiments)),
        sentiments['sentiment_score'],
        color=colors,
        alpha=0.7
    )

    plt.yticks(range(len(sentiments)), sentiments['stock_name'])
    plt.xlabel('감성 점수 (-1.0 ~ 1.0)')
    plt.title('종목별 뉴스 감성 분석', fontsize=14)
    plt.axvline(0, color='black', linewidth=0.8, linestyle='--')

    plt.tight_layout()
    plt.savefig('./static/charts/sentiment_today.png', dpi=150)
    plt.close()
```

#### 3.3 Prophet 예측 차트
```python
def generate_prophet_chart(self, top3_stocks: dict):
    """TOP3 매수 종목 D+1~D+5 예측 차트"""
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    for idx, (stock_code, forecast) in enumerate(top3_stocks.items()):
        ax = axes[idx]

        days = range(1, 6)
        ax.plot(days, forecast['yhat'], 'b-', linewidth=2, label='예측 가격')
        ax.fill_between(
            days,
            forecast['yhat_lower'],
            forecast['yhat_upper'],
            alpha=0.3,
            label='95% 신뢰구간'
        )

        ax.set_title(f'{stock_code} - 향후 5일 예측')
        ax.set_xlabel('예측 일수 (D+N)')
        ax.set_ylabel('가격')
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('./static/charts/prophet_forecast_today.png', dpi=150)
    plt.close()
```

**출력 파일**:
- `heatmap_today.png` (11 features × 30 stocks)
- `quant_features_today.png` (수급/거래량 bars)
- `sentiment_today.png` (감성 점수 by stock)
- `prophet_forecast_today.png` (TOP3 예측 + 신뢰구간)

**파일 관리**: 매일 덮어쓰기 (버전 관리 없음)

---

### Stage 4: Gemini AI 결정

**목적**: 11개 피처를 종합하여 매수/매도 TOP3 결정

#### 프롬프트 생성
```python
# ai/decision_generator.py
def build_context(self, stock_data: pd.DataFrame) -> str:
    """30개 종목 × 11개 피처 컨텍스트 생성"""
    contexts = []

    for _, row in stock_data.iterrows():
        context = f"""
종목: {row['stock_code']} ({row['stock_name']})

[정량 분석]
- 장초반 수익률: {row['morning_return']:.2f}%
- 종가 위치: {row['close_position']:.2f}
- 외국인 순매수: {row['foreign_net_buy']:,}원
- 기관 순매수: {row['institutional_net_buy']:,}원
- PER: {row['per'] if row['per'] else '적자'}
- ROE: {row['roe']:.2f}%
- 영업이익률: {row['operating_margin']:.2f}%

[감성 분석]
- 뉴스 감성: {row['sentiment_score']:.3f}

[시계열 예측]
- 가격 추세: {row['prophet_price_trend']:.4f}
- 거래량 추세: {row['prophet_volume_trend']:.4f}
- 불확실성: {row['prophet_price_uncertainty']:.2f}
"""
        contexts.append(context)

    return '\n'.join(contexts)
```

#### Gemini API 호출
```python
def generate_prompt(self, context: str) -> str:
    return f"""
당신은 한국 주식 시장 AI 트레이딩 어드바이저입니다.
30개 종목의 11개 피처를 분석하여 매수/매도 결정을 내려주세요.

## 분석 대상
{context}

## 판단 기준
1. 수급: 외국인·기관 동반 순매수 → 강한 매수 신호
2. 모멘텀: morning_return, close_position 높음 → 단기 강세
3. 펀더멘탈: PER 낮고 ROE 높음 → 가치주 매력
4. 감성: sentiment_score > 0.5 → 긍정 뉴스
5. 예측: price_trend > 0 & volume_trend > 0 → 상승 기조

## 출력 (JSON만)
{{
  "buy_top3": [
    {{"stock_code": "005930", "reason": "이유"}},
    {{"stock_code": "000660", "reason": "이유"}},
    {{"stock_code": "051910", "reason": "이유"}}
  ],
  "sell_top3": [
    {{"stock_code": "005380", "reason": "이유"}},
    {{"stock_code": "035420", "reason": "이유"}},
    {{"stock_code": "068270", "reason": "이유"}}
  ]
}}
"""

async def get_decision(self, stock_data: pd.DataFrame) -> dict:
    """Gemini API 호출 및 결과 파싱"""
    context = self.build_context(stock_data)
    prompt = self.generate_prompt(context)

    response = self.model.generate_content(prompt)

    # JSON 추출 (마크다운 코드 블록 제거)
    text = response.text
    if '```json' in text:
        text = text.split('```json')[1].split('```')[0]

    decision = json.loads(text.strip())
    return decision
```

#### DB 저장
```sql
-- ai_trade_decision 테이블
INSERT INTO ai_trade_decision (
    stock_code, decision_date,
    decision,        -- 'buy' or 'sell'
    reason,
    rank             -- 1, 2, 3
) VALUES (...);
```

---

### Stage 5: Safety Filter

**목적**: AI 결정을 리스크 기준으로 검증

#### 필터 로직
```python
# filters/safety_filter.py
class SafetyFilter:
    def __init__(self, config: dict):
        self.max_price = config.get('max_price', 500000)
        self.min_price = config.get('min_price', 1000)
        self.max_volatility = config.get('max_volatility', 0.1)
        self.max_quantity = config.get('max_quantity', 10)
        self.max_position_ratio = config.get('max_position_ratio', 0.2)

    def validate_decision(self, decision: dict, stock_info: dict) -> dict:
        """매매 결정 검증"""
        result = {
            'stock_code': decision['stock_code'],
            'passed': True,
            'failure_reason': None,
            'max_quantity': self.max_quantity
        }

        # 가격 체크
        current_price = stock_info['current_price']
        if current_price > self.max_price:
            result['passed'] = False
            result['failure_reason'] = f'가격 초과: {current_price:,}원'
            return result

        # 변동성 체크
        volatility = stock_info['price_volatility']
        if volatility > self.max_volatility:
            result['passed'] = False
            result['failure_reason'] = f'변동성 초과: {volatility:.2%}'
            return result

        # 포지션 크기 체크 (매수 시)
        if decision['decision'] == 'buy':
            portfolio_value = self.get_portfolio_value()
            position_size = current_price * self.max_quantity
            position_ratio = position_size / portfolio_value

            if position_ratio > self.max_position_ratio:
                adjusted_quantity = int(portfolio_value * self.max_position_ratio / current_price)
                result['max_quantity'] = min(adjusted_quantity, self.max_quantity)

        return result
```

#### DB 저장
```sql
-- safety_filter_result 테이블
INSERT INTO safety_filter_result (
    stock_code, filter_date,
    decision,
    passed,
    failure_reason,
    max_quantity
) VALUES (...);
```

---

### Stage 6: 거래 실행

**목적**: 검증된 결정을 Spring Boot API → KIS API로 실행

#### Spring Boot API 연동
```python
# execution/trade_executor.py
class TradeExecutor:
    def __init__(self, api_base_url: str):
        self.api_base_url = api_base_url

    async def check_auto_trading(self, user_id: int) -> bool:
        """자동매매 활성화 확인"""
        async with aiohttp.ClientSession() as session:
            url = f'{self.api_base_url}/api/users/{user_id}/config'
            async with session.get(url) as response:
                config = await response.json()
                return config['is_active']

    async def execute_trades(self, decisions: list[dict], user_id: int = 1):
        """거래 실행"""
        # 자동매매 확인
        if not await self.check_auto_trading(user_id):
            logger.info("자동매매 비활성화 상태")
            return

        # 거래 요청 생성
        trade_requests = []

        for decision in decisions:
            if decision['passed']:  # Safety Filter 통과한 것만
                trade_request = {
                    'user_id': user_id,
                    'stock_code': decision['stock_code'],
                    'trade_type': decision['decision'].upper(),
                    'quantity': decision['max_quantity'],
                    'order_type': 'MARKET',  # 시장가
                    'reason': decision['reason']
                }
                trade_requests.append(trade_request)

        # API 서버로 전송
        async with aiohttp.ClientSession() as session:
            for req in trade_requests:
                url = f'{self.api_base_url}/api/trading/execute'
                async with session.post(url, json=req) as response:
                    result = await response.json()
                    logger.info(f"거래 실행: {req['trade_type']} {req['stock_code']}")
```

---

## 🗄️ 데이터베이스 설계

### 분석 데이터 테이블

| 테이블 | 용도 | 저장 시점 |
|-------|------|----------|
| `stock_filter_score` | Stage 1 필터링 결과 | 매일 08:50 |
| `stock_financial` | DART 재무 지표 | 분기별 (배치 업데이트) |
| `news_analysis` | Stage 2-2 감성 분석 | 매일 08:50 |
| `prophet_forecast` | Stage 2-3 시계열 예측 | 매일 08:50 |
| `ai_trade_decision` | Stage 4 AI 결정 | 매일 08:50 |
| `safety_filter_result` | Stage 5 필터 결과 | 매일 08:50 |
| `trade_history` | Stage 6 거래 내역 | 거래 실행 시 |

### 웹 표시용 추가 테이블

| 테이블 | 용도 | 업데이트 주기 |
|-------|------|-------------|
| `market_daily_summary` | 시장 일일 요약 | 매일 09:30 |
| `stock_realtime_price` | 실시간 가격 | 5분마다 (장중) |
| `user_holdings` | 보유 종목 현황 | 거래 시마다 |

---

## ⚡ 성능 최적화

### API 호출 최적화
```python
# asyncio로 병렬 처리 (초당 5건 제한)
semaphore = asyncio.Semaphore(5)

async def fetch_with_limit(code):
    async with semaphore:
        data = await kis_client.get_supply_demand(code)
        await asyncio.sleep(0.2)  # 5 req/sec
        return data

tasks = [fetch_with_limit(code) for code in stock_codes]
results = await asyncio.gather(*tasks)
```

### 데이터베이스 최적화
- **인덱싱**: `CREATE INDEX idx_filter_score_date ON stock_filter_score(score_date, is_selected);`
- **배치 삽입**: pandas `to_sql(..., method='multi')`
- **뷰 활용**: `v_stock_analysis_summary` (11개 피처 조인)

### ML 모델 최적화
- **Prophet 병렬 학습**: `ThreadPoolExecutor` 사용
- **모델 비저장**: 매일 새로 학습 (종목 변경 대응)
- **피처 메모리 처리**: DB 왕복 최소화

---

## 🔍 에러 처리 및 복구

### 단계별 에러 처리

| Stage | 에러 유형 | 처리 방법 | 복구 전략 |
|-------|----------|----------|----------|
| **Stage 0** | 휴장일 감지 실패 | 기본값: 휴장 처리 | 안전 우선 |
| **Stage 1** | KIS API 실패 | 3회 재시도 | 이전일 데이터 사용 |
| **Stage 2-1** | DART DB 조회 실패 | 캐시 사용 | 최근 분기 데이터 |
| **Stage 2-2** | 뉴스 수집 실패 | 부분 처리 | 가용 데이터만 분석 |
| **Stage 2-3** | Prophet 학습 실패 | 종목 제외 | 해당 종목 스킵 |
| **Stage 4** | Gemini API 실패 | 알림 발송 | 수동 개입 필요 |
| **Stage 5** | Filter 실패 | 전체 차단 | 거래 중지 |
| **Stage 6** | 거래 실행 실패 | 로그 기록 | 다음 사이클 재시도 |

### 복구 스크립트
```python
# scripts/recovery.py
class PipelineRecovery:
    def recover_from_failure(self, stage: int, date: str):
        """특정 단계부터 재실행"""
        if stage == 1:
            return self.run_full_pipeline(date)
        elif stage == 2:
            top_30 = self.load_filter_scores(date)
            return self.run_from_stage2(top_30, date)
        elif stage == 4:
            analysis_df = self.load_analysis_results(date)
            return self.run_from_stage4(analysis_df, date)
```

---

## 📈 모니터링 지표

| 지표 | 목표 | 알림 임계값 |
|-----|------|-----------|
| 파이프라인 실행 시간 | < 5분 | > 10분 |
| KIS API 에러율 | < 5% | > 10% |
| Prophet 학습 실패 | < 3종목 | > 5종목 |
| Gemini API 성공률 | 100% | < 100% |
| 차트 생성 실패 | 0건 | > 0건 |

---

**문서 버전**: 2.0
**최종 수정일**: 2026-06-01
**작성자**: AI Agent 개발팀
