class ColdRoomThermal:
    """冷库简化热力学模型"""
    def __init__(self, room_id: int, initial_temp: float, t_min: float, t_max: float,
                 heat_capacity: float = 20000.0, ambient_gain: float = 5.0):
        self.id = room_id
        self.temp = initial_temp
        self.t_min = t_min
        self.t_max = t_max
        self.C = heat_capacity           # kJ/°C
        self.ambient_gain = ambient_gain # 环境得热 (kW)

    def update(self, cooling_kw: float, disturbance_kw: float, dt_hours: float):
        net_power = self.ambient_gain + disturbance_kw - cooling_kw
        delta_T = (net_power * dt_hours * 3600) / self.C
        self.temp += delta_T
        return self.temp