from agents.base_agent import BaseToolCallingAgent
from tools import read_room_sensor, predict_disturbance_load, calculate_cooling_demand, submit_cooling_demand

CSA_ROLE = "你是冷库{room_id}的智能管家。你需要：1.读取温度；2.预测扰动；3.计算冷量；4.提交需求标书。**优先级必须是0到1之间的小数**，根据温度与上限的接近程度设定：例如温度-16℃接近上限-15℃，优先级约为0.7；温度-18℃接近下限，优先级约为0.2。"

class ColdStorageAgent(BaseToolCallingAgent):
    def __init__(self, room_id: int):
        role_desc = CSA_ROLE.format(room_id=room_id)
        super().__init__(
            name=f"CSA-{room_id}",
            role=role_desc,
            tools=[read_room_sensor, predict_disturbance_load,
                   calculate_cooling_demand, submit_cooling_demand]
        )
        self.room_id = room_id