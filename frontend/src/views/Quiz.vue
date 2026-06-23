<template>
  <div class="quiz-page">
    <!-- 出题设置 -->
    <div class="card" v-if="!quizData">
      <div class="card-title">✏️ 自测出题</div>
      <div class="quiz-settings">
        <div class="setting">
          <label>题目数量</label>
          <input type="range" v-model.number="count" min="5" max="30" step="5" />
          <span>{{ count }} 题</span>
        </div>
        <div class="setting">
          <label>题目来源</label>
          <div class="source-btns">
            <button v-for="s in sources" :key="s.value"
              :class="['source-btn', { active: source === s.value }]"
              @click="source = s.value">{{ s.label }}</button>
          </div>
        </div>
        <button class="btn btn-primary" @click="generateQuiz" :disabled="loading">
          {{ loading ? '生成中...' : '🎯 生成试卷' }}
        </button>
      </div>
    </div>

    <!-- 答题中 -->
    <div v-if="quizData && !quizFinished">
      <div class="card">
        <div class="quiz-progress">
          <span>第 {{ currentIndex + 1 }} / {{ quizData.total }} 题</span>
          <span class="timer" :class="{ 'timer-warn': timeLeft <= 10 }">⏱ {{ timeLeft }}s</span>
          <span class="score">得分：{{ score }}</span>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: (currentIndex / quizData.total * 100) + '%' }"></div>
          </div>
        </div>
      </div>

      <div class="card" v-if="currentQuestion">
        <div class="question-type">
          <span :class="['tag', currentQuestion.type === 'multiple_choice' ? 'tag-blue' : 'tag-purple']">
            {{ currentQuestion.type === 'multiple_choice' ? '单选题' : '选词填空' }}
          </span>
        </div>
        <h3 class="stem">{{ currentQuestion.stem }}</h3>
        <p class="context" v-if="currentQuestion.context_sentence">{{ currentQuestion.context_sentence }}</p>

        <div class="options">
          <button v-for="(opt, i) in currentQuestion.options" :key="i"
            :class="['option-btn', {
              correct: answered && opt === currentQuestion.correct_answer,
              wrong: answered && opt === selectedAnswer && opt !== currentQuestion.correct_answer
            }]"
            :disabled="answered"
            @click="submitAnswer(opt)">
            {{ opt }}
          </button>
        </div>

        <!-- 答题反馈 -->
        <div class="feedback" v-if="answered">
          <div :class="['alert', lastResult?.is_correct ? 'alert-success' : 'alert-danger']">
            {{ lastResult?.is_correct ? '✅ 回答正确！' : '❌ 回答错误' }}
            <span v-if="!lastResult?.is_correct"> 正确答案：{{ lastResult?.correct_answer }}</span>
          </div>
          <div class="explanation" v-if="lastResult?.explanation">
            <strong>解析：</strong>{{ lastResult.explanation }}
          </div>
          <button class="btn btn-primary" @click="nextQuestion" style="margin-top:12px">
            {{ currentIndex < quizData.total - 1 ? '下一题 →' : '查看成绩 →' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 成绩报告 -->
    <div class="card" v-if="quizFinished && report">
      <div class="card-title">📊 测验成绩</div>
      <div class="report">
        <div class="score-circle">{{ report.accuracy }}%</div>
        <div class="report-detail">
          <p>总题数：{{ report.total }} | 正确：{{ report.score }} | 错误：{{ report.wrong_count }}</p>
          <p :class="report.passed ? 'pass' : 'fail'">{{ report.passed ? '🎉 通过！' : '💪 继续加油！' }}</p>
        </div>
      </div>
      <div class="wrong-list" v-if="report.wrong_details?.length">
        <h4>错题回顾</h4>
        <div class="wrong-item" v-for="(w, i) in report.wrong_details" :key="i">
          <p><strong>{{ w.stem }}</strong></p>
          <p>你的答案：<span class="tag tag-red">{{ w.user_answer }}</span> → 正确答案：<span class="tag tag-green">{{ w.correct_answer }}</span></p>
          <p class="explain">{{ w.explanation }}</p>
        </div>
      </div>
      <button class="btn btn-primary" @click="resetQuiz" style="margin-top:16px">🔄 再来一套</button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onBeforeUnmount } from 'vue'
import { useUserStore } from '../stores/user'
import api from '../api'

const userStore = useUserStore()
const count = ref(10)
const source = ref('recent')
const loading = ref(false)
const sources = [
  { label: '最近学习', value: 'recent' },
  { label: '错题相关', value: 'errors' },
  { label: '收藏单词', value: 'favorites' },
]

const quizData = ref(null)
const quizFinished = ref(false)
const currentIndex = ref(0)
const selectedAnswer = ref(null)
const answered = ref(false)
const score = ref(0)
const lastResult = ref(null)
const report = ref(null)

// 倒计时
const TIME_LIMIT = 30
const timeLeft = ref(TIME_LIMIT)
let timerInterval = null

function startTimer() {
  clearTimer()
  timeLeft.value = TIME_LIMIT
  timerInterval = setInterval(() => {
    if (timeLeft.value > 0) {
      timeLeft.value--
    } else {
      // 超时自动提交（答错）
      submitAnswer('（超时未答）')
    }
  }, 1000)
}

function clearTimer() {
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

// 切题时重置倒计时
watch(currentIndex, () => {
  if (quizData.value && !quizFinished.value) {
    startTimer()
  }
})

onBeforeUnmount(() => clearTimer())

const currentQuestion = computed(() => {
  if (!quizData.value?.questions) return null
  return quizData.value.questions[currentIndex.value] || null
})

async function generateQuiz() {
  loading.value = true
  const res = await api.generateQuiz(userStore.userId, count.value, source.value)
  loading.value = false
  if (res.code === 200) {
    quizData.value = res.data
    currentIndex.value = 0
    answered.value = false
    selectedAnswer.value = null
    score.value = 0
    quizFinished.value = false
    report.value = null
    startTimer()
  } else {
    alert(res.message)
  }
}

async function submitAnswer(answer) {
  if (answered.value) return
  clearTimer()
  selectedAnswer.value = answer
  const res = await api.submitAnswer(userStore.userId, {
    quiz_id: quizData.value.quiz_id,
    question_index: currentIndex.value,
    user_answer: answer,
  })
  if (res.code === 200) {
    lastResult.value = res.data
    if (res.data.is_correct) score.value++
    answered.value = true
  }
}

async function nextQuestion() {
  if (currentIndex.value < quizData.value.total - 1) {
    currentIndex.value++
    answered.value = false
    selectedAnswer.value = null
    lastResult.value = null
  } else {
    // 结束测验
    const res = await api.finishQuiz(userStore.userId, quizData.value.quiz_id)
    if (res.code === 200) {
      report.value = res.data
      quizFinished.value = true
    }
  }
}

function resetQuiz() {
  clearTimer()
  quizData.value = null
  quizFinished.value = false
  report.value = null
}
</script>

<style scoped>
.quiz-settings { display: flex; flex-direction: column; gap: 16px; }
.setting label { display: block; font-size: 14px; color: #666; margin-bottom: 6px; }
.setting input[type="range"] { width: 100%; }
.source-btns { display: flex; gap: 8px; }
.source-btn {
  flex: 1; padding: 8px; border: 1px solid #e0e0e0; border-radius: 6px;
  background: #fff; cursor: pointer; font-size: 13px;
}
.source-btn.active { border-color: #667eea; color: #667eea; background: #f0f2ff; }
.quiz-progress { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; font-size: 14px; }
.timer { font-weight: 700; color: #667eea; font-size: 15px; min-width: 50px; }
.timer.timer-warn { color: #ff4d4f; animation: pulse 0.5s ease-in-out infinite alternate; }
@keyframes pulse { from { opacity: 1; } to { opacity: 0.5; } }
.score { margin-left: auto; font-weight: 600; color: #667eea; }
.question-type { margin-bottom: 8px; }
.stem { font-size: 16px; margin-bottom: 8px; line-height: 1.6; }
.context { color: #888; font-size: 14px; margin-bottom: 12px; font-style: italic; }
.options { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
.option-btn {
  padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px;
  background: #fff; cursor: pointer; font-size: 14px; text-align: left; transition: all 0.2s;
}
.option-btn:hover:not(:disabled) { border-color: #667eea; background: #f0f2ff; }
.option-btn.correct { border-color: #52c41a; background: #f6ffed; color: #52c41a; font-weight: 600; }
.option-btn.wrong { border-color: #ff4d4f; background: #fff2f0; color: #ff4d4f; }
.feedback { margin-top: 16px; }
.alert { padding: 10px 14px; border-radius: 8px; font-size: 14px; margin-bottom: 8px; }
.alert-success { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.alert-danger { background: #fff2f0; color: #ff4d4f; border: 1px solid #ffccc7; }
.explanation { font-size: 13px; color: #666; line-height: 1.6; }
/* Report */
.report { display: flex; align-items: center; gap: 24px; padding: 16px 0; }
.score-circle {
  width: 80px; height: 80px; border-radius: 50%; background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff; display: flex; align-items: center; justify-content: center;
  font-size: 24px; font-weight: 700;
}
.report-detail p { margin: 4px 0; font-size: 14px; }
.pass { color: #52c41a; font-weight: 600; }
.fail { color: #ff4d4f; font-weight: 600; }
.wrong-list { margin-top: 16px; }
.wrong-item { padding: 12px; background: #fafafa; border-radius: 8px; margin-bottom: 8px; font-size: 14px; }
.wrong-item p { margin: 4px 0; }
.explain { color: #888; font-size: 13px; }
</style>
