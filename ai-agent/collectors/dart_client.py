"""DART (금융감독원 전자공시시스템) Open API client for financial data collection."""
import logging
import zipfile
import io
import xml.etree.ElementTree as ET
from typing import Optional, Dict, List
from datetime import date
import requests
import pandas as pd
from sqlalchemy import create_engine, text

from config.settings import get_settings
from config.constants import STOCK_NAMES

logger = logging.getLogger(__name__)


class DARTAPIClient:
    """
    DART Open API client for collecting quarterly financial data.

    API Documentation: https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001

    Features:
    - Corp code mapping (stock_code → corp_code)
    - Quarterly financial statement fetching
    - PER, ROE, operating margin extraction
    - Database integration
    """

    BASE_URL = "https://opendart.fss.or.kr/api"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DART API client.

        Args:
            api_key: DART API key (if None, loads from settings)
        """
        settings = get_settings()
        self.api_key = api_key or settings.dart_api_key

        if not self.api_key:
            raise ValueError("DART API key not configured. Set DART_API_KEY environment variable.")

        self.corp_code_map: Dict[str, str] = {}  # stock_code → corp_code
        self.engine = create_engine(settings.database_url)

        logger.info("DARTAPIClient initialized")

    def download_corp_code_list(self) -> Dict[str, str]:
        """
        Download corp_code.xml from DART and build stock_code → corp_code mapping.

        DART API: https://opendart.fss.or.kr/api/corpCode.xml

        Returns:
            Dict mapping stock_code (6-digit) to corp_code (8-digit)
        """
        logger.info("Downloading corp_code list from DART...")

        url = f"{self.BASE_URL}/corpCode.xml"
        params = {'crtfc_key': self.api_key}

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            # Response is a ZIP file containing CORPCODE.xml
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                with z.open('CORPCODE.xml') as xml_file:
                    tree = ET.parse(xml_file)
                    root = tree.getroot()

                    corp_code_map = {}

                    for corp in root.findall('list'):
                        corp_code = corp.find('corp_code').text
                        stock_code = corp.find('stock_code').text
                        corp_name = corp.find('corp_name').text

                        # Filter: Only listed companies with valid stock_code
                        if stock_code and stock_code.strip():
                            corp_code_map[stock_code.strip()] = corp_code.strip()
                            logger.debug(f"Mapped: {stock_code} ({corp_name}) → {corp_code}")

                    self.corp_code_map = corp_code_map
                    logger.info(f"Corp code mapping complete: {len(corp_code_map)} listed companies")

                    return corp_code_map

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download corp_code list: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse corp_code XML: {e}")
            raise

    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """
        Get corp_code for a given stock_code.

        Args:
            stock_code: 6-digit stock code (e.g., '005930')

        Returns:
            8-digit corp_code or None if not found
        """
        if not self.corp_code_map:
            self.download_corp_code_list()

        return self.corp_code_map.get(stock_code)

    def get_financial_statements(
        self,
        corp_code: str,
        bsns_year: str,
        reprt_code: str = "11011"
    ) -> Optional[Dict]:
        """
        Fetch financial statements for a company.

        DART API: https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json

        Args:
            corp_code: 8-digit corp code
            bsns_year: Business year (e.g., '2026')
            reprt_code: Report code
                - 11011: 1분기보고서
                - 11012: 반기보고서
                - 11013: 3분기보고서
                - 11014: 사업보고서 (연간)

        Returns:
            Dict with financial data or None if failed
        """
        url = f"{self.BASE_URL}/fnlttSinglAcntAll.json"

        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': reprt_code,
            'fs_div': 'CFS'  # 연결재무제표 (CFS) vs 개별재무제표 (OFS)
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if data.get('status') == '013':
                logger.warning(f"No data available for corp_code={corp_code}, year={bsns_year}, report={reprt_code}")
                return None

            if data.get('status') != '000':
                logger.error(f"DART API error: {data.get('message')}")
                return None

            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch financial statements: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to parse financial data: {e}")
            return None

    def extract_financial_metrics(self, financial_data: Dict) -> Optional[Dict]:
        """
        Extract PER, ROE, operating margin from financial statements.

        DART financial data structure:
        {
            "status": "000",
            "message": "정상",
            "list": [
                {
                    "rcept_no": "...",
                    "reprt_code": "11011",
                    "bsns_year": "2026",
                    "account_nm": "당기순이익",
                    "thstrm_amount": "1234567890",
                    ...
                },
                ...
            ]
        }

        Args:
            financial_data: Raw DART API response

        Returns:
            Dict with {per, roe, operating_margin} or None
        """
        if not financial_data or 'list' not in financial_data:
            return None

        df = pd.DataFrame(financial_data['list'])

        # Extract key metrics (단위: 원)
        metrics = {}

        for _, row in df.iterrows():
            account_name = row.get('account_nm', '')
            amount_str = row.get('thstrm_amount', '0')

            # Convert string to number (remove commas)
            try:
                amount = float(amount_str.replace(',', ''))
            except (ValueError, AttributeError):
                amount = 0

            # Map account names to metrics
            if '당기순이익' in account_name:
                metrics['net_income'] = amount
            elif '매출액' in account_name or '영업수익' in account_name:
                metrics['revenue'] = amount
            elif '영업이익' in account_name:
                metrics['operating_income'] = amount
            elif '자본총계' in account_name or '자본' in account_name:
                if 'equity' not in metrics:  # Take first occurrence
                    metrics['equity'] = amount

        # Calculate financial ratios
        result = {}

        # PER: Cannot calculate from financial statements alone (need stock price)
        # Set to None - should be calculated separately with market data
        result['per'] = None

        # ROE: (당기순이익 / 자본총계) × 100
        if metrics.get('net_income') and metrics.get('equity') and metrics['equity'] != 0:
            result['roe'] = round((metrics['net_income'] / metrics['equity']) * 100, 2)
        else:
            result['roe'] = None

        # Operating Margin: (영업이익 / 매출액) × 100
        if metrics.get('operating_income') and metrics.get('revenue') and metrics['revenue'] != 0:
            result['operating_margin'] = round((metrics['operating_income'] / metrics['revenue']) * 100, 2)
        else:
            result['operating_margin'] = None

        logger.debug(f"Extracted metrics: {result}")

        return result

    def collect_financials_for_stocks(
        self,
        stock_codes: List[str],
        base_date: Optional[date] = None
    ) -> pd.DataFrame:
        """
        Collect latest quarterly financial data for multiple stocks.

        Args:
            stock_codes: List of 6-digit stock codes
            base_date: Base date for financial data (defaults to latest quarter)

        Returns:
            DataFrame with columns: stock_code, stock_name, base_date, per, roe, operating_margin
        """
        if base_date is None:
            # Default to latest quarter end (Q1 2026: 2026-03-31)
            base_date = date(2026, 3, 31)

        # Determine business year and report code from base_date
        year = str(base_date.year)
        month = base_date.month

        if month <= 3:
            reprt_code = "11011"  # Q1
        elif month <= 6:
            reprt_code = "11012"  # Q2 (반기)
        elif month <= 9:
            reprt_code = "11013"  # Q3
        else:
            reprt_code = "11014"  # Q4 (연간)

        logger.info(f"Collecting financial data for {len(stock_codes)} stocks (year={year}, report={reprt_code})")

        # Load corp_code mapping
        if not self.corp_code_map:
            self.download_corp_code_list()

        results = []

        for stock_code in stock_codes:
            try:
                stock_name = STOCK_NAMES.get(stock_code, 'Unknown')

                # Get corp_code
                corp_code = self.get_corp_code(stock_code)
                if not corp_code:
                    logger.warning(f"Corp code not found for {stock_code} ({stock_name}), skipping")
                    continue

                # Fetch financial statements
                logger.info(f"Fetching financials for {stock_code} ({stock_name}) → corp_code={corp_code}")
                financial_data = self.get_financial_statements(corp_code, year, reprt_code)

                if not financial_data:
                    logger.warning(f"No financial data for {stock_code}, skipping")
                    continue

                # Extract metrics
                metrics = self.extract_financial_metrics(financial_data)

                if metrics:
                    results.append({
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'base_date': base_date,
                        'per': metrics.get('per'),
                        'roe': metrics.get('roe'),
                        'operating_margin': metrics.get('operating_margin')
                    })
                    logger.info(f"✅ {stock_code}: ROE={metrics.get('roe')}, OpMargin={metrics.get('operating_margin')}")
                else:
                    logger.warning(f"Failed to extract metrics for {stock_code}")

            except Exception as e:
                logger.error(f"Error processing {stock_code}: {e}")
                continue

        df = pd.DataFrame(results)
        logger.info(f"Collected financials for {len(df)} stocks")

        return df

    def save_to_database(self, df: pd.DataFrame) -> bool:
        """
        Save financial data to stock_financial table.

        Args:
            df: DataFrame with financial data

        Returns:
            True if successful
        """
        if df.empty:
            logger.warning("No data to save to database")
            return False

        try:
            # Delete existing data for this base_date
            base_date = df['base_date'].iloc[0]

            with self.engine.connect() as conn:
                delete_query = text("DELETE FROM stock_financial WHERE base_date = :base_date")
                result = conn.execute(delete_query, {'base_date': base_date})
                conn.commit()
                logger.info(f"Deleted {result.rowcount} existing records for {base_date}")

            # Insert new data
            df.to_sql('stock_financial', self.engine, if_exists='append', index=False)
            logger.info(f"Saved {len(df)} financial records to database")

            return True

        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            return False

    def get_latest_financials(self, stock_codes: List[str]) -> pd.DataFrame:
        """
        Retrieve latest quarterly financial metrics for given stocks from database.

        This method is kept for backward compatibility with existing code.

        Args:
            stock_codes: List of 6-digit stock codes

        Returns:
            DataFrame with columns: stock_code, per, roe, operating_margin
        """
        query = text("""
            WITH latest_quarter AS (
                SELECT
                    stock_code,
                    base_date,
                    per,
                    roe,
                    operating_margin,
                    ROW_NUMBER() OVER (PARTITION BY stock_code ORDER BY base_date DESC) as rn
                FROM stock_financial
                WHERE stock_code = ANY(:codes)
            )
            SELECT stock_code, per, roe, operating_margin
            FROM latest_quarter
            WHERE rn = 1
            ORDER BY stock_code
        """)

        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, params={'codes': stock_codes})

        return df


# Backward compatibility: Alias DARTClient to DARTAPIClient
class DARTClient(DARTAPIClient):
    """Backward compatibility alias for existing code."""
    pass
