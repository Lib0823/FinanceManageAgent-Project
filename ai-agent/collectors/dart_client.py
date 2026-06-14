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
        reprt_code: str = "11011",
        fs_div: str = "CFS"
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
            fs_div: 재무제표 구분
                - CFS: 연결재무제표 (기본값)
                - OFS: 개별/별도재무제표 (연결 미작성 기업 대비 fallback)

        Returns:
            Dict with financial data or None if failed
        """
        url = f"{self.BASE_URL}/fnlttSinglAcntAll.json"

        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': reprt_code,
            'fs_div': fs_div  # 연결재무제표 (CFS) vs 개별재무제표 (OFS)
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if data.get('status') == '013':
                logger.warning(
                    f"No data (status 013) for corp_code={corp_code}, year={bsns_year}, "
                    f"report={reprt_code}, fs_div={fs_div}"
                )
                return None

            if data.get('status') != '000':
                logger.error(
                    f"DART API error for corp_code={corp_code}, fs_div={fs_div}: "
                    f"status={data.get('status')}, message={data.get('message')}"
                )
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

        # 추출 대상 지표 (단위: 원). 지배기업 소유주지분 우선값을 별도로 보관.
        metrics: Dict[str, float] = {}
        equity_controlling: Optional[float] = None  # 지배기업 소유주지분 자본총계
        net_income_controlling: Optional[float] = None  # 지배기업 소유주지분 순이익

        def _parse_amount(value: str) -> Optional[float]:
            """thstrm_amount 문자열을 숫자로 변환. 결측/비정상 값은 None."""
            try:
                cleaned = str(value).replace(',', '').strip()
                if cleaned in ('', '-'):
                    return None
                return float(cleaned)
            except (ValueError, AttributeError, TypeError):
                return None

        # 우선 매칭 기준: 표준 XBRL account_id + 재무제표 구분(sj_div).
        # DART는 한글 account_nm을 회사·보고서별로 다르게 표기하므로(예: 연결 사업보고서의
        # 순이익이 '반기순이익'/'분기순이익'으로 표기, '기타영업수익'이 '영업수익'을 포함)
        # account_id로 매칭해야 안정적이다. account_id가 없으면 한글명으로 폴백한다.
        for _, row in df.iterrows():
            account_id = str(row.get('account_id', '')).strip()
            account_name = str(row.get('account_nm', '')).strip()
            sj_div = str(row.get('sj_div', '')).strip()  # BS=재무상태표, IS=손익계산서, CIS=포괄손익
            amount = _parse_amount(row.get('thstrm_amount', ''))

            if amount is None:
                continue

            # --- 순이익 (손익계산서 IS/CIS) ---
            # 지배기업 소유주지분 순이익 우선, 없으면 전체 당기순이익(ifrs-full_ProfitLoss)
            if account_id == 'ifrs-full_ProfitLossAttributableToOwnersOfParent':
                if net_income_controlling is None:
                    net_income_controlling = amount
            elif account_id == 'ifrs-full_ProfitLoss':
                if metrics.get('net_income') is None:
                    metrics['net_income'] = amount

            # --- 영업이익 (dart_OperatingIncomeLoss) ---
            elif account_id == 'dart_OperatingIncomeLoss':
                if metrics.get('operating_income') is None:
                    metrics['operating_income'] = amount

            # --- 매출액 (ifrs-full_Revenue). '기타영업수익' 등 유사 계정 오매칭 방지 ---
            elif account_id == 'ifrs-full_Revenue':
                if metrics.get('revenue') is None:
                    metrics['revenue'] = amount

            # --- 자본총계 (ifrs-full_Equity, 재무상태표 BS 한정 → 자본변동표 SCE 중복 제외) ---
            elif account_id == 'ifrs-full_EquityAttributableToOwnersOfParent' and sj_div == 'BS':
                if equity_controlling is None:
                    equity_controlling = amount
            elif account_id == 'ifrs-full_Equity' and sj_div == 'BS':
                if metrics.get('equity') is None:
                    metrics['equity'] = amount

            # --- account_id가 비어있는 경우 한글명 기반 폴백 ---
            elif not account_id:
                if '당기순이익' in account_name and metrics.get('net_income') is None:
                    metrics['net_income'] = amount
                elif '영업이익' in account_name and '영업이익률' not in account_name \
                        and metrics.get('operating_income') is None:
                    metrics['operating_income'] = amount
                elif account_name == '매출액' and metrics.get('revenue') is None:
                    metrics['revenue'] = amount
                elif ('자본총계' in account_name or '총자본' in account_name) \
                        and metrics.get('equity') is None:
                    metrics['equity'] = amount

        # ROE/PER 계산 시 지배기업 소유주지분 값을 우선 적용
        net_income = net_income_controlling if net_income_controlling is not None else metrics.get('net_income')
        equity = equity_controlling if equity_controlling is not None else metrics.get('equity')
        operating_income = metrics.get('operating_income')
        revenue = metrics.get('revenue')

        # Calculate financial ratios
        result: Dict[str, Optional[float]] = {}

        # PER: 재무제표만으로는 산출 불가 (현재 주가·발행주식수 필요).
        # 설계 결정에 따라 None 유지 → Gemini 프롬프트에서 "적자 또는 결측" 표시.
        # PER = current_price / EPS, EPS = net_income / shares_outstanding 이며,
        # current_price(시세)와 shares_outstanding(발행주식수)은 본 재무제표 응답에
        # 포함되지 않는다. 외부 API(KIS 시세 등) 도입은 본 작업 범위(2개 파일)와
        # 의존성 추가 금지 제약을 벗어나므로 None으로 둔다.
        result['per'] = None

        # ROE: (당기순이익 / 자본총계) × 100. 입력 결측·자본 0이면 None 유지 (설계: 결측 보존).
        if net_income is not None and equity is not None and equity != 0:
            result['roe'] = round((net_income / equity) * 100, 2)
        else:
            result['roe'] = None

        # Operating Margin: (영업이익 / 매출액) × 100. 입력 결측·매출 0이면 None 유지.
        if operating_income is not None and revenue is not None and revenue != 0:
            result['operating_margin'] = round((operating_income / revenue) * 100, 2)
        else:
            result['operating_margin'] = None

        logger.debug(f"Extracted metrics: {result} (raw: net_income={net_income}, equity={equity}, "
                     f"operating_income={operating_income}, revenue={revenue})")

        return result

    @staticmethod
    def _base_date_to_report_code(base_date: date) -> str:
        """
        분기 종료일(base_date) → DART 보고서 코드(reprt_code) 변환.

        DART 공식 reprt_code 매핑 (분기 종료일 → 보고서 코드):
            - Q1 (3/31)  → 11013 (1분기보고서, 3개월 누적)
            - Q2 (6/30)  → 11012 (반기보고서, 6개월 누적)
            - Q3 (9/30)  → 11014 (3분기보고서, 9개월 누적)
            - Q4 (12/31) → 11011 (사업보고서, 연간 누적)

        ⚠️ DART 코드는 11011=사업(연간), 11012=반기, 11013=1분기, 11014=3분기 이다.
        (이전 구현은 11011↔Q1, 11014↔Q4 로 뒤바뀌어 12/31 기준일에 3분기(9개월)
        보고서를 조회 → ROE/이익률이 연간 대비 과소 산출되는 버그가 있었음.)

        Args:
            base_date: 분기 종료일

        Returns:
            DART reprt_code 문자열
        """
        month = base_date.month
        if month <= 3:
            return "11013"  # Q1 (1분기보고서)
        elif month <= 6:
            return "11012"  # Q2 (반기보고서)
        elif month <= 9:
            return "11014"  # Q3 (3분기보고서)
        else:
            return "11011"  # Q4 (사업보고서, 연간)

    @staticmethod
    def _previous_quarter_end(base_date: date) -> date:
        """
        직전 분기 종료일 계산 (연도 롤오버 처리).

        예: 2026-03-31(Q1) → 2025-12-31(Q4) → 2025-09-30(Q3) → 2025-06-30(Q2) → ...

        Args:
            base_date: 기준 분기 종료일

        Returns:
            직전 분기의 종료일
        """
        month = base_date.month
        if month <= 3:
            # Q1 → 직전 연도 Q4 (12/31)
            return date(base_date.year - 1, 12, 31)
        elif month <= 6:
            # Q2 → Q1 (3/31)
            return date(base_date.year, 3, 31)
        elif month <= 9:
            # Q3 → Q2 (6/30)
            return date(base_date.year, 6, 30)
        else:
            # Q4 → Q3 (9/30)
            return date(base_date.year, 9, 30)

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

        # Determine business year and report code from base_date (분기 매핑은 한 곳에서 처리)
        year = str(base_date.year)
        reprt_code = self._base_date_to_report_code(base_date)

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
                    logger.warning(f"[SKIP] {stock_code} ({stock_name}): corp_code not found in DART mapping")
                    continue

                # Fetch financial statements (연결 CFS 우선)
                logger.info(f"Fetching financials for {stock_code} ({stock_name}) → corp_code={corp_code}")
                financial_data = self.get_financial_statements(corp_code, year, reprt_code, fs_div='CFS')

                # 연결재무제표 미작성(주로 중소형사 status 013) 시 개별/별도(OFS)로 재시도
                if not financial_data:
                    logger.warning(
                        f"[RETRY] {stock_code} ({stock_name}): no CFS (연결) data, "
                        f"retrying with OFS (개별/별도)"
                    )
                    financial_data = self.get_financial_statements(corp_code, year, reprt_code, fs_div='OFS')

                if not financial_data:
                    logger.warning(
                        f"[SKIP] {stock_code} ({stock_name}): no financial data in CFS or OFS "
                        f"(year={year}, report={reprt_code})"
                    )
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
                    logger.warning(
                        f"[SKIP] {stock_code} ({stock_name}): extract_financial_metrics returned None"
                    )

            except Exception as e:
                logger.error(f"Error processing {stock_code}: {e}")
                continue

        df = pd.DataFrame(results)
        logger.info(f"Collected financials for {len(df)} stocks")

        return df

    def collect_financials_with_fallback(
        self,
        stock_codes: List[str],
        start_base_date: Optional[date] = None,
        max_lookback_quarters: int = 5
    ) -> tuple[pd.DataFrame, Optional[date]]:
        """
        Collect quarterly financials with quarter-by-quarter fallback.

        DART 환경에 따라 최신 분기가 아직 공시/적재되지 않아 모든 종목에서
        status 013(데이터 없음)이 반환될 수 있다. 이때 직전 분기로 한 칸씩
        거슬러 올라가며 실제로 데이터가 잡히는 가장 최신(MOST RECENT) 분기를
        찾아 반환한다. (예: Q1 2026 → Q4 2025 → Q3 2025 → ...)

        성공 판정 임계치:
            - 종목 수가 1개일 때: 1개 이상 수집되면 성공
            - 종목 수가 2개 이상일 때: 전체의 50% 이상 수집되면 성공
        (소수 종목 테스트와 실전 30종목 모두 합리적으로 동작하도록 둘 중 큰 쪽 기준 적용)

        Args:
            stock_codes: 6자리 종목코드 리스트
            start_base_date: 탐색 시작 분기 종료일 (None이면 Q1 2026)
            max_lookback_quarters: 최대 탐색 분기 수 (시작 분기 포함)

        Returns:
            (DataFrame, base_date) 튜플.
            성공 시 해당 분기의 DataFrame과 그 분기 종료일을 반환하고,
            모든 분기 실패 시 빈 DataFrame과 None을 반환한다.
        """
        if start_base_date is None:
            start_base_date = date(2026, 3, 31)

        # 성공 임계치: 전체의 50% 이상 또는 최소 1개 (둘 중 큰 값)
        threshold = max(1, len(stock_codes) // 2)

        # corp_code 매핑은 분기 루프마다 재다운로드하지 않도록 미리 1회 로드
        if not self.corp_code_map:
            self.download_corp_code_list()

        current_base_date = start_base_date

        for attempt in range(max_lookback_quarters):
            reprt_code = self._base_date_to_report_code(current_base_date)
            logger.info(
                f"[Fallback {attempt + 1}/{max_lookback_quarters}] "
                f"Trying quarter base_date={current_base_date} "
                f"(year={current_base_date.year}, report={reprt_code})"
            )

            df = self.collect_financials_for_stocks(
                stock_codes=stock_codes,
                base_date=current_base_date
            )

            collected = len(df)
            if not df.empty and collected >= threshold:
                logger.info(
                    f"[Fallback] Success at base_date={current_base_date}: "
                    f"collected {collected}/{len(stock_codes)} stocks "
                    f"(threshold={threshold})"
                )
                return df, current_base_date

            logger.warning(
                f"[Fallback] Insufficient data at base_date={current_base_date}: "
                f"collected {collected}/{len(stock_codes)} (threshold={threshold}), "
                f"stepping back to previous quarter"
            )

            # 직전 분기로 이동 (연도 롤오버 처리)
            current_base_date = self._previous_quarter_end(current_base_date)

        logger.warning(
            f"[Fallback] No quarter yielded data after trying {max_lookback_quarters} "
            f"quarters back from {start_base_date}"
        )
        return pd.DataFrame(), None

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
