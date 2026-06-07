#!/usr/bin/env python3
"""
DART API 연동 테스트 스크립트

소수 종목으로 실제 DART API 데이터 수집 테스트
"""
import sys
import os
from datetime import date

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from collectors.dart_client import DARTAPIClient
from config.settings import get_settings
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """DART API 데이터 수집 테스트"""

    # DART API 키 설정
    DART_API_KEY = "9875cf37f9e862503115794a2cb349a4c28afdc3"

    logger.info("=" * 80)
    logger.info("DART API 데이터 수집 테스트 시작")
    logger.info("=" * 80)

    # 테스트 종목 (대형주 3개)
    test_stocks = [
        '005930',  # 삼성전자
        '000660',  # SK하이닉스
        '051910',  # LG화학
    ]

    logger.info(f"\n📊 테스트 종목: {test_stocks}")

    try:
        # 1. DARTAPIClient 초기화
        logger.info("\n[Step 1] DARTAPIClient 초기화...")
        client = DARTAPIClient(api_key=DART_API_KEY)
        logger.info("✅ Client 초기화 완료")

        # 2. Corp code 매핑 다운로드
        logger.info("\n[Step 2] Corp code 매핑 다운로드...")
        corp_code_map = client.download_corp_code_list()
        logger.info(f"✅ Corp code 매핑 완료: {len(corp_code_map)} 개 상장사")

        # 테스트 종목의 corp_code 확인
        logger.info("\n[Step 3] 테스트 종목 corp_code 확인...")
        for stock_code in test_stocks:
            corp_code = client.get_corp_code(stock_code)
            stock_name = client.corp_code_map.get(stock_code, 'Unknown')
            if corp_code:
                logger.info(f"  {stock_code} ({stock_name}) → corp_code: {corp_code}")
            else:
                logger.warning(f"  ⚠️ {stock_code}: Corp code not found")

        # 3. 최신 분기 설정 (DART 가용 분기 기준)
        logger.info("\n[Step 4] 최신 분기 설정...")

        # 실제 DART에서 확인된 최신 분기 사용
        base_year = 2025
        base_quarter = 3
        base_date = date(2025, 9, 30)

        logger.info(f"  사용 분기: {base_year}년 Q{base_quarter} (기준일: {base_date})")
        logger.info(f"  ℹ️  DART API에서 확인된 최신 공시 분기입니다.")

        # 4. 재무 데이터 수집
        logger.info("\n[Step 5] 재무 데이터 수집 시작...")
        df = client.collect_financials_for_stocks(test_stocks, base_date=base_date)

        # 5. 결과 출력
        logger.info("\n[Step 6] 수집 결과:")
        logger.info("=" * 80)

        if df.empty:
            logger.error("❌ 수집된 데이터 없음!")
            return

        logger.info(f"✅ 수집 성공: {len(df)} 개 종목\n")

        # 데이터 품질 확인
        for idx, row in df.iterrows():
            logger.info(f"📈 {row['stock_code']} ({row['stock_name']})")
            logger.info(f"   기준일: {row['base_date']}")
            logger.info(f"   PER: {row['per'] if row['per'] else 'N/A (적자 또는 결측)'}")
            logger.info(f"   ROE: {row['roe']:.2f}%" if row['roe'] else "   ROE: N/A")
            logger.info(f"   영업이익률: {row['operating_margin']:.2f}%" if row['operating_margin'] else "   영업이익률: N/A")
            logger.info("")

        # 6. 데이터베이스 저장 테스트
        logger.info("\n[Step 7] 데이터베이스 저장 시작...")
        logger.info("💾 테스트 데이터를 stock_financial 테이블에 저장합니다...")

        success = client.save_to_database(df)

        if success:
            logger.info("✅ 데이터베이스 저장 완료!")

            # 저장된 데이터 확인
            logger.info("\n[Step 8] 저장된 데이터 확인...")
            saved_df = client.get_latest_financials(test_stocks)
            logger.info(f"DB 조회 결과: {len(saved_df)} 개 종목\n")
            logger.info(saved_df.to_string())
        else:
            logger.error("❌ 데이터베이스 저장 실패")

        logger.info("\n" + "=" * 80)
        logger.info("✅ DART API 테스트 완료!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"\n❌ 테스트 실패: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
