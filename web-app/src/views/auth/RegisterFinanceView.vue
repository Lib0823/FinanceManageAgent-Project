<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/services/api'
import { Toast } from 'vant'

const router = useRouter()
const authStore = useAuthStore()

const stockInvestment = ref(true)
const coinInvestment = ref(false)
const isRegistering = ref(false)

const brokerForm = ref({
  accountNumber: '',
  appKey: '',
  appSecret: ''
})

// Step 1 데이터 확인
onMounted(() => {
  if (!authStore.hasStep1Data()) {
    Toast.fail('기본 정보를 먼저 입력해주세요')
    router.push('/register')
  }
})

const handleGetAppKey = () => {
  window.open('https://apiportal.koreainvestment.com', '_blank')
}

const handleRegister = async () => {
  // KIS 계좌 정보 검증
  if (stockInvestment.value) {
    if (!brokerForm.value.accountNumber || !brokerForm.value.appKey || !brokerForm.value.appSecret) {
      Toast.fail('KIS 계좌 정보를 모두 입력해주세요')
      return
    }
  }

  try {
    isRegistering.value = true

    // Step 1 데이터 가져오기
    const step1Data = authStore.registrationData.step1

    // 회원가입 요청 데이터 생성
    const registrationData = {
      username: step1Data.id,
      password: step1Data.password,
      passwordConfirm: step1Data.passwordConfirm,
      email: step1Data.email || null,
      name: step1Data.name,
      phone: step1Data.phone,
      birthDate: step1Data.birthDate,
      kisAccount: stockInvestment.value ? {
        accountNumber: brokerForm.value.accountNumber,
        appKey: brokerForm.value.appKey,
        appSecret: brokerForm.value.appSecret
      } : null
    }

    // API 호출
    const response = await authApi.register(registrationData)

    Toast.success('회원가입이 완료되었습니다')

    // 토큰 저장 (백엔드가 RegisterResponse에 토큰을 포함하지 않으므로 로그인 필요)
    // 회원가입 후 바로 로그인할 수도 있지만, 약관 동의 후 로그인으로 진행
    authStore.clearRegistrationData()

    // 약관 페이지로 이동
    router.push('/terms')
  } catch (error) {
    console.error('Registration error:', error)

    // 에러 메시지 처리
    if (error.response?.data?.message) {
      Toast.fail(error.response.data.message)
    } else if (error.response?.data?.error) {
      Toast.fail(error.response.data.error)
    } else {
      Toast.fail('회원가입 중 오류가 발생했습니다')
    }

    // 중복 에러인 경우 Step 1로 돌아가기
    if (error.response?.data?.code === 3001 || error.response?.data?.code === 3002) {
      setTimeout(() => {
        router.push('/register')
      }, 1500)
    }
  } finally {
    isRegistering.value = false
  }
}
</script>

<template>
  <div class="register-finance-screen">
    <div class="content">
      <!-- Header -->
      <div class="header">
        <div class="logo">
          <span class="logo-text">F</span>
          <span class="logo-dot">.</span>
        </div>
        <div class="title-group">
          <h1 class="title">회원가입</h1>
          <p class="step-indicator">• 금융 정보</p>
        </div>
      </div>

      <!-- Form -->
      <div class="form">
        <!-- Stock Investment -->
        <div class="option-group">
          <label class="checkbox-wrapper">
            <input type="checkbox" v-model="stockInvestment" />
            <span class="checkbox-label">주식/채권 투자</span>
          </label>

          <div v-if="stockInvestment" class="broker-card">
            <h3 class="broker-title">한국 투자 증권</h3>

            <div class="form-group">
              <label class="label">계좌번호</label>
              <input
                v-model="brokerForm.accountNumber"
                type="text"
                class="input"
                placeholder="Account Number"
              />
            </div>

            <div class="form-group">
              <label class="label">APP_Key</label>
              <input
                v-model="brokerForm.appKey"
                type="text"
                class="input"
                placeholder="APP Key"
              />
            </div>

            <div class="form-group">
              <label class="label">APP_Secret</label>
              <input
                v-model="brokerForm.appSecret"
                type="password"
                class="input"
                placeholder="APP Secret"
              />
            </div>

            <button class="link-btn" @click="handleGetAppKey">
              APP Key(Secret) 발급 >
            </button>
          </div>
        </div>

        <!-- Coin Investment -->
        <div class="option-group">
          <label class="checkbox-wrapper">
            <input type="checkbox" v-model="coinInvestment" />
            <span class="checkbox-label">코인 투자</span>
          </label>
        </div>

        <!-- Register Button -->
        <button class="btn btn-register" @click="handleRegister" :disabled="isRegistering">
          {{ isRegistering ? '처리 중...' : '회원가입' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register-finance-screen {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: var(--spacing-3xl) var(--spacing-xl);
  background: var(--color-bg-primary);
}

.content {
  display: flex;
  flex-direction: column;
  max-width: 340px;
  margin: 0 auto;
  width: 100%;
}

.header {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-3xl);
}

.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  background: var(--color-primary);
  border-radius: var(--radius-lg);
  flex-shrink: 0;
}

.logo-text {
  font-size: 28px;
  font-weight: var(--font-weight-bold);
  color: var(--color-text-inverse);
}

.logo-dot {
  font-size: 28px;
  font-weight: var(--font-weight-bold);
  color: var(--color-text-inverse);
}

.title-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.step-indicator {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2xl);
}

.option-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.checkbox-wrapper {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
}

.checkbox-wrapper input {
  width: 20px;
  height: 20px;
  accent-color: var(--color-primary);
}

.checkbox-label {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.broker-card {
  background: var(--color-bg-highlight);
  border-radius: var(--radius-xl);
  padding: var(--spacing-lg);
}

.broker-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  text-align: center;
  margin-bottom: var(--spacing-lg);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-md);
}

.label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.input {
  padding: var(--spacing-md);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-base);
  outline: none;
  background: var(--color-bg-primary);
}

.input::placeholder {
  color: var(--color-text-tertiary);
}

.link-btn {
  background: none;
  border: none;
  font-size: var(--font-size-sm);
  color: var(--color-primary);
  cursor: pointer;
  text-align: center;
  width: 100%;
}

.btn-register {
  width: 100%;
  padding: var(--spacing-lg);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--font-size-md);
  font-weight: var(--font-weight-semibold);
  cursor: pointer;
  margin-top: var(--spacing-lg);
}

.btn-register:hover {
  background: var(--color-primary-dark);
}
</style>
