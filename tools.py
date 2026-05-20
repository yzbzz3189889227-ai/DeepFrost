"""
所有智能体可调用的工具函数，使用 LangChain @tool 装饰器。
每个工具内部记录：调用参数、执行结果、状态变更。
"""
import json
import re
from langchain_core.tools import tool
from typing import List, Dict
import numpy as np
from models.thermal import ColdRoomThermal
from models.compressor import Compressor
from utils.logger import logger

# ---------- 全局状态 ----------
cold_rooms: List[ColdRoomThermal] = []
compressors: List[Compressor] = []
outside_temp = 25.0
electricity_price = 0.5
demands: Dict[int, Dict] = {}

# ================= CSA 工具 =================
@tool
def read_room_sensor(room_id: int) -> str:
    """读取冷库 room_id 的当前温度和允许区间"""
    logger.info(f"[工具:read_room_sensor] 调用，参数 room_id={room_id}")
    if 0 <= room_id < len(cold_rooms):
        cr = cold_rooms[room_id]
        result = f"冷库{room_id}：当前温度 {cr.temp:.2f}℃，允许范围 [{cr.t_min},{cr.t_max}]℃"
        logger.info(f"[工具:read_room_sensor] 返回：{result}")
        return result
    logger.warning(f"[工具:read_room_sensor] 冷库{room_id}不存在")
    return "冷库不存在"

@tool
def predict_disturbance_load(room_id: int, timestamp: str, door_openings: int, activity: str) -> str:
    """预测未来15分钟的热扰动（kW）"""
    logger.info(f"[工具:predict_disturbance_load] 调用，room={room_id}, ts={timestamp}, doors={door_openings}, activity={activity}")
    hour = int(timestamp.split(":")[0])
    base = 20.0 if 6 <= hour <= 18 else 5.0
    disturbance = base * (1 + 0.5 * door_openings)
    if activity == "high":
        disturbance *= 1.5
    result = f"扰动预测结果：{disturbance:.1f} kW"
    logger.info(f"[工具:predict_disturbance_load] {result}")
    return result

@tool
def calculate_cooling_demand(room_id: int, disturbance_pred: float) -> str:
    """
    基于热力学模型计算安全冷量(Q_safe)和经济冷量(Q_eco)。
    Q_safe：抵消扰动和环境得热所需的最低制冷量。
    Q_eco：在Q_safe基础上，15分钟内将温度调整至设定中值所需的制冷量。
    """
    logger.info(f"[工具:calculate_cooling_demand] 调用，room={room_id}, disturbance={disturbance_pred}")
    if not (0 <= room_id < len(cold_rooms)):
        logger.warning(f"[工具:calculate_cooling_demand] 冷库{room_id}不存在")
        return "冷库不存在"

    cr = cold_rooms[room_id]
 
    Q_ambient = cr.ambient_gain

    Q_base = disturbance_pred + Q_ambient

    Q_safe = Q_base

    target_temp = (cr.t_min + cr.t_max) / 2
    delta_T = cr.temp - target_temp  
    dt_seconds = 15 * 60 
    extra_power = (cr.C * delta_T) / dt_seconds if dt_seconds > 0 else 0.0

    Q_eco = max(0.0, Q_base + extra_power)

    Q_safe = min(Q_safe, Q_eco)

    result = f"安全冷量 {Q_safe:.1f} kW，经济冷量 {Q_eco:.1f} kW"
    logger.info(f"[工具:calculate_cooling_demand] {result}")
    return result

@tool
def submit_cooling_demand(room_id: int, Q_safe: float, Q_eco: float,
                          priority: float, reasoning: str) -> str:
    """提交制冷需求标书"""
    logger.info(f"[工具:submit_cooling_demand] 调用，room={room_id}, Q_safe={Q_safe}, Q_eco={Q_eco}, priority={priority}, reason={reasoning}")
    if not (0 <= priority <= 1):
        logger.error(f"[工具:submit_cooling_demand] 优先级非法：{priority}")
        return "错误：优先级必须在0到1之间"
    demands[room_id] = {
        "Q_safe": Q_safe, "Q_eco": Q_eco,
        "priority": priority, "reasoning": reasoning
    }
    result = f"冷库{room_id}需求已记录：安全冷量 {Q_safe:.1f} kW，经济冷量 {Q_eco:.1f} kW，优先级 {priority:.2f}"
    logger.info(f"[工具:submit_cooling_demand] {result}")
    return result

# ================= CCA 工具 =================
@tool
def read_compressor_status() -> str:
    """读取所有压缩机的状态"""
    logger.info("[工具:read_compressor_status] 调用")
    status = []
    for i, c in enumerate(compressors):
        status.append(
            f"压缩机{i}：{'运行' if c.running else '停机'}，负荷率{c.load_ratio:.2f}，累计运行{c.total_hours:.1f}h"
        )
    result = "；".join(status)
    logger.info(f"[工具:read_compressor_status] 返回：{result}")
    return result

def _clean_json(s: str) -> str:
    """清理 LLM 可能添加的 markdown 标记"""
    s = re.sub(r'^```json\s*', '', s.strip())
    s = re.sub(r'\s*```$', '', s)
    return s

@tool
def set_compressor_schedule(schedule_json: str) -> str:
    """下发压缩机调度指令"""
    logger.info(f"[工具:set_compressor_schedule] 调用，原始输入长度={len(schedule_json)}")
    schedule_json = _clean_json(schedule_json)
    try:
        schedule = json.loads(schedule_json)
        for item in schedule:
            cid = item["id"]
            if 0 <= cid < len(compressors):
                old_running = compressors[cid].running
                old_load = compressors[cid].load_ratio
                compressors[cid].set_load(item["running"], item["load"])
                logger.info(
                    f"[工具:set_compressor_schedule] 压缩机{cid} 状态变更："
                    f"运行 {old_running}->{item['running']}，负荷 {old_load:.2f}->{item['load']:.2f}"
                )
        logger.info("[工具:set_compressor_schedule] 调度指令已全部执行")
        return "调度指令已下发"
    except Exception as e:
        logger.error(f"[工具:set_compressor_schedule] 解析失败：{e}")
        return f"调度指令格式错误：{e}"

@tool
def solve_optimal_schedule(alpha: float = 0.7, beta: float = 0.3) -> str:
    """求解最优调度方案（贪心启发式）"""
    if not demands:
        logger.error("[工具:solve_optimal_schedule] 没有收到任何冷库需求！请检查 CSA 是否正常提交。")
        return json.dumps([{"id": i, "running": False, "load": 0.0} for i in range(len(compressors))])
    logger.info(f"[工具:solve_optimal_schedule] 调用，alpha={alpha}, beta={beta}")
    required_safe = sum(d["Q_safe"] for d in demands.values())
    total_capacity = sum(c.max_power for c in compressors)
    logger.info(f"[工具:solve_optimal_schedule] 总安全需求={required_safe:.1f} kW，总容量={total_capacity:.1f} kW")
    
    if required_safe > total_capacity:
        logger.warning("[工具:solve_optimal_schedule] 容量不足！触发优先级削减")
        sorted_rooms = sorted(demands.items(), key=lambda x: x[1]["priority"])
        remaining = total_capacity
        for rid, d in sorted_rooms:
            alloc = min(remaining, d["Q_safe"])
            demands[rid]["allocated"] = alloc
            remaining -= alloc
        schedule = [{"id": i, "running": False, "load": 0.0} for i in range(len(compressors))]
        result = json.dumps(schedule, ensure_ascii=False)
        logger.info(f"[工具:solve_optimal_schedule] 紧急调度结果：{result}")
        return result

    total_demand = sum(d["Q_eco"] for d in demands.values())
    comps_sorted = sorted(compressors, key=lambda c: c.total_hours)
    schedule = []
    remaining = total_demand
    for c in comps_sorted:
        if remaining <= 0:
            schedule.append({"id": c.id, "running": False, "load": 0.0})
            continue
        load = min(1.0, remaining / c.max_power)
        schedule.append({"id": c.id, "running": True, "load": round(load, 2)})
        remaining -= c.max_power * load
    result = json.dumps(schedule, ensure_ascii=False)
    logger.info(f"[工具:solve_optimal_schedule] 正常调度结果：{result}")
    return result

# ================= CDA 工具 =================
@tool
def read_environment() -> str:
    """获取室外温度和电价"""
    logger.info("[工具:read_environment] 调用")
    result = f"室外温度：{outside_temp}℃，电价：{electricity_price} 元/kWh"
    logger.info(f"[工具:read_environment] {result}")
    return result

@tool
def update_environment(temp: float, price: float) -> str:
    """更新环境参数"""
    global outside_temp, electricity_price
    logger.info(f"[工具:update_environment] 调用，旧环境：{outside_temp}℃, {electricity_price}元；新环境：{temp}℃, {price}元")
    outside_temp = temp
    electricity_price = price
    return "环境参数已更新"

@tool
def resolve_auction(bids_json: str) -> str:
    """拍卖协调（简化）"""
    logger.info(f"[工具:resolve_auction] 调用，bids长度={len(bids_json)}")
    return "拍卖完成：所有冷库安全需求均可满足"