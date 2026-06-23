<template>
  <div class="plan-page">
    <!-- 今日计划 -->
    <div class="card" v-if="planData.today">
      <div class="card-title">📅 今日计划</div>
      <div class="today-info">
        <div class="date">{{ planData.today.date }}</div>
        <div class="streak" v-if="planData.streak_days > 0">
          🔥 连续学习 <strong>{{ planData.streak_days }}</strong> 天
        </div>
      </div>
      <div class="today-stats">
        <div class="t-stat">
          <span class="t-num">{{ planData.today.review_count }}</span>
          <span class="t-label">待复习</span>
        </div>
        <div class="t-stat">
          <span class="t-num">{{ planData.today.completed_review }}</span>
          <span class="t-label">已完成复习</span>
        </div>
        <div class="t-stat">
          <span class="t-num">{{ studyMinutes }}</span>
          <span class="t-label">学习时长(分)</span>
        </div>
      </div>
      <button class="btn btn-success checkin-btn" @click="doCheckIn" :disabled="planData.today.is_checked_in">
        {{ planData.today.is_checked_in ? '✅ 今日已打卡' : '📌 完成打卡' }}
      </button>
    </div>

    <!-- 进度总览 -->
    <div class="card" v-if="progress">
      <div class="card-title">📊 学习进度总览</div>
      <div class="progress-stats">
        <div class="p-stat"><span class="big">{{ progress.total_words }}</span>已学单词</div>
        <div class="p-stat"><span class="big">{{ progress.mastered }}</span>已掌握</div>
        <div class="p-stat"><span class="big">{{ progress.mastery_rate }}%</span>掌握率</div>
        <div class="p-stat"><span class="big">{{ progress.accuracy }}%</span>正确率</div>
        <div class="p-stat"><span class="big">{{ progress.streak_days }}</span>打卡天数</div>
      </div>
      <div class="progress-stats" style="margin-top:8px">
        <div class="p-stat"><span class="big">{{ progress.total_actions || 0 }}</span>学习次数</div>
        <div class="p-stat"><span class="big">{{ progress.total_correct || 0 }}</span>答对次数</div>
        <div class="p-stat"><span class="big">{{ progress.total_wrong || 0 }}</span>答错次数</div>
        <div class="p-stat"><span class="big">{{ progress.new || 0 }}</span>新词待复习</div>
        <div class="p-stat"><span class="big">{{ progress.learning || 0 }}</span>学习中</div>
      </div>
      <div class="stage-dist" v-if="planData.ebbinghaus_info">
        <h4>艾宾浩斯阶段分布</h4>
        <div class="stages">
          <div v-for="(cnt, stage, i) in planData.ebbinghaus_info.current_stage_distribution" :key="stage"
            class="stage-bar" :style="{ height: Math.max(cnt * 2, 4) + 'px', opacity: 0.3 + i * 0.08,
              background: i >= 4 ? '#52c41a' : '#667eea' }"
            :title="`阶段${stage.slice(-1)}: ${cnt}个单词 — ${i >= 4 ? '已掌握✓' : i === 0 ? '初学' : '复习中'}`">
          </div>
        </div>
        <div class="stage-labels">
          <span>初学(0天)</span><span>✓ 已掌握(≥7天)</span>
        </div>
      </div>
    </div>

    <!-- 未来7天计划（不含今天） -->
    <div class="card">
      <div class="card-title">📆 未来6天计划</div>
      <div class="week-plan">
        <div v-for="day in weekPlanWithoutToday" :key="day.date"
          :class="['day-card']">
          <div class="day-name">{{ day.day_name }}</div>
          <div class="day-date">{{ day.date.slice(5) }}</div>
          <div class="day-detail">
            <span class="tag tag-blue">复习:{{ day.estimated_review }}</span>
            <span class="tag tag-green">新词:{{ day.estimated_new }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useUserStore } from '../stores/user'
import api from '../api'

const userStore = useUserStore()
const planData = reactive({ today: null, week_plan: [], ebbinghaus_info: {}, streak_days: 0 })
const progress = ref(null)

// 学习时长（分钟）
const studyMinutes = computed(() => {
  const sec = planData.today?.study_seconds || 0
  return Math.floor(sec / 60)
})

// 7天计划去掉今天（今天已在"今日计划"卡片展示）
const weekPlanWithoutToday = computed(() => {
  return (planData.week_plan || []).filter(day => !day.is_today)
})

async function loadPlan() {
  const res = await api.getDailyPlan(userStore.userId)
  if (res.code === 200) Object.assign(planData, res.data)
  const prog = await api.getProgress(userStore.userId)
  if (prog.code === 200) progress.value = prog.data
}

async function doCheckIn() {
  const res = await api.checkIn(userStore.userId)
  if (res.code === 200) {
    planData.today.is_checked_in = true
    planData.streak_days = res.data.streak_days
    alert(res.data.message)
  }
}

onMounted(loadPlan)
</script>

<style scoped>
.today-info { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.date { font-size: 18px; font-weight: 600; }
.streak { font-size: 14px; color: #fa8c16; }
.today-stats { display: flex; gap: 12px; margin-bottom: 16px; }
.t-stat { flex: 1; text-align: center; background: #f9faff; border-radius: 8px; padding: 12px; }
.t-num { display: block; font-size: 24px; font-weight: 700; color: #667eea; }
.t-label { font-size: 12px; color: #999; }
.checkin-btn { width: 100%; padding: 14px; font-size: 16px; justify-content: center; margin-top: 8px; }
.progress-stats { display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }
.p-stat { text-align: center; font-size: 12px; color: #666; }
.p-stat .big { display: block; font-size: 24px; font-weight: 700; color: #333; }
.stage-dist { margin-top: 20px; }
.stage-dist h4 { font-size: 14px; margin-bottom: 8px; }
.stages { display: flex; gap: 4px; align-items: flex-end; height: 60px; }
.stage-bar { flex: 1; background: #667eea; border-radius: 2px 2px 0 0; min-height: 4px; }
.stage-labels { display: flex; justify-content: space-between; font-size: 11px; color: #aaa; margin-top: 4px; }
.week-plan { display: flex; gap: 8px; overflow-x: auto; }
.day-card {
  flex: 1; min-width: 80px; padding: 12px; border-radius: 10px;
  text-align: center; background: #fafafa; border: 1px solid #e8e8e8;
}
.day-card.today { border-color: #667eea; background: #f0f2ff; }
.day-name { font-size: 13px; color: #666; }
.day-date { font-size: 12px; color: #aaa; margin: 4px 0; }
.day-detail { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }
</style>
