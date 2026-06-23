"""
FastAPI API路由 —— 承接前端请求、参数校验、任务分发
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.schemas.api_schemas import (
    APIResponse, UserSettingsRequest, QuizSubmitRequest,
    ReviewMarkRequest, FavoriteRequest,
)
from backend.services.agent_service import AgentService
from backend.models.database import create_async_session

router = APIRouter(prefix="/api/v1", tags=["单词备考"])
service = AgentService()


def _respond(result):
    """统一包装服务返回值：如果包含 error 字段则返回 error 响应"""
    if isinstance(result, dict) and result.get("error"):
        return APIResponse.error(result.get("error"))
    return APIResponse.ok(result)


async def get_session():
    """异步数据库会话依赖注入"""
    async with create_async_session() as session:
        try:
            yield session
            # 在请求处理成功后提交事务
            await session.commit()
        except Exception:
            # 出现异常时回滚以避免脏数据
            await session.rollback()
            raise


# ==================== 用户相关 ====================

@router.post("/user/init", summary="初始化用户")
async def init_user(req: UserSettingsRequest, session: AsyncSession = Depends(get_session)):
    """注册或登录用户，设置考纲和每日背诵量"""
    try:
        user = await service.ensure_user(
            session, req.username, req.exam_type, req.daily_count
        )
        return APIResponse.ok(user, "用户初始化成功")
    except Exception as e:
        return APIResponse.error(str(e))


@router.put("/user/settings", summary="更新用户设置")
async def update_settings(
    user_id: int = Query(..., description="用户ID"),
    exam_type: str | None = Query(None, description="考纲"),
    daily_count: int | None = Query(None, description="每日背诵量"),
    session: AsyncSession = Depends(get_session),
):
    """更新考纲、每日背诵量等设置"""
    kwargs = {}
    if exam_type:
        kwargs["exam_type"] = exam_type
    if daily_count is not None:
        kwargs["daily_count"] = daily_count
    result = await service.update_settings(session, user_id, **kwargs)
    return APIResponse.ok(result)


# ==================== 背诵相关 ====================

@router.get("/recite/daily-list", summary="获取每日背诵清单")
async def get_daily_list(
    user_id: int = Query(..., description="用户ID"),
    session: AsyncSession = Depends(get_session),
):
    """获取今日待背新词 + 待复习旧词列表"""
    try:
        result = await service.get_daily_words(session, user_id)
        return APIResponse.ok(result)
    except ValueError as e:
        return APIResponse.error(str(e))


@router.get("/recite/word-detail", summary="获取单词详细讲解")
async def get_word_detail(
    user_id: int = Query(..., description="用户ID"),
    word_id: int = Query(..., description="单词ID"),
    session: AsyncSession = Depends(get_session),
):
    """词根词缀拆解、真题例句、近反义词、记忆技巧"""
    try:
        result = await service.explain_word(session, user_id, word_id)
        return _respond(result)
    except ValueError as e:
        return APIResponse.error(str(e))


@router.post("/recite/review-word", summary="单词复习标记")
async def mark_review(
    req: ReviewMarkRequest,
    user_id: int = Query(..., description="用户ID"),
    session: AsyncSession = Depends(get_session),
):
    """标记复习结果（记得/忘记），更新艾宾浩斯阶段"""
    try:
        result = await service.review_word(session, user_id, req.word_id, req.remembered)
        return APIResponse.ok(result)
    except ValueError as e:
        return APIResponse.error(str(e))


# ==================== 学习时长心跳 ====================

@router.post("/recite/heartbeat", summary="上报学习时长")
async def heartbeat(
    user_id: int = Query(..., description="用户ID"),
    seconds: int = Query(default=30, description="本次上报的秒数", ge=1, le=120),
    session: AsyncSession = Depends(get_session),
):
    """每30秒调用一次，累计今日学习时长"""
    result = await service.heartbeat(session, user_id, seconds)
    return APIResponse.ok(result)


# ==================== 自测出题 ====================

@router.post("/quiz/generate", summary="生成自测题")
async def generate_quiz(
    user_id: int = Query(..., description="用户ID"),
    count: int = Query(default=10, description="题目数量", ge=5, le=30),
    source: str = Query(default="recent", description="题目来源: recent/errors/favorites"),
    session: AsyncSession = Depends(get_session),
):
    """生成专项自测试卷"""
    try:
        result = await service.generate_quiz(session, user_id, count, source)
        return _respond(result)
    except Exception as e:
        return APIResponse.error(str(e))


@router.post("/quiz/submit", summary="提交答案")
async def submit_quiz_answer(
    req: QuizSubmitRequest,
    user_id: int = Query(..., description="用户ID"),
    session: AsyncSession = Depends(get_session),
):
    """提交单题答案，自动判分并收录错题"""
    try:
        result = await service.submit_quiz_answer(
            session, user_id, req.quiz_id, req.question_index, req.user_answer
        )
        return _respond(result)
    except Exception as e:
        return APIResponse.error(str(e))


@router.post("/quiz/finish", summary="结束测验")
async def finish_quiz(
    quiz_id: str = Query(..., description="测验会话ID"),
    user_id: int = Query(..., description="用户ID"),
    session: AsyncSession = Depends(get_session),
):
    """结束测验，返回成绩报告"""
    try:
        result = await service.finish_quiz(session, user_id, quiz_id)
        return _respond(result)
    except Exception as e:
        return APIResponse.error(str(e))


# ==================== 错题复盘 ====================

@router.get("/errors/list", summary="错题列表")
async def get_error_list(
    user_id: int = Query(..., description="用户ID"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """获取用户错题本"""
    result = await service.get_errors(session, user_id, limit, offset)
    return APIResponse.ok(result)


@router.get("/errors/analysis", summary="错题统计分析")
async def get_error_analysis(
    user_id: int = Query(..., description="用户ID"),
    session: AsyncSession = Depends(get_session),
):
    """错题统计 + 高频错词TOP10"""
    result = await service.get_error_analysis(session, user_id)
    return APIResponse.ok(result)


@router.post("/errors/review-exercises", summary="生成错题巩固练习")
async def generate_review_exercises(
    user_id: int = Query(..., description="用户ID"),
    session: AsyncSession = Depends(get_session),
):
    """基于错题生成LLM定制化巩固练习"""
    result = await service.generate_review_exercises(session, user_id)
    return _respond(result)


# ==================== 生词收藏 ====================

@router.post("/favorite/add", summary="添加生词收藏")
async def add_favorite(
    req: FavoriteRequest,
    user_id: int = Query(..., description="用户ID"),
    session: AsyncSession = Depends(get_session),
):
    """一键收藏生词"""
    result = await service.add_favorite(session, user_id, req.word_id)
    return APIResponse.ok(result)


@router.delete("/favorite/remove", summary="取消收藏")
async def remove_fav(
    word_id: int = Query(..., description="单词ID"),
    user_id: int = Query(..., description="用户ID"),
    session: AsyncSession = Depends(get_session),
):
    """取消收藏"""
    result = await service.remove_favorite(session, user_id, word_id)
    return APIResponse.ok(result)


@router.get("/favorite/list", summary="生词收藏列表")
async def list_favorites(
    user_id: int = Query(..., description="用户ID"),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """获取收藏列表"""
    result = await service.get_favorites(session, user_id, limit)
    return APIResponse.ok(result)


# ==================== 计划打卡 ====================

@router.get("/plan/daily", summary="每日学习计划")
async def get_daily_plan(
    user_id: int = Query(..., description="用户ID"),
    session: AsyncSession = Depends(get_session),
):
    """今日复习计划 + 7天日程预览"""
    try:
        result = await service.get_daily_plan(session, user_id)
        return APIResponse.ok(result)
    except ValueError as e:
        return APIResponse.error(str(e))


@router.post("/plan/check-in", summary="每日打卡")
async def check_in(
    user_id: int = Query(..., description="用户ID"),
    session: AsyncSession = Depends(get_session),
):
    """完成今日学习，打卡记录"""
    try:
        result = await service.check_in(session, user_id)
        return APIResponse.ok(result)
    except ValueError as e:
        return APIResponse.error(str(e))


@router.get("/plan/progress", summary="学习进度总览")
async def get_progress(
    user_id: int = Query(..., description="用户ID"),
    session: AsyncSession = Depends(get_session),
):
    """总单词数、掌握率、正确率、打卡天数"""
    try:
        result = await service.get_progress(session, user_id)
        return APIResponse.ok(result)
    except ValueError as e:
        return APIResponse.error(str(e))


# ==================== 发音 ====================

@router.get("/tools/pronunciation", summary="获取单词发音")
async def get_pronunciation(
    word: str = Query(..., description="单词"),
    accent: str = Query(default="us", description="发音: uk/us"),
):
    """获取单词英美发音音频URL"""
    result = await service.get_pronunciation(word)
    if accent == "uk":
        return APIResponse.ok({
            "word": word,
            "audio_url": result.get("uk_audio_url"),
            "phonetic": result.get("phonetic_uk"),
        })
    return APIResponse.ok({
        "word": word,
        "audio_url": result.get("us_audio_url"),
        "phonetic": result.get("phonetic_us"),
    })


# ==================== 单词查询 ====================

@router.get("/word/search", summary="查词")
async def search_word(
    word: str = Query(..., description="单词"),
    user_id: int = Query(..., description="用户ID"),
    exam_type: str = Query(default=None, description="考纲（可选，不传则查所有考纲）"),
    session: AsyncSession = Depends(get_session),
):
    """搜索单词（优先数据库，其次本地词典）"""
    from backend.core.tools.dictionary import DictionaryTool
    from backend.config import DATA_DIR

    # 先查数据库（按考纲过滤，不传则查所有）
    from sqlalchemy import select
    from backend.models.database import Word
    stmt = select(Word).where(Word.word == word.lower().strip())
    if exam_type:
        stmt = stmt.where(Word.exam_type == exam_type)
    db_result = await session.execute(stmt)
    db_words = db_result.scalars().all()

    # 查本地词库
    dt = DictionaryTool(DATA_DIR)
    local_result = dt.lookup(word)

    # 合并结果：优先数据库（信息更全），数据库无则用本地词库
    merged = {}
    if db_words:
        # 取第一个匹配的数据库记录
        db_word = db_words[0]
        merged = {
            "word": db_word.word,
            "phonetic_uk": db_word.phonetic_uk or (local_result.get("phonetic_uk", "") if local_result else ""),
            "phonetic_us": db_word.phonetic_us or (local_result.get("phonetic_us", "") if local_result else ""),
            "definition": db_word.definition or (local_result.get("definition", "") if local_result else ""),
            "etymology": db_word.etymology or (local_result.get("etymology", "") if local_result else ""),
            "example_sentences": db_word.example_sentences or (local_result.get("example_sentences", "") if local_result else ""),
            "synonyms": db_word.synonyms or (local_result.get("synonyms", "") if local_result else ""),
            "antonyms": db_word.antonyms or (local_result.get("antonyms", "") if local_result else ""),
            "frequency": db_word.frequency or (local_result.get("frequency", 0) if local_result else 0),
            "exam_type": db_word.exam_type.value if db_word.exam_type else (local_result.get("exam_type", "") if local_result else ""),
            "category": db_word.category or (local_result.get("category", "") if local_result else ""),
        }
    elif local_result:
        merged = {
            "word": local_result.get("word", word),
            "phonetic_uk": local_result.get("phonetic_uk", ""),
            "phonetic_us": local_result.get("phonetic_us", ""),
            "definition": local_result.get("definition", ""),
            "etymology": local_result.get("etymology", ""),
            "example_sentences": local_result.get("example_sentences", ""),
            "synonyms": local_result.get("synonyms", ""),
            "antonyms": local_result.get("antonyms", ""),
            "frequency": local_result.get("frequency", 0),
            "exam_type": local_result.get("exam_type", ""),
            "category": local_result.get("category", ""),
        }

    return APIResponse.ok(merged)
