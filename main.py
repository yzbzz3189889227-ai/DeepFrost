# main.py
import argparse
import json
import os
from config import *
from models.thermal import ColdRoomThermal
from models.compressor import Compressor
from agents.csa import ColdStorageAgent
from agents.cca import CompressorClusterAgent
from agents.cda import CoordinatorAgent
from tools import cold_rooms, compressors, demands, update_environment
from evaluation import evaluate_cycle, format_eval_feedback
from utils.logger import logger


def load_scenario(scenario: str):
    """从 tests/test_{scenario}.json 加载场景数据，初始化物理模型"""
    logger.info("========== 场景加载 ==========")
    filepath = os.path.join("tests", f"test_{scenario}.json")
    logger.info(f"从文件加载场景：{filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    outside_temp = config_data.get("outside_temp", 25.0)
    electricity_price = config_data.get("electricity_price", 0.5)

    cold_rooms.clear()
    rooms_data = config_data.get("cold_rooms", [])
    activity = []
    for room in rooms_data:
        rid = room.get("id", len(cold_rooms))
        temp = room.get("initial_temp", -18.0)
        t_min = room.get("t_min", -20)
        t_max = room.get("t_max", -15)
        act = room.get("activity", "low")
        cr = ColdRoomThermal(rid, temp, t_min, t_max)
        cold_rooms.append(cr)
        activity.append(act)
        logger.info(f"创建冷库{rid}：初始温度 {temp}℃，范围 [{t_min},{t_max}]，活动：{act}")

    compressors.clear()
    comps_data = config_data.get("compressors", [])
    for comp in comps_data:
        cid = comp.get("id", len(compressors))
        hours = comp.get("total_hours", 0)
        cmpr = Compressor(cid, max_power=MAX_COMPRESSOR_POWER_KW)
        cmpr.total_hours = hours
        compressors.append(cmpr)
        logger.info(f"创建压缩机{cid}：累计运行 {hours}h")

    update_environment.invoke({"temp": outside_temp, "price": electricity_price})
    logger.info(f"环境设置：室外{outside_temp}℃，电价{electricity_price}元")
    logger.info("========== 场景加载完成 ==========")
    return activity


def run_cycle(csa_agents, cca, cda, activity, cycle_idx, start_hour):
    """执行一个 15 分钟的决策周期"""
    logger.info(f"\n{'#'*10} 周期 {cycle_idx} 开始 {'#'*10}")

    # 1. 环境更新
    logger.info("--- 环境更新 ---")
    cda.run("请报告当前环境信息")

    # 2. 冷库需求提交
    logger.info("--- 冷库需求提交 ---")
    # 计算当前时间
    total_minutes = cycle_idx * 15
    hour_now = (start_hour + total_minutes // 60) % 24
    minute_now = total_minutes % 60
    timestamp = f"{hour_now:02d}:{minute_now:02d}"

    for i, csa in enumerate(csa_agents):
        doors = 2 if activity[i] == 'high' else 0
        prompt = (
            f"当前时间 {timestamp}，活动程度 {activity[i]}，进出货次数 {doors}。"
            "请依次调用 read_room_sensor, predict_disturbance_load, calculate_cooling_demand, submit_cooling_demand。"
            "每一步都必须真实调用工具，不要跳过任何工具。"
        )
        csa.run(prompt)

    # 检查需求是否全部提交
    if len(demands) < len(csa_agents):
        logger.warning(f"仅收到 {len(demands)} 个冷库需求，预期 {len(csa_agents)} 个。")

    # 3. 压缩机调度
    logger.info("--- 压缩机调度 ---")
    cca.run("请读取压缩机状态，并根据当前所有冷库需求求解最优调度方案并下发。")

    # 4. 物理仿真（15 分钟）
    logger.info("--- 物理仿真 ---")
    dt = 15 / 60   # 小时
    total_cooling_actual = sum(c.cooling_output() for c in compressors)
    total_eco_demand = sum(d["Q_eco"] for d in demands.values())

    for i, cr in enumerate(cold_rooms):
        # 扰动计算：与 predict_disturbance_load 工具保持一致
        base = 20.0 if 6 <= hour_now <= 18 else 5.0
        doors = 2 if activity[i] == 'high' else 0
        disturbance = base * (1 + 0.5 * doors)
        if activity[i] == 'high':
            disturbance *= 1.5

        # 按需求比例分配实际制冷量
        if i in demands and total_eco_demand > 0:
            alloc = (demands[i]["Q_eco"] / total_eco_demand) * total_cooling_actual
        else:
            alloc = 0.0

        old_temp = cr.temp
        cr.update(alloc, disturbance, dt)
        logger.info(
            f"冷库{i}：需求 {demands.get(i, {}).get('Q_eco', 0):.1f} kW，"
            f"实际制冷 {alloc:.1f} kW，扰动 {disturbance:.1f} kW，"
            f"温度 {old_temp:.2f} -> {cr.temp:.2f}℃"
        )

    # 5. 评估与反馈
    logger.info("--- 评估与反馈 ---")
    report = evaluate_cycle(cold_rooms, compressors, demands)
    feedback = format_eval_feedback(report)
    logger.info(f"[记忆注入] 向 CCA 记忆写入评估反馈")
    cca.memory.save_context({"input": "系统"}, {"output": feedback})

    demands.clear()
    logger.info(f"{'#'*10} 周期 {cycle_idx} 结束 {'#'*10}\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["day", "night"], default="day")
    parser.add_argument("--cycles", type=int, default=2, help="模拟的决策周期数")
    args = parser.parse_args()

    # 根据场景设置起始小时
    start_hour = 8 if args.scenario == "day" else 18

    activity = load_scenario(args.scenario)
    csa_agents = [ColdStorageAgent(i) for i in range(len(cold_rooms))]
    cca = CompressorClusterAgent()
    cda = CoordinatorAgent()

    for cyc in range(args.cycles):
        report = run_cycle(csa_agents, cca, cda, activity, cyc, start_hour)
        logger.info(f"周期 {cyc} 温度合规：{report['temp_compliance']}")


if __name__ == "__main__":
    main()