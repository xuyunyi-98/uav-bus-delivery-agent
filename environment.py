"""
农村公交-无人机配送环境建模模块

功能：
1. 创建公交线路（支持多仓库）
2. 计算任务与各仓库/公交距离
3. 判断无人机可行性
4. 任务自动分配到最近仓库
"""

import math
import random


class Environment:

    def __init__(self, tasks, drone_num=3, depots=None):
        """
        初始化环境

        tasks:     task_generator生成的任务列表
        drone_num: 全局无人机数量（无 depots 时使用）
        depots:    仓库列表（可选），每项包含：
                   {"id": "A", "name": "城关镇", "x": 25, "y": 50,
                    "bus_route": [(0,50),(50,50)], "uav_count": 2, "bus_count": 1}
                   如果为 None，使用默认单仓库模式（向后兼容）
        """
        self.tasks = tasks
        self.max_drone_load = 10

        # ==========================================
        # 仓库建模（多仓库模式 / 单仓库向后兼容）
        # ==========================================
        if depots is None:
            self.depots = [{
                "id": "A", "name": "主仓库", "x": 50, "y": 50,
                "bus_routes": [[(0, 50), (50, 50), (100, 50)]],
                "uav_count": drone_num, "bus_count": 2,
                "drone_batteries": [100.0 for _ in range(drone_num)]
            }]
        else:
            self.depots = []
            for d in depots:
                depot = dict(d)
                depot["drone_batteries"] = [100.0 for _ in range(depot.get("uav_count", 1))]
                self.depots.append(depot)

        # 为每个任务预计算最近仓库（贪心分仓依据）
        self._task_depot_map = {}
        for task in self.tasks:
            nearest = self._find_nearest_depot(task)
            self._task_depot_map[task["id"]] = nearest["id"]

    # ==========================================
    # 仓库相关方法
    # ==========================================
    def _find_nearest_depot(self, task):
        best = None
        best_dist = float("inf")
        for depot in self.depots:
            d = self.distance((task["x"], task["y"]), (depot["x"], depot["y"]))
            if d < best_dist:
                best_dist = d
                best = depot
        return best

    def get_depot_for_task(self, task_id):
        return self._task_depot_map.get(task_id, self.depots[0]["id"])

    def get_depot_tasks(self, depot_id):
        return [t for t in self.tasks if self._task_depot_map.get(t["id"]) == depot_id]

    def get_depot_by_id(self, depot_id):
        for d in self.depots:
            if d["id"] == depot_id:
                return d
        return self.depots[0]

    def get_all_drone_battery_status(self):
        result = []
        for depot in self.depots:
            for i, batt in enumerate(depot.get("drone_batteries", [])):
                result.append({
                    "drone_id": f"{depot['id']}-{i+1}",
                    "depot": depot["name"],
                    "battery": round(batt, 1)
                })
        return result

    def get_drone_battery_status(self):
        return self.get_all_drone_battery_status()

    def get_available_drone_count(self):
        return sum(
            sum(1 for b in d.get("drone_batteries", []) if b > 20.0)
            for d in self.depots
        )

    def is_drone_available(self, drone_id):
        return True

    def consume_battery(self, drone_id, amount=5.0):
        pass

    def drone_available_for_task(self):
        return self.get_available_drone_count() > 0

    # ==========================================
    # 距离计算
    # ==========================================
    def distance(self, p1, p2):
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    def nearest_bus_distance(self, task):
        task_point = (task["x"], task["y"])
        depot_id = self._task_depot_map.get(task["id"])
        depot = self.get_depot_by_id(depot_id)
        min_dist = float("inf")
        routes = depot.get("bus_routes", [depot.get("bus_route", [(50, 50)])])
        for route in routes:
            for station in route:
                d = self.distance(task_point, station)
                if d < min_dist:
                    min_dist = d
        return min_dist if min_dist < 999 else 999

    def distance_to_depot(self, task):
        depot = self.get_depot_by_id(self._task_depot_map.get(task["id"]))
        return self.distance((task["x"], task["y"]), (depot["x"], depot["y"]))

    # ==========================================
    # 任务分析
    # ==========================================
    def analyze_tasks(self):
        results = []
        for task in self.tasks:
            depot_id = self._task_depot_map.get(task["id"], "A")
            depot = self.get_depot_by_id(depot_id)
            bus_distance = self.nearest_bus_distance(task)
            depot_distance = self.distance_to_depot(task)

            drone_available = task["weight"] <= self.max_drone_load
            urgency = task.get("urgency", "普通")
            item_type = task.get("item_type", "常规")

            result = {
                "id": task["id"],
                "x": task["x"],
                "y": task["y"],
                "weight": task["weight"],
                "bus_distance": round(bus_distance, 2),
                "depot_distance": round(depot_distance, 2),
                "drone_available": drone_available,
                "urgency": urgency,
                "item_type": item_type,
                "depot_id": depot_id,
                "depot_name": depot["name"],
            }
            results.append(result)
        return results