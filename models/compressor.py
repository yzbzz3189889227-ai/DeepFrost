class Compressor:
    """压缩机模型，包含能效曲线"""
    def __init__(self, comp_id: int, max_power: float = 100.0, cop_rated: float = 3.0):
        self.id = comp_id
        self.max_power = max_power
        self.cop_rated = cop_rated
        self.running = False
        self.load_ratio = 0.0          # 0~1
        self.total_hours = 0.0         # 累计运行小时

    def set_load(self, running: bool, load_ratio: float):
        self.running = running
        self.load_ratio = max(0.0, min(1.0, load_ratio)) if running else 0.0

    def power_consumption(self) -> float:
        """当前电功率 (kW)"""
        if not self.running:
            return 0.0
        cop = self.cop_rated * (0.8 + 0.4 * self.load_ratio - 0.4 * self.load_ratio ** 2)
        cooling_output = self.max_power * self.load_ratio
        return cooling_output / cop if cop > 0 else 0.0

    def cooling_output(self) -> float:
        """当前制冷输出 (kW)"""
        return self.max_power * self.load_ratio if self.running else 0.0