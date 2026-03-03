import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from core.config import settings

def setup_logger(name: str = "analysis_platform") -> logging.Logger:
    """
    配置标准应用日志
    """
    logger = logging.getLogger(name)
    logger.setLevel(settings.system.log_level)
    
    # 防止多重 handler
    if logger.handlers:
        return logger
        
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s"
    )

    # 1. 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. 文件输出（按大小切割）
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10*1024*1024, # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()
