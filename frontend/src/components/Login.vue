<template>
  <div class="login-box">
    <h2>📚 单词备考智能体</h2>
    <p class="subtitle">考研 · 四级 · 六级 | 艾宾浩斯科学记忆</p>
    <div class="form">
      <label>昵称</label>
      <input v-model="username" placeholder="请输入昵称" />
      <label>考纲选择</label>
      <div class="exam-btns">
        <button v-for="e in exams" :key="e.value"
          :class="['exam-btn', { active: examType === e.value }]"
          @click="examType = e.value">{{ e.label }}</button>
      </div>
      <label>每日背诵量：<strong>{{ dailyCount }}</strong> 个</label>
      <input type="range" v-model.number="dailyCount" min="5" max="100" step="5" />
      <button class="btn btn-primary start-btn" @click="start">开始学习</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['login'])
const username = ref('')
const examType = ref('kaoyan')
const dailyCount = ref(30)
const exams = [
  { label: '四级', value: 'cet4' },
  { label: '六级', value: 'cet6' },
  { label: '考研英语', value: 'kaoyan' },
]

function start() {
  if (!username.value.trim()) {
    alert('请输入昵称')
    return
  }
  emit('login', {
    username: username.value.trim(),
    examType: examType.value,
    dailyCount: dailyCount.value,
  })
}
</script>

<style scoped>
.login-box {
  background: #fff; border-radius: 16px; padding: 40px; width: 400px;
  box-shadow: 0 8px 40px rgba(0,0,0,0.12); text-align: center;
}
h2 { font-size: 24px; margin-bottom: 8px; }
.subtitle { color: #999; font-size: 14px; margin-bottom: 24px; }
.form { text-align: left; }
label { display: block; margin: 12px 0 6px; font-size: 14px; color: #666; }
input[type="text"], input[type="range"] { width: 100%; }
input[type="text"] {
  padding: 10px 14px; border: 1px solid #e0e0e0; border-radius: 8px;
  font-size: 14px; outline: none;
}
input[type="text"]:focus { border-color: #667eea; }
.exam-btns { display: flex; gap: 8px; }
.exam-btn {
  flex: 1; padding: 10px; border: 1px solid #e0e0e0; border-radius: 8px;
  background: #fff; cursor: pointer; font-size: 14px; transition: all 0.2s;
}
.exam-btn.active { border-color: #667eea; color: #667eea; background: #f0f2ff; font-weight: 600; }
.start-btn {
  width: 100%; margin-top: 20px; padding: 12px;
  font-size: 16px; justify-content: center;
}
</style>
