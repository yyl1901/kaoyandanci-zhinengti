"""
API 响应模型定义
"""
from pydantic import BaseModel, Field
from typing import Any


class APIResponse(BaseModel):
    """统一API响应格式"""
    code: int = 200
    message: str = "success"
    data: Any = None

    @classmethod
    def ok(cls, data: Any = None, message: str = "success") -> dict:
        return {"code": 200, "message": message, "data": data}

    @classmethod
    def error(cls, message: str = "error", code: int = 400, data: Any = None) -> dict:
        return {"code": code, "message": message, "data": data}


class UserSettingsRequest(BaseModel):
    """用户设置请求"""
    username: str = Field(..., description="用户名", min_length=1, max_length=64)
    exam_type: str = Field(default="kaoyan", description="考纲类型: cet4/cet6/kaoyan")
    daily_count: int = Field(default=30, description="每日背诵量", ge=5, le=200)


class WordQueryRequest(BaseModel):
    """单词查询请求"""
    word: str = Field(..., description="单词", min_length=1)
    exam_type: str = Field(default="kaoyan", description="限定考纲")


class QuizSubmitRequest(BaseModel):
    """答题提交请求"""
    quiz_id: str = Field(..., description="测验会话ID")
    question_index: int = Field(..., description="题目索引", ge=0)
    user_answer: str = Field(..., description="用户答案")


class ReviewMarkRequest(BaseModel):
    """复习标记请求"""
    word_id: int = Field(..., description="单词ID")
    remembered: bool = Field(..., description="是否记住")


class FavoriteRequest(BaseModel):
    """收藏请求"""
    word_id: int = Field(..., description="单词ID")
