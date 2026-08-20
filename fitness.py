"""
适应度评价模块 (动态自适应权重版)

评价指标（严格对齐小论文）：
1. 时间 (Time)
2. 成本 (Cost)
3. 碳排放 (Carbon Emissions)
4. 物理载荷惩罚 (Payload Constraints)
5. 资源约束惩罚 (Resource Penalty)
"""

class FitnessCalculator:

    def __init__(self, time_weight=0.4, cost_weight=0.4, carbon_weight=0.2):
        self.time_weight = time_weight
        self.cost_weight = cost_weight
        self.carbon_weight = carbon_weight
        self.constraint_penalty = 100

    def _get_weather_factors(self, weather):
        """
        根据天气返回无人机配送的成本/时间/碳排倍率。
        weather: "晴朗" / "大风" / "阵雨"
        返回: (cost_mult, time_mult, carbon_mult)
        """
        if "大风" in weather:
            return 3.0, 0.7, 2.0    # 大风：成本×3, 时间×0.7, 碳排×2
        elif "阵雨" in weather:
            return 1.5, 2.0, 1.0    # 阵雨：成本×1.5, 时间×2, 碳排不变
        else:
            return 1.0, 1.0, 1.0    # 晴朗：无影响

    def calculate(
            self,
            plan,
            environment_info,
            resource_info=None,
            weather="晴朗"
    ):
        """
        计算多目标综合 Fitness (适应度代价)
        weather: 天气状况，影响无人机配送参数
        """
        cost_mult, time_mult, carbon_mult = self._get_weather_factors(weather)

        total_time = 0
        total_cost = 0
        total_carbon = 0  

        uav_count = 0
        bus_count = 0

        for item in plan:
            task_id = item["task_id"]
            method = item["method"]

            task = None
            for env in environment_info:
                if env["id"] == task_id:
                    task = env
                    break

            distance = task["bus_distance"]
            weight = task.get("weight", 0)
            urgency = task.get("urgency", "普通")

            if method == "公交":
                bus_count += 1
                # 公交不受天气影响
                if urgency == "加急":
                    total_cost += 1000
                total_time += distance * 0.8
                total_cost += 2
                total_carbon += 0.5
            else:
                uav_count += 1
                if weight > 10.0:
                    total_cost += 1000
                # 天气影响无人机
                total_time += distance * 0.5 * time_mult
                total_cost += 5 * cost_mult
                total_carbon += 2 * carbon_mult

        # 利用大模型解析出的动态偏好权重，计算综合适应度
        fitness = (
            self.time_weight * total_time +
            self.cost_weight * total_cost +
            self.carbon_weight * total_carbon
        )

        # =====================
        # 处理底层运力资源数量约束
        # =====================
        if resource_info is not None:
            max_uav = resource_info.get("uav_num", 999)
            max_bus = resource_info.get("bus_num", 999)

            if uav_count > max_uav:
                fitness += (uav_count - max_uav) * self.constraint_penalty

            if bus_count > max_bus:
                fitness += (bus_count - max_bus) * self.constraint_penalty

        return round(fitness, 2)

    def get_details(self, plan, environment_info, weather="晴朗"):
        cost_mult, time_mult, carbon_mult = self._get_weather_factors(weather)

        total_time = 0
        total_cost = 0
        total_carbon = 0
        tw_violations = 0

        for item in plan:
            task_id = item["task_id"]
            method = item["method"]

            task = next((env for env in environment_info if env["id"] == task_id), None)
            if not task: continue
            
            distance = task["bus_distance"]
            weight = task.get("weight", 0)
            deadline = task.get("deadline")
            arrival = item.get("estimated_arrival")

            if method == "公交":
                total_time += distance * 0.8
                total_cost += 2
                total_carbon += 0.5
            else:
                if weight > 10.0:
                    total_cost += 1000
                total_time += distance * 0.5 * time_mult
                total_cost += 5 * cost_mult
                total_carbon += 2 * carbon_mult

            # 时间窗检查
            if deadline is not None and arrival is not None and arrival > deadline:
                tw_violations += 1
                total_cost += (arrival - deadline) * 10  # 每分钟超时罚10元

        return {
            "time": round(total_time, 2),
            "cost": round(total_cost, 2),
            "carbon": round(total_carbon, 2),
            "tw_violations": tw_violations,
        }
