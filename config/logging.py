import logging
import sys

from loguru import logger


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_loguru():
    logger.configure(patcher=lambda record: record["extra"].setdefault("request_id", "N/A"))
    logger.remove()

    logger.add(sys.stderr, level="INFO")

    # Add file handler with rotation and retention
    logger.add(
        "app.log",
        rotation="500 MB",
        retention="10 days",
        level="INFO",
        compression="zip",
        enqueue=True,  # Thread-safe
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {extra[request_id]} | {name}:{function}:{line} - {message}",
    )
