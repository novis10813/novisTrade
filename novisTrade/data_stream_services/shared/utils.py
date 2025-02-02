import logging


def map_logging_level(logging_level: str) -> int:
    """將 logging level 轉換成 logging 模組的數字"""
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    return levels.get(logging_level, logging.INFO)