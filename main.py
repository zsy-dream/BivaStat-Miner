import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from core.config import settings
from core.logging import logger
from api.data_router import router as data_router
from api.algorithm_router import router as algorithm_router

def create_app() -> FastAPI:
    app = FastAPI(
        title="双变量关联挖掘与非参数统计分析平台",
        description="基于启发式算法的企业级智能数据分析平台",
        version="1.0.0"
    )

    # 跨域配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(data_router, prefix="/api/data", tags=["数据管理"])
    app.include_router(algorithm_router, prefix="/api/algorithm", tags=["算法逻辑"])

    # 静态资源处理
    os.makedirs("static", exist_ok=True)
    os.makedirs("uploads", exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # 全局错误处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global Error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(exc), "message": "系统内部错误"}
        )

    @app.get("/")
    async def index():
        # 如果有前端 build 好的 index.html，优先返回
        index_path = os.path.join("static", "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"status": "ok", "message": "API Server is running. Please explore via /docs"}

    return app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.system.host,
        port=settings.system.port,
        reload=settings.system.enable_debug
    )
