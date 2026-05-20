import os

# DeepSeek V4 API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-api-key")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# 仿真参数
DECISION_INTERVAL_MIN = 15        # 决策间隔（分钟）
MAX_COMPRESSOR_POWER_KW = 100     # 单台压缩机最大功率 (kW)
COMPRESSOR_COUNT = 8              # 压缩机台数
COLD_ROOM_COUNT = 5               # 冷库数量