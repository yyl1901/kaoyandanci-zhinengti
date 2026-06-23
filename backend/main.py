"""
FastAPI 主入口 —— 考研/四六级单词备考智能体
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.api.routes import router
from backend.config import SERVER_CONFIG
from backend.models.database import init_db, is_using_sqlite


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时：初始化数据库
    print("[启动] 正在初始化数据库...")
    try:
        init_db()
        if is_using_sqlite():
            print("[启动] 已启用 SQLite 备用数据库")
        else:
            print("[启动] 数据库初始化完成，已连接 MySQL")
    except Exception as e:
        print(f"[启动] 数据库初始化失败: {e}")
        print("[启动] 请检查 MySQL 配置或设置 USE_SQLITE=true 启用 SQLite 备用数据库")

    # 初始化向量存储
    print("[启动] 正在初始化向量知识库...")
    try:
        from backend.core.knowledge.vector_store import VectorStore
        vs = VectorStore()
        collections = vs.list_collections()
        print(f"[启动] 向量知识库初始化完成，已有集合: {collections}")
    except Exception as e:
        print(f"[启动] 向量知识库初始化失败: {e}")

    yield

    # 关闭时的清理工作
    print("[关闭] 服务正在关闭...")


app = FastAPI(
    title="单词备考智能体",
    description="基于分层架构的考研/四六级英语单词备考智能助手",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 中间件（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(router)

# 挂载前端静态文件（生产部署时使用）
try:
    app.mount("/app", StaticFiles(directory="../frontend/dist", html=True), name="frontend")
except Exception:
    pass  # 开发阶段前端可能未构建


@app.get("/")
async def root():
    """API根路径"""
    return {
        "name": "单词备考智能体 API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok"}


# ==================== 启动入口 ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=SERVER_CONFIG["host"],
        port=SERVER_CONFIG["port"],
        reload=SERVER_CONFIG["reload"],
    )
