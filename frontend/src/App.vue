<template>
  <div class="app">
    <!-- 顶部导航 -->
    <header class="app-header" v-if="userStore.isLoggedIn">
      <div class="header-left">
        <h1 class="logo">📚 单词备考智能体</h1>
        <span class="exam-badge">{{ examLabel }}</span>
      </div>
      <nav class="header-nav">
        <router-link to="/recite" class="nav-link">📖 背诵</router-link>
        <router-link to="/quiz" class="nav-link">✏️ 自测</router-link>
        <router-link to="/errors" class="nav-link">📝 错题</router-link>
        <router-link to="/favorites" class="nav-link">⭐ 收藏</router-link>
        <router-link to="/plan" class="nav-link">📅 打卡</router-link>
        <router-link to="/search" class="nav-link">🔍 搜索</router-link>
      </nav>
      <div class="header-right">
        <span class="user-info">{{ userStore.username }}</span>
        <button class="btn-logout" @click="handleLogout" title="退出登录">↪</button>
      </div>
    </header>

    <!-- 登录页 -->
    <div class="login-container" v-if="!userStore.isLoggedIn">
      <Login @login="handleLogin" />
    </div>

    <!-- 主内容区 -->
    <main class="app-main" v-else>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useUserStore } from './stores/user'
import Login from './components/Login.vue'

const userStore = useUserStore()

const examLabel = computed(() => {
  const labels = { cet4: '四级', cet6: '六级', kaoyan: '考研英语' }
  return labels[userStore.examType] || userStore.examType
})

async function handleLogin({ username, examType, dailyCount }) {
  await userStore.initUser(username, examType, dailyCount)
}

function handleLogout() {
  if (confirm('确定要退出登录吗？退出后学习记录将保留。')) {
    userStore.logout()
  }
}
</script>

<style>
.app { min-height: 100vh; display: flex; flex-direction: column; }

/* 顶部导航 */
.app-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 56px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  position: sticky; top: 0; z-index: 100;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.logo { font-size: 18px; font-weight: 700; }
.exam-badge {
  font-size: 12px; padding: 2px 10px; border-radius: 10px;
  background: rgba(255,255,255,0.25);
}
.header-nav { display: flex; gap: 4px; }
.nav-link {
  color: rgba(255,255,255,0.85); text-decoration: none; padding: 8px 14px;
  border-radius: 8px; font-size: 14px; transition: all 0.2s;
}
.nav-link:hover, .nav-link.router-link-active {
  background: rgba(255,255,255,0.2); color: #fff;
}
.header-right { display: flex; align-items: center; gap: 12px; }
.user-info { font-size: 14px; opacity: 0.9; }
.btn-logout {
  background: rgba(255,255,255,0.2); color: #fff; border: none;
  width: 30px; height: 30px; border-radius: 50%; cursor: pointer;
  font-size: 16px; display: flex; align-items: center; justify-content: center;
  transition: background 0.2s;
}
.btn-logout:hover { background: rgba(255,255,255,0.35); }

/* 主内容 */
.app-main { flex: 1; padding: 24px; max-width: 900px; margin: 0 auto; width: 100%; }

/* 登录容器 */
.login-container {
  flex: 1; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 通用组件样式 */
.card {
  background: #fff; border-radius: 12px; padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06); margin-bottom: 16px;
}
.card-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #333; }
.btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 20px; border: none; border-radius: 8px; font-size: 14px;
  cursor: pointer; transition: all 0.2s; font-weight: 500;
}
.btn-primary { background: #667eea; color: #fff; }
.btn-primary:hover { background: #5a6fd6; }
.btn-success { background: #52c41a; color: #fff; }
.btn-danger { background: #ff4d4f; color: #fff; }
.btn-outline { background: #fff; color: #667eea; border: 1px solid #667eea; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.tag {
  display: inline-block; padding: 2px 10px; border-radius: 4px;
  font-size: 12px; margin-right: 6px;
}
.tag-blue { background: #e6f7ff; color: #1890ff; }
.tag-green { background: #f6ffed; color: #52c41a; }
.tag-red { background: #fff2f0; color: #ff4d4f; }
.tag-purple { background: #f9f0ff; color: #722ed1; }
.empty-state { text-align: center; padding: 40px; color: #999; font-size: 14px; }
.loading { text-align: center; padding: 24px; color: #999; }
.progress-bar {
  height: 8px; background: #f0f0f0; border-radius: 4px; overflow: hidden;
}
.progress-fill { height: 100%; background: #667eea; border-radius: 4px; transition: width 0.3s; }
</style>
