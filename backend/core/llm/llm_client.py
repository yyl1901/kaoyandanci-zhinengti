"""
LLM 模块 —— 提示词工程 + 大模型API对接
"""
import json
import httpx
from backend.config import LLM_CONFIG

# ============================================================
# 定制化提示词模板
# ============================================================

SYSTEM_PROMPT_BASE = """你是一位专业的英语词汇教学专家，擅长用词根词缀法、联想记忆法帮助学生记忆单词。
你必须严格按JSON格式返回结果，不要包含任何JSON之外的内容。"""

# ---- 背词提示词 ----
RECITATION_PROMPT = """{base}

请为以下单词生成详细的背诵学习内容：
**单词**: {word}
**考纲**: {exam_name}
**已知释义**: {definition}

请按以下JSON格式返回（务必严格遵守格式）：
```json
{{
  "word": "单词",
  "phonetic_uk": "英式音标",
  "phonetic_us": "美式音标",
  "definitions": [
    {{"pos": "词性", "meaning": "中文释义"}}
  ],
  "etymology": {{
    "root": "词根",
    "affix": ["前缀/后缀列表"],
    "explanation": "词根词缀拆解说明（中文，生动形象）"
  }},
  "example_sentences": [
    {{"en": "真题例句英文", "cn": "中文翻译", "source": "真题来源（如2020考研阅读）"}}
  ],
  "synonyms": [
    {{"word": "近义词", "nuance": "与目标词的区别说明"}}
  ],
  "antonyms": ["反义词列表"],
  "memory_tip": "记忆技巧（联想、谐音等，中文）",
  "exam_focus": ["考点1", "考点2"],
  "common_mistakes": ["常见错误1"]
}}
"""

# ---- 出题提示词 ----
QUIZ_PROMPT = """{base}

请根据以下已背单词列表生成自测题：
**已背单词列表**（含释义）：
{word_list}

**出题要求**：
- 生成 {question_count} 道{quiz_type}
- 单选：4个选项，考查词义辨析、固定搭配、近义词区分
- 选词填空：给出一个句子及4个备选词，考查语境理解
- 难度递进，覆盖不同掌握程度

请严格按以下JSON格式返回：
```json
{{
  "questions": [
    {{
      "type": "multiple_choice 或 cloze",
      "stem": "题干",
      "context_sentence": "上下文句子（选词填空必有）",
      "options": ["A. 选项1", "B. 选项2", "C. 选项3", "D. 选项4"],
      "correct_answer": "正确选项（完整字符串）",
      "explanation": "解析说明",
      "target_word_id": 对应单词ID,
      "exam_point": "考查的知识点"
    }}
  ]
}}
```
"""

# ---- 复盘提示词 ----
REVIEW_PROMPT = """{base}

用户以下单词的题目做错了，请生成定制化的巩固练习：
**错题列表**：
{error_list}

**要求**：
- 每道错题生成2道变式巩固练习，换一种考查角度
- 重点强化易错知识点
- 1道单选题 + 1道选词填空

请严格按以下JSON格式返回：
```json
{{
  "exercises": [
    {{
      "original_word": "原单词",
      "mistake_analysis": "错误原因分析",
      "reinforcement": [
        {{
          "type": "multiple_choice 或 cloze",
          "stem": "题干",
          "options": ["A. x", "B. x", "C. x", "D. x"],
          "correct_answer": "正确选项",
          "explanation": "解析"
        }}
      ]
    }}
  ]
}}
```
"""


class LLMClient:
    """大模型API客户端"""

    def __init__(self, config: dict | None = None):
        cfg = config or LLM_CONFIG
        self.api_base = cfg["api_base"]
        self.api_key = cfg["api_key"]
        self.model = cfg["model"]
        self.temperature = cfg.get("temperature", 0.3)
        self.max_tokens = cfg.get("max_tokens", 2048)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat(self, messages: list[dict], **kwargs) -> str:
        """通用对话调用"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            }
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def generate_recitation(self, word: str, definition: str, exam_type: str) -> dict:
        """生成单词背诵内容"""
        exam_names = {"cet4": "四级", "cet6": "六级", "kaoyan": "考研英语"}
        prompt = RECITATION_PROMPT.format(
            base=SYSTEM_PROMPT_BASE.format(),
            word=word,
            definition=definition,
            exam_name=exam_names.get(exam_type, exam_type),
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_BASE},
            {"role": "user", "content": prompt},
        ]
        result = await self.chat(messages)
        return self._parse_json(result)

    async def generate_quiz(self, word_list: list[dict], question_count: int = 10) -> dict:
        """生成自测题目"""
        words_text = json.dumps(word_list, ensure_ascii=False, indent=2)
        prompt = QUIZ_PROMPT.format(
            base=SYSTEM_PROMPT_BASE,
            word_list=words_text,
            question_count=question_count,
            quiz_type="混合（单选题+选词填空）",
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_BASE},
            {"role": "user", "content": prompt},
        ]
        result = await self.chat(messages)
        return self._parse_json(result)

    async def generate_review_exercises(self, errors: list[dict]) -> dict:
        """生成错题复盘巩固练习"""
        errors_text = json.dumps(errors, ensure_ascii=False, indent=2)
        prompt = REVIEW_PROMPT.format(
            base=SYSTEM_PROMPT_BASE,
            error_list=errors_text,
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_BASE},
            {"role": "user", "content": prompt},
        ]
        result = await self.chat(messages)
        return self._parse_json(result)

    def _parse_json(self, text: str) -> dict:
        """从LLM返回中提取JSON"""
        text = text.strip()
        # 移除 markdown 代码块标记
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:] if lines[0].startswith("```") else lines
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取 JSON 片段
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            raise
