import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config.config import settings
from src.core.exceptions.exception_handlers import register_exception_handlers
from src.core.middlewares.middlewares import global_error_handler
from src.routers.account import router as accounts_router
from src.routers.healthcheck import router as healthcheck_router
from src.utils.logger.setup_logger import setup_logger

setup_logger()

APP_VERSION = "0.1.0"
app = FastAPI(
    title="my_money-API",
    version=APP_VERSION,
)
app.state.app_version = APP_VERSION  # noqa

register_exception_handlers(app)

app.middleware("http")(global_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(healthcheck_router)
app.include_router(accounts_router)


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_config=None,
    )

# command to start fastapi app with uvicorn server -> uvicorn src.main:app --port 8000 --reload
