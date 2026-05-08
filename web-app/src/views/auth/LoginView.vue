<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/services/api'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({
  username: '',
  password: ''
})

const autoLogin = ref(true)
const loading = ref(false)
const errorMessage = ref('')

// Load auto-login preference from localStorage
onMounted(() => {
  const savedUiSettings = localStorage.getItem('uiSettings')
  if (savedUiSettings) {
    const uiSettings = JSON.parse(savedUiSettings)
    if (uiSettings.autoLogin !== undefined) {
      autoLogin.value = uiSettings.autoLogin
    }
  }
})

const handleLogin = async () => {
  if (!form.value.username || !form.value.password) {
    errorMessage.value = '아이디와 비밀번호를 입력해주세요'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    const response = await authApi.login({
      username: form.value.username,
      password: form.value.password
    })

    // Save auto-login preference
    const uiSettings = JSON.parse(localStorage.getItem('uiSettings') || '{}')
    uiSettings.autoLogin = autoLogin.value
    localStorage.setItem('uiSettings', JSON.stringify(uiSettings))

    // Use auth store to manage authentication state
    authStore.setAuthData({
      accessToken: response.data.accessToken,
      refreshToken: response.data.refreshToken,
      user: response.data.user
    })

    // Navigate to home
    router.push('/home')
  } catch (error) {
    console.error('Login failed:', error)
    errorMessage.value = error.response?.data?.message || '로그인에 실패했습니다'
  } finally {
    loading.value = false
  }
}

const goToResetPassword = () => {
  router.push('/reset-password')
}
</script>

<template>
  <div class="login-screen">
    <div class="content">
      <!-- Logo & Title -->
      <div class="header">
        <div class="logo">
          <span class="logo-text">F</span>
          <span class="logo-dot">.</span>
        </div>
        <h1 class="title">로그인</h1>
      </div>

      <!-- Form -->
      <div class="form">
        <div class="form-group">
          <label class="label">ID</label>
          <input
            v-model="form.username"
            type="text"
            class="input"
            placeholder="Input ID"
            :disabled="loading"
          />
        </div>

        <div class="form-group">
          <label class="label">PW</label>
          <input
            v-model="form.password"
            type="password"
            class="input"
            placeholder="Input Password"
            :disabled="loading"
            @keyup.enter="handleLogin"
          />
        </div>

        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <button class="btn btn-login" @click="handleLogin" :disabled="loading">
          {{ loading ? '로그인 중...' : '로그인' }}
        </button>

        <div class="options">
          <label class="checkbox-wrapper">
            <input type="checkbox" v-model="autoLogin" />
            <span class="checkmark"></span>
            <span class="checkbox-label">자동 로그인</span>
          </label>

          <button class="link-btn" @click="goToResetPassword">
            비밀번호 재설정
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-screen {
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
  align-items: center;
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

.title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.form {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.label {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.input {
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

.input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  padding: var(--spacing-md);
  background: var(--color-error);
  color: white;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  text-align: center;
}

.btn-login {
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

.btn-login:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.btn-login:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.options {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
  accent-color: var(--color-success);
}

.checkbox-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
}

.link-btn {
  background: none;
  border: none;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.link-btn:hover {
  color: var(--color-primary);
}
</style>
