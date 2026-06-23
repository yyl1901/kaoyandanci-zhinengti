import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 响应拦截器
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    console.error('API Error:', err)
    return { code: 500, message: err.message || '网络错误', data: null }
  }
)

export default {
  // 用户
  initUser: (data) => api.post('/user/init', data),
  updateSettings: (userId, params) => api.put('/user/settings', null, { params: { user_id: userId, ...params } }),

  // 背诵
  getDailyList: (userId) => api.get('/recite/daily-list', { params: { user_id: userId } }),
  getWordDetail: (userId, wordId) => api.get('/recite/word-detail', { params: { user_id: userId, word_id: wordId } }),
  reviewWord: (userId, data) => api.post('/recite/review-word', data, { params: { user_id: userId } }),
  heartbeat: (userId, seconds) => api.post('/recite/heartbeat', null, { params: { user_id: userId, seconds } }),

  // 自测
  generateQuiz: (userId, count, source) => api.post('/quiz/generate', null, { params: { user_id: userId, count, source } }),
  submitAnswer: (userId, data) => api.post('/quiz/submit', data, { params: { user_id: userId } }),
  finishQuiz: (userId, quizId) => api.post('/quiz/finish', null, { params: { user_id: userId, quiz_id: quizId } }),

  // 错题
  getErrors: (userId, limit, offset) => api.get('/errors/list', { params: { user_id: userId, limit, offset } }),
  getErrorAnalysis: (userId) => api.get('/errors/analysis', { params: { user_id: userId } }),
  getReviewExercises: (userId) => api.post('/errors/review-exercises', null, { params: { user_id: userId } }),

  // 收藏
  addFavorite: (userId, data) => api.post('/favorite/add', data, { params: { user_id: userId } }),
  removeFavorite: (userId, wordId) => api.delete('/favorite/remove', { params: { user_id: userId, word_id: wordId } }),
  listFavorites: (userId) => api.get('/favorite/list', { params: { user_id: userId } }),

  // 计划
  getDailyPlan: (userId) => api.get('/plan/daily', { params: { user_id: userId } }),
  checkIn: (userId) => api.post('/plan/check-in', null, { params: { user_id: userId } }),
  getProgress: (userId) => api.get('/plan/progress', { params: { user_id: userId } }),

  // 发音
  getPronunciation: (word) => api.get('/tools/pronunciation', { params: { word } }),

  // 查词
  searchWord: (word, userId, examType) => api.get('/word/search', { params: { word, user_id: userId, exam_type: examType || null } }),
}
