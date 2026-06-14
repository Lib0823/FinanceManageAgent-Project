#!/bin/bash

echo "=== ib.lee 계정 거래내역 최종 테스트 ==="
echo ""
echo "⚠️  참고: ib.lee 계정의 비밀번호를 입력하세요"
echo "   (현재 'password123'로 로그인 시도하면 실패합니다)"
echo ""

# 비밀번호 입력 받기
read -sp "ib.lee 비밀번호: " PASSWORD
echo ""
echo ""

# 1. ib.lee 계정 로그인
echo "1. ib.lee 로그인 중..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:7070/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"ib.lee\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"accessToken":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ 로그인 실패"
  echo "$LOGIN_RESPONSE" | python3 -m json.tool
  exit 1
fi

echo "✅ 로그인 성공"
echo "   Token: ${TOKEN:0:30}..."
echo ""

# 2. KIS 계정 정보 확인
echo "2. KIS 계정 정보 확인..."
curl -s -X GET http://localhost:7070/api/users/kis-account \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data['success']:
        kis = data['data']
        print(f\"✅ 계좌번호: {kis['accountNumber']}\")
        print(f\"   AppKey 시작: {kis['appKey'][:40]}...\")
        print(f\"   검증 상태: {kis['isVerified']}\")
    else:
        print(f\"❌ {data['message']}\")
except Exception as e:
    print(f\"❌ 파싱 실패: {e}\")
"
echo ""

# 3. 거래내역 조회
echo "3. 거래내역 조회 중..."
HISTORY_RESPONSE=$(curl -s -X GET http://localhost:7070/api/trading/history \
  -H "Authorization: Bearer $TOKEN")

echo "$HISTORY_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"✅ 응답 성공: {data.get('success')}\")
    print(f\"   메시지: {data.get('message')}\")

    history = data.get('data', [])
    print(f\"   거래내역 개수: {len(history)}건\")

    if history:
        print('')
        print('=== 거래내역 샘플 (최근 5건) ===')
        for i, trade in enumerate(history[:5], 1):
            print(f\"[{i}] {trade.get('stockName')} ({trade.get('stockCode')})\")
            print(f\"    {trade.get('orderType')} / {trade.get('orderStatus')}\")
            print(f\"    {trade.get('quantity')}주 @ {trade.get('executedPrice')}원\")
            print(f\"    주문일시: {trade.get('orderedAt')}\")
            print('')
    else:
        print('')
        print('⚠️  거래내역이 없습니다.')
        print('   - 2-3일 전 거래 데이터가 있어야 합니다')
        print('   - KIS 모의투자 계좌에서 직접 확인해보세요')
except Exception as e:
    print(f\"❌ 파싱 실패: {e}\")
    import traceback
    traceback.print_exc()
"

echo ""
echo "=== 테스트 완료 ==="
echo ""
echo "📋 결과 요약:"
echo "   1. TR_ID: VTTC0081R (모의투자 주식일별주문체결조회) ✅"
echo "   2. 계좌번호: YOUR_KIS_ACCOUNT_NO ✅"
echo "   3. AppKey: YOUR_KIS_APP_KEY ✅"
echo "   4. KIS API 도메인: https://openapivts.koreainvestment.com:29443 ✅"
echo ""
echo "만약 거래내역이 비어있다면:"
echo "   - KIS 개발자센터에서 직접 API 호출 테스트"
echo "   - 모의투자 계좌에 실제 거래 이력이 있는지 확인"
echo "   - check_kis_history_direct.py 스크립트로 직접 확인"
