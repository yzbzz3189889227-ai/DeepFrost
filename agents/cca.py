from agents.base_agent import BaseToolCallingAgent
from tools import read_compressor_status, set_compressor_schedule, solve_optimal_schedule

CCA_ROLE = """你是压缩机集群的调度指挥官。你的任务是：
0. 首先确认已有冷库提交了需求（若无需求则终止并报错）。
1. 查询所有压缩机的当前状态。
2. 根据冷库需求和压缩机状态，求解最优调度方案。
3. 下发调度指令。
你需要同时优化总能耗和运行时长均衡，优先保证冷库温度达标。
"""

class CompressorClusterAgent(BaseToolCallingAgent):
    def __init__(self):
        super().__init__(
            name="CCA",
            role=CCA_ROLE,
            tools=[read_compressor_status, set_compressor_schedule, solve_optimal_schedule]
        )