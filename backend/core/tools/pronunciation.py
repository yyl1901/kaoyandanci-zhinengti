"""
发音API工具 —— 获取单词英美发音音频
"""
import httpx
from typing import Literal


class PronunciationTool:
    """
    发音工具，支持多种免费发音API源：
    1. dictionaryapi.dev (免费，无需API Key)
    2. 备用：有道发音API
    """

    # 免费发音API基础URL
    DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

    # 有道的TTS接口（备用）
    YOUDAO_TTS_UK = "https://dict.youdao.com/dictvoice?type=1&audio={word}"
    YOUDAO_TTS_US = "https://dict.youdao.com/dictvoice?type=2&audio={word}"

    def __init__(self):
        self._cache: dict[str, dict] = {}

    async def get_pronunciation(self, word: str) -> dict:
        """
        获取单词发音信息
        :return: {uk_audio_url, us_audio_url, phonetic_uk, phonetic_us}
        """
        cache_key = word.lower().strip()
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = {
            "word": word,
            "uk_audio_url": None,
            "us_audio_url": None,
            "phonetic_uk": "",
            "phonetic_us": "",
        }

        # 优先使用 Dictionary API
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self.DICTIONARY_API.format(word=word))
                if resp.status_code == 200:
                    data = resp.json()
                    if data and isinstance(data, list):
                        for entry in data:
                            phonetics = entry.get("phonetics", [])
                            for p in phonetics:
                                audio_url = p.get("audio", "")
                                region = p.get("text", "")
                                if not audio_url:
                                    continue
                                # 区分英美音
                                if "uk" in audio_url or "UK" in str(p):
                                    result["uk_audio_url"] = audio_url
                                    result["phonetic_uk"] = region or result["phonetic_uk"]
                                elif "us" in audio_url or "US" in str(p):
                                    result["us_audio_url"] = audio_url
                                    result["phonetic_us"] = region or result["phonetic_us"]
                                else:
                                    if not result["uk_audio_url"]:
                                        result["uk_audio_url"] = audio_url
                                    elif not result["us_audio_url"]:
                                        result["us_audio_url"] = audio_url
        except Exception:
            pass

        # 有道TTS作为备用音频源
        if not result["uk_audio_url"]:
            result["uk_audio_url"] = self.YOUDAO_TTS_UK.format(word=word)
        if not result["us_audio_url"]:
            result["us_audio_url"] = self.YOUDAO_TTS_US.format(word=word)

        self._cache[cache_key] = result
        return result

    async def get_audio_stream(self, word: str, accent: Literal["uk", "us"] = "us") -> bytes | None:
        """直接获取音频数据流"""
        try:
            url = self.YOUDAO_TTS_UK if accent == "uk" else self.YOUDAO_TTS_US
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url.format(word=word))
                if resp.status_code == 200:
                    return resp.content
        except Exception:
            pass
        return None
