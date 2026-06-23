"""
背诵智能体 —— 每日新词推送、词义讲解
"""
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.llm.llm_client import LLMClient
from backend.core.memory.long_term import (
    get_words_by_exam, get_learned_word_ids, get_due_reviews,
    upsert_study_record, get_study_records,
)
from backend.core.tools.ebbinghaus import EbbinghausCalculator
from backend.core.knowledge.retriever import RAGRetriever
from backend.models.database import WordStatus


class RecitationAgent:
    """
    背诵智能体

    职责：
    1. 每日新词推送：根据考纲和用户进度，选择今日新词
    2. 词义讲解：结合词根词缀、真题例句、RAG检索生成详细讲解
    3. 学习记录：记录背诵进度，计算下次复习时间
    """

    def __init__(self):
        self.llm = LLMClient()
        self.rag = RAGRetriever()
        self.ebbinghaus = EbbinghausCalculator()

    async def get_daily_word_list(
        self,
        session: AsyncSession,
        user_id: int,
        daily_count: int,
        exam_type: str,
    ) -> dict:
        """
        生成每日背诵清单
        包含：新词 + 需复习的旧词
        """
        # 1. 获取待复习单词
        due_reviews = await get_due_reviews(session, user_id)
        review_ids = []
        for r in due_reviews:
            if r.word_id:
                review_ids.append(r.word_id)

        # 2. 获取已学单词ID
        learned_ids = await get_learned_word_ids(session, user_id)

        # 3. 计算今日可学新词数
        new_word_count = self.ebbinghaus.get_new_words_count(daily_count, len(review_ids))

        # 4. 从未学单词中按顺序取新词
        new_words = await get_words_by_exam(
            session, exam_type, category="core", offset=0,
            limit=new_word_count * 3, order_by_frequency=True,
        )
        new_word_candidates = [w for w in new_words if w.id not in learned_ids][:new_word_count]

        # 5. 获取复习单词详情（批量）
        from backend.core.memory.long_term import get_words_by_ids
        review_words = await get_words_by_ids(session, review_ids)
        review_word_map = {w.id: w for w in review_words}

        # 6. 获取今日学习时长
        from backend.core.memory.long_term import get_or_create_daily_plan
        plan = await get_or_create_daily_plan(session, user_id)
        study_seconds = plan.study_seconds if plan else 0

        # 7. 构建返回结果
        result = {
            "review_list": [],
            "new_list": [],
            "total": 0,
            "study_seconds": study_seconds,
        }

        for r in due_reviews:
            w = review_word_map.get(r.word_id)
            if w:
                result["review_list"].append({
                    "word_id": w.id,
                    "word": w.word,
                    "definition": w.definition,
                    "ebbinghaus_stage": r.ebbinghaus_stage,
                    "next_review": r.next_review.isoformat() if r.next_review else None,
                    "status": r.status.value if r.status else None,
                })
                result["total"] += 1

        for w in new_word_candidates:
            result["new_list"].append({
                "word_id": w.id,
                "word": w.word,
                "phonetic_uk": w.phonetic_uk,
                "phonetic_us": w.phonetic_us,
                "definition": w.definition,
            })
            result["total"] += 1

        return result

    async def explain_word(
        self,
        session: AsyncSession,
        user_id: int,
        word_id: int,
        exam_type: str,
    ) -> dict:
        """
        为单个单词生成详细讲解（RAG增强）
        包含：词根词缀拆解、真题例句、近反义词、记忆技巧、考点
        """
        from backend.core.memory.long_term import get_word as db_get_word

        word = await db_get_word(session, word_id)
        if not word:
            return {"error": "单词不存在"}

        # 先尝试用LLM生成丰富讲解
        try:
            explanation = await self.rag.get_word_detail_with_rag(word.word, exam_type)
        except Exception:
            explanation = None

        # 合并数据库已有数据
        result = {
            "word_id": word.id,
            "word": word.word,
            "phonetic_uk": word.phonetic_uk,
            "phonetic_us": word.phonetic_us,
            "definition": word.definition,
            "etymology": word.etymology or "",
            "example_sentences": word.example_sentences or "",
            "synonyms": word.synonyms or "",
            "antonyms": word.antonyms or "",
            "frequency": word.frequency or 0,
            "llm_explanation": explanation,
        }

        # 记录学习
        await upsert_study_record(
            session, user_id, word_id,
            status=WordStatus.learning,
            ebbinghaus_stage=0,
            next_review=self.ebbinghaus.get_next_review_date(0),
        )

        return result

    async def mark_word_reviewed(
        self,
        session: AsyncSession,
        user_id: int,
        word_id: int,
        remembered: bool,
    ) -> dict:
        """
        标记单词复习结果，更新艾宾浩斯阶段
        """
        from backend.core.memory.long_term import record_review_result
        from backend.core.memory.long_term import get_word as db_get_word

        records = await get_study_records(session, user_id)
        current_record = None
        for r in records:
            if r.word_id == word_id:
                current_record = r
                break

        current_stage = 0
        if current_record:
            current_stage = current_record.ebbinghaus_stage or 0

        new_stage, next_date = self.ebbinghaus.calc_next_stage(current_stage, remembered)

        await record_review_result(
            session, user_id, word_id, remembered, new_stage, next_date,
        )

        word = await db_get_word(session, word_id)
        return {
            "word_id": word_id,
            "word": word.word if word else "",
            "previous_stage": current_stage,
            "new_stage": new_stage,
            "next_review": next_date.isoformat(),
            "mastered": new_stage >= 8,
        }
