"""Internal API client — ai-agent → api-server service-to-service channel.

멀티유저 파이프라인용. 사용자 KIS 키는 api-server(DB, Jasypt)에만 있으며,
ai-agent 는 식별자/보유종목만 받는다. 인증은 공유 시크릿 헤더
(X-Internal-Api-Key)로 수행한다. 모든 호출은 실패 시 빈 결과로 degrade 하여
파이프라인을 막지 않는다.
"""
import logging
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class InternalApiClient:
    """api-server 의 /internal/** 엔드포인트 비동기 클라이언트."""

    def __init__(self, base_url: str, api_key: Optional[str], timeout: int = 30):
        """
        Args:
            base_url: api-server base URL (컨텍스트패스 /api 제외, 예: http://api-server:7070)
            api_key: X-Internal-Api-Key 값 (INTERNAL_API_KEY)
            timeout: HTTP 타임아웃(초)
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def _headers(self) -> Dict[str, str]:
        return {"X-Internal-Api-Key": self.api_key or ""}

    async def get_active_auto_trading_users(self) -> List[Dict]:
        """
        자동매매 활성 사용자 목록 조회.

        Returns:
            [{user_id, kis_account_id, order_amount, max_holdings, order_type}, ...]
            실패 시 빈 리스트.
        """
        url = f"{self.base_url}/api/internal/auto-trading/users"
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=self._headers) as resp:
                    if resp.status != 200:
                        logger.error(f"Active users fetch failed: HTTP {resp.status}")
                        return []
                    body = await resp.json(content_type=None)
            users = (body or {}).get("data") or []
            logger.info(f"Fetched {len(users)} active auto-trading users")
            return users
        except Exception as e:
            logger.error(f"Active users fetch error: {e}")
            return []

    async def get_user_holdings(self, user_id: int) -> List[str]:
        """
        특정 사용자의 보유 종목코드 목록 조회 (api-server 가 사용자 KIS 키로 KIS 조회).

        Args:
            user_id: 사용자 id

        Returns:
            보유 종목코드 리스트(6자리). 보유 없음/조회 실패 시 빈 리스트.
        """
        url = f"{self.base_url}/api/internal/users/{user_id}/holdings"
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=self._headers) as resp:
                    if resp.status != 200:
                        logger.warning(f"Holdings fetch for user {user_id} failed: HTTP {resp.status}")
                        return []
                    body = await resp.json(content_type=None)
            data = (body or {}).get("data") or {}
            holdings = data.get("holdings") or []
            codes = [h.get("stockCode") for h in holdings if h.get("stockCode")]
            logger.info(f"User {user_id}: {len(codes)} holdings")
            return codes
        except Exception as e:
            logger.warning(f"Holdings fetch error for user {user_id}: {e}")
            return []
