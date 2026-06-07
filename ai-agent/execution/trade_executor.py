"""
Trade Executor Module

Executes buy/sell orders via Spring Boot API-Server → KIS API integration.
"""

import aiohttp
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    Executes filtered trading decisions via Spring Boot API-Server.

    Flow:
    1. Check user_trade_config.is_active flag via API-Server
    2. For buy decisions: Execute orders as-is
    3. For sell decisions: Check holdings first, only sell if quantity > 0
    4. POST to /api/trading/execute endpoint
    """

    def __init__(self, api_base_url: str, timeout: int = 30):
        """
        Initialize trade executor.

        Args:
            api_base_url: Spring Boot API-Server base URL (e.g., http://api-server:8080)
            timeout: HTTP request timeout in seconds
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def check_auto_trading_enabled(self, user_id: int = 1) -> bool:
        """
        Check if auto-trading is enabled for the user.

        Args:
            user_id: User ID (MVP: always 1)

        Returns:
            True if is_active flag is true, False otherwise
        """
        url = f'{self.api_base_url}/api/config/{user_id}'

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch config: {resp.status}")
                        return False

                    config = await resp.json()
                    is_active = config.get('is_active', False)

                    logger.info(f"Auto-trading status for user {user_id}: {is_active}")
                    return is_active

        except Exception as e:
            logger.error(f"Error checking auto-trading status: {e}")
            return False

    async def get_holdings(self, user_id: int = 1) -> Dict[str, int]:
        """
        Get current holdings for the user.

        Args:
            user_id: User ID (MVP: always 1)

        Returns:
            Dict mapping stock_code -> quantity
        """
        url = f'{self.api_base_url}/api/assets/holdings'

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, params={'user_id': user_id}) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch holdings: {resp.status}")
                        return {}

                    holdings_list = await resp.json()

                    # Convert list to dict: stock_code -> quantity
                    holdings_dict = {
                        item['stock_code']: item['quantity']
                        for item in holdings_list
                    }

                    logger.info(f"Current holdings: {holdings_dict}")
                    return holdings_dict

        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")
            return {}

    async def execute_order(self,
                           stock_code: str,
                           side: str,
                           quantity: int,
                           price: int = 0,
                           reason: str = "") -> Dict:
        """
        Execute a single order via API-Server.

        Args:
            stock_code: 6-digit stock code (e.g., '005930')
            side: 'BUY' or 'SELL'
            quantity: Number of shares
            price: Order price (0 = market order)
            reason: Trading reason from Gemini AI

        Returns:
            API response dict
        """
        url = f'{self.api_base_url}/api/trading/execute'

        payload = {
            'stock_code': stock_code,
            'side': side,
            'quantity': quantity,
            'price': price,
            'reason': reason
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(url, json=payload) as resp:
                    result = await resp.json()

                    if resp.status == 200:
                        logger.info(f"[{side}] {stock_code} x{quantity} executed successfully: {result}")
                    else:
                        logger.error(f"[{side}] {stock_code} x{quantity} failed: {result}")

                    return result

        except Exception as e:
            logger.error(f"Error executing order {side} {stock_code}: {e}")
            return {'success': False, 'error': str(e)}

    async def execute_trades(self,
                            filtered_decisions: Dict[str, List[Dict]],
                            user_id: int = 1) -> Dict[str, List[Dict]]:
        """
        Execute all filtered trading decisions.

        Args:
            filtered_decisions: Output from SafetyFilter.filter_decisions()
                               Contains buy_top3, sell_top3, filter_results
            user_id: User ID (MVP: always 1)

        Returns:
            Execution results dict with buy_results and sell_results lists
        """
        # Check if auto-trading is enabled
        if not await self.check_auto_trading_enabled(user_id):
            logger.warning("[Trade Execution] Auto-trading is disabled. Skipping execution.")
            return {
                'buy_results': [],
                'sell_results': [],
                'status': 'skipped',
                'reason': 'Auto-trading is disabled'
            }

        # Get current holdings
        holdings = await self.get_holdings(user_id)

        execution_results = {
            'buy_results': [],
            'sell_results': [],
            'status': 'executed',
            'executed_at': datetime.now().isoformat()
        }

        # Execute buy orders
        for item in filtered_decisions.get('buy_top3', []):
            stock_code = item['stock_code']
            reason = item.get('reason', '')
            max_quantity = item.get('max_quantity', 1)  # Use max_quantity from safety filter

            logger.info(f"[BUY] Executing order for {stock_code} (qty: {max_quantity}): {reason}")

            result = await self.execute_order(
                stock_code=stock_code,
                side='BUY',
                quantity=max_quantity,  # Use calculated max_quantity based on order_amount
                price=0,                # Market order
                reason=reason
            )

            execution_results['buy_results'].append({
                'stock_code': stock_code,
                'reason': reason,
                'quantity': max_quantity,
                'result': result
            })

        # Execute sell orders (only if holding quantity > 0)
        for item in filtered_decisions.get('sell_top3', []):
            stock_code = item['stock_code']
            reason = item.get('reason', '')

            # Check holdings
            holding_quantity = holdings.get(stock_code, 0)
            if holding_quantity <= 0:
                logger.warning(f"[SELL] {stock_code} not in holdings. Skipping.")
                execution_results['sell_results'].append({
                    'stock_code': stock_code,
                    'reason': reason,
                    'result': {'success': False, 'error': 'No holdings to sell'}
                })
                continue

            logger.info(f"[SELL] Executing order for {stock_code} x{holding_quantity}: {reason}")

            result = await self.execute_order(
                stock_code=stock_code,
                side='SELL',
                quantity=holding_quantity,  # Sell all holdings
                price=0,                     # Market order
                reason=reason
            )

            execution_results['sell_results'].append({
                'stock_code': stock_code,
                'quantity': holding_quantity,
                'reason': reason,
                'result': result
            })

        # Summary logging
        buy_count = len([r for r in execution_results['buy_results'] if r['result'].get('success')])
        sell_count = len([r for r in execution_results['sell_results'] if r['result'].get('success')])

        logger.info(f"[Trade Execution] Completed: {buy_count} buys, {sell_count} sells")

        return execution_results
