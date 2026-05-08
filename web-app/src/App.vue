<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import BottomNav from './components/common/BottomNav.vue'

const route = useRoute()
const authStore = useAuthStore()

const showBottomNav = computed(() => route.meta.showBottomNav)

// Auto-login: Restore session from localStorage on app start
onMounted(() => {
  authStore.loadAuthDataFromStorage()
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
