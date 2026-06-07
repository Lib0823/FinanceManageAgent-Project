-- ============================================================
-- AI 주식 자동매매 시스템 - Unified Database Schema
-- PostgreSQL 16
-- 프로젝트: FinanceManageAgent
-- 작성일: 2025-05-01
-- 업데이트: 2026-05-25
-- ============================================================

-- ============================================================
-- 1. 사용자 & 인증 테이블
-- ============================================================

-- 사용자 기본 정보
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    birth_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

COMMENT ON TABLE users IS '사용자 기본 정보 (회원가입 지원)';
COMMENT ON COLUMN users.username IS '로그인 ID';
COMMENT ON COLUMN users.email IS '이메일';
COMMENT ON COLUMN users.password IS 'BCrypt 암호화된 비밀번호';


-- JWT 리프레시 토큰
CREATE TABLE refresh_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token ON refresh_tokens(token);

COMMENT ON TABLE refresh_tokens IS 'JWT 리프레시 토큰 관리';
COMMENT ON COLUMN refresh_tokens.revoked_at IS '토큰 무효화 시각';


-- 사용자별 KIS 계좌 정보
CREATE TABLE user_kis_accounts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_number VARCHAR(50) NOT NULL,
    account_product_code VARCHAR(10) NOT NULL DEFAULT '01',
    app_key VARCHAR(255) NOT NULL,
    app_secret VARCHAR(255) NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

CREATE INDEX idx_user_kis_accounts_user ON user_kis_accounts(user_id);
CREATE UNIQUE INDEX idx_user_kis_accounts_account ON user_kis_accounts(account_number);

COMMENT ON TABLE user_kis_accounts IS '사용자별 한국투자증권 API 키 및 계좌번호 (Jasypt 암호화 저장)';
COMMENT ON COLUMN user_kis_accounts.account_number IS 'KIS 계좌번호 (8자리)';
COMMENT ON COLUMN user_kis_accounts.account_product_code IS 'KIS 계좌상품코드 (기본값: 01)';
COMMENT ON COLUMN user_kis_accounts.app_key IS 'KIS APP Key (Jasypt 암호화 저장)';
COMMENT ON COLUMN user_kis_accounts.app_secret IS 'KIS APP Secret (Jasypt 암호화 저장)';
COMMENT ON COLUMN user_kis_accounts.is_verified IS 'KIS API 연동 검증 완료 여부';


-- 사용자 투자 전략 설정
CREATE TABLE user_trade_config (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_amount BIGINT NOT NULL DEFAULT 1000000,
    max_holdings INT NOT NULL DEFAULT 10,
    order_type VARCHAR(20) NOT NULL DEFAULT 'market',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

CREATE INDEX idx_user_trade_config_user ON user_trade_config(user_id);

COMMENT ON TABLE user_trade_config IS '사용자별 자동매매 설정';
COMMENT ON COLUMN user_trade_config.order_amount IS '1회 주문 금액 (원)';
COMMENT ON COLUMN user_trade_config.max_holdings IS '최대 보유 종목 수';
COMMENT ON COLUMN user_trade_config.order_type IS '주문 유형 (market: 시장가, limit: 지정가)';
COMMENT ON COLUMN user_trade_config.is_active IS '자동매매 활성화 여부 (ON/OFF)';


-- 사용자 UI 설정
CREATE TABLE user_settings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    asset_order JSONB DEFAULT '[{"key":"stocks_overseas","label":"주식 (해외)","icon":"📈"},{"key":"stocks_domestic","label":"주식 (국내)","icon":"🏠"},{"key":"coins","label":"코인","icon":"🪙"},{"key":"bonds","label":"채권","icon":"📜"}]',
    dark_mode BOOLEAN NOT NULL DEFAULT FALSE,
    auto_login BOOLEAN NOT NULL DEFAULT FALSE,
    notifications JSONB DEFAULT '{"stocks":{"news":true,"trading":true},"coins":{"news":true,"trading":true}}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

CREATE INDEX idx_user_settings_user ON user_settings(user_id);

COMMENT ON TABLE user_settings IS '사용자별 UI 설정 정보';
COMMENT ON COLUMN user_settings.user_id IS '사용자 ID (FK)';
COMMENT ON COLUMN user_settings.asset_order IS '관심 자산 표시 순서 (드래그앤드롭)';
COMMENT ON COLUMN user_settings.dark_mode IS '다크 모드 활성화 여부';
COMMENT ON COLUMN user_settings.auto_login IS '자동 로그인 설정';
COMMENT ON COLUMN user_settings.notifications IS '알림 설정 (주식/코인 뉴스/매매)';


-- ============================================================
-- 2. 종목 필터링 & 분석 데이터
-- ============================================================

-- 종목 필터링 스코어 (코스피 100 → 30개 선정)
CREATE TABLE stock_filter_score (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    score_date DATE NOT NULL,
    foreign_net_buy BIGINT NOT NULL,
    institutional_net_buy BIGINT NOT NULL,
    vol_avg_multiple NUMERIC(10, 2) NOT NULL,
    price_volatility NUMERIC(10, 4) NOT NULL,
    scaler_score NUMERIC(10, 4) NOT NULL,
    is_selected BOOLEAN NOT NULL DEFAULT FALSE,
    morning_return NUMERIC(10, 4),
    close_position NUMERIC(5, 4),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, score_date)
);

CREATE INDEX idx_stock_filter_score_date ON stock_filter_score(score_date);
CREATE INDEX idx_stock_filter_score_selected ON stock_filter_score(score_date, is_selected);

COMMENT ON TABLE stock_filter_score IS '코스피 100 종목 스코어링 결과 (매일 갱신)';
COMMENT ON COLUMN stock_filter_score.foreign_net_buy IS '외국인 순매수 (원)';
COMMENT ON COLUMN stock_filter_score.institutional_net_buy IS '기관 순매수 (원)';
COMMENT ON COLUMN stock_filter_score.vol_avg_multiple IS '거래량 배율 (vs 평균)';
COMMENT ON COLUMN stock_filter_score.price_volatility IS '가격 변동성';
COMMENT ON COLUMN stock_filter_score.scaler_score IS 'StandardScaler 정규화 후 가중 합산 점수';
COMMENT ON COLUMN stock_filter_score.is_selected IS '분석 대상 30개 선정 여부';


-- DART 재무지표 (분기별)
CREATE TABLE stock_financial (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    base_date DATE NOT NULL,
    per NUMERIC(10, 2),
    roe NUMERIC(10, 2),
    operating_margin NUMERIC(10, 2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, base_date)
);

CREATE INDEX idx_stock_financial_code ON stock_financial(stock_code);
CREATE INDEX idx_stock_financial_date ON stock_financial(base_date);

COMMENT ON TABLE stock_financial IS 'DART API 재무지표 (분기별 수집)';
COMMENT ON COLUMN stock_financial.base_date IS '재무제표 기준일 (분기말)';
COMMENT ON COLUMN stock_financial.per IS 'PER (주가수익비율)';
COMMENT ON COLUMN stock_financial.roe IS 'ROE (자기자본이익률, %)';
COMMENT ON COLUMN stock_financial.operating_margin IS '영업이익률 (%)';


-- 뉴스 감성 분석 결과
CREATE TABLE news_analysis (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10),
    analysis_date DATE NOT NULL,
    sentiment_score NUMERIC(5, 3) NOT NULL,
    news_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, analysis_date)
);

CREATE INDEX idx_news_analysis_date ON news_analysis(analysis_date);
CREATE INDEX idx_news_analysis_stock ON news_analysis(stock_code, analysis_date);

COMMENT ON TABLE news_analysis IS 'KR-FinBERT 감성 분석 결과';
COMMENT ON COLUMN news_analysis.stock_code IS '종목코드 (NULL: 시장 전반 감성)';
COMMENT ON COLUMN news_analysis.analysis_date IS '분석 일자';
COMMENT ON COLUMN news_analysis.sentiment_score IS '감성 점수 (-1.0 ~ +1.0)';
COMMENT ON COLUMN news_analysis.news_count IS '분석된 뉴스 기사 수';


-- Prophet 시계열 예측 결과
CREATE TABLE prophet_forecast (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    forecast_date DATE NOT NULL,
    yhat_d1 NUMERIC(12, 2),
    yhat_d2 NUMERIC(12, 2),
    yhat_d3 NUMERIC(12, 2),
    yhat_d4 NUMERIC(12, 2),
    yhat_d5 NUMERIC(12, 2),
    yhat_upper_d1 NUMERIC(12, 2),
    yhat_upper_d2 NUMERIC(12, 2),
    yhat_upper_d3 NUMERIC(12, 2),
    yhat_upper_d4 NUMERIC(12, 2),
    yhat_upper_d5 NUMERIC(12, 2),
    yhat_lower_d1 NUMERIC(12, 2),
    yhat_lower_d2 NUMERIC(12, 2),
    yhat_lower_d3 NUMERIC(12, 2),
    yhat_lower_d4 NUMERIC(12, 2),
    yhat_lower_d5 NUMERIC(12, 2),
    price_trend NUMERIC(10, 6),
    volume_trend NUMERIC(10, 6),
    price_uncertainty NUMERIC(10, 4),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, forecast_date)
);

CREATE INDEX idx_prophet_forecast_code ON prophet_forecast(stock_code);
CREATE INDEX idx_prophet_forecast_date ON prophet_forecast(forecast_date);

COMMENT ON TABLE prophet_forecast IS 'Prophet D+1~D+5 시계열 예측 결과';
COMMENT ON COLUMN prophet_forecast.forecast_date IS '예측 기준일';
COMMENT ON COLUMN prophet_forecast.yhat_d1 IS 'D+1 예측 가격';
COMMENT ON COLUMN prophet_forecast.yhat_upper_d1 IS 'D+1 신뢰구간 상한';
COMMENT ON COLUMN prophet_forecast.yhat_lower_d1 IS 'D+1 신뢰구간 하한';
COMMENT ON COLUMN prophet_forecast.price_trend IS '가격 추세 (선형회귀 slope)';
COMMENT ON COLUMN prophet_forecast.volume_trend IS '거래량 추세 (선형회귀 slope)';
COMMENT ON COLUMN prophet_forecast.price_uncertainty IS '예측 불확실성 (평균 신뢰구간 폭)';


-- 시장 전체 일일 요약 (신규)
CREATE TABLE market_daily_summary (
    id BIGSERIAL PRIMARY KEY,
    summary_date DATE NOT NULL UNIQUE,
    kospi_index NUMERIC(10, 2),           -- KOSPI 지수
    kospi_change_rate NUMERIC(6, 2),      -- KOSPI 변화율(%)
    kospi_volume BIGINT,                  -- KOSPI 거래량
    total_stocks INT,                     -- 전체 분석 종목 수
    rising_stocks INT,                    -- 상승 종목 수
    falling_stocks INT,                   -- 하락 종목 수
    unchanged_stocks INT,                 -- 보합 종목 수
    total_foreign_net_buy BIGINT,         -- 전체 외국인 순매수
    total_institutional_net_buy BIGINT,   -- 전체 기관 순매수
    market_sentiment_score NUMERIC(5, 3), -- 시장 전반 감성
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_market_summary_date ON market_daily_summary(summary_date DESC);

COMMENT ON TABLE market_daily_summary IS '시장 전체 일일 요약 데이터';
COMMENT ON COLUMN market_daily_summary.kospi_index IS 'KOSPI 지수';
COMMENT ON COLUMN market_daily_summary.kospi_change_rate IS 'KOSPI 변화율(%)';
COMMENT ON COLUMN market_daily_summary.kospi_volume IS 'KOSPI 거래량';
COMMENT ON COLUMN market_daily_summary.market_sentiment_score IS '시장 전반 뉴스 감성 점수';


-- 실시간 가격 정보 (신규)
CREATE TABLE stock_realtime_price (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50),
    current_price BIGINT NOT NULL,
    change_amount BIGINT,              -- 전일 대비 변화량
    change_rate NUMERIC(6, 2),         -- 전일 대비 변화율(%)
    volume BIGINT,                      -- 거래량
    high_price BIGINT,                 -- 당일 고가
    low_price BIGINT,                  -- 당일 저가
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code)
);

CREATE INDEX idx_realtime_price_code ON stock_realtime_price(stock_code);
CREATE INDEX idx_realtime_price_updated ON stock_realtime_price(updated_at DESC);

COMMENT ON TABLE stock_realtime_price IS '종목별 실시간 가격 정보 (캐시)';
COMMENT ON COLUMN stock_realtime_price.current_price IS '현재가';
COMMENT ON COLUMN stock_realtime_price.change_amount IS '전일 대비 변화량';
COMMENT ON COLUMN stock_realtime_price.change_rate IS '전일 대비 변화율(%)';


-- 보유 종목 현황 (신규)
CREATE TABLE user_holdings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50),
    quantity INT NOT NULL,
    avg_price BIGINT,                  -- 평균 매입가
    current_price BIGINT,              -- 현재가
    profit_loss BIGINT,                -- 평가 손익
    profit_loss_rate NUMERIC(6, 2),    -- 평가 손익률(%)
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, stock_code)
);

CREATE INDEX idx_user_holdings_user ON user_holdings(user_id);
CREATE INDEX idx_user_holdings_stock ON user_holdings(stock_code);

COMMENT ON TABLE user_holdings IS '사용자별 보유 종목 현황';
COMMENT ON COLUMN user_holdings.avg_price IS '평균 매입가';
COMMENT ON COLUMN user_holdings.current_price IS '현재가';
COMMENT ON COLUMN user_holdings.profit_loss IS '평가 손익 (현재가 - 평균매입가) * 수량';
COMMENT ON COLUMN user_holdings.profit_loss_rate IS '평가 손익률(%)';


-- Gemini AI 매매 판단 결과
CREATE TABLE ai_trade_decision (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    decision_date DATE NOT NULL,
    decision VARCHAR(10) NOT NULL,
    rank INT,
    reason TEXT,
    prompt_summary TEXT,
    confidence_score DECIMAL(5, 4),  -- Gemini의 판단 신뢰도 (0.0 ~ 1.0)
    feature_summary JSONB,  -- 판단 근거가 된 주요 피처값
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, decision_date, decision)
);

CREATE INDEX idx_ai_trade_decision_date ON ai_trade_decision(decision_date);
CREATE INDEX idx_ai_trade_decision_code ON ai_trade_decision(stock_code, decision_date);
CREATE INDEX idx_ai_trade_decision_rank ON ai_trade_decision(decision_date, decision, rank);

COMMENT ON TABLE ai_trade_decision IS 'Gemini AI 매매 판단 결과';
COMMENT ON COLUMN ai_trade_decision.decision_date IS '판단 일자';
COMMENT ON COLUMN ai_trade_decision.decision IS '판단 (buy, sell, hold)';
COMMENT ON COLUMN ai_trade_decision.rank IS '순위 (1, 2, 3 for TOP3)';
COMMENT ON COLUMN ai_trade_decision.reason IS 'AI 판단 근거 (2-3문장)';
COMMENT ON COLUMN ai_trade_decision.prompt_summary IS 'Gemini에 전달한 프롬프트 요약';
COMMENT ON COLUMN ai_trade_decision.confidence_score IS 'Gemini 판단 신뢰도 (0.0~1.0, 추후 확장용)';
COMMENT ON COLUMN ai_trade_decision.feature_summary IS '판단 근거 주요 피처값 요약';

-- 예시 feature_summary JSON:
-- {
--   "foreign_net_buy": 1234567890,
--   "institutional_net_buy": 987654321,
--   "sentiment_score": 0.65,
--   "prophet_price_trend": 0.0234,
--   "per": 12.5,
--   "roe": 15.2
-- }


-- 안전망 필터 결과 (Gemini 판단 사후 검증)
CREATE TABLE safety_filter_result (
    id BIGSERIAL PRIMARY KEY,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    filter_date DATE NOT NULL,
    decision VARCHAR(10) NOT NULL,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    failure_reason TEXT,
    feature_values JSONB,
    max_quantity INT,  -- 투자금액 기준 최대 매수 가능 수량
    current_price BIGINT,  -- 필터링 시점의 현재가
    filter_checks JSONB,  -- 각 규칙별 통과 여부
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_code, filter_date, decision)
);

CREATE INDEX idx_safety_filter_date ON safety_filter_result(filter_date);
CREATE INDEX idx_safety_filter_passed ON safety_filter_result(filter_date, passed);
CREATE INDEX idx_safety_filter_code ON safety_filter_result(stock_code, filter_date);

COMMENT ON TABLE safety_filter_result IS 'Gemini AI 판단에 대한 안전망 필터 검증 결과';
COMMENT ON COLUMN safety_filter_result.filter_date IS '필터링 일자';
COMMENT ON COLUMN safety_filter_result.decision IS '판단 (buy, sell)';
COMMENT ON COLUMN safety_filter_result.passed IS '안전망 필터 통과 여부';
COMMENT ON COLUMN safety_filter_result.failure_reason IS '필터 실패 사유';
COMMENT ON COLUMN safety_filter_result.feature_values IS '필터링 시 사용된 피처 값 (JSON)';

-- 예시 filter_checks JSON:
-- {
--   "uncertainty_check": {"passed": true, "value": 350, "threshold": 500},
--   "foreign_net_buy_check": {"passed": true, "value": 123456789, "threshold": 0},
--   "institutional_net_buy_check": {"passed": true, "value": 987654321, "threshold": 0},
--   "sentiment_check": {"passed": true, "value": 0.65, "threshold": 0.3},
--   "price_trend_check": {"passed": true, "value": 0.0234, "threshold": 0},
--   "investment_limit_check": {"passed": true, "max_quantity": 34, "order_amount": 10000000}
-- }


-- ============================================================
-- 3. 거래 이력
-- ============================================================

-- 주문 체결 이력
CREATE TABLE trade_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_number VARCHAR(50),
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(50) NOT NULL,
    order_type VARCHAR(10) NOT NULL,
    order_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    quantity INT NOT NULL,
    order_price NUMERIC(12, 2) NOT NULL,
    executed_price NUMERIC(12, 2),
    executed_quantity INT,
    ordered_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trade_history_user ON trade_history(user_id);
CREATE INDEX idx_trade_history_stock ON trade_history(stock_code);
CREATE INDEX idx_trade_history_status ON trade_history(order_status);
CREATE INDEX idx_trade_history_date ON trade_history(ordered_at);

COMMENT ON TABLE trade_history IS '주문 및 체결 이력 (자동매매/수동매매)';
COMMENT ON COLUMN trade_history.order_number IS 'KIS API 주문번호 (ODNO)';
COMMENT ON COLUMN trade_history.order_type IS '주문 유형 (BUY: 매수, SELL: 매도)';
COMMENT ON COLUMN trade_history.order_status IS '주문 상태 (PENDING: 접수, EXECUTED: 체결, CANCELLED: 취소, FAILED: 실패)';
COMMENT ON COLUMN trade_history.quantity IS '주문 수량';
COMMENT ON COLUMN trade_history.order_price IS '주문 단가';
COMMENT ON COLUMN trade_history.executed_price IS '체결 단가';
COMMENT ON COLUMN trade_history.executed_quantity IS '체결 수량';
COMMENT ON COLUMN trade_history.ordered_at IS '주문 시각';
COMMENT ON COLUMN trade_history.executed_at IS '체결 시각';


-- ============================================================
-- 4. Stage 4 & Stage 5 확장 테이블 (Safety Filter & Execution)
-- ============================================================

-- Trade Execution Plan (신규)
-- Safety Filter를 통과한 종목의 실제 매매 계획 저장
CREATE TABLE IF NOT EXISTS trade_execution_plan (
    id SERIAL PRIMARY KEY,
    execution_date DATE NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    stock_name VARCHAR(100),

    -- 매매 계획
    trade_type VARCHAR(4) NOT NULL,  -- 'BUY' or 'SELL'
    planned_quantity INT NOT NULL,    -- 계획 수량
    reference_price BIGINT,           -- 참조 가격 (계획 시점)
    estimated_amount BIGINT,          -- 예상 거래금액

    -- Gemini 판단 근거
    gemini_reason TEXT NOT NULL,
    gemini_rank INT NOT NULL,         -- TOP3 중 순위 (1, 2, 3)

    -- Safety Filter 정보
    safety_filter_passed BOOLEAN NOT NULL,
    safety_filter_details JSONB,

    -- 실행 상태
    execution_status VARCHAR(20) DEFAULT 'PENDING',  -- 'PENDING', 'EXECUTED', 'FAILED', 'SKIPPED'
    executed_at TIMESTAMP,
    execution_result JSONB,  -- KIS API 응답 결과

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_execution_plan_date_stock ON trade_execution_plan(execution_date, stock_code);
CREATE INDEX IF NOT EXISTS idx_execution_plan_status ON trade_execution_plan(execution_status);
CREATE INDEX IF NOT EXISTS idx_execution_plan_date ON trade_execution_plan(execution_date DESC);

COMMENT ON TABLE trade_execution_plan IS 'Safety Filter 통과 후 실제 매매 계획 및 실행 결과';
COMMENT ON COLUMN trade_execution_plan.safety_filter_details IS '각 규칙별 검증 상세 내용 (JSONB)';
COMMENT ON COLUMN trade_execution_plan.execution_result IS 'KIS API 응답 결과 (주문번호, 체결가 등)';


-- Feature Threshold Config (신규)
-- Safety Filter 임계값을 동적으로 관리 (추후 UI에서 조정 가능)
CREATE TABLE IF NOT EXISTS feature_threshold_config (
    id SERIAL PRIMARY KEY,
    feature_name VARCHAR(50) NOT NULL UNIQUE,  -- 피처 이름

    -- BUY 규칙
    buy_enabled BOOLEAN DEFAULT TRUE,
    buy_operator VARCHAR(10),      -- '>', '>=', '<', '<=', '==', '!='
    buy_threshold DECIMAL(20, 8),  -- 임계값
    buy_description TEXT,           -- 규칙 설명

    -- SELL 규칙
    sell_enabled BOOLEAN DEFAULT TRUE,
    sell_operator VARCHAR(10),
    sell_threshold DECIMAL(20, 8),
    sell_description TEXT,

    -- 메타데이터
    is_active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(50) DEFAULT 'SYSTEM'
);

-- 기본 임계값 설정
INSERT INTO feature_threshold_config (
    feature_name,
    buy_enabled, buy_operator, buy_threshold, buy_description,
    sell_enabled, sell_operator, sell_threshold, sell_description
) VALUES
    -- 외국인 순매수 (원화)
    ('foreign_net_buy', TRUE, '>', 0, '외국인 순매수 양수 (매수세)',
     TRUE, '<', 0, '외국인 순매도 음수 (매도세)'),

    -- 기관 순매수 (원화)
    ('institutional_net_buy', TRUE, '>', 0, '기관 순매수 양수',
     TRUE, '<', 0, '기관 순매도 음수'),

    -- 감성 점수 (-1.0 ~ 1.0)
    ('sentiment_score', TRUE, '>=', 0.3, '긍정적 뉴스 감성 (0.3 이상)',
     TRUE, '<=', -0.3, '부정적 뉴스 감성 (-0.3 이하)'),

    -- 가격 추세 (D+1~D+5 기울기)
    ('prophet_price_trend', TRUE, '>', 0, '가격 상승 추세',
     TRUE, '<', 0, '가격 하락 추세'),

    -- 거래량 추세 (매수 비율 기울기)
    ('prophet_volume_trend', TRUE, '>', 0, '매수 거래량 증가 추세',
     FALSE, NULL, NULL, 'SELL 시 거래량 추세 미사용'),

    -- 가격 예측 불확실성
    ('prophet_price_uncertainty', TRUE, '<=', 500, '예측 불확실성 낮음 (500 이하)',
     TRUE, '<=', 500, '예측 불확실성 낮음'),

    -- PER (주가수익비율)
    ('per', TRUE, '<=', 30, 'PER 30 이하 (저평가 기준)',
     FALSE, NULL, NULL, 'SELL 시 PER 미사용'),

    -- ROE (자기자본이익률, %)
    ('roe', TRUE, '>=', 10, 'ROE 10% 이상 (수익성 양호)',
     FALSE, NULL, NULL, 'SELL 시 ROE 미사용'),

    -- 영업이익률 (%)
    ('operating_margin', TRUE, '>=', 5, '영업이익률 5% 이상',
     FALSE, NULL, NULL, 'SELL 시 영업이익률 미사용'),

    -- 장초반 수익률 (%)
    ('morning_return', TRUE, '>', 0, '장초반 상승 (양수)',
     FALSE, NULL, NULL, 'SELL 시 장초반 수익률 미사용'),

    -- 종가 위치 (0~1)
    ('close_position', TRUE, '>=', 0.6, '고가 근처 마감 (0.6 이상)',
     FALSE, NULL, NULL, 'SELL 시 종가 위치 미사용')
ON CONFLICT (feature_name) DO NOTHING;


-- ============================================================
-- 5. 추가 인덱스 (성능 최적화)
-- ============================================================

-- ai_trade_decision 인덱스
CREATE INDEX IF NOT EXISTS idx_ai_decision_date_type
ON ai_trade_decision(decision_date DESC, decision);

CREATE INDEX IF NOT EXISTS idx_ai_decision_stock
ON ai_trade_decision(stock_code, decision_date DESC);

-- safety_filter_result 인덱스
CREATE INDEX IF NOT EXISTS idx_safety_filter_date_passed
ON safety_filter_result(filter_date DESC, passed);

CREATE INDEX IF NOT EXISTS idx_safety_filter_stock
ON safety_filter_result(stock_code, filter_date DESC);


-- ============================================================
-- 6. 뷰 (View) 생성 - Web-App 조회 편의성
-- ============================================================

-- View 1: 최신 매매 계획 요약
CREATE OR REPLACE VIEW v_latest_trade_plan AS
SELECT
    execution_date,
    trade_type,
    COUNT(*) as plan_count,
    SUM(CASE WHEN safety_filter_passed THEN 1 ELSE 0 END) as passed_count,
    SUM(CASE WHEN execution_status = 'EXECUTED' THEN 1 ELSE 0 END) as executed_count,
    SUM(estimated_amount) as total_estimated_amount
FROM trade_execution_plan
WHERE execution_date = CURRENT_DATE
GROUP BY execution_date, trade_type;

-- View 2: Gemini 판단 + Safety Filter 결합 결과
CREATE OR REPLACE VIEW v_decision_with_filter AS
SELECT
    d.decision_date,
    d.stock_code,
    d.decision,
    d.reason as gemini_reason,
    d.rank as gemini_rank,
    f.passed as safety_passed,
    f.failure_reason,
    f.feature_values,
    f.max_quantity,
    f.current_price
FROM ai_trade_decision d
LEFT JOIN safety_filter_result f
    ON d.stock_code = f.stock_code
    AND d.decision_date = f.filter_date
    AND d.decision = f.decision
WHERE d.decision_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY d.decision_date DESC, d.rank ASC;


-- ============================================================
-- 7. 초기 데이터 삽입 (선택)
-- ============================================================

-- admin 계정 생성 (비밀번호: admin123 - BCrypt 해시)
-- 실제 운영 시에는 안전한 비밀번호로 변경 필요
INSERT INTO users (username, email, password, name)
VALUES ('admin', 'admin@example.com', '$2a$10$XQY7QZJ8h.N/YJyZ8.N/YJyZ8.N/YJyZ8.N/YJyZ8.N/YJy', 'Administrator')
ON CONFLICT DO NOTHING;

-- admin 투자 설정 초기화
INSERT INTO user_trade_config (user_id, order_amount, max_holdings, order_type, is_active)
SELECT 1, 1000000, 10, 'market', FALSE
WHERE EXISTS (SELECT 1 FROM users WHERE id = 1)
ON CONFLICT DO NOTHING;