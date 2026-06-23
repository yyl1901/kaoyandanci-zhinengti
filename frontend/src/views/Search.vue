<template>
  <div class="search-page">
    <div class="card">
      <div class="card-title">🔍 单词搜索</div>
      <div class="search-bar">
        <input
          v-model="keyword"
          type="text"
          placeholder="输入英语单词，如 abandon..."
          class="search-input"
          @keyup.enter="doSearch"
        />
        <button class="btn btn-primary" @click="doSearch" :disabled="searching">
          {{ searching ? '搜索中...' : '搜索' }}
        </button>
      </div>
    </div>

    <!-- 搜索结果 -->
    <div class="card" v-if="result">
      <div class="word-header">
        <h2 class="word-title">{{ result.word }}</h2>
        <button class="btn btn-outline" @click="playSound(result.word)">🔊 发音</button>
      </div>

      <!-- 音标 -->
      <div class="phonetics" v-if="result.phonetic_uk || result.phonetic_us">
        <span v-if="result.phonetic_uk">英 {{ result.phonetic_uk }}</span>
        <span v-if="result.phonetic_us">美 {{ result.phonetic_us }}</span>
      </div>

      <!-- 释义 -->
      <div class="section" v-if="defList.length">
        <h4>📖 释义</h4>
        <div class="defs">
          <span v-for="(d, i) in defList" :key="i" class="tag tag-blue">
            <strong>{{ d.pos }}</strong> {{ d.meaning }}
          </span>
        </div>
      </div>

      <!-- 词根词缀 -->
      <div class="section" v-if="etymologyObj">
        <h4>🧩 词根拆解</h4>
        <p>{{ etymologyObj.explanation || result.etymology }}</p>
      </div>

      <!-- 例句 -->
      <div class="section" v-if="examples.length">
        <h4>📝 真题例句</h4>
        <div class="example-item" v-for="(ex, i) in examples" :key="i">
          <p class="en">{{ ex.en }}</p>
          <p class="cn">{{ ex.cn }}</p>
          <span v-if="ex.source" class="tag tag-purple">{{ ex.source }}</span>
        </div>
      </div>

      <!-- 近义词 / 反义词 -->
      <div class="section" v-if="synonyms.length || antonyms.length">
        <div v-if="synonyms.length">
          <h4>✅ 近义词</h4>
          <span v-for="s in synonyms" :key="s" class="tag tag-green">{{ s }}</span>
        </div>
        <div v-if="antonyms.length" style="margin-top:8px">
          <h4>❌ 反义词</h4>
          <span v-for="a in antonyms" :key="a" class="tag tag-red">{{ a }}</span>
        </div>
      </div>

      <!-- 考纲信息 -->
      <div class="section meta">
        <span class="tag tag-purple">📋 {{ examLabel }}</span>
        <span v-if="result.category" class="tag" :class="result.category === 'rare' ? 'tag-red' : 'tag-blue'">
          {{ result.category === 'rare' ? '⚠️ 熟词僻义' : '核心词' }}
        </span>
        <span v-if="result.frequency" class="tag tag-green">⭐ {{ result.frequency }} 级考频</span>
      </div>
    </div>

    <!-- 无结果 -->
    <div class="empty-state" v-if="searched && !result && !searching">
      未找到单词 "{{ lastKeyword }}"，请检查拼写后重试
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '../stores/user'
import api from '../api'

const userStore = useUserStore()
const keyword = ref('')
const lastKeyword = ref('')
const searching = ref(false)
const searched = ref(false)
const result = ref(null)

function tryParseJSON(str) {
  if (!str) return null
  try { return typeof str === 'string' ? JSON.parse(str) : str }
  catch { return null }
}

const defList = ref([])
const etymologyObj = ref(null)
const examples = ref([])
const synonyms = ref([])
const antonyms = ref([])

const examLabelMap = { cet4: '四级', cet6: '六级', kaoyan: '考研英语' }
const examLabel = ref('')

async function doSearch() {
  const word = keyword.value.trim()
  if (!word) return

  searching.value = true
  searched.value = true
  lastKeyword.value = word

  try {
    const res = await api.searchWord(word, userStore.userId || 0, userStore.examType)
    if (res.code === 200 && res.data) {
      const data = res.data

      // 如果返回的是数组（来自多个来源），取第一个
      const wordData = Array.isArray(data) ? data[0] : data

      if (wordData) {
        result.value = wordData
        defList.value = tryParseJSON(wordData.definition) || []
        etymologyObj.value = tryParseJSON(wordData.etymology)
        examples.value = tryParseJSON(wordData.example_sentences) || []
        synonyms.value = tryParseJSON(wordData.synonyms) || []
        antonyms.value = tryParseJSON(wordData.antonyms) || []
        examLabel.value = examLabelMap[wordData.exam_type] || wordData.exam_type || ''
      } else {
        result.value = null
      }
    } else {
      result.value = null
    }
  } catch {
    result.value = null
  } finally {
    searching.value = false
  }
}

function playSound(word) {
  const audio = new Audio(`https://dict.youdao.com/dictvoice?type=2&audio=${encodeURIComponent(word)}`)
  audio.play().catch(() => {})
}
</script>

<style scoped>
.search-page { max-width: 700px; margin: 0 auto; }

.search-bar { display: flex; gap: 10px; }
.search-input {
  flex: 1; padding: 10px 16px; border: 2px solid #e0e0e0; border-radius: 10px;
  font-size: 15px; outline: none; transition: border-color 0.2s;
}
.search-input:focus { border-color: #667eea; }

.word-header { display: flex; align-items: center; gap: 16px; margin-bottom: 8px; }
.word-title { font-size: 28px; font-weight: 700; color: #333; }

.phonetics { display: flex; gap: 18px; color: #888; font-size: 14px; margin-bottom: 16px; }

.section { margin-top: 20px; }
.section h4 { font-size: 14px; color: #666; margin-bottom: 8px; }

.defs { display: flex; flex-wrap: wrap; gap: 8px; }

.example-item {
  padding: 12px; background: #fafafa; border-radius: 8px; margin-bottom: 8px;
}
.example-item .en { font-size: 14px; color: #333; margin-bottom: 4px; }
.example-item .cn { font-size: 13px; color: #888; }

.meta { display: flex; gap: 6px; flex-wrap: wrap; }
</style>
