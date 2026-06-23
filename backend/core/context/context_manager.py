"""
上下文管理模块 —— 会话上下文保存 + 超长自动压缩
"""
import json
from datetime import datetime
from typing import Any
from backend.config import CONTEXT_CONFIG

try:
    import tiktoken
    _HAS_TIKTOKEN = True
except ImportError:
    _HAS_TIKTOKEN = False


class ContextManager:
    """
    管理单次对话上下文，在上下文超长时自动压缩，
    剔除无效历史内容，仅保留关键信息。
    """

    def __init__(self, user_id: int, max_tokens: int | None = None):
        self.user_id = user_id
        self.max_tokens = max_tokens or CONTEXT_CONFIG["max_tokens"]
        self.compress_threshold = CONTEXT_CONFIG["compress_threshold"]
        self.reserved_tokens = CONTEXT_CONFIG["reserved_tokens"]

        # 上下文存储
        self._history: list[dict] = []
        self._key_context: dict[str, Any] = {
            "current_word_ids": [],      # 当前背诵单词ID列表
            "error_contents": [],         # 最近错题内容
            "progress": {                 # 用户背诵进度
                "today_new": 0,
                "today_review": 0,
                "total_learned": 0,
                "streak_days": 0,
            },
            "last_quiz_result": None,     # 最近一次测试结果摘要
        }

        if _HAS_TIKTOKEN:
            try:
                self._tokenizer = tiktoken.encoding_for_model("gpt-4")
            except Exception:
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
        else:
            self._tokenizer = None

    def _count_tokens(self, text: str) -> int:
        """估算文本 token 数"""
        try:
            return len(self._tokenizer.encode(text))
        except Exception:
            return len(text) // 2  # 粗略估算

    def _total_tokens(self) -> int:
        """计算当前上下文总 token 数"""
        total = 0
        for msg in self._history:
            total += self._count_tokens(msg.get("content", ""))
        total += self._count_tokens(json.dumps(self._key_context, ensure_ascii=False))
        return total

    def add_message(self, role: str, content: str) -> None:
        """添加一条消息到上下文"""
        self._history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self._maybe_compress()

    def update_key_context(self, **kwargs) -> None:
        """更新关键上下文（单词ID、错题、进度等）"""
        for key in self._key_context:
            if key in kwargs:
                self._key_context[key] = kwargs[key]
        self._maybe_compress()

    def add_current_word(self, word_id: int) -> None:
        """记录当前背诵的单词ID"""
        ids = self._key_context["current_word_ids"]
        if word_id not in ids:
            ids.append(word_id)
            if len(ids) > 100:
                ids[:] = ids[-80:]  # 保留最近80个

    def add_error(self, error_content: dict) -> None:
        """记录错题"""
        errors = self._key_context["error_contents"]
        errors.append(error_content)
        if len(errors) > 50:
            errors[:] = errors[-30:]

    def _maybe_compress(self) -> None:
        """如果上下文超长，自动压缩"""
        if self._total_tokens() > self.compress_threshold:
            self._compress()

    def _compress(self) -> None:
        """
        压缩策略：
        1. 保留最近3轮对话
        2. 合并旧消息为摘要
        3. 剔除无效请求/响应
        """
        if len(self._history) <= 6:
            return

        # 保留最近6条（3轮对话）
        recent = self._history[-6:]
        old = self._history[:-6]

        # 从旧消息中提取关键信息
        key_snippets = []
        for msg in old:
            content = msg.get("content", "")
            # 只保留有实质内容的片段
            if len(content) > 20 and len(content) < 200:
                key_snippets.append(content[:100])

        # 构建压缩后的上下文
        compressed = {
            "role": "system",
            "content": f"[历史摘要] 之前讨论涉及以下关键内容: {'; '.join(key_snippets[-5:])}",
            "compressed": True,
        }

        self._history = [compressed] + recent

    def get_messages(self) -> list[dict]:
        """获取当前可用上下文消息列表"""
        key_context_str = json.dumps(self._key_context, ensure_ascii=False)
        system_msg = {
            "role": "system",
            "content": (
                f"当前会话关键上下文（优先参考）:\n{key_context_str}\n"
                f"注意：以上信息来自数据库和用户当前进度，请据此提供个性化服务。"
            ),
        }
        return [system_msg] + self._history

    def get_key_context(self) -> dict:
        """获取关键上下文快照"""
        return dict(self._key_context)

    def clear_history(self, keep_key_context: bool = True) -> None:
        """清空对话历史，可选保留关键上下文"""
        self._history = []
        if not keep_key_context:
            self._key_context = {k: [] if isinstance(v, list) else v for k, v in self._key_context.items()}

    def to_persist(self) -> dict:
        """转为可持久化的格式"""
        return {
            "current_word_ids": json.dumps(self._key_context["current_word_ids"]),
            "last_error_ids": json.dumps([
                e.get("word_id") for e in self._key_context["error_contents"][-20:]
            ]),
            "progress_summary": json.dumps(self._key_context["progress"], ensure_ascii=False),
        }

    def restore_from_persist(self, data: dict) -> None:
        """从持久化数据恢复上下文"""
        if data.get("current_word_ids"):
            try:
                self._key_context["current_word_ids"] = json.loads(data["current_word_ids"])
            except json.JSONDecodeError:
                pass
        if data.get("progress_summary"):
            try:
                self._key_context["progress"] = json.loads(data["progress_summary"])
            except json.JSONDecodeError:
                pass


# 全局上下文管理器缓存（短期记忆的一部分）
_context_cache: dict[int, ContextManager] = {}


def get_context_manager(user_id: int) -> ContextManager:
    """获取或创建用户的上下文管理器"""
    if user_id not in _context_cache:
        _context_cache[user_id] = ContextManager(user_id)
    return _context_cache[user_id]


def clear_context(user_id: int) -> None:
    """清除用户上下文缓存"""
    if user_id in _context_cache:
        del _context_cache[user_id]
