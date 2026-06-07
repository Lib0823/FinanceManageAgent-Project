"""Trading Decision Generator - Stage 4

Integrates 11 features from Stages 2-1, 2-2, 2-3 and generates trading decisions using Gemini AI.

Features:
- Quantitative (7): morning_return, close_position, foreign_net_buy, institutional_net_buy, per, roe, operating_margin
- Sentiment (1): sentiment_score
- Time-Series (3): prophet_price_trend, prophet_volume_trend, prophet_price_uncertainty
"""
import pandas as pd
from typing import Dict, List
from datetime import datetime
import logging

from ai.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class TradingDecisionGenerator:
    """Generate AI-powered trading decisions using Gemini."""

    def __init__(self):
        """Initialize decision generator with Gemini client."""
        self.gemini_client = GeminiClient()
        logger.info("TradingDecisionGenerator initialized")

    def generate_decisions(
        self,
        quant_features: pd.DataFrame,
        sentiment_features: pd.DataFrame,
        timeseries_features: pd.DataFrame
    ) -> Dict:
        """
        Generate TOP3 buy/sell decisions using Gemini AI.

        Args:
            quant_features: DataFrame with 7 quantitative features
            sentiment_features: DataFrame with sentiment_score
            timeseries_features: DataFrame with 3 time-series features

        Returns:
            dict: {
                'buy_top3': [{'stock_code': str, 'reason': str}, ...],
                'sell_top3': [{'stock_code': str, 'reason': str}, ...]
            }
        """
        logger.info("Generating trading decisions with Gemini AI...")

        # 1. Merge all features into single DataFrame
        all_features_df = self._merge_all_features(quant_features, sentiment_features, timeseries_features)

        # 2. Build context for each stock (11 features)
        stock_contexts = self._build_stock_contexts(all_features_df)

        # 3. Generate Gemini prompt
        prompt = self._generate_gemini_prompt(stock_contexts)

        # 4. Call Gemini API
        try:
            decision = self.gemini_client.generate_decision(prompt)
            logger.info("Trading decision generated successfully")
            return decision

        except Exception as e:
            logger.error(f"Failed to generate decision: {e}")
            raise

    def _merge_all_features(
        self,
        quant_df: pd.DataFrame,
        sentiment_df: pd.DataFrame,
        timeseries_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Merge all feature DataFrames on stock_code.

        Args:
            quant_df: Quantitative features (7)
            sentiment_df: Sentiment features (1)
            timeseries_df: Time-series features (3)

        Returns:
            DataFrame with all 11 features per stock
        """
        # Merge quantitative and sentiment
        merged = pd.merge(quant_df, sentiment_df, on='stock_code', how='left')

        # Merge time-series
        merged = pd.merge(merged, timeseries_df, on='stock_code', how='left')

        logger.info(f"Merged features for {len(merged)} stocks with 11 features each")

        return merged

    def _build_stock_contexts(self, df: pd.DataFrame) -> List[str]:
        """
        Build context string for each stock with 11 features.

        Args:
            df: DataFrame with all 11 features

        Returns:
            List of context strings (one per stock)
        """
        contexts = []

        for _, row in df.iterrows():
            stock_code = row['stock_code']

            context = f"""
[종목: {stock_code}]

정량 분석 (KIS 기반):
- 장초반 수익률: {row['morning_return']:.2f}%
- 종가 위치 (고저 범위 내): {row['close_position']:.2f}
- 외국인 순매수: {row['foreign_net_buy']:,}원
- 기관 순매수: {row['institutional_net_buy']:,}원

정량 분석 (DART 기반):
- PER: {self._format_per(row['per'])}
- ROE: {row['roe']:.2f}%
- 영업이익률: {row['operating_margin']:.2f}%

감성 분석:
- 뉴스 감성 점수: {row['sentiment_score']:.2f} (범위: -1.0 ~ 1.0)

시계열 예측:
- 가격 추세 (D+1~D+5): {row['prophet_price_trend']:.4f} (양수: 상승, 음수: 하락)
- 거래량 추세 (매수 비율): {row['prophet_volume_trend']:.4f} (양수: 매수세 강화)
- 가격 예측 불확실성: {row['prophet_price_uncertainty']:.2f}

"""
            contexts.append(context)

        return contexts

    def _format_per(self, per_value) -> str:
        """
        Format PER value (handle None for loss-making companies).

        Args:
            per_value: PER value or None

        Returns:
            str: Formatted PER string
        """
        if pd.isna(per_value) or per_value is None:
            return "적자 또는 결측"
        else:
            return f"{per_value:.2f}"

    def _generate_gemini_prompt(self, stock_contexts: List[str]) -> str:
        """
        Generate complete prompt for Gemini AI.

        Args:
            stock_contexts: List of context strings (30 stocks)

        Returns:
            str: Complete Gemini prompt
        """
        contexts_text = '\n'.join(stock_contexts)

        prompt = f"""
당신은 한국 주식 시장의 AI 트레이딩 어드바이저입니다.
아래 30개 종목의 11개 피처를 분석하여 매수/매도 결정을 내려주세요.

## 분석 종목 (30개)
{contexts_text}

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
각 매수/매도 결정은 정확히 3개씩이어야 합니다.
"""

        return prompt

    def validate_decision(self, decision: Dict) -> Dict[str, bool]:
        """
        Validate generated decision for completeness and correctness.

        Args:
            decision: Decision dictionary from Gemini

        Returns:
            dict: {validation_metric: is_valid}
        """
        validation_results = {}

        # Check structure
        validation_results['has_buy_top3'] = 'buy_top3' in decision
        validation_results['has_sell_top3'] = 'sell_top3' in decision

        if 'buy_top3' in decision and 'sell_top3' in decision:
            # Check count
            validation_results['buy_count_correct'] = len(decision['buy_top3']) == 3
            validation_results['sell_count_correct'] = len(decision['sell_top3']) == 3

            # Check each item has required fields
            buy_valid = all('stock_code' in item and 'reason' in item for item in decision['buy_top3'])
            sell_valid = all('stock_code' in item and 'reason' in item for item in decision['sell_top3'])

            validation_results['buy_items_valid'] = buy_valid
            validation_results['sell_items_valid'] = sell_valid

            # Check for unique stock codes (no duplicates)
            buy_codes = [item['stock_code'] for item in decision['buy_top3']]
            sell_codes = [item['stock_code'] for item in decision['sell_top3']]

            validation_results['buy_unique'] = len(buy_codes) == len(set(buy_codes))
            validation_results['sell_unique'] = len(sell_codes) == len(set(sell_codes))

            # Check for overlap between buy and sell (should not buy AND sell same stock)
            overlap = set(buy_codes) & set(sell_codes)
            validation_results['no_overlap'] = len(overlap) == 0

            if overlap:
                logger.warning(f"Buy/Sell overlap detected: {overlap}")

        return validation_results
