import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useUserStore = defineStore('user', () => {
  const userId = ref(parseInt(localStorage.getItem('userId') || '0'))
  const username = ref(localStorage.getItem('username') || '')
  const examType = ref(localStorage.getItem('examType') || 'cet4')
  const dailyCount = ref(parseInt(localStorage.getItem('dailyCount') || '30'))
  const progress = ref(null)

  const isLoggedIn = computed(() => userId.value > 0)

  async function initUser(name, exam, count) {
    const res = await api.initUser({ username: name, exam_type: exam, daily_count: count })
    if (res.code === 200 && res.data) {
      userId.value = res.data.user_id
      username.value = res.data.username
      examType.value = res.data.exam_type
      dailyCount.value = res.data.daily_count
      saveToLocal()
    }
    return res
  }

  async function updateSettings(params) {
    const res = await api.updateSettings(userId.value, params)
    if (res.code === 200) {
      if (params.exam_type) examType.value = params.exam_type
      if (params.daily_count) dailyCount.value = params.daily_count
      saveToLocal()
    }
    return res
  }

  async function fetchProgress() {
    if (!userId.value) return
    const res = await api.getProgress(userId.value)
    if (res.code === 200) progress.value = res.data
    return res
  }

  function saveToLocal() {
    localStorage.setItem('userId', userId.value)
    localStorage.setItem('username', username.value)
    localStorage.setItem('examType', examType.value)
    localStorage.setItem('dailyCount', dailyCount.value)
  }

  function logout() {
    userId.value = 0
    username.value = ''
    examType.value = 'kaoyan'
    dailyCount.value = 20
    progress.value = null
    localStorage.clear()
  }

  return { userId, username, examType, dailyCount, progress, isLoggedIn, initUser, updateSettings, fetchProgress, saveToLocal, logout }
})
