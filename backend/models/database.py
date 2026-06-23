"""
SQLAlchemy 数据库模型定义
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Date, DateTime,
    Enum, Float, ForeignKey, Index, UniqueConstraint, create_engine
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class ExamType(str, enum.Enum):
    cet4 = "cet4"
    cet6 = "cet6"
    kaoyan = "kaoyan"


class WordStatus(str, enum.Enum):
    new = "new"           # 新词，尚未学习
    learning = "learning"  # 学习中
    review = "review"     # 复习中
    mastered = "mastered" # 已掌握


class QuizType(str, enum.Enum):
    multiple_choice = "multiple_choice"  # 单选题
    cloze = "cloze"                      # 选词填空


# ==================== 用户表 ====================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, comment="用户名")
    exam_type = Column(Enum(ExamType), default=ExamType.kaoyan, nullable=False, comment="考纲类型")
    daily_count = Column(Integer, default=30, nullable=False, comment="每日背诵量")
    total_words_learned = Column(Integer, default=0, comment="已学单词总数")
    streak_days = Column(Integer, default=0, comment="连续打卡天数")
    created_at = Column(DateTime, server_default=func.now(), comment="注册时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 关系
    study_records = relationship("StudyRecord", back_populates="user")
    error_records = relationship("ErrorBook", back_populates="user")
    favorites = relationship("Favorite", back_populates="user")
    daily_plans = relationship("DailyPlan", back_populates="user")


# ==================== 单词表 ====================
class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(128), nullable=False, index=True, comment="单词")
    phonetic_uk = Column(String(128), comment="英式音标")
    phonetic_us = Column(String(128), comment="美式音标")
    definition = Column(Text, nullable=False, comment="释义（JSON格式：包含词性、释义）")
    exam_type = Column(Enum(ExamType), nullable=False, index=True, comment="考纲分类")
    category = Column(String(32), default="core", comment="单词子类：core核心词 / rare熟词僻义")
    etymology = Column(Text, comment="词根词缀拆解")
    example_sentences = Column(Text, comment="真题例句（JSON）")
    synonyms = Column(Text, comment="近义词（JSON数组）")
    antonyms = Column(Text, comment="反义词（JSON数组）")
    frequency = Column(Integer, default=0, comment="考频星级（1-5）")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_exam_category", "exam_type", "category"),
    )


# ==================== 学习记录表 ====================
class StudyRecord(Base):
    __tablename__ = "study_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(BigInteger, ForeignKey("words.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(WordStatus), default=WordStatus.new, nullable=False, comment="学习状态")
    ebbinghaus_stage = Column(Integer, default=0, comment="艾宾浩斯复习阶段（0-8）")
    correct_count = Column(Integer, default=0, comment="正确次数")
    wrong_count = Column(Integer, default=0, comment="错误次数")
    last_reviewed = Column(Date, comment="上次复习日期")
    next_review = Column(Date, index=True, comment="下次复习日期")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="study_records")
    word = relationship("Word")

    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_user_word"),
        Index("idx_user_next_review", "user_id", "next_review"),
    )


# ==================== 错题本表 ====================
class ErrorBook(Base):
    __tablename__ = "error_book"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(BigInteger, ForeignKey("words.id", ondelete="CASCADE"), nullable=False)
    quiz_type = Column(Enum(QuizType), nullable=False, comment="题目类型")
    question = Column(Text, nullable=False, comment="题目内容")
    user_answer = Column(String(512), comment="用户答案")
    correct_answer = Column(String(512), nullable=False, comment="正确答案")
    is_correct = Column(Integer, default=0, comment="是否答对 0/1")
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="error_records")
    word = relationship("Word")

    __table_args__ = (
        Index("idx_user_error", "user_id", "created_at"),
    )


# ==================== 生词收藏表 ====================
class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_id = Column(BigInteger, ForeignKey("words.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="favorites")
    word = relationship("Word")

    __table_args__ = (
        UniqueConstraint("user_id", "word_id", name="uq_user_favorite"),
    )


# ==================== 每日计划表 ====================
class DailyPlan(Base):
    __tablename__ = "daily_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_date = Column(Date, nullable=False, comment="计划日期")
    planned_count = Column(Integer, default=0, comment="计划背诵数")
    completed_new = Column(Integer, default=0, comment="完成新词数")
    completed_review = Column(Integer, default=0, comment="完成复习数")
    study_seconds = Column(Integer, default=0, comment="今日累计学习时长（秒）")
    is_checked_in = Column(Integer, default=0, comment="是否打卡 0/1")
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="daily_plans")

    __table_args__ = (
        UniqueConstraint("user_id", "plan_date", name="uq_user_date"),
    )


# ==================== 对话上下文表 ====================
class ConversationContext(Base):
    """持久化存储压缩后的关键上下文，跨会话恢复"""
    __tablename__ = "conversation_contexts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    current_word_ids = Column(Text, comment="当前背诵中的单词ID列表（JSON）")
    last_error_ids = Column(Text, comment="最近错题ID列表（JSON）")
    progress_summary = Column(Text, comment="学习进度摘要")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ==================== 数据库初始化 ====================
from backend.config import (
    DATABASE_URL,
    DATABASE_URL_SYNC,
    SQLITE_DATABASE_URL,
    SQLITE_DATABASE_URL_SYNC,
    USE_SQLITE,
)

# 异步引擎
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession as _AsyncSession
from sqlalchemy.orm import sessionmaker

engine_sync = None
async_engine = None
_async_session_factory = None
_current_db = "sqlite" if USE_SQLITE else "mysql"


def _create_engines(use_sqlite: bool = False):
    global engine_sync, async_engine, _async_session_factory, _current_db
    if use_sqlite:
        sync_url = SQLITE_DATABASE_URL_SYNC
        async_url = SQLITE_DATABASE_URL
        _current_db = "sqlite"
        # SQLite 不支持连接池参数
        engine_sync = create_engine(sync_url, echo=False)
        async_engine = create_async_engine(async_url, echo=False)
    else:
        sync_url = DATABASE_URL_SYNC
        async_url = DATABASE_URL
        _current_db = "mysql"
        engine_sync = create_engine(sync_url, echo=False, pool_pre_ping=True)
        async_engine = create_async_engine(async_url, echo=False, pool_size=10, max_overflow=20)

    _async_session_factory = sessionmaker(async_engine, class_=_AsyncSession, expire_on_commit=False)
    return engine_sync, async_engine


try:
    _create_engines(use_sqlite=USE_SQLITE)
except ModuleNotFoundError as e:
    if "aiosqlite" in str(e):
        raise RuntimeError(
            "❌ SQLite 异步驱动未安装！\n"
            "请运行: pip install aiosqlite>=0.20.0\n"
            "或安装完整依赖: pip install -r backend/requirements.txt\n"
            "或配置 MySQL 数据库后将 .env 中 USE_SQLITE 改为 false"
        ) from e
    raise
except Exception:
    if not USE_SQLITE:
        _create_engines(use_sqlite=True)
    else:
        raise


def init_db():
    """初始化数据库——建表 + 自动迁移"""
    global _current_db
    try:
        Base.metadata.create_all(engine_sync)
        # 自动为旧数据库添加缺失的列
        _migrate_existing_tables()
        print(f"[数据库] 已使用 {_current_db} 创建表结构")
    except ModuleNotFoundError as e:
        if "aiosqlite" in str(e):
            raise RuntimeError(
                "❌ SQLite 异步驱动未安装！请运行: pip install aiosqlite>=0.20.0"
            ) from e
        raise
    except Exception:
        if _current_db != "sqlite":
            try:
                _create_engines(use_sqlite=True)
                Base.metadata.create_all(engine_sync)
                print("[数据库] 已自动回退到 SQLite")
            except Exception as fallback_err:
                raise RuntimeError(
                    f"❌ 数据库初始化完全失败。MySQL 不可用，SQLite 回退也失败: {fallback_err}"
                ) from fallback_err
        else:
            raise


def is_using_sqlite() -> bool:
    return _current_db == "sqlite"


def _migrate_existing_tables():
    """自动迁移：为已存在的表添加缺失列"""
    try:
        from sqlalchemy import inspect as sa_inspect, text
        insp = sa_inspect(engine_sync)
        table_names = insp.get_table_names()

        # daily_plans: 添加 study_seconds (2026-06-19)
        if "daily_plans" in table_names:
            cols = {c["name"] for c in insp.get_columns("daily_plans")}
            if "study_seconds" not in cols:
                with engine_sync.connect() as conn:
                    conn.execute(text("ALTER TABLE daily_plans ADD COLUMN study_seconds INTEGER DEFAULT 0"))
                    conn.commit()
    except Exception:
        pass  # 迁移失败不阻塞启动


def create_async_session() -> _AsyncSession:
    """创建异步数据库会话"""
    return _async_session_factory()


async def close_db():
    """关闭数据库连接"""
    await async_engine.dispose()
