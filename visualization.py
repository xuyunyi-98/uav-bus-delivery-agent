import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

# 多仓库颜色方案
DEPOT_COLORS = {
    "A": {"marker": "s", "color": "#1f77b4", "uav_color": "#d62728", "label": "Depot A: 城关镇"},
    "B": {"marker": "D", "color": "#ff7f0e", "uav_color": "#e377c2", "label": "Depot B: 青山乡"},
}

class VisualizationAgent:
    def draw(self, tasks, plan):
        if not os.path.exists("results"):
            os.makedirs("results")

        fig, ax = plt.subplots(figsize=(10, 7))

        # ==========================================
        # 画多仓库标记 + 各自服务区 + 多条公交线
        # ==========================================
        # 仓库 A: 蓝色系
        depot_a_routes = [
            ([(0, 50), (25, 50), (50, 50)], '-', 2.5, '#1f77b4'),
            ([(25, 50), (25, 20), (25, 80)], '--', 1.8, '#5ba3d9'),
            ([(0, 20), (25, 20), (50, 20)], ':', 1.5, '#7fc3f0'),
        ]
        ax.plot(25, 50, marker='s', color='#1f77b4', markersize=12,
                label='Depot A: 城关镇 (2 UAV + 1 Bus)', zorder=5)
        for i, (pts, ls, lw, clr) in enumerate(depot_a_routes):
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            ax.plot(xs, ys, color=clr, linestyle=ls, linewidth=lw,
                    label='Depot A Routes' if i == 0 else "")
        circle_a = patches.Circle((25, 50), radius=30, fill=False, linestyle='--',
                                   color='#1f77b4', alpha=0.3)
        ax.add_patch(circle_a)

        # 仓库 B: 橙色系
        depot_b_routes = [
            ([(50, 50), (75, 50), (100, 50)], '-', 2.5, '#ff7f0e'),
            ([(75, 50), (75, 20), (75, 80)], '--', 1.8, '#f5a623'),
            ([(50, 80), (75, 80), (100, 80)], ':', 1.5, '#ffc374'),
        ]
        ax.plot(75, 50, marker='D', color='#ff7f0e', markersize=12,
                label='Depot B: 青山乡 (1 UAV + 1 Bus)', zorder=5)
        for i, (pts, ls, lw, clr) in enumerate(depot_b_routes):
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            ax.plot(xs, ys, color=clr, linestyle=ls, linewidth=lw,
                    label='Depot B Routes' if i == 0 else "")
        circle_b = patches.Circle((75, 50), radius=30, fill=False, linestyle='--',
                                   color='#ff7f0e', alpha=0.3)
        ax.add_patch(circle_b)

        # 换乘站标记（坐标在 ≥2 条线路中出现）
        all_stations = {}
        for pts, _, _, _ in depot_a_routes + depot_b_routes:
            for p in pts:
                all_stations[p] = all_stations.get(p, 0) + 1
        transfer_xy = [p for p, cnt in all_stations.items() if cnt >= 2]
        if transfer_xy:
            tx, ty = zip(*transfer_xy)
            ax.scatter(tx, ty, marker='s', s=80, c='#dc2626', zorder=6,
                       edgecolors='white', linewidths=1.5, label='Transfer Station')

        # ==========================================
        # 画任务点 + 连接到各自仓库
        # ==========================================
        uav_plotted = {"A": False, "B": False}
        bus_plotted = {"A": False, "B": False}

        for task in tasks:
            tid = task["id"]
            assignment = next((p for p in plan if p.get("task_id") == tid),
                              {"method": "公交", "vehicle_id": "A-Bus-1"})
            method = assignment.get("method", "公交")
            vehicle_id = assignment.get("vehicle_id", "?")
            # 从 vehicle_id 推断仓库 "A-UAV-1" → depot = "A"
            depot_id = vehicle_id.split("-")[0] if "-" in vehicle_id else "A"

            depot_style = DEPOT_COLORS.get(depot_id, DEPOT_COLORS["A"])
            x, y = task["x"], task["y"]
            depot_x, depot_y = (25, 50) if depot_id == "A" else (75, 50)

            if method == "无人机":
                ax.plot(x, y, marker='^', color=depot_style["uav_color"], markersize=8,
                        label=f'{depot_id}-UAV' if not uav_plotted[depot_id] else "")
                ax.plot([depot_x, x], [depot_y, y], color='#9467bd', linestyle=':', linewidth=1)
                uav_plotted[depot_id] = True
            else:
                ax.plot(x, y, marker='o', color='#2ca02c', markersize=8,
                        label=f'{depot_id}-Bus' if not bus_plotted[depot_id] else "")
                ax.plot([x, x], [depot_y, y], color='#7f7f7f', linestyle='--', linewidth=1)
                bus_plotted[depot_id] = True

            ax.text(x + 1.5, y + 1.5, f"T{tid}({vehicle_id})", fontsize=7, fontweight='bold')

        ax.set_title("Multi-Depot Bus-UAV Collaborative Delivery Planning",
                     fontsize=13, fontweight='bold')
        ax.set_xlabel("X coordinate")
        ax.set_ylabel("Y coordinate")
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.legend(loc='upper right', fontsize=8, framealpha=0.9, edgecolor='black')
        ax.grid(True, linestyle='--', alpha=0.6)

        save_path = os.path.join("results", "Bus_UAV_Collaborative_Planning.png")
        fig.savefig(save_path, dpi=300, bbox_inches='tight')
        return fig