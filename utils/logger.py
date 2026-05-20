import logging
import sys

def setup_logger(name: str, level=logging.INFO, log_file: str = "deepfrost.log") -> logging.Logger:
    """
    创建日志记录器，同时输出到：
    1. 控制台（实时查看）
    2. 文件（持久保存，默认 deepfrost.log）
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 避免重复添加 handler
    if logger.handlers:
        logger.handlers.clear()

    # 格式：时间 + 级别 + 消息
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )

    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件 handler（编码 utf-8，避免中文乱码）
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

# 全局日志对象
logger = setup_logger("coldstorage")