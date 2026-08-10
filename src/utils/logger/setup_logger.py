import sys

from loguru import logger

from src.core.config.config import settings


LOG_LEVEL = "DEBUG" if settings.DEBUG else "INFO"

FORMAT_MESSAGE = (
    "<green>{time:HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<blue>{module}</blue>:<blue>{function}</blue>:<blue>{line}</blue> — "
    "<level>{message}</level>"
)


def setup_logger():
    logger.remove()
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format=FORMAT_MESSAGE,
        enqueue=True,
        colorize=True,
        backtrace=True,
        diagnose=settings.DEBUG,
    )
