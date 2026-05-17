import { showToast } from 'vant'

/**
 * Toast 유틸리티
 * 체크/에러 아이콘과 간단한 문구로 사용자에게 피드백을 제공합니다.
 */

// Toast 기본 옵션
const defaultOptions = {
  duration: 2000,
  position: 'bottom',
  forbidClick: false,
  overlay: false
}

/**
 * 성공 메시지 Toast
 * @param {string} message - 표시할 메시지
 * @param {object} options - 추가 옵션
 */
export const showSuccess = (message, options = {}) => {
  return showToast({
    ...defaultOptions,
    message,
    icon: 'success',
    iconSize: '18px',
    className: 'success-toast',
    ...options
  })
}

/**
 * 에러 메시지 Toast
 * @param {string} message - 표시할 메시지
 * @param {object} options - 추가 옵션
 */
export const showError = (message, options = {}) => {
  return showToast({
    ...defaultOptions,
    message,
    icon: 'fail',
    iconSize: '18px',
    className: 'error-toast',
    ...options
  })
}

/**
 * 경고 메시지 Toast
 * @param {string} message - 표시할 메시지
 * @param {object} options - 추가 옵션
 */
export const showWarning = (message, options = {}) => {
  return showToast({
    ...defaultOptions,
    message,
    icon: 'warning',
    iconSize: '18px',
    className: 'warning-toast',
    ...options
  })
}

/**
 * 정보 메시지 Toast
 * @param {string} message - 표시할 메시지
 * @param {object} options - 추가 옵션
 */
export const showInfo = (message, options = {}) => {
  return showToast({
    ...defaultOptions,
    message,
    className: 'info-toast',
    ...options
  })
}

/**
 * 로딩 Toast
 * @param {string} message - 표시할 메시지
 * @param {object} options - 추가 옵션
 */
export const showLoading = (message = '로딩 중...', options = {}) => {
  return showToast({
    ...defaultOptions,
    message,
    icon: 'loading',
    iconSize: '18px',
    duration: 0, // 무한
    forbidClick: true,
    className: 'loading-toast',
    ...options
  })
}

/**
 * Toast 닫기
 */
export const closeToast = () => {
  showToast.clear()
}

// 기본 export
export default {
  success: showSuccess,
  error: showError,
  warning: showWarning,
  info: showInfo,
  loading: showLoading,
  close: closeToast
}
