# backend/main.py
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging

# Импортируем модели, чтобы Base.metadata знал о них при создании таблиц
from backend.models.user_model import User  # noqa: F401
from backend.models.graph_model import Graph, Node, Edge  # noqa: F401

from backend.db.session import engine, Base
from backend.api.v1 import users, graphs, nodes, edges, comments # Убедитесь, что все импортированы

# Настройка логирования для отладки
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Lifespan для создания таблиц при старте ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Приложение запускается, создаем таблицы в БД...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Таблицы успешно созданы или уже существуют.")
    yield
    logger.info("Приложение останавливается.")

app = FastAPI(lifespan=lifespan, title="Taideteos API")

# --- Настройка CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Подключение роутеров API ---
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(graphs.router, prefix="/api/v1/graphs", tags=["graphs"])
app.include_router(nodes.router, prefix="/api/v1/nodes", tags=["nodes"]) 
app.include_router(edges.router, prefix="/api/v1/edges", tags=["edges"]) 
app.include_router(comments.router, prefix="/api/v1", tags=["comments"])

# --- Настройка для обслуживания одностраничного приложения (SPA) ---
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_FILES_DIR = BASE_DIR / "frontend"

app.mount("/assets", StaticFiles(directory=STATIC_FILES_DIR / "assets"), name="assets")
app.mount("/js", StaticFiles(directory=STATIC_FILES_DIR / "js"), name="js")
app.mount("/pages", StaticFiles(directory=STATIC_FILES_DIR / "pages"), name="pages")
app.mount("/assets", StaticFiles(directory=STATIC_FILES_DIR / "assets"), name="assets")

# --- Catch-all маршрут для SPA ---
@app.get("/{full_path:path}", response_class=FileResponse, include_in_schema=False)
async def serve_spa(request: Request, full_path: str):
    """
    Отдает index.html на любой путь, который не был обработан API или StaticFiles.
    """
    logger.info(f"Catch-all route: Запрос на путь '{full_path}', отдаем index.html")
    return FileResponse(STATIC_FILES_DIR / "index.html")