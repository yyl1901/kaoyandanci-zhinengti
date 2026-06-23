<template>
  <div class="recite-page">
    <!-- 每日清单 -->
    <div class="card" v-if="!currentWord">
      <div class="card-title">📖 今日背诵清单</div>
      <div class="stats-row">
        <div class="stat">
          <span class="num">{{ studyMinutes }}<small>分钟</small></span>
          <span class="label">已学时长</span>
        </div>
        <div class="stat">
          <span class="num">{{ Math.max(0, (dailyData.review_list?.length || 0) - studiedReviewCount) }}</span>
          <span class="label">待复习</span>
        </div>
        <div class="stat">
          <span class="num">{{ Math.max(0, (dailyData.new_list?.length || 0) - studiedNewCount) }}</span>
          <span class="label">今日新词</span>
        </div>
      </div>
      <div v-if="dailyData.review_list?.length" style="margin-top:16px">
        <div class="card-title" style="font-size:14px">📋 待复习</div>
        <div class="word-grid">
          <span class="word-chip chip-review" v-for="w in remainingReviewList" :key="w.word_id"
            @click="startWord(w.word_id)">{{ w.word }}</span>
        </div>
        <div v-if="remainingReviewList.length === 0" style="color:#52c41a;font-size:13px;margin-top:8px">
          ✅ 复习词已全部完成！
        </div>
      </div>
      <div v-if="dailyData.new_list?.length" style="margin-top:12px">
        <div class="card-title" style="font-size:14px">🆕 新词</div>
        <div class="word-grid">
          <span class="word-chip chip-new" v-for="w in remainingNewList" :key="w.word_id"
            @click="startWord(w.word_id)">{{ w.word }}</span>
        </div>
        <div v-if="remainingNewList.length === 0" style="color:#52c41a;font-size:13px;margin-top:8px">
          ✅ 新词已全部完成！
        </div>
      </div>
      <div v-if="!dailyData.new_list?.length && !dailyData.review_list?.length" class="empty-state">
        🎉 今日任务已完成！去打卡吧～
      </div>
    </div>

    <!-- 单词讲解 -->
    <div class="card" v-if="currentWord">
      <div class="word-header">
        <button class="btn btn-outline" @click="currentWord = null">← 返回列表</button>
        <button class="btn btn-outline" @click="playSound">{{ playing ? '⏹' : '🔊' }} 发音</button>
        <button class="btn btn-outline" @click="toggleFavorite">
          {{ isFaved ? '⭐' : '☆' }} {{ isFaved ? '已收藏' : '收藏' }}
        </button>
      </div>

      <div class="word-main" v-if="wordDetail">
        <h2 class="word-title">{{ wordDetail.word }}</h2>
        <div class="phonetic" v-if="wordDetail.phonetic_uk">
          UK: {{ wordDetail.phonetic_uk }} | US: {{ wordDetail.phonetic_us }}
        </div>

        <!-- 释义 -->
        <div class="section" v-if="wordDetail.definition">
          <h4>📖 释义</h4>
          <p>{{ formatDef(wordDetail.definition) }}</p>
        </div>

        <!-- 词根词缀 -->
        <div class="section" v-if="hasEtymology">
          <h4>🌱 词根词缀拆解</h4>
          <p>{{ formatEtymology() }}</p>
        </div>

        <!-- LLM增强讲解（如果生成了） -->
        <div class="section" v-if="llmExplanation">
          <h4>🤖 AI智能讲解</h4>
          <div v-if="llmExplanation.etymology?.explanation" style="margin-bottom:8px">
            <strong>词根拆解：</strong>{{ llmExplanation.etymology.explanation }}
          </div>
          <div v-if="llmExplanation.memory_tip" style="margin-bottom:8px">
            <strong>记忆技巧：</strong>{{ llmExplanation.memory_tip }}
          </div>
          <div v-if="llmExplanation.exam_focus?.length">
            <strong>考点：</strong>
            <span class="tag tag-red" v-for="(fp, i) in llmExplanation.exam_focus" :key="i">{{ fp }}</span>
          </div>
        </div>

        <!-- 真题例句 -->
        <div class="section" v-if="examples.length">
          <h4>📝 真题例句</h4>
          <div class="example" v-for="(ex, i) in examples" :key="i">
            <p class="en">{{ ex.en || ex }}</p>
            <p class="cn" v-if="ex.cn">{{ ex.cn }}</p>
            <span class="tag tag-blue" v-if="ex.source">{{ ex.source }}</span>
          </div>
        </div>

        <!-- 近反义词 -->
        <div class="section" v-if="synonymsList.length || antonymsList.length">
          <h4>🔄 近义词 / 反义词</h4>
          <div v-if="synonymsList.length">
            <strong>近义：</strong>
            <span class="tag tag-green" v-for="s in synonymsList" :key="s.word || s">
              {{ s.word || s }}
              <small v-if="s.nuance">（{{ s.nuance }}）</small>
            </span>
          </div>
          <div v-if="antonymsList.length" style="margin-top:4px">
            <strong>反义：</strong>
            <span class="tag tag-purple" v-for="a in antonymsList" :key="a">{{ a }}</span>
          </div>
        </div>

        <!-- 常见错误 -->
        <div class="section" v-if="commonMistakes.length">
          <h4>⚠️ 常见错误</h4>
          <ul>
            <li v-for="(m, i) in commonMistakes" :key="i">{{ m }}</li>
          </ul>
        </div>

        <!-- 复习按钮 -->
        <div class="review-actions">
          <button class="btn btn-danger" @click="markReview(false)">😰 忘记了</button>
          <button class="btn btn-success" @click="markReview(true)">✅ 记住了</button>
        </div>
      </div>

      <div v-else class="loading">加载中...</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, onBeforeUnmount } from 'vue'
import { useUserStore } from '../stores/user'
import api from '../api'

const userStore = useUserStore()
const dailyData = reactive({ new_list: [], review_list: [], study_seconds: 0 })
const currentWord = ref(null)
const wordDetail = ref(null)
const playing = ref(false)
const isFaved = ref(false)

// 本会话已点开过的单词（用数组保证 Vue 3 兼容）
const studiedNewIds = ref([])
const studiedReviewIds = ref([])
const studiedNewCount = computed(() => studiedNewIds.value.length)
const studiedReviewCount = computed(() => studiedReviewIds.value.length)

// 过滤已学单词，只显示剩余
const remainingReviewList = computed(() =>
  (dailyData.review_list || []).filter(w => !studiedReviewIds.value.includes(w.word_id))
)
const remainingNewList = computed(() =>
  (dailyData.new_list || []).filter(w => !studiedNewIds.value.includes(w.word_id))
)

// ---- 学习计时器 ----
const studySeconds = ref(0)
let tickTimer = null
let heartbeatTimer = null

function startStudyTimer(initialSeconds = 0) {
  studySeconds.value = initialSeconds
  // 每秒 tick
  tickTimer = setInterval(() => {
    studySeconds.value++
  }, 1000)
  // 每30s 向服务端上报一次
  heartbeatTimer = setInterval(async () => {
    try {
      await api.heartbeat(userStore.userId, 30)
    } catch { /* 网络错误忽略，本地计时器继续 */}
  }, 30000)
}

function stopStudyTimer() {
  clearInterval(tickTimer)
  clearInterval(heartbeatTimer)
}

const studyMinutes = computed(() => Math.floor(studySeconds.value / 60))

async function loadDailyList() {
  const res = await api.getDailyList(userStore.userId)
  if (res.code === 200) {
    Object.assign(dailyData, res.data)
    // 从服务端获取今日已累计时长
    startStudyTimer(dailyData.study_seconds || 0)
  }
}

async function startWord(wordId) {
  if (dailyData.new_list?.some(w => w.word_id === wordId) && !studiedNewIds.value.includes(wordId))
    studiedNewIds.value.push(wordId)
  if (dailyData.review_list?.some(w => w.word_id === wordId) && !studiedReviewIds.value.includes(wordId))
    studiedReviewIds.value.push(wordId)

  currentWord.value = wordId
  wordDetail.value = null
  const res = await api.getWordDetail(userStore.userId, wordId)
  if (res.code === 200) wordDetail.value = res.data
}

async function markReview(remembered) {
  if (!currentWord.value) return
  const res = await api.reviewWord(userStore.userId, {
    word_id: currentWord.value, remembered
  })
  if (res.code === 200) {
    const msg = remembered ? `已掌握！下次复习：${res.data.next_review}` : `已记录，下次复习日期重置`
    alert(msg)
    currentWord.value = null
  }
}

async function toggleFavorite() {
  if (isFaved.value) {
    await api.removeFavorite(userStore.userId, currentWord.value)
    isFaved.value = false
  } else {
    await api.addFavorite(userStore.userId, { word_id: currentWord.value })
    isFaved.value = true
  }
}

function playSound() {
  if (!wordDetail.value?.word) return
  playing.value = true
  const audio = new Audio(`https://dict.youdao.com/dictvoice?type=2&audio=${wordDetail.value.word}`)
  audio.play()
  audio.onended = () => playing.value = false
}

// 辅助计算
const llmExplanation = computed(() => wordDetail.value?.llm_explanation)
const examples = computed(() => {
  const raw = wordDetail.value?.example_sentences
  if (!raw) return []
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) } catch { return raw.split('\n').filter(Boolean) }
  }
  return raw
})
const synonymsList = computed(() => {
  const raw = wordDetail.value?.synonyms
  if (!raw) return []
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) } catch { return [] }
  }
  return raw
})
const antonymsList = computed(() => {
  const raw = wordDetail.value?.antonyms
  if (!raw) return []
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) } catch { return [] }
  }
  return raw
})
const commonMistakes = computed(() => {
  return llmExplanation.value?.common_mistakes || []
})
const hasEtymology = computed(() => wordDetail.value?.etymology)

function formatDef(def) {
  if (!def) return ''
  if (typeof def === 'string') return def
  return JSON.stringify(def, null, 2)
}
function formatEtymology() {
  const e = wordDetail.value?.etymology
  if (!e) return ''
  if (typeof e === 'string') return e
  return JSON.stringify(e, null, 2)
}

onMounted(loadDailyList)
onBeforeUnmount(stopStudyTimer)
</script>

<style scoped>
.stats-row { display: flex; gap: 12px; }
.stat { flex: 1; text-align: center; padding: 12px 8px; background: #f9faff; border-radius: 8px; font-size: 14px; color: #666; }
.stat .num { display: block; font-size: 26px; font-weight: 700; color: #667eea; }
.stat .num small { font-size: 13px; font-weight: 400; color: #999; margin-left: 2px; }
.stat .label { display: block; font-size: 11px; color: #aaa; margin-top: 2px; }
.word-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.word-chip {
  padding: 6px 14px; border-radius: 20px; font-size: 14px; cursor: pointer; transition: all 0.2s;
}
.chip-review { background: #fff7e6; color: #fa8c16; border: 1px solid #ffd591; }
.chip-new { background: #f0f5ff; color: #2f54eb; border: 1px solid #adc6ff; }
.word-chip:hover { transform: scale(1.05); }
.word-header { display: flex; gap: 8px; margin-bottom: 16px; }
.word-title { font-size: 32px; margin-bottom: 4px; }
.phonetic { color: #999; font-size: 14px; margin-bottom: 16px; }
.section { margin: 16px 0; padding: 12px; background: #fafafa; border-radius: 8px; }
.section h4 { margin-bottom: 8px; font-size: 14px; color: #333; }
.section p { font-size: 14px; color: #555; line-height: 1.6; }
.example { margin-bottom: 10px; }
.example .en { font-size: 14px; color: #333; font-style: italic; }
.example .cn { font-size: 13px; color: #888; margin-top: 2px; }
.review-actions { display: flex; gap: 12px; margin-top: 20px; justify-content: center; }
.review-actions .btn { padding: 12px 32px; font-size: 16px; }
</style>
