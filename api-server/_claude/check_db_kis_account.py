#!/usr/bin/env python3
"""DB에 저장된 KIS 계정 정보 확인"""

import psycopg2

# DB 연결 정보 (application.yml과 동일)
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="financemanage",
    user="admin",
    password="admin1234"
)

cursor = conn.cursor()

# KIS 계정 조회
cursor.execute("""
    SELECT
        id,
        account_number,
        account_product_code,
        SUBSTRING(app_key, 1, 30) as app_key_start,
        LENGTH(app_key) as app_key_len,
        SUBSTRING(app_secret, 1, 30) as app_secret_start,
        LENGTH(app_secret) as app_secret_len,
        is_verified,
        user_id
    FROM user_kis_accounts
    ORDER BY id
""")

print("=" * 100)
print("KIS 계정 정보 (DB)")
print("=" * 100)

rows = cursor.fetchall()
for row in rows:
    print(f"\nID: {row[0]}")
    print(f"계좌번호: {row[1]}")
    print(f"상품코드: {row[2]}")
    print(f"AppKey 시작: {row[3]}... (길이: {row[4]})")
    print(f"AppSecret 시작: {row[5]}... (길이: {row[6]})")
    print(f"검증 여부: {row[7]}")
    print(f"사용자 ID: {row[8]}")

cursor.close()
conn.close()

print("\n" + "=" * 100)
print("\n실제 사용해야 할 값 (dev_note.txt):")
print("Account: 50187173")
print("AppKey: PSeTJxnzlAjc0WKeijyeQpuD7aEHhfBb4jv5")
print("AppSecret: d5UVrY6J0EnF3w0/K4gd22gs5VmSOvrNB1vkXVp8RSlu4LW2d1oZvLYYB7cHshNhinQrvC4uBggOwejuPMnbS9uuBNbHSI0QfAkj88CjXss12kVwxPt8dOHFx9Fywo6VhFu9yqICSAlukQ3OcuKr2Ui/44YKzj71jw+W7R2jo/Mx6Sj9oU8=")
