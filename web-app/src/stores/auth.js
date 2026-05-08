import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  // Registration multi-step data
  const registrationData = ref({
    // Step 1: Personal information
    step1: {
      id: '',
      password: '',
      passwordConfirm: '',
      email: '',
      name: '',
      phone: '',
      birthDate: ''
    },
    // Step 2: Financial information
    step2: {
      stockInvestment: false,
      kisAccount: null
    },
    // Validation states
    validation: {
      isIdChecked: false,
      isIdAvailable: false,
      isEmailChecked: false,
      isEmailAvailable: false,
      isPhoneVerified: true // 임시 우회: 기본값 true
    }
  })

  // User authentication state
  const user = ref(null)
  const accessToken = ref(null)
  const refreshToken = ref(null)

  // Actions
  function saveStep1Data(data) {
    registrationData.value.step1 = {
      id: data.id,
      password: data.password,
      passwordConfirm: data.passwordConfirm,
      email: data.email || '',
      name: data.name,
      phone: data.phone,
      birthDate: data.birthDate
    }
  }

  function saveStep2Data(data) {
    registrationData.value.step2 = {
      stockInvestment: data.stockInvestment,
      kisAccount: data.kisAccount
    }
  }

  function setIdCheckResult(available) {
    registrationData.value.validation.isIdChecked = true
    registrationData.value.validation.isIdAvailable = available
  }

  function setEmailCheckResult(available) {
    registrationData.value.validation.isEmailChecked = true
    registrationData.value.validation.isEmailAvailable = available
  }

  function setPhoneVerified(verified) {
    registrationData.value.validation.isPhoneVerified = verified
  }

  function clearRegistrationData() {
    registrationData.value = {
      step1: {
        id: '',
        password: '',
        passwordConfirm: '',
        email: '',
        name: '',
        phone: '',
        birthDate: ''
      },
      step2: {
        stockInvestment: false,
        kisAccount: null
      },
      validation: {
        isIdChecked: false,
        isIdAvailable: false,
        isEmailChecked: false,
        isEmailAvailable: false,
        isPhoneVerified: true
      }
    }
  }

  function setAuthData(data) {
    accessToken.value = data.accessToken
    refreshToken.value = data.refreshToken
    user.value = data.user

    // Save to localStorage
    localStorage.setItem('accessToken', data.accessToken)
    localStorage.setItem('refreshToken', data.refreshToken)
    localStorage.setItem('user', JSON.stringify(data.user))
  }

  function clearAuthData() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null

    // Clear from localStorage
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('user')
  }

  function loadAuthDataFromStorage() {
    const storedAccessToken = localStorage.getItem('accessToken')
    const storedRefreshToken = localStorage.getItem('refreshToken')
    const storedUser = localStorage.getItem('user')

    if (storedAccessToken && storedRefreshToken && storedUser) {
      accessToken.value = storedAccessToken
      refreshToken.value = storedRefreshToken
      user.value = JSON.parse(storedUser)
      return true
    }
    return false
  }

  async function logout() {
    try {
      const token = refreshToken.value
      if (token) {
        await authApi.logout(token)
      }
    } catch (error) {
      console.error('Logout error:', error)
      // 에러가 발생해도 로컬 데이터는 삭제
    } finally {
      clearAuthData()
    }
  }

  // Getters
  function hasStep1Data() {
    const step1 = registrationData.value.step1
    return step1.id && step1.password && step1.name && step1.phone && step1.birthDate
  }

  function isAuthenticated() {
    return !!accessToken.value && !!user.value
  }

  return {
    // State
    registrationData,
    user,
    accessToken,
    refreshToken,

    // Actions
    saveStep1Data,
    saveStep2Data,
    setIdCheckResult,
    setEmailCheckResult,
    setPhoneVerified,
    clearRegistrationData,
    setAuthData,
    clearAuthData,
    loadAuthDataFromStorage,
    logout,

    // Getters
    hasStep1Data,
    isAuthenticated
  }
})
