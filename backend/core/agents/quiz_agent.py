"""
出题测评智能体 —— 基于用户生词/错题生成专项试卷
"""
import json
import re
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.llm.llm_client import LLMClient
from backend.core.memory.long_term import (
    get_errors, get_favorites, get_words_by_ids, add_error,
    get_study_records, upsert_study_record,
)
from backend.core.memory.short_term import get_short_term_memory
from backend.core.tools.ebbinghaus import EbbinghausCalculator
from backend.models.database import WordStatus


def _normalize_answer(ans: str) -> str:
    """提取选项字母，处理 'A' / 'A. xxx' / '(A)' 等格式"""
    ans = (ans or "").strip()
    if not ans:
        return ""
    # 纯字母且长度<=2（如 "A" 或 "Aa"）
    if len(ans) <= 2 and ans.replace(" ", "").isalpha():
        return ans.replace(" ", "").upper()
    # "A. xxx" 或 "A) xxx" 或 "(A) xxx" 或 "A、xxx"
    m = re.match(r'^\(?([A-Da-d])[\.\\)\、\s]', ans)
    if m:
        return m.group(1).upper()
    # 回退：全大写后取第一个字母
    return ans[0].upper() if ans else ""


class QuizAgent:
    """
    出题测评智能体

    职责：
    1. 基于用户已背单词生成自测试卷
    2. 支持两种题型：单选（词义辨析/近义词） + 选词填空（语境理解）
    3. 自动收录错题到错题本
    4. 错题统计分析
    """

    def __init__(self):
        self.llm = LLMClient()
        self.stm = get_short_term_memory()

    async def generate_quiz(
        self,
        session: AsyncSession,
        user_id: int,
        question_count: int = 10,
        source: str = "recent",  # recent | errors | favorites
    ) -> dict:
        """
        生成专项试卷
        :param source: 题目来源
            - recent: 基于最近学习的单词
            - errors: 基于错题本
            - favorites: 基于生词收藏
        """
        # 1. 收集素材单词
        target_words, target_word_objects = await self._collect_target_words(
            session, user_id, source
        )

        if not target_words:
            return {"error": "没有足够的单词生成题目，请先学习一些单词"}

        # 2. 优先尝试 LLM 生成，失败则使用本地算法
        quiz_data = None
        try:
            sample_words = target_words[:min(len(target_words), question_count)]
            quiz_data = await self.llm.generate_quiz(sample_words, question_count)
            if not quiz_data or not quiz_data.get("questions"):
                quiz_data = None  # LLM 返回空，降级到本地生成
        except Exception:
            quiz_data = None  # LLM 不可用，降级

        if quiz_data is None:
            # 本地算法兜底生成题目
            quiz_data = self._generate_local_quiz(target_word_objects, question_count)

        # 3. 创建测验会话
        quiz_id = str(uuid.uuid4())
        questions = quiz_data.get("questions", [])
        # 确保每道题都有 target_word_id
        for q in questions:
            if not q.get("target_word_id"):
                q["target_word_id"] = 0

        self.stm.start_quiz(quiz_id, {
            "user_id": user_id,
            "source": source,
            "questions": questions,
            "total": len(questions),
            "answers": {},
            "score": 0,
        })

        return {
            "quiz_id": quiz_id,
            "total": len(questions),
            "questions": questions,
        }

    async def _collect_target_words(
        self, session: AsyncSession, user_id: int, source: str
    ) -> tuple[list[dict], list]:
        """收集出题素材单词"""
        target_words = []
        target_word_objects = []

        if source == "errors":
            errors = await get_errors(session, user_id, limit=30)
            word_ids = list(set(e.word_id for e in errors if e.word_id))
            words = await get_words_by_ids(session, word_ids)
            target_word_objects = words
            target_words = [
                {"id": w.id, "word": w.word, "definition": w.definition}
                for w in words
            ]
        elif source == "favorites":
            favs = await get_favorites(session, user_id, limit=30)
            word_ids = [f["word"]["id"] for f in favs]
            words = await get_words_by_ids(session, word_ids)
            target_word_objects = words
            target_words = [
                {"id": w.id, "word": w.word, "definition": w.definition}
                for w in words
            ]
        else:  # recent
            records = await get_study_records(session, user_id)
            records.sort(key=lambda r: r.updated_at or r.created_at, reverse=True)
            recent_word_ids = [r.word_id for r in records[:50] if r.word_id]
            words = await get_words_by_ids(session, recent_word_ids)
            target_word_objects = words
            target_words = [
                {"id": w.id, "word": w.word, "definition": w.definition}
                for w in words
            ]

        return target_words, target_word_objects

    @staticmethod
    def _parse_definitions(def_text: str) -> list[str]:
        """解析单词释义 JSON 字符串，提取中文释义列表"""
        if not def_text:
            return ["（无释义）"]
        try:
            defs = json.loads(def_text)
            if isinstance(defs, list):
                return [d.get("meaning", str(d)) for d in defs if d.get("meaning")]
            elif isinstance(defs, dict):
                return [defs.get("meaning", str(defs))]
            elif isinstance(defs, str):
                return [defs]
        except (json.JSONDecodeError, TypeError):
            # 纯文本释义，直接返回
            return [def_text]
        return ["（无释义）"]

    @staticmethod
    def _parse_example_sentences(sent_text: str) -> list[dict]:
        """解析例句 JSON 字符串"""
        if not sent_text:
            return []
        try:
            examples = json.loads(sent_text)
            if isinstance(examples, list):
                return examples
            elif isinstance(examples, dict):
                return [examples]
        except (json.JSONDecodeError, TypeError):
            return []
        return []

    def _generate_local_quiz(
        self, target_words: list, question_count: int
    ) -> dict:
        """
        本地算法生成自测题（无需 LLM）
        从单词数据中自动创建单选 + 选词填空题
        """
        import random

        questions = []
        random.shuffle(target_words)
        words_pool = target_words[:question_count]

        # 收集所有释义作为干扰项池
        all_defs = []
        for w in target_words:
            meanings = self._parse_definitions(w.definition if hasattr(w, 'definition') else w.get("definition", ""))
            for m in meanings:
                all_defs.append(m)

        for i, w in enumerate(words_pool):
            word_text = w.word if hasattr(w, 'word') else w.get("word", "")
            word_id = w.id if hasattr(w, 'id') else w.get("id", 0)
            def_text = w.definition if hasattr(w, 'definition') else w.get("definition", "")
            meanings = self._parse_definitions(def_text)
            correct_meaning = meanings[0] if meanings else "（无释义）"

            # 交替生成单选题和选词填空
            if i % 2 == 0:
                # 单选题：问释义
                distractors = [d for d in all_defs if d != correct_meaning]
                if len(distractors) >= 3:
                    distractor_set = random.sample(distractors, 3)
                else:
                    distractor_set = (list(distractors) * 3)[:3]

                raw_options = [correct_meaning] + list(distractor_set)
                random.shuffle(raw_options)
                labels = ["A", "B", "C", "D"]
                options = [f"{labels[j]}. {raw_options[j]}" for j in range(len(raw_options))]
                correct_label = labels[raw_options.index(correct_meaning)]

                questions.append({
                    "type": "multiple_choice",
                    "stem": f"单词「{word_text}」的中文释义是什么？",
                    "context_sentence": "",
                    "options": options,
                    "correct_answer": f"{correct_label}. {correct_meaning}",
                    "explanation": f"「{word_text}」的意思是「{correct_meaning}」。{' 其他释义：' + '、'.join(meanings[1:]) if len(meanings) > 1 else ''}",
                    "target_word_id": word_id,
                    "exam_point": f"考查 {word_text} 的词义理解",
                })
            else:
                # 选词填空：从例句中挖空
                examples = self._parse_example_sentences(
                    w.example_sentences if hasattr(w, 'example_sentences') else w.get("example_sentences", "")
                )
                if examples and len(examples) > 0:
                    ex = examples[0]
                    sentence = ex.get("en", f"The {word_text} is important.")
                    cn_hint = ex.get("cn", "")
                    cloze_sentence = sentence.replace(word_text, "______", 1)
                    if cloze_sentence == sentence:
                        cloze_sentence = f"The word ______ is being tested."

                    other_words = [ow for ow in target_words if (ow.word if hasattr(ow, 'word') else ow.get("word", "")) != word_text]
                    if len(other_words) >= 3:
                        distractors = random.sample(other_words, 3)
                    else:
                        distractors = other_words[:3]
                    distractor_words = [(d.word if hasattr(d, 'word') else d.get("word", "")) for d in distractors]

                    raw_options = [word_text] + distractor_words
                    random.shuffle(raw_options)
                    labels = ["A", "B", "C", "D"]
                    options = [f"{labels[j]}. {raw_options[j]}" for j in range(len(raw_options))]
                    correct_label = labels[raw_options.index(word_text)]

                    questions.append({
                        "type": "cloze",
                        "stem": "选择正确的单词填入空白处：",
                        "context_sentence": f"{cloze_sentence}\n（{cn_hint}）" if cn_hint else cloze_sentence,
                        "options": options,
                        "correct_answer": f"{correct_label}. {word_text}",
                        "explanation": f"根据句意「{cn_hint or cloze_sentence}」，应填入「{word_text}」，意为「{correct_meaning}」。",
                        "target_word_id": word_id,
                        "exam_point": f"考查 {word_text} 的语境理解",
                    })
                else:
                    # 无例句时回退为单选题
                    distractors = [d for d in all_defs if d != correct_meaning]
                    if len(distractors) >= 3:
                        distractor_set = random.sample(distractors, 3)
                    else:
                        distractor_set = (list(distractors) * 3)[:3]

                    raw_options = [correct_meaning] + list(distractor_set)
                    random.shuffle(raw_options)
                    labels = ["A", "B", "C", "D"]
                    options = [f"{labels[j]}. {raw_options[j]}" for j in range(len(raw_options))]
                    correct_label = labels[raw_options.index(correct_meaning)]

                    questions.append({
                        "type": "multiple_choice",
                        "stem": f"单词「{word_text}」的中文释义是什么？",
                        "context_sentence": "",
                        "options": options,
                        "correct_answer": f"{correct_label}. {correct_meaning}",
                        "explanation": f"「{word_text}」的意思是「{correct_meaning}」。",
                        "target_word_id": word_id,
                        "exam_point": f"考查 {word_text} 的词义理解",
                    })

        return {"questions": questions}

    async def submit_answer(
        self,
        session: AsyncSession,
        user_id: int,
        quiz_id: str,
        question_index: int,
        user_answer: str,
    ) -> dict:
        """
        提交单题答案
        """
        quiz = self.stm.get_quiz(quiz_id)
        if not quiz:
            return {"error": "测验会话不存在或已过期"}

        questions = quiz.get("questions", [])
        if question_index >= len(questions):
            return {"error": "题目索引超出范围"}

        question = questions[question_index]
        correct_answer = question.get("correct_answer", "")
        is_correct = _normalize_answer(user_answer) == _normalize_answer(correct_answer)

        # 记录答案
        quiz["answers"][str(question_index)] = {
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
        }

        # 错题入库
        if not is_correct:
            target_word_id = question.get("target_word_id")
            await add_error(
                session, user_id,
                word_id=target_word_id or 0,
                quiz_type=question.get("type", "multiple_choice"),
                question=question.get("stem", ""),
                user_answer=user_answer,
                correct_answer=correct_answer,
            )

        # 更新正确数
        total_answered = len(quiz["answers"])
        correct_count = sum(1 for a in quiz["answers"].values() if a.get("is_correct"))
        quiz["score"] = correct_count

        return {
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": question.get("explanation", ""),
            "progress": f"{total_answered}/{quiz['total']}",
            "score": correct_count,
            "exam_point": question.get("exam_point", ""),
        }

    async def finish_quiz(
        self,
        session: AsyncSession,
        user_id: int,
        quiz_id: str,
    ) -> dict:
        """结束测验，返回成绩报告"""
        quiz = self.stm.end_quiz(quiz_id)
        if not quiz:
            return {"error": "测验会话不存在"}

        total = quiz["total"]
        score = quiz.get("score", 0)
        answers = quiz.get("answers", {})

        # 统计错题
        wrong_details = []
        for idx_str, ans in answers.items():
            if not ans.get("is_correct"):
                q = quiz["questions"][int(idx_str)]
                wrong_details.append({
                    "question_index": int(idx_str),
                    "stem": q.get("stem", ""),
                    "user_answer": ans["user_answer"],
                    "correct_answer": ans["correct_answer"],
                    "explanation": q.get("explanation", ""),
                })

        return {
            "quiz_id": quiz_id,
            "total": total,
            "score": score,
            "accuracy": round(score / max(total, 1) * 100, 1),
            "wrong_count": len(wrong_details),
            "wrong_details": wrong_details,
            "passed": score >= total * 0.6,
        }

    async def get_error_stats_analysis(
        self, session: AsyncSession, user_id: int
    ) -> dict:
        """错题统计分析"""
        from backend.core.memory.long_term import get_error_stats
        stats = await get_error_stats(session, user_id)
        errors = await get_errors(session, user_id, limit=100)

        # 按单词聚合统计
        word_error_count = {}
        for e in errors:
            if e.word_id:
                word_error_count[e.word_id] = word_error_count.get(e.word_id, 0) + 1

        # 高频错词TOP10
        sorted_errors = sorted(word_error_count.items(), key=lambda x: x[1], reverse=True)
        top_error_ids = [wid for wid, _ in sorted_errors[:10]]

        words = await get_words_by_ids(session, top_error_ids)
        word_map = {w.id: w for w in words}

        top_errors = []
        for word_id, count in sorted_errors[:10]:
            w = word_map.get(word_id)
            top_errors.append({
                "word_id": word_id,
                "word": w.word if w else "未知",
                "error_count": count,
            })

        return {
            "total_errors": stats["total"],
            "today_errors": stats["today"],
            "top_error_words": top_errors,
        }
