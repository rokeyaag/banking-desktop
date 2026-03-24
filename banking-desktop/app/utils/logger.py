import logging
import os
from logging.handlers import RotatingFileHandler

_loggers: dict = {}

def get_logger(name: str) -> logging.Logger:
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(console)

    try:
        os.makedirs("./logs", exist_ok=True)
        fh = RotatingFileHandler("./logs/nexabank.log", maxBytes=5*1024*1024, backupCount=3)
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(fh)
    except Exception:
        pass

    _loggers[name] = logger
    return logger
