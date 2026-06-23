"""
短期记忆模块 —— 内存缓存当日背诵单词、临时错题
会话结束短期缓存失效
"""
import time
import threading
from typing import Any
from backend.config import MEMORY_CONFIG


class ShortTermMemory:
    """
    短期记忆缓存

    特点：
    - 会话级别：进程重启 / 会话结束即失效
    - TTL过期：单词缓存24小时后自动清理
    - 适用场景：单次会话中的临时数据暂存
    """

    def __init__(self, ttl: int | None = None, max_words: int | None = None):
        self.ttl = ttl or MEMORY_CONFIG["short_term_ttl"]
        self.max_words = max_words or MEMORY_CONFIG["max_cached_words"]

        # 存储结构
        self._word_cache: dict[int, dict[str, Any]] = {}        # word_id → 单词详细数据
        self._daily_words: dict[int, list[int]] = {}             # user_id → 今日单词ID列表
        self._error_cache: dict[int, list[dict]] = {}            # user_id → 临时错题列表
        self._quiz_sessions: dict[int, dict] = {}                # quiz_id → 测验会话数据
        self._user_settings: dict[int, dict] = {}                # user_id → 用户设置缓存

        # TTL 记录
        self._timestamps: dict[str, float] = {}

        # 定期清理后台线程
        self._lock = threading.Lock()
        self._start_cleaner()

    def _start_cleaner(self):
        """启动定期清理线程（每小时清理一次过期数据）"""
        def _clean():
            while True:
                time.sleep(3600)
                self._clean_expired()
        t = threading.Thread(target=_clean, daemon=True)
        t.start()

    def _clean_expired(self):
        """清理过期的缓存数据"""
        now = time.time()
        with self._lock:
            expired_keys = [
                k for k, ts in self._timestamps.items()
                if now - ts > self.ttl
            ]
            for k in expired_keys:
                # 清理各类缓存中的过期条目
                parts = k.split(":")
                if len(parts) >= 2:
                    cache_type, key = parts[0], ":".join(parts[1:])
                    if cache_type == "word" and int(key) in self._word_cache:
                        del self._word_cache[int(key)]
                    elif cache_type == "user_daily" and int(key) in self._daily_words:
                        del self._daily_words[int(key)]
                    elif cache_type == "user_errors" and int(key) in self._error_cache:
                        del self._error_cache[int(key)]
                del self._timestamps[k]

    def _touch(self, key: str) -> None:
        """更新时间戳"""
        self._timestamps[key] = time.time()

    # ---- 单词缓存 ----
    def cache_word(self, word_id: int, data: dict) -> None:
        with self._lock:
            if len(self._word_cache) >= self.max_words:
                # 按时间戳淘汰最早的
                oldest = min(
                    self._word_cache.keys(),
                    key=lambda w: self._timestamps.get(f"word:{w}", 0),
                    default=next(iter(self._word_cache.keys())) if self._word_cache else None,
                )
                if oldest:
                    del self._word_cache[oldest]
            self._word_cache[word_id] = data
            self._touch(f"word:{word_id}")

    def get_cached_word(self, word_id: int) -> dict | None:
        return self._word_cache.get(word_id)

    # ---- 每日单词列表 ----
    def set_daily_words(self, user_id: int, word_ids: list[int]) -> None:
        with self._lock:
            self._daily_words[user_id] = word_ids
            self._touch(f"user_daily:{user_id}")

    def get_daily_words(self, user_id: int) -> list[int]:
        return self._daily_words.get(user_id, [])

    # ---- 临时错题 ----
    def add_error(self, user_id: int, error: dict) -> None:
        with self._lock:
            if user_id not in self._error_cache:
                self._error_cache[user_id] = []
            self._error_cache[user_id].append(error)
            if len(self._error_cache[user_id]) > 100:
                self._error_cache[user_id] = self._error_cache[user_id][-50:]
            self._touch(f"user_errors:{user_id}")

    def get_temp_errors(self, user_id: int) -> list[dict]:
        return self._error_cache.get(user_id, [])

    def clear_temp_errors(self, user_id: int) -> None:
        self._error_cache.pop(user_id, None)

    # ---- 测验会话 ----
    def start_quiz(self, quiz_id: str, session_data: dict) -> None:
        self._quiz_sessions[quiz_id] = session_data

    def get_quiz(self, quiz_id: str) -> dict | None:
        return self._quiz_sessions.get(quiz_id)

    def end_quiz(self, quiz_id: str) -> dict | None:
        return self._quiz_sessions.pop(quiz_id, None)

    # ---- 用户设置缓存 ----
    def cache_user_settings(self, user_id: int, settings: dict) -> None:
        self._user_settings[user_id] = settings

    def get_user_settings(self, user_id: int) -> dict | None:
        return self._user_settings.get(user_id)

    def clear_user_cache(self, user_id: int) -> None:
        """清除某个用户的所有短期缓存"""
        self._daily_words.pop(user_id, None)
        self._error_cache.pop(user_id, None)
        self._user_settings.pop(user_id, None)


# 全局短期记忆实例
_global_stm: ShortTermMemory | None = None


def get_short_term_memory() -> ShortTermMemory:
    global _global_stm
    if _global_stm is None:
        _global_stm = ShortTermMemory()
    return _global_stm
