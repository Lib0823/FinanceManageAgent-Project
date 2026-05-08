<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/services/api'
import { Toast } from 'vant'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({
  id: '',
  password: '',
  passwordConfirm: '',
  email: '',
  name: '',
  phone: '',
  authCode: '',
  birth: ['1990', '01', '01']
})

const showDatePicker = ref(false)
const isIdChecked = ref(false)
const isIdAvailable = ref(false)
const isCheckingId = ref(false)
const isEmailChecked = ref(false)
const isEmailAvailable = ref(false)
const isCheckingEmail = ref(false)
const isPhoneVerified = ref(false)

const formattedBirth = computed(() => {
  const [year, month, day] = form.value.birth
  return `${year}년 ${month}월 ${day}일`
})

const onConfirmDate = ({ selectedValues }) => {
  form.value.birth = selectedValues
  showDatePicker.value = false
}

const handleCheckDuplicate = async () => {
  if (!form.value.id) {
    Toast.fail('아이디를 입력해주세요')
    return
  }

  try {
    isCheckingId.value = true
    const response = await authApi.checkUsername(form.value.id)
    isIdChecked.value = true
    isIdAvailable.value = response.data.available

    if (response.data.available) {
      Toast.success('사용 가능한 아이디입니다')
      authStore.setIdCheckResult(true)
    } else {
      Toast.fail('이미 사용 중인 아이디입니다')
      authStore.setIdCheckResult(false)
    }
  } catch (error) {
    console.error('ID check error:', error)
    Toast.fail('아이디 확인 중 오류가 발생했습니다')
  } finally {
    isCheckingId.value = false
  }
}

const handleCheckEmail = async () => {
  if (!form.value.email) {
    Toast.fail('이메일을 입력해주세요')
    return
  }

  // 이메일 형식 검증
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(form.value.email)) {
    Toast.fail('올바른 이메일 형식이 아닙니다')
    return
  }

  try {
    isCheckingEmail.value = true
    const response = await authApi.checkEmail(form.value.email)
    isEmailChecked.value = true
    isEmailAvailable.value = response.data.available

    if (response.data.available) {
      Toast.success('사용 가능한 이메일입니다')
      authStore.setEmailCheckResult(true)
    } else {
      Toast.fail('이미 사용 중인 이메일입니다')
      authStore.setEmailCheckResult(false)
    }
  } catch (error) {
    console.error('Email check error:', error)
    Toast.fail('이메일 확인 중 오류가 발생했습니다')
  } finally {
    isCheckingEmail.value = false
  }
}

const handleSendAuthCode = () => {
  // 임시 우회: 휴대폰 인증 없이 진행
  if (!form.value.phone) {
    Toast.fail('핸드폰 번호를 입력해주세요')
    return
  }

  Toast.success('개발 중 - 인증번호 자동 발송 완료')
  isPhoneVerified.value = true
  authStore.setPhoneVerified(true)
}

const handleVerifyCode = () => {
  // 임시 우회: 인증 자동 완료
  Toast.success('개발 중 - 인증 완료')
  isPhoneVerified.value = true
  authStore.setPhoneVerified(true)
}

const handleNext = () => {
  // 유효성 검사
  if (!form.value.id) {
    Toast.fail('아이디를 입력해주세요')
    return
  }

  if (!isIdChecked.value || !isIdAvailable.value) {
    Toast.fail('아이디 중복 확인을 해주세요')
    return
  }

  if (!form.value.password) {
    Toast.fail('비밀번호를 입력해주세요')
    return
  }

  if (form.value.password.length < 8) {
    Toast.fail('비밀번호는 8자 이상이어야 합니다')
    return
  }

  if (form.value.password !== form.value.passwordConfirm) {
    Toast.fail('비밀번호가 일치하지 않습니다')
    return
  }

  // 이메일 입력 시 중복 확인 필수
  if (form.value.email && (!isEmailChecked.value || !isEmailAvailable.value)) {
    Toast.fail('이메일 중복 확인을 해주세요')
    return
  }

  if (!form.value.name) {
    Toast.fail('이름을 입력해주세요')
    return
  }

  if (!form.value.phone) {
    Toast.fail('핸드폰 번호를 입력해주세요')
    return
  }

  if (!isPhoneVerified.value) {
    Toast.fail('휴대폰 인증을 완료해주세요')
    return
  }

  // Pinia store에 데이터 저장
  const [year, month, day] = form.value.birth
  const birthDate = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`

  authStore.saveStep1Data({
    id: form.value.id,
    password: form.value.password,
    passwordConfirm: form.value.passwordConfirm,
    email: form.value.email,
    name: form.value.name,
    phone: form.value.phone,
    birthDate: birthDate
  })

  router.push('/register/finance')
}
</script>

<template>
  <div class="register-screen">
    <div class="content">
      <!-- Header -->
      <div class="header">
        <div class="logo">
          <span class="logo-text">F</span>
          <span class="logo-dot">.</span>
        </div>
        <div class="title-group">
          <h1 class="title">회원가입</h1>
          <p class="step-indicator">• 기본 정보</p>
        </div>
      </div>

      <!-- Form -->
      <div class="form">
        <!-- ID -->
        <div class="form-group">
          <label class="label">아이디</label>
          <div class="input-with-btn">
            <input
              v-model="form.id"
              type="text"
              class="input"
              placeholder="ID"
            />
            <button class="inline-btn" @click="handleCheckDuplicate">중복 확인</button>
          </div>
        </div>

        <!-- Password -->
        <div class="form-group">
          <label class="label">비밀번호</label>
          <input
            v-model="form.password"
            type="password"
            class="input"
            placeholder="Password"
          />
        </div>

        <!-- Password Confirm -->
        <div class="form-group">
          <label class="label">비밀번호 확인</label>
          <input
            v-model="form.passwordConfirm"
            type="password"
            class="input"
            placeholder="Password Check"
          />
        </div>

        <!-- Email (optional) -->
        <div class="form-group">
          <label class="label">이메일 (선택)</label>
          <div class="input-with-btn">
            <input
              v-model="form.email"
              type="email"
              class="input"
              placeholder="Email (optional)"
            />
            <button class="inline-btn" @click="handleCheckEmail">중복 확인</button>
          </div>
        </div>

        <!-- Name -->
        <div class="form-group">
          <label class="label">이름</label>
          <input
            v-model="form.name"
            type="text"
            class="input"
            placeholder="Name"
          />
        </div>

        <!-- Phone -->
        <div class="form-group">
          <label class="label">핸드폰</label>
          <div class="input-with-btn">
            <input
              v-model="form.phone"
              type="tel"
              class="input"
              placeholder="Phone Number"
            />
            <button class="inline-btn orange" @click="handleSendAuthCode">인증 번호 전송</button>
          </div>
        </div>

        <!-- Auth Code -->
        <div class="form-group">
          <label class="label">인증번호</label>
          <div class="input-with-btn">
            <input
              v-model="form.authCode"
              type="text"
              class="input"
              placeholder="Auth Number"
            />
            <button class="inline-btn" @click="handleVerifyCode">인증</button>
          </div>
        </div>

        <!-- Birth Date -->
        <div class="form-group">
          <label class="label">생년월일</label>
          <div class="date-display" @click="showDatePicker = true">
            <span class="date-value">{{ formattedBirth }}</span>
            <van-icon name="arrow-down" class="date-icon" />
          </div>
        </div>

        <!-- Date Picker Popup -->
        <van-popup v-model:show="showDatePicker" position="bottom" round>
          <van-date-picker
            v-model="form.birth"
            title="생년월일 선택"
            :min-date="new Date(1900, 0, 1)"
            :max-date="new Date()"
            @confirm="onConfirmDate"
            @cancel="showDatePicker = false"
          />
        </van-popup>

        <!-- Next Button -->
        <button class="btn btn-next" @click="handleNext">
          다음
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register-screen {
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
  margin-bottom: var(--spacing-2xl);
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
  gap: var(--spacing-lg);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.input {
  flex: 1;
  padding: var(--spacing-md) 0;
  border: none;
  border-bottom: 1px solid var(--color-border);
  font-size: var(--font-size-base);
  outline: none;
  background: transparent;
}

.input::placeholder {
  color: var(--color-text-tertiary);
}

.input:focus {
  border-bottom-color: var(--color-primary);
}

.input-with-btn {
  display: flex;
  gap: var(--spacing-sm);
  align-items: flex-end;
}

.inline-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-tertiary);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  color: var(--color-text-primary);
  cursor: pointer;
  white-space: nowrap;
}

.inline-btn.orange {
  background: #F97316;
  color: var(--color-text-inverse);
}

.inline-btn:hover {
  opacity: 0.9;
}

.date-display {
  padding: var(--spacing-md);
  background: var(--color-bg-highlight);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.date-display:active {
  opacity: 0.8;
}

.date-value {
  font-size: var(--font-size-base);
  color: var(--color-primary);
  font-weight: var(--font-weight-medium);
}

.date-icon {
  color: var(--color-text-tertiary);
  font-size: var(--font-size-md);
}

.btn-next {
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

.btn-next:hover {
  background: var(--color-primary-dark);
}
</style>
