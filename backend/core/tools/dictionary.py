"""
CLI词典工具 —— 本地词库脚本查词
"""
import json
import subprocess
from pathlib import Path
from typing import Any


class DictionaryTool:
    """
    本地词典工具，从词库数据中查询单词信息。
    支持 CLI 脚本调用和直接数据文件读取两种模式。
    """

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self._word_cache: dict[str, dict] = {}
        self._loaded = False

    def _load_word_data(self) -> None:
        """加载所有词库数据到内存缓存"""
        if self._loaded:
            return
        for json_file in self.data_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    words = json.load(f)
                if isinstance(words, list):
                    for w in words:
                        key = w.get("word", "").lower().strip()
                        if key:
                            w["_source"] = json_file.stem
                            self._word_cache[key] = w
                elif isinstance(words, dict):
                    for key, w in words.items():
                        w["_source"] = json_file.stem
                        self._word_cache[key.lower().strip()] = w
            except (json.JSONDecodeError, OSError):
                continue
        self._loaded = True

    def lookup(self, word: str) -> dict[str, Any] | None:
        """
        查询单词
        :param word: 待查单词
        :return: 单词信息字典，未找到返回 None
        """
        self._load_word_data()
        key = word.lower().strip()
        result = self._word_cache.get(key)
        if result:
            return dict(result)
        return None

    def lookup_batch(self, words: list[str]) -> dict[str, dict | None]:
        """批量查询单词"""
        self._load_word_data()
        return {w: self.lookup(w) for w in words}

    def search_by_prefix(self, prefix: str, limit: int = 20) -> list[dict]:
        """按前缀搜索单词"""
        self._load_word_data()
        prefix = prefix.lower().strip()
        results = []
        for key, val in self._word_cache.items():
            if key.startswith(prefix):
                results.append(dict(val))
                if len(results) >= limit:
                    break
        return results

    @staticmethod
    def cli_lookup(word: str, data_dir: str | None = None) -> dict | None:
        """
        CLI 方式查词（可通过 subprocess 调用外部脚本）
        作为 MCP CLI 工具的备选方案
        """
        script_path = Path(data_dir or ".") / "scripts" / "lookup.py"
        if script_path.exists():
            result = subprocess.run(
                ["python", str(script_path), word],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return None
        return None

    def get_stats(self) -> dict:
        """获取词库统计信息"""
        self._load_word_data()
        sources = {}
        for w in self._word_cache.values():
            src = w.get("_source", "unknown")
            sources[src] = sources.get(src, 0) + 1
        return {
            "total_words": len(self._word_cache),
            "by_source": sources,
        }
