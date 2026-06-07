#!/usr/bin/env python3
"""
DART API 가용 분기 확인 스크립트

여러 분기를 시도해서 실제 공시된 데이터가 있는 분기를 찾음
"""
import sys
import os
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from collectors.dart_client import DARTAPIClient
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    DART_API_KEY = "9875cf37f9e862503115794a2cb349a4c28afdc3"

    # 삼성전자로 테스트
    test_stock = '005930'

    logger.info("=" * 80)
    logger.info("DART 가용 분기 확인 (삼성전자 기준)")
    logger.info("=" * 80)

    client = DARTAPIClient(api_key=DART_API_KEY)

    # Corp code 매핑
    logger.info("\nCorp code 매핑 중...")
    client.download_corp_code_list()
    corp_code = client.get_corp_code(test_stock)
    logger.info(f"삼성전자 corp_code: {corp_code}")

    # 테스트할 분기 리스트
    test_cases = [
        # 2025년
        ("2025", "11013", date(2025, 9, 30), "2025 Q3"),
        ("2025", "11012", date(2025, 6, 30), "2025 Q2 (반기)"),
        ("2025", "11011", date(2025, 3, 31), "2025 Q1"),

        # 2024년
        ("2024", "11014", date(2024, 12, 31), "2024 연간 (사업보고서)"),
        ("2024", "11013", date(2024, 9, 30), "2024 Q3"),
        ("2024", "11012", date(2024, 6, 30), "2024 Q2 (반기)"),
        ("2024", "11011", date(2024, 3, 31), "2024 Q1"),

        # 2023년
        ("2023", "11014", date(2023, 12, 31), "2023 연간 (사업보고서)"),
    ]

    logger.info("\n분기별 데이터 확인 중...\n")

    available_quarters = []

    for year, report_code, base_date, label in test_cases:
        logger.info(f"시도: {label} (year={year}, report={report_code})")

        financial_data = client.get_financial_statements(corp_code, year, report_code)

        if financial_data and financial_data.get('status') == '000':
            metrics = client.extract_financial_metrics(financial_data)
            if metrics:
                logger.info(f"  ✅ 데이터 있음!")
                logger.info(f"     ROE: {metrics.get('roe')}")
                logger.info(f"     영업이익률: {metrics.get('operating_margin')}")
                available_quarters.append((year, report_code, base_date, label))
        else:
            logger.info(f"  ❌ 데이터 없음")

        logger.info("")

    logger.info("=" * 80)
    logger.info(f"✅ 가용한 분기: {len(available_quarters)}개")
    logger.info("=" * 80)

    if available_quarters:
        logger.info("\n사용 가능한 분기:")
        for year, report, base_date, label in available_quarters:
            logger.info(f"  - {label} (base_date: {base_date})")

        # 가장 최신 분기 추천
        latest = available_quarters[0]
        logger.info(f"\n💡 추천: {latest[3]} (base_date: {latest[2]})")
    else:
        logger.error("\n❌ 사용 가능한 분기를 찾지 못했습니다!")


if __name__ == "__main__":
    main()
