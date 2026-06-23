"""
复习规划智能体 —— 依托艾宾浩斯算法生成每日复习清单
"""
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.tools.ebbinghaus import EbbinghausCalculator
from backend.core.memory.long_term import (
    get_due_reviews, get_study_records, get_or_create_daily_plan,
    update_plan_progress, get_checkin_streak, get_words_by_ids,
)
from backend.models.database import WordStatus


class ReviewPlanningAgent:
    """
    复习规划智能体

    职责：
    1. 基于艾宾浩斯遗忘曲线生成每日复习清单
    2. 规划未来7天学习日程
    3. 打卡和进度追踪
    """

    def __init__(self):
        self.ebbinghaus = EbbinghausCalculator()

    async def get_daily_review_plan(
        self,
        session: AsyncSession,
        user_id: int,
        daily_count: int,
    ) -> dict:
        """
        获取今日复习计划（包含复习+新词）
        """
        today = date.today()

        # 1. 今日待复习
        due_reviews = await get_due_reviews(session, user_id)
        review_word_ids = [r.word_id for r in due_reviews if r.word_id]
        review_words = await get_words_by_ids(session, review_word_ids)
        review_word_map = {w.id: w for w in review_words}

        review_list = []
        for r in due_reviews:
            w = review_word_map.get(r.word_id)
            if w:
                review_list.append({
                    "record_id": r.id,
                    "word_id": w.id,
                    "word": w.word,
                    "definition": w.definition,
                    "ebbinghaus_stage": r.ebbinghaus_stage or 0,
                    "next_review": r.next_review.isoformat() if r.next_review else None,
                    "status": r.status.value if r.status else "new",
                    "correct_count": r.correct_count or 0,
                })

        # 2. 今日计划
        plan = await get_or_create_daily_plan(session, user_id)
        plan.planned_count = daily_count
        await session.flush()

        # 3. 7天计划预览（今日+未来6天，前端会过滤掉今天）
        week_plan = []
        for i in range(7):
            d = today + timedelta(days=i)
            # 预估当天待复习数
            if i == 0:
                estimated_review = len(review_list)
                estimated_new = daily_count
            else:
                # 粗略估计：每天新增 daily_count 个待复习
                estimated_review = max(0, len(review_list) + i * daily_count // 3 - i * 3)
                estimated_new = daily_count  # 新词始终按目标量

            week_plan.append({
                "date": d.isoformat(),
                "day_name": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][d.weekday()],
                "estimated_review": estimated_review,
                "estimated_new": estimated_new,
                "is_today": i == 0,
            })

        # 4. 连续打卡天数
        streak = await get_checkin_streak(session, user_id)

        return {
            "today": {
                "date": today.isoformat(),
                "review_count": len(review_list),
                "review_list": review_list,
                "new_word_quota": daily_count,
                "study_seconds": plan.study_seconds or 0,
                "completed_review": plan.completed_review or 0,
                "completed_new": plan.completed_new or 0,
                "is_checked_in": bool(plan.is_checked_in),
            },
            "streak_days": streak,
            "week_plan": week_plan,
            "ebbinghaus_info": {
                "stage_intervals": self.ebbinghaus.STAGE_INTERVALS,
                "current_stage_distribution": self._calc_stage_distribution(due_reviews),
            },
        }

    async def check_in(self, session: AsyncSession, user_id: int) -> dict:
        """
        每日打卡
        """
        await update_plan_progress(session, user_id, check_in=True)

        # 更新用户连续打卡天数
        from backend.core.memory.long_term import update_user_settings
        streak = await get_checkin_streak(session, user_id)
        await update_user_settings(session, user_id, streak_days=streak)

        return {
            "checked_in": True,
            "streak_days": streak,
            "date": date.today().isoformat(),
            "message": f"打卡成功！已连续学习 {streak} 天",
        }

    async def get_progress_summary(
        self, session: AsyncSession, user_id: int
    ) -> dict:
        """
        学习进度总览
        - 已掌握：艾宾浩斯阶段 >= 4（已复习至少4轮，接近长期记忆）
        - 学习中：阶段 1-3
        - 新词：阶段 0（刚学，尚未复习）
        - 学习次数：累计复习操作次数（反映投入时间）
        """
        records = await get_study_records(session, user_id)
        total = len(records)

        # 按阶段重新划分，比旧版只用 WordStatus 更精确
        mastered = sum(1 for r in records if (r.ebbinghaus_stage or 0) >= 4)
        learning = sum(1 for r in records if 1 <= (r.ebbinghaus_stage or 0) <= 3)
        new = sum(1 for r in records if (r.ebbinghaus_stage or 0) == 0)
        review = sum(1 for r in records if (r.ebbinghaus_stage or 0) >= 1)

        total_correct = sum(r.correct_count or 0 for r in records)
        total_wrong = sum(r.wrong_count or 0 for r in records)
        total_actions = total_correct + total_wrong  # 累计学习次数

        streak = await get_checkin_streak(session, user_id)

        # 掌握率：已掌握 / 已学（阶段>=1的）
        learned_total = review  # 至少复习过1次的
        mastery_rate = round(mastered / max(learned_total, 1) * 100, 1)

        return {
            "total_words": total,
            "mastered": mastered,
            "learning": learning + new,  # 学习中 = 阶段1-3 + 阶段0
            "review": review,
            "new": new,
            "mastery_rate": mastery_rate,
            "total_correct": total_correct,
            "total_wrong": total_wrong,
            "total_actions": total_actions,  # 累计学习操作次数
            "accuracy": round(
                total_correct / max(total_correct + total_wrong, 1) * 100, 1
            ),
            "streak_days": streak,
        }

    @staticmethod
    def _calc_stage_distribution(records: list) -> dict:
        """计算各艾宾浩斯阶段的单词分布"""
        dist = {}
        for i in range(9):
            dist[f"stage_{i}"] = 0
        for r in records:
            stage = r.ebbinghaus_stage or 0
            dist[f"stage_{min(stage, 8)}"] = dist.get(f"stage_{min(stage, 8)}", 0) + 1
        return dist
