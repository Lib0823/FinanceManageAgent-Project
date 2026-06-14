#!/usr/bin/env python3
"""
KIS API 거래내역 직접 조회 스크립트
주식일별주문체결조회 API를 직접 호출하여 응답 확인
"""

import requests
import json
from datetime import datetime, timedelta

# KIS 계정 정보 (dev_note.txt에서 제공받은 정보)
APP_KEY = "YOUR_KIS_APP_KEY"
APP_SECRET = "YOUR_KIS_APP_SECRET"
ACCOUNT = "YOUR_KIS_ACCOUNT_NO"
ACCOUNT_PRODUCT_CODE = "01"  # 종합계좌

# KIS API Base URL (모의투자)
BASE_URL = "https://openapivts.koreainvestment.com:29443"

def get_access_token():
    """KIS Access Token 발급"""
    url = f"{BASE_URL}/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }

    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    else:
        print(f"❌ Token 발급 실패: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def get_trade_history(access_token):
    """주식일별주문체결조회 (VTTC0081R)"""
    url = f"{BASE_URL}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"

    # 조회 기간: 최근 3개월
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "VTTC0081R",  # 모의투자 주식일별주문체결조회
        "custtype": "P"
    }

    params = {
        "CANO": ACCOUNT,
        "ACNT_PRDT_CD": ACCOUNT_PRODUCT_CODE,
        "INQR_STRT_DT": start_date.strftime("%Y%m%d"),
        "INQR_END_DT": end_date.strftime("%Y%m%d"),
        "SLL_BUY_DVSN_CD": "00",  # 00: 전체, 01: 매도, 02: 매수
        "INQR_DVSN": "00",  # 00: 역순
        "PDNO": "",  # 전체 종목
        "CCLD_DVSN": "01",  # 00: 전체, 01: 체결, 02: 미체결
        "ORD_GNO_BRNO": "",
        "ODNO": "",
        "INQR_DVSN_3": "00",
        "INQR_DVSN_1": "",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }

    print(f"\n📅 조회 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print(f"🔍 조회 시작...\n")

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()

        print(f"✅ API 응답 코드: {data.get('rt_cd')} ({data.get('msg1')})")
        print(f"   메시지 코드: {data.get('msg_cd')}")

        output1 = data.get('output1', [])
        output2 = data.get('output2', {})

        print(f"\n📊 총 주문 수량: {output2.get('tot_ord_qty', '0')}")
        print(f"📊 총 체결 수량: {output2.get('tot_ccld_qty', '0')}")
        print(f"📊 총 체결 금액: {output2.get('tot_ccld_amt', '0')}")
        print(f"\n📋 거래내역 개수: {len(output1)}개\n")

        if len(output1) == 0:
            print("⚠️  거래내역이 비어있습니다!")
            print("   가능한 원인:")
            print("   1. 실제로 거래내역이 없음")
            print("   2. 조회 기간 내에 체결된 거래가 없음")
            print("   3. 계좌번호 또는 계좌상품코드가 틀림")
            print("   4. CCLD_DVSN 파라미터 문제 (00: 전체, 01: 체결, 02: 미체결)")
        else:
            print("=" * 80)
            for idx, item in enumerate(output1, 1):
                print(f"\n[{idx}] 주문일자: {item.get('ord_dt')} {item.get('ord_tmd')}")
                print(f"    주문번호: {item.get('odno')}")
                print(f"    매매구분: {item.get('sll_buy_dvsn_cd_name')} ({item.get('sll_buy_dvsn_cd')})")
                print(f"    종목명: {item.get('prdt_name')} ({item.get('pdno')})")
                print(f"    주문수량: {item.get('ord_qty')}주 @ {item.get('ord_unpr')}원")
                print(f"    체결수량: {item.get('tot_ccld_qty')}주")
                print(f"    평균가: {item.get('avg_prvs')}원")
                print(f"    체결금액: {item.get('tot_ccld_amt')}원")
                print(f"    취소여부: {item.get('cncl_yn')}")
                print(f"    잔여수량: {item.get('rmn_qty')}주")

                if idx >= 10:
                    print(f"\n   ... 외 {len(output1) - 10}건 더 있음")
                    break
            print("=" * 80)

        # 전체 JSON 저장
        with open('/tmp/kis_history_response.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 전체 응답 저장: /tmp/kis_history_response.json")

    else:
        print(f"❌ API 호출 실패: {response.status_code}")
        print(f"   Response: {response.text}")

if __name__ == "__main__":
    print("=" * 80)
    print("KIS API 거래내역 직접 조회")
    print("=" * 80)

    # 1. Access Token 발급
    print("\n🔑 Access Token 발급 중...")
    access_token = get_access_token()

    if not access_token:
        print("❌ Token 발급 실패")
        exit(1)

    print(f"✅ Token 발급 성공: {access_token[:20]}...")

    # 2. 거래내역 조회
    get_trade_history(access_token)

    print("\n" + "=" * 80)
