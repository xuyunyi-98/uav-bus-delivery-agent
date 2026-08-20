# -*- coding: utf-8 -*-
"""????????? (GIF)"""
import os, math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation, PillowWriter

import matplotlib
for fp in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/simsun.ttc"]:
    if os.path.exists(fp):
        from matplotlib import font_manager
        font_manager.fontManager.addfont(fp)
        matplotlib.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=fp).get_name()]
        matplotlib.rcParams["axes.unicode_minus"] = False
        break


def _dist(p1, p2):
    return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)


def generate_delivery_animation(tasks, plan, output_path=None, fps=6):
    """???? GIF ????? (gif_path, ????)"""
    if output_path is None:
        os.makedirs("results", exist_ok=True)
        output_path = os.path.join("results", "delivery_animation.gif")

    depots = {"A": (25, 50), "B": (75, 50)}
    bus_routes = {
        "A": [[(0,50),(25,50),(50,50)],[(25,50),(25,20),(25,80)],[(0,20),(25,20),(50,20)]],
        "B": [[(50,50),(75,50),(100,50)],[(75,50),(75,20),(75,80)],[(50,80),(75,80),(100,80)]],
    }
    task_map = {t["id"]: (t["x"], t["y"]) for t in tasks}

    groups = {}
    for p in plan:
        vid = p.get("vehicle_id", "unknown")
        groups.setdefault(vid, []).append(p)
    for vid in groups:
        groups[vid].sort(key=lambda x: x.get("route_order", 0))

    timeline = []
    for vid, items in groups.items():
        for it in items:
            timeline.append({"vehicle_id": vid, "method": it["method"],
                             "depot_id": it.get("depot_id", "A"), "task_id": it["task_id"]})
    total = len(timeline)

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.grid(True, linestyle="--", alpha=0.4)

    for did, routes in bus_routes.items():
        base = "#1f77b4" if did == "A" else "#ff7f0e"
        for i, route in enumerate(routes):
            xs = [p[0] for p in route]; ys = [p[1] for p in route]
            ls = "-" if i == 0 else ("--" if i == 1 else ":")
            ax.plot(xs, ys, color=base, linestyle=ls, linewidth=1.5, alpha=0.5)
    for did, (dx, dy) in depots.items():
        m = "s" if did == "A" else "D"
        c = "#1f77b4" if did == "A" else "#ff7f0e"
        ax.plot(dx, dy, marker=m, color=c, markersize=14, zorder=5)
        ax.add_patch(patches.Circle((dx, dy), 30, fill=False, linestyle="--", color=c, alpha=0.25))

    ax.set_title("Delivery Process", fontsize=13, fontweight="bold")
    ax.set_xlabel("X"); ax.set_ylabel("Y")

    uav_sc = ax.scatter([], [], marker="^", s=120, c="#d62728", zorder=6)
    bus_sc = ax.scatter([], [], marker="o", s=140, c="#2ca02c", zorder=6)
    done_sc = ax.scatter([], [], marker="x", s=80, c="#888", zorder=5)
    status = ax.text(0.02, 0.97, "", transform=ax.transAxes, fontsize=11, va="top", fontweight="bold")

    n_frames = max(total * 2, 2)

    def update(frame):
        idx = min(frame // 2, total - 1)
        done = timeline[:idx + 1]
        ev = timeline[idx]
        if done:
            dx = [task_map[e["task_id"]][0] for e in done]
            dy = [task_map[e["task_id"]][1] for e in done]
            done_sc.set_offsets(np.column_stack([dx, dy]))
        else:
            done_sc.set_offsets(np.empty((0, 2)))
        tx, ty = task_map[ev["task_id"]]
        if ev["method"] == "???":
            uav_sc.set_offsets([[tx, ty]]); bus_sc.set_offsets(np.empty((0, 2)))
        else:
            bus_sc.set_offsets([[tx, ty]]); uav_sc.set_offsets(np.empty((0, 2)))
        status.set_text(f"{idx+1}/{total}  {ev['vehicle_id']} -> #{ev['task_id']} ({ev['method']})")
        return uav_sc, bus_sc, done_sc, status

    ani = FuncAnimation(fig, update, frames=n_frames, interval=1000/fps, blit=True)
    ani.save(output_path, writer=PillowWriter(fps=fps), dpi=80)
    plt.close(fig)
    return output_path, total
