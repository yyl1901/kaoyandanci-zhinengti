"""
全局配置模块
"""
import os
from pathlib import Path

# 加载 .env 文件（必须在读取环境变量之前）
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # python-dotenv 未安装时忽略

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# ============ 数据库配置 ============
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "123456"),
    "database": os.getenv("MYSQL_DB", "danci"),
}

SQLITE_DB_FILE = BASE_DIR / "data" / "danci.sqlite"
SQLITE_DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_DB_FILE}"
SQLITE_DATABASE_URL_SYNC = f"sqlite:///{SQLITE_DB_FILE}"

USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() in ("1", "true", "yes")

# SQLAlchemy 连接串
MYSQL_DATABASE_URL = (
    f"mysql+aiomysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
    f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
    "?charset=utf8mb4"
)

MYSQL_DATABASE_URL_SYNC = (
    f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
    f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}"
    "?charset=utf8mb4"
)

DATABASE_URL = os.getenv("DATABASE_URL") or (
    SQLITE_DATABASE_URL if USE_SQLITE else MYSQL_DATABASE_URL
)

# 同步连接串（初始化用）
DATABASE_URL_SYNC = os.getenv("DATABASE_URL_SYNC") or (
    SQLITE_DATABASE_URL_SYNC if USE_SQLITE else MYSQL_DATABASE_URL_SYNC
)

# ============ LLM 配置 ============
LLM_CONFIG = {
    "api_base": os.getenv("LLM_API_BASE", "https://api.openai.com/v1"),
    "api_key": os.getenv("LLM_API_KEY", ""),
    "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
    "temperature": 0.3,
    "max_tokens": 2048,
}

# ============ Chroma 向量库配置 ============
CHROMA_CONFIG = {
    "persist_directory": str(BASE_DIR / "data" / "chroma_db"),
    "collection_prefix": "word_kb",
}

# ============ 上下文管理配置 ============
CONTEXT_CONFIG = {
    "max_tokens": 6000,       # 最大上下文 token 数
    "compress_threshold": 4000,  # 超过此阈值触发压缩
    "reserved_tokens": 1500,     # 保留给系统提示词的 token 数
}

# ============ 记忆模块配置 ============
MEMORY_CONFIG = {
    "short_term_ttl": 86400,  # 短期记忆过期时间（24小时，单位秒）
    "max_cached_words": 200,   # 最大缓存单词数
}

# ============ 艾宾浩斯复习间隔（天） ============
EBBINGHAUS_INTERVALS = [0, 1, 2, 4, 7, 15, 30, 60, 120]

# ============ 考纲分类 ============
EXAM_TYPES = {
    "cet4": {"name": "四级", "word_count": 4500},
    "cet6": {"name": "六级", "word_count": 6000},
    "kaoyan": {"name": "考研英语", "word_count": 5500},
}

# ============ 服务端口 ============
SERVER_CONFIG = {
    "host": "0.0.0.0",
    "port": int(os.getenv("API_PORT", 8000)),
    "reload": os.getenv("DEBUG", "true").lower() == "true",
}

# ============ 数据文件路径 ============
DATA_DIR = BASE_DIR / "data"
CET4_WORDS_FILE = DATA_DIR / "cet4.json"
CET6_WORDS_FILE = DATA_DIR / "cet6.json"
KAOYAN_WORDS_FILE = DATA_DIR / "kaoyan.json"
