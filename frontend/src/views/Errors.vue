<template>
  <div class="errors-page">
    <!-- 错题统计 -->
    <div class="card" v-if="analysis">
      <div class="card-title">📝 错题分析</div>
      <div class="error-stats">
        <div class="stat"><span class="num">{{ analysis.total_errors }}</span>总错题</div>
        <div class="stat"><span class="num">{{ analysis.today_errors }}</span>今日错题</div>
      </div>
      <div v-if="analysis.top_error_words?.length" style="margin-top:16px">
        <div class="card-title" style="font-size:14px">🔴 高频错词 TOP10</div>
        <div class="word-grid">
          <span class="word-chip" v-for="w in analysis.top_error_words" :key="w.word_id">
            {{ w.word }} <small>(×{{ w.error_count }})</small>
          </span>
        </div>
      </div>
    </div>

    <!-- 错题列表 -->
    <div class="card">
      <div class="card-title">错题列表</div>
      <div v-if="errors.length === 0" class="empty-state">暂无错题，继续保持！</div>
      <div class="error-item" v-for="e in errors" :key="e.id">
        <div class="error-word">{{ e.word }}</div>
        <div class="error-question">{{ e.question }}</div>
        <div class="error-answers">
          <span class="tag tag-red">你的答案：{{ e.user_answer }}</span>
          <span class="tag tag-green">正确答案：{{ e.correct_answer }}</span>
        </div>
        <div class="error-time">{{ e.created_at }}</div>
      </div>
    </div>

    <!-- LLM巩固练习 -->
    <div class="card">
      <div class="card-title">🤖 AI巩固练习</div>
      <button class="btn btn-primary" @click="generateReview" :disabled="reviewLoading">
        {{ reviewLoading ? '生成中...' : '生成定制化巩固练习' }}
      </button>
      <div v-if="reviewExercises?.exercises?.length" style="margin-top:16px">
        <div class="exercise-item" v-for="(ex, i) in reviewExercises.exercises" :key="i">
          <h4>{{ ex.original_word }}</h4>
          <p class="mistake-analysis">📌 错误分析：{{ ex.mistake_analysis }}</p>
          <div v-for="(rein, j) in ex.reinforcement" :key="j" class="rein-item">
            <span :class="['tag', rein.type === 'multiple_choice' ? 'tag-blue' : 'tag-purple']">
              {{ rein.type === 'multiple_choice' ? '单选' : '填空' }}
            </span>
            <p>{{ rein.stem }}</p>
            <p class="rein-answer">答案：{{ rein.correct_answer }}</p>
            <p class="rein-explain">{{ rein.explanation }}</p>
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
const errors = ref([])
const analysis = ref(null)
const reviewLoading = ref(false)
const reviewExercises = ref(null)

async function loadErrors() {
  const res = await api.getErrors(userStore.userId, 50, 0)
  if (res.code === 200) {
    errors.value = res.data.errors || []
  }
  const ana = await api.getErrorAnalysis(userStore.userId)
  if (ana.code === 200) analysis.value = ana.data
}

async function generateReview() {
  reviewLoading.value = true
  const res = await api.getReviewExercises(userStore.userId)
  reviewLoading.value = false
  if (res.code === 200) reviewExercises.value = res.data
}

onMounted(loadErrors)
</script>

<style scoped>
.error-stats { display: flex; gap: 16px; }
.stat { flex: 1; text-align: center; padding: 12px; background: #fff2f0; border-radius: 8px; font-size: 14px; color: #666; }
.stat .num { display: block; font-size: 28px; font-weight: 700; color: #ff4d4f; }
.word-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.word-chip {
  padding: 4px 12px; background: #fff2f0; color: #ff4d4f;
  border-radius: 16px; font-size: 13px;
}
.error-item {
  padding: 12px; border-bottom: 1px solid #f0f0f0;
}
.error-word { font-size: 16px; font-weight: 600; margin-bottom: 4px; color: #333; }
.error-question { font-size: 13px; color: #666; margin-bottom: 6px; }
.error-answers { margin: 4px 0; }
.error-time { font-size: 12px; color: #bbb; margin-top: 4px; }
.exercise-item { margin-bottom: 16px; padding: 12px; background: #fafafa; border-radius: 8px; }
.exercise-item h4 { margin-bottom: 6px; }
.mistake-analysis { font-size: 13px; color: #ff4d4f; margin-bottom: 8px; }
.rein-item { margin: 8px 0; padding: 8px; background: #fff; border-radius: 6px; font-size: 13px; }
.rein-item p { margin: 4px 0; }
.rein-answer { color: #52c41a; font-weight: 500; }
.rein-explain { color: #888; font-size: 12px; }
</style>
