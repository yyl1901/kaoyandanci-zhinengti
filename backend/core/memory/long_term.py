"""
长期记忆模块 —— MySQL持久化存储
用户背诵记录、错题本、生词本、艾宾浩斯复习日程
"""
from datetime import date, timedelta
from sqlalchemy import select, update, delete, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.database import (
    User, Word, StudyRecord, ErrorBook, Favorite,
    DailyPlan, ConversationContext, WordStatus, QuizType,
)


# ==================== 用户相关 ====================

async def get_or_create_user(
    session: AsyncSession,
    username: str,
    exam_type: str = "cet4",
    daily_count: int = 30,
) -> User:
    """获取或创建用户"""
    result = await session.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(username=username, exam_type=exam_type, daily_count=daily_count)
        session.add(user)
        await session.flush()
    return user


async def update_user_settings(
    session: AsyncSession, user_id: int, **kwargs
) -> User | None:
    """更新用户设置"""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        for k, v in kwargs.items():
            if hasattr(user, k) and v is not None:
                setattr(user, k, v)
        await session.flush()
    return user


# ==================== 单词相关 ====================

async def get_word(session: AsyncSession, word_id: int) -> Word | None:
    """获取单词详情"""
    result = await session.execute(select(Word).where(Word.id == word_id))
    return result.scalar_one_or_none()


async def get_words_by_ids(session: AsyncSession, word_ids: list[int]) -> list[Word]:
    """批量获取单词"""
    if not word_ids:
        return []
    result = await session.execute(select(Word).where(Word.id.in_(word_ids)))
    return list(result.scalars().all())


async def get_words_by_exam(
    session: AsyncSession,
    exam_type: str,
    category: str | None = None,
    offset: int = 0,
    limit: int = 100,
    order_by_frequency: bool = False,
) -> list[Word]:
    """按考纲获取单词列表"""
    stmt = select(Word).where(Word.exam_type == exam_type)
    if category:
        stmt = stmt.where(Word.category == category)
    if order_by_frequency:
        stmt = stmt.order_by(desc(Word.frequency), Word.id)
    else:
        stmt = stmt.order_by(Word.id)
    stmt = stmt.offset(offset).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ==================== 学习记录 ====================

async def get_study_records(
    session: AsyncSession, user_id: int, status: WordStatus | None = None
) -> list[StudyRecord]:
    """获取用户学习记录"""
    stmt = select(StudyRecord).where(StudyRecord.user_id == user_id)
    if status:
        stmt = stmt.where(StudyRecord.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_due_reviews(
    session: AsyncSession, user_id: int, as_of: date | None = None
) -> list[StudyRecord]:
    """获取待复习的学习记录"""
    today = as_of or date.today()
    stmt = (
        select(StudyRecord)
        .where(
            and_(
                StudyRecord.user_id == user_id,
                StudyRecord.next_review <= today,
                StudyRecord.status != WordStatus.mastered,
            )
        )
        .order_by(StudyRecord.next_review.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_learned_word_ids(session: AsyncSession, user_id: int) -> set[int]:
    """获取用户已学的单词ID集合"""
    result = await session.execute(
        select(StudyRecord.word_id).where(StudyRecord.user_id == user_id)
    )
    return {row[0] for row in result.all()}


async def upsert_study_record(
    session: AsyncSession,
    user_id: int,
    word_id: int,
    status: WordStatus = WordStatus.new,
    ebbinghaus_stage: int = 0,
    next_review: date | None = None,
) -> StudyRecord:
    """创建或更新学习记录"""
    result = await session.execute(
        select(StudyRecord).where(
            and_(StudyRecord.user_id == user_id, StudyRecord.word_id == word_id)
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        record = StudyRecord(
            user_id=user_id,
            word_id=word_id,
            status=status,
            ebbinghaus_stage=ebbinghaus_stage,
            last_reviewed=date.today(),
            next_review=next_review or date.today() + timedelta(days=1),
        )
        session.add(record)
    else:
        record.status = status
        record.ebbinghaus_stage = ebbinghaus_stage
        record.last_reviewed = date.today()
        if next_review:
            record.next_review = next_review
    await session.flush()
    return record


async def record_review_result(
    session: AsyncSession,
    user_id: int,
    word_id: int,
    is_correct: bool,
    new_stage: int,
    next_review: date,
) -> StudyRecord:
    """记录复习结果并更新阶段"""
    result = await session.execute(
        select(StudyRecord).where(
            and_(StudyRecord.user_id == user_id, StudyRecord.word_id == word_id)
        )
    )
    record = result.scalar_one_or_none()
    if record:
        if is_correct:
            record.correct_count = (record.correct_count or 0) + 1
        else:
            record.wrong_count = (record.wrong_count or 0) + 1
        record.ebbinghaus_stage = new_stage
        record.last_reviewed = date.today()
        record.next_review = next_review
        if new_stage >= 8:
            record.status = WordStatus.mastered
        elif record.status == WordStatus.new:
            record.status = WordStatus.learning
        else:
            record.status = WordStatus.review
        await session.flush()
    return record


# ==================== 错题本 ====================

async def add_error(
    session: AsyncSession,
    user_id: int,
    word_id: int,
    quiz_type: str,
    question: str,
    user_answer: str,
    correct_answer: str,
) -> ErrorBook:
    """添加错题记录"""
    error = ErrorBook(
        user_id=user_id,
        word_id=word_id,
        quiz_type=quiz_type,
        question=question,
        user_answer=user_answer,
        correct_answer=correct_answer,
        is_correct=0,
    )
    session.add(error)
    await session.flush()
    return error


async def get_errors(
    session: AsyncSession, user_id: int, limit: int = 50, offset: int = 0
) -> list[ErrorBook]:
    """获取用户错题列表"""
    result = await session.execute(
        select(ErrorBook)
        .where(ErrorBook.user_id == user_id)
        .order_by(ErrorBook.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_error_stats(session: AsyncSession, user_id: int) -> dict:
    """错题统计"""
    total_result = await session.execute(
        select(func.count()).where(ErrorBook.user_id == user_id)
    )
    recent_result = await session.execute(
        select(func.count()).where(
            and_(
                ErrorBook.user_id == user_id,
                ErrorBook.created_at >= date.today(),
            )
        )
    )
    return {
        "total": total_result.scalar() or 0,
        "today": recent_result.scalar() or 0,
    }


# ==================== 生词收藏 ====================

async def add_favorite(session: AsyncSession, user_id: int, word_id: int) -> Favorite | None:
    """添加生词收藏"""
    # 检查是否已收藏
    result = await session.execute(
        select(Favorite).where(
            and_(Favorite.user_id == user_id, Favorite.word_id == word_id)
        )
    )
    if result.scalar_one_or_none():
        return None  # 已收藏
    fav = Favorite(user_id=user_id, word_id=word_id)
    session.add(fav)
    await session.flush()
    return fav


async def remove_favorite(session: AsyncSession, user_id: int, word_id: int) -> bool:
    """取消收藏"""
    result = await session.execute(
        delete(Favorite).where(
            and_(Favorite.user_id == user_id, Favorite.word_id == word_id)
        )
    )
    await session.flush()
    return result.rowcount > 0


async def get_favorites(
    session: AsyncSession, user_id: int, limit: int = 50
) -> list[dict]:
    """获取收藏列表（含单词信息）"""
    result = await session.execute(
        select(Favorite, Word)
        .join(Word, Favorite.word_id == Word.id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .limit(limit)
    )
    rows = result.all()
    return [
        {
            "id": fav.id,
            "created_at": fav.created_at.isoformat() if fav.created_at else None,
            "word": {
                "id": word.id,
                "word": word.word,
                "phonetic_uk": word.phonetic_uk,
                "phonetic_us": word.phonetic_us,
                "definition": word.definition,
            },
        }
        for fav, word in rows
    ]


# ==================== 每日计划 ====================

async def get_or_create_daily_plan(
    session: AsyncSession, user_id: int, plan_date: date | None = None
) -> DailyPlan:
    """获取或创建每日学习计划"""
    today = plan_date or date.today()
    result = await session.execute(
        select(DailyPlan).where(
            and_(DailyPlan.user_id == user_id, DailyPlan.plan_date == today)
        )
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        plan = DailyPlan(user_id=user_id, plan_date=today)
        session.add(plan)
        await session.flush()
    return plan


async def update_plan_progress(
    session: AsyncSession,
    user_id: int,
    completed_new: int = 0,
    completed_review: int = 0,
    study_seconds: int = 0,
    check_in: bool = False,
) -> DailyPlan | None:
    """更新计划进度"""
    result = await session.execute(
        select(DailyPlan).where(
            and_(DailyPlan.user_id == user_id, DailyPlan.plan_date == date.today())
        )
    )
    plan = result.scalar_one_or_none()
    if plan:
        plan.completed_new += completed_new
        plan.completed_review += completed_review
        plan.study_seconds = (plan.study_seconds or 0) + study_seconds
        if check_in:
            plan.is_checked_in = 1
        await session.flush()
    return plan


async def get_checkin_streak(session: AsyncSession, user_id: int) -> int:
    """计算连续打卡天数"""
    today = date.today()
    streak = 0
    for i in range(365):
        check_date = today - timedelta(days=i)
        result = await session.execute(
            select(DailyPlan).where(
                and_(
                    DailyPlan.user_id == user_id,
                    DailyPlan.plan_date == check_date,
                    DailyPlan.is_checked_in == 1,
                )
            )
        )
        if result.scalar_one_or_none():
            streak += 1
        else:
            break
    return streak


# ==================== 对话上下文持久化 ====================

async def save_context(
    session: AsyncSession, user_id: int, context_data: dict
) -> ConversationContext:
    """保存用户对话上下文"""
    result = await session.execute(
        select(ConversationContext).where(ConversationContext.user_id == user_id)
    )
    ctx = result.scalar_one_or_none()
    if ctx is None:
        ctx = ConversationContext(user_id=user_id, **context_data)
        session.add(ctx)
    else:
        for k, v in context_data.items():
            if hasattr(ctx, k):
                setattr(ctx, k, v)
    await session.flush()
    return ctx


async def load_context(
    session: AsyncSession, user_id: int
) -> ConversationContext | None:
    """加载用户对话上下文"""
    result = await session.execute(
        select(ConversationContext).where(ConversationContext.user_id == user_id)
    )
    return result.scalar_one_or_none()
