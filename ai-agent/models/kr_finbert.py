"""KR-FinBERT Model Wrapper for Korean Financial Sentiment Analysis

Model: snunlp/KR-FinBert-SC (Seoul National University NLP Lab)
Output: 3-class classification (negative, neutral, positive)
"""
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import List
import logging

logger = logging.getLogger(__name__)


class KRFinBERTAnalyzer:
    """Korean Financial BERT sentiment analyzer."""

    MODEL_NAME = 'snunlp/KR-FinBert-SC'

    def __init__(self):
        """Initialize KR-FinBERT model and tokenizer."""
        logger.info(f"Loading KR-FinBERT model: {self.MODEL_NAME}")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.MODEL_NAME)
            self.model.eval()  # Set to evaluation mode

            # Move to GPU if available
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model.to(self.device)

            logger.info(f"KR-FinBERT loaded successfully (device: {self.device})")

        except Exception as e:
            logger.error(f"Failed to load KR-FinBERT model: {e}")
            raise

    def analyze_single(self, text: str) -> float:
        """
        Analyze sentiment for a single text.

        Args:
            text: Input text (title + summary/content, max 512 tokens)

        Returns:
            float: Sentiment score from -1.0 (negative) to 1.0 (positive)
        """
        if not text or len(text.strip()) == 0:
            return 0.0  # Neutral for empty text

        try:
            # Tokenize input
            inputs = self.tokenizer(
                text,
                return_tensors='pt',
                max_length=512,
                truncation=True,
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Run inference
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits

            # Convert logits to probabilities
            probs = torch.nn.functional.softmax(logits, dim=1)

            # KR-FinBert-SC classes: [negative, neutral, positive]
            prob_negative = probs[0][0].item()
            prob_neutral = probs[0][1].item()
            prob_positive = probs[0][2].item()

            # Calculate sentiment score: P(positive) - P(negative)
            # Range: -1.0 to 1.0
            sentiment_score = prob_positive - prob_negative

            return round(sentiment_score, 4)

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return 0.0

    def analyze_multiple_time_weighted(self, articles: List[dict]) -> float:
        """
        Analyze multiple articles with time-weighted averaging.

        Recent articles have higher weight (linear decay).

        Args:
            articles: List of article dicts with 'title', 'content'/'summary' keys
                     Ordered from newest to oldest

        Returns:
            float: Time-weighted sentiment score (-1.0 to 1.0)
        """
        if not articles:
            return 0.0

        scores = []
        for article in articles:
            # Combine title and content/summary
            title = article.get('title', '')
            content = article.get('content', article.get('summary', ''))
            text = f"{title} {content}"

            score = self.analyze_single(text)
            scores.append(score)

        # Time-weighted average: [5, 4, 3, 2, 1] for 5 articles (newest = highest weight)
        weights = list(range(len(scores), 0, -1))
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)

        logger.debug(f"Analyzed {len(scores)} articles → weighted score: {weighted_score:.4f}")

        return round(weighted_score, 4)

    def analyze_multiple_simple_average(self, articles: List[dict]) -> float:
        """
        Analyze multiple articles with simple averaging (equal weights).

        Args:
            articles: List of article dicts with 'title', 'content'/'summary' keys

        Returns:
            float: Average sentiment score (-1.0 to 1.0)
        """
        if not articles:
            return 0.0

        scores = []
        for article in articles:
            title = article.get('title', '')
            content = article.get('content', article.get('summary', ''))
            text = f"{title} {content}"

            score = self.analyze_single(text)
            scores.append(score)

        avg_score = sum(scores) / len(scores)

        logger.debug(f"Analyzed {len(scores)} articles → avg score: {avg_score:.4f}")

        return round(avg_score, 4)
