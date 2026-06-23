import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  { path: '/', redirect: '/recite' },
  { path: '/recite', name: 'Recite', component: () => import('../views/Recite.vue'), meta: { title: '单词背诵' } },
  { path: '/quiz', name: 'Quiz', component: () => import('../views/Quiz.vue'), meta: { title: '自测出题' } },
  { path: '/errors', name: 'Errors', component: () => import('../views/Errors.vue'), meta: { title: '错题复盘' } },
  { path: '/favorites', name: 'Favorites', component: () => import('../views/Favorites.vue'), meta: { title: '生词收藏' } },
  { path: '/plan', name: 'Plan', component: () => import('../views/Plan.vue'), meta: { title: '计划打卡' } },
  { path: '/search', name: 'Search', component: () => import('../views/Search.vue'), meta: { title: '单词搜索' } },
  { path: '/:pathMatch(.*)*', redirect: '/recite' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 路由守卫：未登录时重定向到登录页（首页）
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  if (userStore.isLoggedIn) {
    next()
  } else {
    next('/')
  }
})

export default router
