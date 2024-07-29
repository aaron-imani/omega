import logging
import os

import colorlog

log_level = os.getenv("LOG_LEVEL", "WARNING").upper()


def get_logger(name):
    logger = colorlog.getLogger(name)
    ch = colorlog.StreamHandler()
    ch.setLevel(log_level)
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(name)s: %(reset)s%(message)s",
        log_colors={
            "DEBUG": "green",
            "INFO": "cyan",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    ch.setFormatter(formatter)
    ch.setLevel(log_level)
    logger.setLevel(log_level)

    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(ch)

    return logger


colorlog.getLogger().setLevel(logging.ERROR)
