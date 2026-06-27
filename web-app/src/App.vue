<script setup>
import { computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { showNotify } from 'vant'
import { useAuthStore } from '@/stores/auth'
import { useRealtimeStore } from '@/stores/realtime'
import BottomNav from './components/common/BottomNav.vue'

const route = useRoute()
const authStore = useAuthStore()
const realtimeStore = useRealtimeStore()

const { accessToken } = storeToRefs(authStore)

const showBottomNav = computed(() => route.meta.showBottomNav)

// 체결통보 전역 구독: 계좌 단위 단일 스트림이라 App에서 1회만 구독한다.
// 인증 상태(accessToken)에 따라 구독/해제하며, 해제 함수를 보관해 중복 구독을 막는다.
let unsubscribeFills = null

function startFillsSubscription() {
  if (unsubscribeFills) return
  unsubscribeFills = realtimeStore.subscribeFills((fill) => {
    if (!fill || !fill.isFill) return
    const sideLabel = fill.side === 'buy' ? '매수' : '매도'
    showNotify({
      type: 'success',
      message: `${sideLabel} 체결: ${fill.symbol} ${fill.qty}주 @ ${fill.price}`
    })
  })
}

function stopFillsSubscription() {
  if (unsubscribeFills) {
    unsubscribeFills()
    unsubscribeFills = null
  }
}

// Auto-login: Restore session from localStorage on app start
onMounted(() => {
  authStore.loadAuthDataFromStorage()
  if (authStore.isAuthenticated()) {
    startFillsSubscription()
  }
})

// 로그인/로그아웃 전환 처리.
watch(accessToken, (token) => {
  if (token) {
    startFillsSubscription()
  } else {
    stopFillsSubscription()
  }
})

onBeforeUnmount(() => {
  stopFillsSubscription()
})
</script>

<template>
  <div class="app-container">
    <RouterView />
    <BottomNav v-if="showBottomNav" />
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  position: relative;
}
</style>
