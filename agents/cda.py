from agents.base_agent import BaseToolCallingAgent
from tools import read_environment, update_environment, resolve_auction

CDA_ROLE = "你是系统的环境协调员。你的任务是：1.提供室外温度、电价；2.在供需紧张时主持拍卖；3.更新环境参数。"

class CoordinatorAgent(BaseToolCallingAgent):
    def __init__(self):
        super().__init__(
            name="CDA",
            role=CDA_ROLE,
            tools=[read_environment, update_environment, resolve_auction]
        )