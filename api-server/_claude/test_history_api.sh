#!/bin/bash

echo "=== 거래내역 API 테스트 ==="

# 1. 로그인
echo "1. 로그인 중..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:7070/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123"}')

TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"accessToken":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "❌ 로그인 실패"
  echo "$LOGIN_RESPONSE"
  exit 1
fi

echo "✅ 로그인 성공"
echo "   Token: ${TOKEN:0:30}..."

# 2. 거래내역 조회
echo ""
echo "2. 거래내역 조회 중..."
HISTORY_RESPONSE=$(curl -s -X GET http://localhost:7070/api/trading/history \
  -H "Authorization: Bearer $TOKEN")

echo "$HISTORY_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"✅ 응답 성공: {data.get('success')}\")
    print(f\"   메시지: {data.get('message')}\")

    history = data.get('data', [])
    print(f\"   거래내역 개수: {len(history)}개\")

    if history:
        print('')
        print('=== 거래내역 샘플 ===')
        for i, trade in enumerate(history[:3], 1):
            print(f\"[{i}] {trade.get('stockName')} ({trade.get('stockCode')})\")
            print(f\"    {trade.get('orderType')} / {trade.get('orderStatus')}\")
            print(f\"    {trade.get('quantity')}주 @ {trade.get('executedPrice')}원\")
            print(f\"    주문일시: {trade.get('orderedAt')}\")
            print('')
except Exception as e:
    print(f\"❌ 파싱 실패: {e}\")
    print(sys.stdin.read())
"

echo ""
echo "=== 테스트 완료 ==="
