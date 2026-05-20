-- KIS 계좌 정보 복구 및 올바른 사용자에 할당
-- testuser는 테스트 데이터로 유지
-- ib.lee(user_id=8)에 실제 KIS 모의투자 계정 연결

BEGIN;

-- 1. testuser(user_id=1) 원래 테스트 데이터로 복구
UPDATE user_kis_accounts
SET
    account_number = '50000000',
    account_product_code = '01',
    app_key = 'ENC(test_encrypted_app_key_placeholder)',
    app_secret = 'ENC(test_encrypted_app_secret_placeholder)',
    is_verified = true,
    updated_at = CURRENT_TIMESTAMP
WHERE user_id = 1;

-- 2. ib.lee(user_id=8)에 실제 KIS 모의투자 계정 정보 추가
INSERT INTO user_kis_accounts (
    user_id,
    account_number,
    account_product_code,
    app_key,
    app_secret,
    is_verified,
    created_at,
    updated_at
) VALUES (
    8,
    '50187173',
    '01',
    'PSeTJxnzlAjc0WKeijyeQpuD7aEHhfBb4jv5',
    'd5UVrY6J0EnF3w0/K4gd22gs5VmSOvrNB1vkXVp8RSlu4LW2d1oZvLYYB7cHshNhinQrvC4uBggOwejuPMnbS9uuBNbHSI0QfAkj88CjXss12kVwxPt8dOHFx9Fywo6VhFu9yqICSAlukQ3OcuKr2Ui/44YKzj71jw+W7R2jo/Mx6Sj9oU8=',
    true,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
)
ON CONFLICT (account_number) DO UPDATE SET
    app_key = EXCLUDED.app_key,
    app_secret = EXCLUDED.app_secret,
    is_verified = EXCLUDED.is_verified,
    updated_at = CURRENT_TIMESTAMP;

-- 3. 확인
SELECT
    u.username,
    u.name,
    ka.account_number,
    SUBSTRING(ka.app_key, 1, 40) as app_key_start,
    ka.is_verified
FROM user_kis_accounts ka
JOIN users u ON ka.user_id = u.id
ORDER BY u.id;

COMMIT;
