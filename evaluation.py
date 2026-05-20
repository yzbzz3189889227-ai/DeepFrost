"""
评估工具集。
在每次调度结束后调用，结果反馈到 COA 的记忆中。
"""
import numpy as np
from utils.logger import logger

def evaluate_cycle(cold_rooms, compressors, demands) -> dict:
    """计算单周期性能指标，并记录详细日志"""
    logger.info("========== 评估开始 ==========")
    # 温度合规
    temp_compliance = all(cr.t_min <= cr.temp <= cr.t_max for cr in cold_rooms)
    for cr in cold_rooms:
        logger.info(f"[评估] 冷库{cr.id} 温度：{cr.temp:.2f}℃，合规：{cr.t_min <= cr.temp <= cr.t_max}")

    # 总能耗 (kWh) – 15分钟周期
    total_energy = sum(c.power_consumption() for c in compressors) * (15/60)
    logger.info(f"[评估] 总能耗：{total_energy:.2f} kWh")

    # 运行时长标准差
    hours = [c.total_hours for c in compressors]
    runtime_std = float(np.std(hours))
    logger.info(f"[评估] 运行时长标准差：{runtime_std:.2f} h，各压缩机时间：{hours}")

    # 需求满足率
    total_cooling = sum(c.cooling_output() for c in compressors)
    total_safe = sum(d["Q_safe"] for d in demands.values())
    demand_satisfaction = total_cooling / total_safe if total_safe > 0 else 1.0
    logger.info(f"[评估] 需求满足率：{demand_satisfaction:.2f} (实际制冷 {total_cooling:.1f} kW / 安全需求 {total_safe:.1f} kW)")

    report = {
        "temp_compliance": temp_compliance,
        "total_energy": total_energy,
        "runtime_std": runtime_std,
        "demand_satisfaction": demand_satisfaction
    }
    logger.info("========== 评估结束 ==========")
    return report

def format_eval_feedback(report: dict) -> str:
    """将评估报告转为自然语言反馈"""
    feedback = "上一周期评估结果："
    if report["temp_compliance"]:
        feedback += "温度全部达标；"
    else:
        feedback += "存在温度越限！"
    feedback += f"总能耗 {report['total_energy']:.2f} kWh；"
    feedback += f"运行时长标准差 {report['runtime_std']:.2f} h；"
    feedback += f"需求满足率 {report['demand_satisfaction']:.2f}。"
    logger.info(f"[评估反馈] {feedback}")
    return feedback