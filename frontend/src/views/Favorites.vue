<template>
  <div class="favorites-page">
    <div class="card">
      <div class="card-title">⭐ 生词收藏</div>
      <div v-if="favorites.length === 0" class="empty-state">
        暂无收藏单词，背诵时点击 ☆ 收藏吧～
      </div>
      <div class="fav-grid" v-else>
        <div class="fav-card" v-for="fav in favorites" :key="fav.id">
          <div class="fav-word">{{ fav.word?.word }}</div>
          <div class="fav-phonetic" v-if="fav.word?.phonetic_uk">{{ fav.word.phonetic_uk }}</div>
          <div class="fav-def">{{ formatDef(fav.word?.definition) }}</div>
          <div class="fav-actions">
            <button class="btn btn-outline" @click="playSound(fav.word?.word)">🔊</button>
            <button class="btn btn-outline" @click="removeFav(fav.word?.id)">取消收藏</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useUserStore } from '../stores/user'
import api from '../api'

const userStore = useUserStore()
const favorites = ref([])

async function loadFavorites() {
  const res = await api.listFavorites(userStore.userId)
  if (res.code === 200) favorites.value = res.data.favorites || []
}

async function removeFav(wordId) {
  await api.removeFavorite(userStore.userId, wordId)
  favorites.value = favorites.value.filter(f => f.word?.id !== wordId)
}

function playSound(word) {
  const audio = new Audio(`https://dict.youdao.com/dictvoice?type=2&audio=${word}`)
  audio.play()
}

function formatDef(def) {
  if (!def) return ''
  if (typeof def === 'string') {
    try { const p = JSON.parse(def); return typeof p === 'string' ? p : JSON.stringify(p) } catch { return def }
  }
  return JSON.stringify(def)
}

onMounted(loadFavorites)
</script>

<style scoped>
.fav-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.fav-card {
  padding: 16px; border: 1px solid #e8e8e8; border-radius: 10px;
  background: #fff; transition: box-shadow 0.2s;
}
.fav-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.fav-word { font-size: 20px; font-weight: 700; color: #333; margin-bottom: 2px; }
.fav-phonetic { font-size: 12px; color: #999; margin-bottom: 6px; }
.fav-def { font-size: 13px; color: #666; margin-bottom: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fav-actions { display: flex; gap: 6px; }
.fav-actions .btn { padding: 4px 10px; font-size: 12px; }
</style>
