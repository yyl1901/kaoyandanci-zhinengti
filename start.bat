@echo off
chcp 65001 >nul
echo ============================================
echo    📚 单词备考智能体 —— 启动脚本
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 安装后端依赖
echo [1/5] 安装后端依赖...
cd /d "%~dp0"
pip install -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️ 清华源安装失败，尝试使用默认源...
    pip install -r backend\requirements.txt
)

:: 检查 USE_SQLITE 环境
echo.
echo [2/5] 检查数据库配置...
findstr /C:"USE_SQLITE=true" .env >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   ✅ 使用 SQLite 本地模式（无需 MySQL）
) else (
    echo   ℹ️ 使用 MySQL 模式，请确保 MySQL 已启动
)

:: 初始化词库数据
echo.
echo [3/5] 初始化词库数据...
python scripts/init_data.py
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️ 词库初始化失败，将跳过此步骤
    echo   💡 如果有自己的词库文件，请运行: python scripts/import_user_wordlist.py
)

:: 安装前端依赖
echo.
echo [4/5] 安装前端依赖...
cd frontend
call npm install 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️ npm install 失败，请确保已安装 Node.js
    echo 前端可稍后手动启动：cd frontend ^&^& npm run dev
)
cd ..

:: 启动服务
echo.
echo [5/5] 启动服务...
echo.
echo ============================================
echo   🚀 服务启动中...
echo   后端API: http://localhost:8000
echo   API文档: http://localhost:8000/docs
echo   健康检查: http://localhost:8000/health
echo   前端页面: http://localhost:3000
echo ============================================
echo   📌 首次使用请确认:
echo   1. 安装 Python 依赖: pip install -r backend/requirements.txt
echo   2. 初始化数据: python scripts/init_data.py
echo   3. 导入词库: python scripts/import_user_wordlist.py
echo   4. 安装前端: cd frontend ^&^& npm install
echo ============================================
echo.

:: 同时启动后端和前端
start "单词备考智能体-后端" cmd /c "cd /d %~dp0 && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
start "单词备考智能体-前端" cmd /c "cd /d %~dp0\frontend && npm run dev"

echo ✅ 服务已启动！按任意键关闭此窗口（不会停止服务）。
pause >nul
