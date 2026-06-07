"""Gemini AI Client for Trading Decisions

Uses Google Gemini API (free tier, 1 call/day limit) for buy/sell decision generation.
"""
import google.generativeai as genai
import json
import logging
from typing import Optional, Dict

from config.settings import get_settings

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini AI client for generating trading decisions."""

    MODEL_NAME = 'models/gemini-2.5-flash'  # Gemini 2.5 Flash (stable, fast, free tier)

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client.

        Args:
            api_key: Gemini API key (optional, reads from settings if not provided)
        """
        settings = get_settings()
        self.api_key = api_key or settings.gemini_api_key

        if not self.api_key:
            logger.warning("Gemini API key not provided - decisions will be mocked")
            self.model = None
        else:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.MODEL_NAME)
                logger.info(f"Gemini AI client initialized with model: {self.MODEL_NAME}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.model = None

    def generate_decision(self, prompt: str) -> Dict:
        """
        Generate trading decision from Gemini AI.

        Args:
            prompt: Complete prompt with 30 stock contexts and 11 features each

        Returns:
            dict: {
                'buy_top3': [{'stock_code': str, 'reason': str}, ...],
                'sell_top3': [{'stock_code': str, 'reason': str}, ...]
            }

        Raises:
            RuntimeError: If Gemini client is not initialized or API call fails
        """
        if not self.model:
            logger.warning("Gemini client not available, returning mock decision")
            return self._get_mock_decision()

        try:
            logger.info("Calling Gemini API for trading decision...")

            response = self.model.generate_content(prompt)

            if not response or not response.text:
                raise ValueError("Empty response from Gemini API")

            # Parse JSON from response text
            decision = self._parse_gemini_response(response.text)

            logger.info("Gemini decision generated successfully")
            logger.debug(f"Buy TOP3: {[d['stock_code'] for d in decision['buy_top3']]}")
            logger.debug(f"Sell TOP3: {[d['stock_code'] for d in decision['sell_top3']]}")

            return decision

        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise RuntimeError(f"Gemini decision generation failed: {e}")

    def _parse_gemini_response(self, response_text: str) -> Dict:
        """
        Parse Gemini response text to extract JSON.

        Args:
            response_text: Raw response from Gemini

        Returns:
            dict: Parsed decision JSON

        Raises:
            ValueError: If response cannot be parsed as valid JSON
        """
        try:
            # Remove markdown code blocks if present
            text = response_text.strip()

            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]

            # Parse JSON
            decision = json.loads(text.strip())

            # Validate structure
            if 'buy_top3' not in decision or 'sell_top3' not in decision:
                raise ValueError("Missing buy_top3 or sell_top3 in response")

            if len(decision['buy_top3']) != 3 or len(decision['sell_top3']) != 3:
                raise ValueError("buy_top3 and sell_top3 must have exactly 3 items each")

            # Validate each item has stock_code and reason
            for item in decision['buy_top3'] + decision['sell_top3']:
                if 'stock_code' not in item or 'reason' not in item:
                    raise ValueError("Each decision item must have stock_code and reason")

            return decision

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            raise ValueError(f"Gemini response is not valid JSON: {e}")

        except Exception as e:
            logger.error(f"Failed to validate Gemini response: {e}")
            raise ValueError(f"Invalid Gemini response structure: {e}")

    def _get_mock_decision(self) -> Dict:
        """
        Generate mock decision for testing without Gemini API.

        Returns:
            dict: Mock decision with placeholder values
        """
        logger.warning("Generating mock decision (Gemini API not available)")

        return {
            'buy_top3': [
                {'stock_code': '005930', 'reason': '[MOCK] Strong fundamentals with positive sentiment'},
                {'stock_code': '000660', 'reason': '[MOCK] Rising price trend and institutional buying'},
                {'stock_code': '051910', 'reason': '[MOCK] High ROE with favorable news sentiment'}
            ],
            'sell_top3': [
                {'stock_code': '005380', 'reason': '[MOCK] Declining trend with negative sentiment'},
                {'stock_code': '035420', 'reason': '[MOCK] High uncertainty in price forecast'},
                {'stock_code': '068270', 'reason': '[MOCK] Foreign sell-off and weak fundamentals'}
            ]
        }

    def test_connection(self) -> bool:
        """
        Test Gemini API connection with a simple request.

        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.model:
            logger.error("Gemini client not initialized")
            return False

        try:
            logger.info("Testing Gemini API connection...")

            response = self.model.generate_content("Hello, respond with 'OK'")

            if response and response.text:
                logger.info("Gemini API connection successful")
                return True
            else:
                logger.error("Gemini API returned empty response")
                return False

        except Exception as e:
            logger.error(f"Gemini API connection test failed: {e}")
            return False
