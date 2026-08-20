"""TSP 路径规划 + 时间窗检查"""
import math


def distance(p1, p2):
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def nearest_neighbor_route(depot_xy, tasks_xy, speed=1.0):
    """
    贪心最近邻路径规划
    depot_xy: (x, y) 起点
    tasks_xy: [(task_id, x, y), ...]
    speed: 速度 (km/min)
    返回: (ordered_tasks, total_distance, arrival_times)
    """
    if not tasks_xy:
        return [], 0.0, []

    cx, cy = depot_xy
    remaining = list(tasks_xy)
    ordered = []
    cum_time = 0.0
    times = []

    while remaining:
        best_i = min(range(len(remaining)),
                     key=lambda i: distance((cx, cy), (remaining[i][1], remaining[i][2])))
        t = remaining.pop(best_i)
        d = distance((cx, cy), (t[1], t[2]))
        cum_time += d / max(0.1, speed)
        ordered.append(t)
        times.append(round(cum_time, 1))
        cx, cy = t[1], t[2]

    total_d = distance(depot_xy, (ordered[0][1], ordered[0][2]))
    for i in range(1, len(ordered)):
        total_d += distance((ordered[i - 1][1], ordered[i - 1][2]),
                            (ordered[i][1], ordered[i][2]))

    return ordered, round(total_d, 2), times


def check_time_windows(ordered_tasks, arrival_times, task_deadlines):
    """
    检查时间窗违约
    task_deadlines: {task_id: deadline_minutes}
    返回: (violations, total_late, details)
    """
    violations = 0
    total_late = 0.0
    details = []
    for (tid, _, _), at in zip(ordered_tasks, arrival_times):
        dl = task_deadlines.get(tid)
        if dl is not None and at > dl:
            late = at - dl
            violations += 1
            total_late += late
            details.append({"task_id": tid, "arrival": at, "deadline": dl, "late": round(late, 1)})
    return violations, round(total_late, 1), details
