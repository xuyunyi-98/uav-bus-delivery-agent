from environment import Environment
from eapso_agent import EAPSOAgent
from llm_agent import LLMTaskAgent
from fitness import FitnessCalculator
from task_generator import generate_tasks
import routing


# ==========================================
# 多仓库配置（Phase 1: 2个固定仓库）
# ==========================================
MULTI_DEPOTS = [
    {
        "id": "A", "name": "城关镇",
        "x": 25, "y": 50,
        "bus_routes": [
            [(0, 50), (25, 50), (50, 50)],           # A1 主干线
            [(25, 50), (25, 20), (25, 80)],           # A2 纵线
            [(0, 20), (25, 20), (50, 20)],            # A3 下方横线
        ],
        "uav_count": 2, "bus_count": 1,
    },
    {
        "id": "B", "name": "青山乡",
        "x": 75, "y": 50,
        "bus_routes": [
            [(50, 50), (75, 50), (100, 50)],          # B1 主干线
            [(75, 50), (75, 20), (75, 80)],           # B2 纵线
            [(50, 80), (75, 80), (100, 80)],          # B3 上方横线
        ],
        "uav_count": 1, "bus_count": 1,
    },
]


class UAVBusAgent:
    def run(self, command, custom_tasks=None, resource_limits=None, weather="晴朗"):

        # ==========================================
        # 1. 意图解析阶段 (打通 LLM)
        # ==========================================
        llm_agent = LLMTaskAgent()
        command_str = str(command) if command is not None else ""
        task_info = llm_agent.parse(command_str)

        # ==========================================
        # 2. 环境初始化阶段 (接入真实业务数据)
        # ==========================================
        if custom_tasks is not None:
            tasks = custom_tasks
        else:
            task_num = task_info.get("task_num", 12)
            tasks = generate_tasks(task_num)

        # 多仓库环境（任务自动贪心分配到最近仓库）
        env = Environment(tasks, depots=MULTI_DEPOTS)
        environment_info = env.analyze_tasks()

        # ==========================================
        # 3. 权重自适应映射 + 配送方式强制约束
        # ==========================================
        force_all_bus = False
        force_all_drone = False

        if not command_str or not command_str.strip():
            dynamic_weights = {"time_weight": 0.33, "cost_weight": 0.33, "carbon_weight": 0.34}
            task_info["objective"] = "多目标平衡"
        else:
            intent_text = command_str
            if ("公交" in intent_text or "巴士" in intent_text) and \
               ("全部" in intent_text or "所有" in intent_text or "都" in intent_text or "仅" in intent_text or "只" in intent_text):
                force_all_bus = True
                dynamic_weights = {"time_weight": 0.33, "cost_weight": 0.33, "carbon_weight": 0.34}
                task_info["objective"] = "全部公交配送"
            elif ("无人机" in intent_text) and \
                 ("全部" in intent_text or "所有" in intent_text or "都" in intent_text or "仅" in intent_text or "只" in intent_text):
                force_all_drone = True
                dynamic_weights = {"time_weight": 0.33, "cost_weight": 0.33, "carbon_weight": 0.34}
                task_info["objective"] = "全部无人机配送"
            elif "碳" in intent_text or "排放" in intent_text or "环保" in intent_text:
                dynamic_weights = {"time_weight": 0.2, "cost_weight": 0.2, "carbon_weight": 0.6}
                task_info["objective"] = "碳排放最低"
            elif "时间" in intent_text or "快" in intent_text or "加急" in intent_text:
                dynamic_weights = {"time_weight": 0.6, "cost_weight": 0.2, "carbon_weight": 0.2}
                task_info["objective"] = "时间最短"
            elif "成本" in intent_text or "钱" in intent_text or "便宜" in intent_text:
                dynamic_weights = {"time_weight": 0.2, "cost_weight": 0.6, "carbon_weight": 0.2}
                task_info["objective"] = "成本最低"
            else:
                dynamic_weights = {"time_weight": 0.33, "cost_weight": 0.33, "carbon_weight": 0.34}
                task_info["objective"] = "多目标平衡"

        # ==========================================
        # 4. 核心算法寻优阶段 (多仓库独立调度)
        # ==========================================
        fc = FitnessCalculator(**dynamic_weights)
        all_plans = []
        depot_histories = []
        total_score = 0

        for depot in env.depots:
            depot_id = depot["id"]
            depot_tasks = env.get_depot_tasks(depot_id)

            if not depot_tasks:
                continue

            # 筛选该仓库的 environment_info
            depot_env_info = [e for e in environment_info if e["depot_id"] == depot_id]

            # 该仓库分配给「无人机」的包裹最多不超过其无人机数量
            # （force_all_bus/force_all_drone 全局生效）
            optimizer = EAPSOAgent(particles=max(5, len(depot_tasks)), iterations=15, weights=dynamic_weights)
            drone_battery_list = [100.0 for _ in range(depot["uav_count"])]
            plan, score, history = optimizer.optimize(
                depot_env_info,
                drone_num=depot["uav_count"],
                bus_num=depot["bus_count"],
                drone_batteries=drone_battery_list,
                force_all_bus=force_all_bus,
                force_all_drone=force_all_drone,
                weather=weather,
                depot_id=depot_id,
            )
            all_plans.extend(plan)
            depot_histories.append(history)
            total_score += score

        # ========== TSP 路径规划 + 时间窗检查 ==========
        deadlines = {}
        for t in tasks:
            dl = t.get("deadline")
            if dl is not None:
                deadlines[t["id"]] = float(dl)

        # 按车辆分组
        vehicle_groups = {}
        for item in all_plans:
            vid = item.get("vehicle_id", "unknown")
            if vid not in vehicle_groups:
                vehicle_groups[vid] = []
            vehicle_groups[vid].append(item)

        for vid, items in vehicle_groups.items():
            # 确定 depot 位置
            depot_id = items[0].get("depot_id", "A")
            depot = next((d for d in env.depots if d["id"] == depot_id), env.depots[0])
            is_drone = "UAV" in vid
            speed = 2.0 if is_drone else 1.0  # km/min

            tasks_xy = [(it["task_id"],
                         float(next((t["x"] for t in tasks if t["id"] == it["task_id"]), 0)),
                         float(next((t["y"] for t in tasks if t["id"] == it["task_id"]), 0)))
                        for it in items]

            ordered, total_dist, arrival_times = routing.nearest_neighbor_route(
                (depot["x"], depot["y"]), tasks_xy, speed=speed)

            # 写回 route_order 和 estimated_arrival
            for rank, (tid, _, _) in enumerate(ordered):
                for it in items:
                    if it["task_id"] == tid:
                        it["route_order"] = rank + 1
                        it["estimated_arrival"] = arrival_times[rank]
                        break

        # 合并 score 取平均（或加权）
        merged_score = round(total_score / max(1, len(env.depots)), 2)

        # ???????????????????????????
        merged_history = []
        if depot_histories:
            max_len = max(len(h) for h in depot_histories)
            for i in range(max_len):
                s = sum(h[i] for h in depot_histories if i < len(h))
                merged_history.append(round(s, 2))

        # 把 plan 中的 task_id 映射回完整 environment_info 用于 get_details
        metrics = fc.get_details(all_plans, environment_info, weather=weather)

        return {
            "plan": all_plans,
            "score": merged_score,
            "history": merged_history,
            "tasks": tasks,
            "task_info": task_info,
            "weights": dynamic_weights,
            "metrics": metrics,
            "battery_status": env.get_drone_battery_status(),
        }