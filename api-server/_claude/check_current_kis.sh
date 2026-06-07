#!/bin/bash

TOKEN=$(curl -s -X POST http://localhost:7070/api/auth/login -H "Content-Type: application/json" -d '{"username":"testuser","password":"password123"}' | grep -o '"accessToken":"[^"]*' | cut -d'"' -f4)

echo "현재 저장된 KIS 계좌 정보:"
curl -s -X GET http://localhost:7070/api/users/kis-account -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
