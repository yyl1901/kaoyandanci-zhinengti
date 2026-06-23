# 考研单词备考智能体 🎓

> 基于大语言模型 + RAG 检索增强的智能单词备考助手，专注**考研英语**核心词库，融合艾宾浩斯遗忘曲线、词根词缀拆解、真题例句记忆法，提供一站式的单词学习、自测、错题复盘体验。

---

## ✨ 核心特性

- **🧠 LLM 驱动的深度讲解** — 每个单词自动生成音标、词根拆解、考研真题例句、近反义词辨析、记忆口诀和背诵优先级标记
- **📚 RAG 检索增强生成** — 基于 Chroma 向量知识库检索单词释义与真题考法，减少 LLM 幻觉，确保内容精准
- **🔄 艾宾浩斯科学复习** — 新学单词在第 1、2、4、7、15 天自动推送复习提醒，先测后讲，重点强化易错词
- **📝 智能自测系统** — 支持英译汉、汉译英、听写、单选、选词填空等多种自测模式
- **❌ 错题自动复盘** — 错题自动归集入库，隔天主动推送复盘，并由 LLM 生成定制化变式巩固练习
- **🎯 应试提分导向** — 拒绝机械直译，所有内容服务应试得分，覆盖熟词僻义、高频考点、写作同义替换

---

## 🏗️ 技术架构

```
danci/
├── frontend/                  # Vue 3 前端（SPA）
│   ├── src/
│   │   ├── views/
│   │   │   ├── Favorites.vue  # 生词收藏页
│   │   │   └── Errors.vue     # 错题分析与AI巩固练习
│   │   ├── stores/            # Pinia 状态管理
│   │   ├── router/            # Vue Router 路由
│   │   └── api/               # Axios 请求封装
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
│
├── backend/                   # Python 后端服务
│   ├── api/                   # API 路由层
│   ├── core/
│   │   ├── llm/               # LLM 客户端 + 提示词工程
│   │   │   └── llm_client.py  # 背诵内容生成 / 自测出题 / 错题复盘
│   │   ├── knowledge/         # RAG 知识库
│   │   │   ├── vector_store.py # Chroma 向量存储（四级/六级/考研核心/熟词僻义）
│   │   │   └── retriever.py   # 检索增强生成管线
│   │   ├── memory/            # 短期记忆缓存（会话级 TTL）
│   │   ├── context/           # 上下文管理 + 超长自动压缩
│   │   └── tools/
│   │       ├── dictionary.py  # 本地词库查词工具
│   │       └── pronunciation.py # 发音 API（英/美音 TTS）
│   ├── models/                # 数据库模型
│   ├── schemas/               # Pydantic 数据校验
│   ├── services/              # 业务逻辑层
│   └── config.py              # 全局配置（LLM / DB / Chroma / 艾宾浩斯间隔）
│
├── data/                      # 数据文件
│   ├── kaoyan.json            # 考研核心词库（~5500 词）
│   ├── cet4.json              # 四级词库（~4500 词）
│   ├── cet6.json              # 六级词库（~6000 词）
│   ├── all_words.json         # 全词库汇总
│   ├── danci.sqlite           # SQLite 本地数据库
│   └── chroma_db/             # Chroma 向量持久化目录
│
├── memory/                    # 用户记忆文件（学习进度、错题本）
├── scripts/                   # 辅助脚本
├── CLAUDE.md                  # Claude 智能体行为规范（项目灵魂）
└── README.md
```

### 技术栈

| 层 | 技术选型 |
|---|---|
| **前端框架** | Vue 3 + Vite + Pinia + Vue Router |
| **HTTP 客户端** | Axios |
| **后端语言** | Python 3.12+ (async/await) |
| **LLM 接入** | OpenAI 兼容 API（GPT-4o-mini / 可替换任意模型） |
| **向量数据库** | Chroma（本地持久化存储） |
| **关系数据库** | SQLite（默认）/ MySQL 8.0（可选） |
| **异步 HTTP** | httpx |
| **CSS 方案** | Scoped CSS (零依赖) |

---

## 🚀 快速开始

### 环境要求

- **Python** ≥ 3.10
- **Node.js** ≥ 18
- **Chroma** 向量数据库（自动安装依赖）

### 1. 克隆项目

```bash
git clone <repo-url>
cd danci
```

### 2. 后端配置

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r backend/requirements.txt

# 配置环境变量
cp .env.example .env
```

编辑 `.env` 文件，填入你的 LLM API Key：

```env
# LLM 配置（支持任意 OpenAI 兼容 API）
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini

# 数据库
USE_SQLITE=true
# 如使用 MySQL: USE_SQLITE=false 并配置 MYSQL_* 变量
```

### 3. 初始化数据

```bash
# 导入词库到向量数据库
python scripts/init_knowledge_base.py

# 初始化数据库表结构
python scripts/init_db.py
```

### 4. 启动服务

```bash
# 启动后端 API（默认 :8000）
python -m backend.main

# 启动前端开发服务器
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173` 开始背词。

---

## 📖 使用指南

### 智能体对话指令

在对话中直接输入以下指令即可触发对应功能：

| 指令 | 功能说明 |
|---|---|
| `自测` / `英译汉自测` | 英文报词，回复中文释义 |
| `默写` / `汉译英默写` | 中文报词，拼写英文 |
| `听写` | 进入听写模式（播放发音后拼写） |
| `今日清单` / `生成今日背诵清单` | 生成今日 20 词学习任务 |
| `复习` / `快速复盘旧词` | 抽查已学单词 |
| `错题` / `导出错题` | 查看或导出错题本 |
| `下一个20词` / `下一天` | 进入下一组 20 个新词 |
| `词根速记` | 按词根专题批量记忆 |
| `同义替换` | 写作高分替换词整理 |

### 发送单个单词

输入任意单词即可获得深度讲解：

- 📢 标准音标（英音 + 美音）
- 📖 核心释义（**考试高频义** vs **熟词僻义**）
- 🌳 词根词缀拆解
- 📝 2 个考研真题原句（标注年份和题型）
- 🔄 易混形近词辨析（表格对比）
- 🧠 记忆口诀
- ⭐ 背诵优先级（必背 / 高频 / 低频 / 熟词僻义）

### 复习机制

```
学习 Day 0  ──→ 第1天复习 ──→ 第2天复习 ──→ 第4天复习 ──→ 第7天复习 ──→ 第15天复习
                 (短时记忆)   (巩固)       (强化)       (长期记忆)   (稳定)
```

每次复习**先测试再讲解**，已掌握单词自动弱化，集中火力攻克易错词和熟词僻义。

---

## ⚙️ 配置说明

### 艾宾浩斯复习间隔

可在 `backend/config.py` 中自定义复习间隔：

```python
EBBINGHAUS_INTERVALS = [0, 1, 2, 4, 7, 15, 30, 60, 120]  # 单位：天
```

### 每日新词量

在 `CLAUDE.md` 中修改：

```markdown
- 每日新词量：**20词**   ← 改成你需要的数量
```

### LLM 模型切换

支持任意兼容 OpenAI API 格式的大模型，在 `.env` 中修改：

```env
LLM_MODEL=gpt-4o-mini       # 可换成 deepseek-chat / qwen-turbo / glm-4 等
LLM_API_BASE=https://your-api-endpoint/v1
```

---

## 📂 项目文件说明

| 文件/目录 | 用途 |
|---|---|
| `CLAUDE.md` | **项目灵魂** — 定义智能体的身份、行为规范、输出格式、互动指令 |
| `memory/` | 用户学习进度、错题本等记忆文件的持久化存储 |
| `data/*.json` | 各考纲词库原始数据 |
| `data/danci.sqlite` | 关系型数据库（用户、单词、错题、进度） |
| `data/chroma_db/` | Chroma 向量库持久化文件 |
| `backend/config.py` | 全局配置唯一入口 |

---

## 🛠️ 开发计划

- [ ] WebSocket 实时推送复习提醒
- [ ] 单词发音播放（已完成前端集成）
- [ ] 移动端 PWA 适配
- [ ] 背诵打卡与连续天数统计
- [ ] 研友排行榜 / 学习小组
- [ ] 更多考纲支持（雅思、托福）

---

## 📄 License

MIT — 仅供学习交流使用，考研真题例句版权归原出版方所有。
