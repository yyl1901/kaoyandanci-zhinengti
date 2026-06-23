"""
智能体服务层 —— 统一调度三大子智能体
向后端API网关提供统一的业务接口
"""
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.agents.recitation_agent import RecitationAgent
from backend.core.agents.quiz_agent import QuizAgent
from backend.core.agents.review_agent import ReviewPlanningAgent
from backend.core.memory.short_term import get_short_term_memory
from backend.core.memory.long_term import (
    get_or_create_user, update_user_settings,
    add_favorite, remove_favorite, get_favorites,
    get_errors, get_error_stats,
)
from backend.core.context.context_manager import get_context_manager
from backend.core.tools.pronunciation import PronunciationTool


def _enum_val(field, default=""):
    """安全提取枚举值：SQLite 下 Enum 字段可能是字符串而非枚举对象"""
    if field is None:
        return default
    if hasattr(field, "value"):
        return field.value
    return str(field) if field else default


class AgentService:
    """
    智能体服务总线

    前端请求 → API网关 → AgentService → 子智能体（背诵/出题/复习）
    负责：参数校验、任务分发、结果聚合、上下文管理
    """

    def __init__(self):
        self.recitation = RecitationAgent()
        self.quiz = QuizAgent()
        self.review = ReviewPlanningAgent()
        self.pronunciation = PronunciationTool()
        self.stm = get_short_term_memory()

    # ==================== 用户相关 ====================

    async def ensure_user(
        self, session: AsyncSession, username: str, exam_type: str, daily_count: int
    ) -> dict:
        """获取或创建用户"""
        user = await get_or_create_user(session, username, exam_type, daily_count)
        # 恢复上下文
        from backend.core.memory.long_term import load_context
        ctx = await load_context(session, user.id)
        cm = get_context_manager(user.id)
        if ctx:
            cm.restore_from_persist({
                "current_word_ids": ctx.current_word_ids,
                "last_error_ids": ctx.last_error_ids,
                "progress_summary": ctx.progress_summary,
            })
        return {
            "user_id": user.id,
            "username": user.username,
            "exam_type": _enum_val(user.exam_type, "kaoyan"),
            "daily_count": user.daily_count,
            "total_words_learned": user.total_words_learned or 0,
            "streak_days": user.streak_days or 0,
        }

    async def update_settings(
        self, session: AsyncSession, user_id: int, **kwargs
    ) -> dict:
        """更新用户设置"""
        user = await update_user_settings(session, user_id, **kwargs)
        if user:
            return {"message": "设置已更新", "settings": kwargs}
        return {"error": "用户不存在"}

    # ==================== 背诵 ====================

    async def get_daily_words(
        self, session: AsyncSession, user_id: int
    ) -> dict:
        """获取每日背诵清单"""
        user = await self._get_user(session, user_id)
        result = await self.recitation.get_daily_word_list(
            session, user_id,
            daily_count=user.daily_count or 30,
            exam_type=_enum_val(user.exam_type, "kaoyan"),
        )
        # 更新短期记忆
        all_ids = [w["word_id"] for w in result.get("new_list", [])]
        all_ids += [w["word_id"] for w in result.get("review_list", [])]
        self.stm.set_daily_words(user_id, all_ids)

        # 更新上下文
        cm = get_context_manager(user_id)
        cm.update_key_context(current_word_ids=all_ids)

        return result

    async def explain_word(
        self, session: AsyncSession, user_id: int, word_id: int
    ) -> dict:
        """讲解单词（含词根词缀拆解、真题例句等）"""
        user = await self._get_user(session, user_id)
        result = await self.recitation.explain_word(
            session, user_id, word_id,
            exam_type=_enum_val(user.exam_type, "kaoyan"),
        )
        cm = get_context_manager(user_id)
        cm.add_current_word(word_id)
        return result

    async def review_word(
        self, session: AsyncSession, user_id: int, word_id: int, remembered: bool
    ) -> dict:
        """标记复习结果"""
        return await self.recitation.mark_word_reviewed(
            session, user_id, word_id, remembered
        )

    # ==================== 出题测评 ====================

    async def generate_quiz(
        self, session: AsyncSession, user_id: int, count: int, source: str
    ) -> dict:
        """生成自测试卷"""
        return await self.quiz.generate_quiz(
            session, user_id, question_count=count, source=source
        )

    async def submit_quiz_answer(
        self, session: AsyncSession, user_id: int,
        quiz_id: str, question_index: int, user_answer: str,
    ) -> dict:
        """提交答案"""
        result = await self.quiz.submit_answer(
            session, user_id, quiz_id, question_index, user_answer
        )
        cm = get_context_manager(user_id)
        cm.add_error({
            "question_index": question_index,
            "is_correct": result.get("is_correct", False),
            "word": result.get("exam_point", ""),
        })
        return result

    async def finish_quiz(
        self, session: AsyncSession, user_id: int, quiz_id: str
    ) -> dict:
        """结束测验"""
        return await self.quiz.finish_quiz(session, user_id, quiz_id)

    # ==================== 错题复盘 ====================

    async def get_errors(
        self, session: AsyncSession, user_id: int, limit: int = 50, offset: int = 0
    ) -> dict:
        """获取错题列表"""
        errors = await get_errors(session, user_id, limit, offset)
        error_stats = await get_error_stats(session, user_id)

        from backend.core.memory.long_term import get_words_by_ids
        word_ids = [e.word_id for e in errors if e.word_id]
        words = await get_words_by_ids(session, word_ids)
        word_map = {w.id: w for w in words}

        error_list = []
        for e in errors:
            w = word_map.get(e.word_id)
            error_list.append({
                "id": e.id,
                "word": w.word if w else "未知",
                "definition": w.definition if w else "",
                "quiz_type": _enum_val(e.quiz_type, ""),
                "question": e.question,
                "user_answer": e.user_answer,
                "correct_answer": e.correct_answer,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            })

        return {"errors": error_list, "stats": error_stats}

    async def get_error_analysis(
        self, session: AsyncSession, user_id: int
    ) -> dict:
        """错题统计分析"""
        return await self.quiz.get_error_stats_analysis(session, user_id)

    # ==================== 复习巩固（LLM生成） ====================

    async def generate_review_exercises(
        self, session: AsyncSession, user_id: int
    ) -> dict:
        """根据错题生成定制化巩固练习"""
        errors = await get_errors(session, user_id, limit=20)
        if not errors:
            return {"message": "暂无错题，无需巩固"}

        error_data = []
        for e in errors:
            error_data.append({
                "word": str(e.word_id),
                "quiz_type": _enum_val(e.quiz_type, ""),
                "question": e.question,
                "user_wrong_answer": e.user_answer,
                "correct_answer": e.correct_answer,
            })

        return await self.quiz.llm.generate_review_exercises(error_data)

    # ==================== 生词收藏 ====================

    async def add_favorite(
        self, session: AsyncSession, user_id: int, word_id: int
    ) -> dict:
        """添加收藏"""
        result = await add_favorite(session, user_id, word_id)
        if result:
            return {"message": "收藏成功", "favorite_id": result.id}
        return {"message": "已收藏过该单词"}

    async def remove_favorite(
        self, session: AsyncSession, user_id: int, word_id: int
    ) -> dict:
        """取消收藏"""
        success = await remove_favorite(session, user_id, word_id)
        return {"message": "已取消收藏" if success else "未找到该收藏"}

    async def get_favorites(
        self, session: AsyncSession, user_id: int, limit: int = 50
    ) -> dict:
        """获取收藏列表"""
        favs = await get_favorites(session, user_id, limit)
        return {"favorites": favs, "total": len(favs)}

    # ==================== 计划打卡 ====================

    async def get_daily_plan(
        self, session: AsyncSession, user_id: int
    ) -> dict:
        """获取每日复习计划"""
        user = await self._get_user(session, user_id)
        return await self.review.get_daily_review_plan(
            session, user_id,
            daily_count=user.daily_count or 30,
        )

    async def check_in(self, session: AsyncSession, user_id: int) -> dict:
        """每日打卡"""
        return await self.review.check_in(session, user_id)

    async def get_progress(self, session: AsyncSession, user_id: int) -> dict:
        """学习进度总览"""
        return await self.review.get_progress_summary(session, user_id)

    # ==================== 发音 ====================

    async def get_pronunciation(self, word: str) -> dict:
        """获取单词发音URL"""
        return await self.pronunciation.get_pronunciation(word)

    # ==================== 学习时长 ====================

    async def heartbeat(self, session: AsyncSession, user_id: int, seconds: int = 30) -> dict:
        """心跳上报学习时长，每30秒调用一次"""
        from backend.core.memory.long_term import update_plan_progress
        plan = await update_plan_progress(session, user_id, study_seconds=seconds)
        total = plan.study_seconds if plan else 0
        return {
            "study_seconds": total,
            "study_minutes": round(total / 60, 1),
        }

    # ==================== 辅助方法 ====================

    async def _get_user(self, session: AsyncSession, user_id: int):
        """获取用户，不存在则报错"""
        from sqlalchemy import select
        from backend.models.database import User
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise ValueError(f"用户 {user_id} 不存在")
        return user
