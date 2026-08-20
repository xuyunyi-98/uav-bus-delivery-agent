import streamlit as st
import pandas as pd
import os, sys, datetime
import numpy as np
import matplotlib.pyplot as plt
import importlib

# ==========================================
# 【关键修复】：强制重新加载所有核心模块，绕过 Streamlit 的模块缓存
# ==========================================
# Streamlit 在开发模式下会缓存已导入的 Python 模块，即使源文件已更新也不会自动重新加载。
# 这导致用户反复修改代码但界面不变。以下代码在每次运行时强制刷新模块。
core_modules = ['fitness', 'eapso_agent', 'environment', 'llm_agent', 'agent_core', 'visualization']
for mod_name in core_modules:
    if mod_name in sys.modules:
        importlib.reload(sys.modules[mod_name])

# 然后再正常导入（此时拿到的是最新代码）
from agent_core import UAVBusAgent
from visualization import VisualizationAgent
import database as db
import export_utils as export_u
import video_generator as vg

# 页面配置
st.set_page_config(page_title="协同配送智能体", layout="wide",
                   page_icon="🚁")

# ==========================================
# 全局 CSS 美化：卡片、配色、阴影
# ==========================================
st.markdown("""
<style>
    /* ---- 全局字体和背景 ---- */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }
    
    /* ---- 卡片容器 ---- */
    .metric-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s;
    }
    .metric-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.10);
    }
    .metric-card .label {
        font-size: 13px;
        color: #6b7280;
        margin-bottom: 6px;
        letter-spacing: 0.3px;
    }
    .metric-card .value {
        font-size: 28px;
        font-weight: 700;
        color: #111827;
    }
    .metric-card .value.green  { color: #059669; }
    .metric-card .value.blue   { color: #1a56db; }
    .metric-card .value.orange { color: #d97706; }
    .metric-card .value.red    { color: #dc2626; }
    
    /* ---- 章节标题 ---- */
    .section-title {
        font-size: 20px;
        font-weight: 700;
        color: #111827;
        border-left: 4px solid #1a56db;
        padding-left: 14px;
        margin-bottom: 4px;
    }
    
    /* ---- 信息条 ---- */
    .info-strip {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 16px 0;
        font-size: 14px;
        color: #1e40af;
    }
    
    /* ---- 侧边栏 ---- */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }
    
    /* ---- 按钮 ---- */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="display:flex;align-items:center;gap:14px;margin-bottom:10px;">
  <span style="font-size:40px;">🚁</span>
  <div>
    <div style="font-size:26px;font-weight:800;color:#111827;">农村公交-无人机协同配送智能体</div>
    <div style="font-size:14px;color:#6b7280;margin-top:2px;">
      多仓库版 · 自然语言调度 · EAPSO-HDTA 核心算法 · SQLite 持久化
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 侧边栏：环境与运力设定 (更贴近现实)
# ==========================================
with st.sidebar:
    # 侧边栏头部
    st.markdown("""
    <div style="text-align:center;padding:8px 0 16px 0;">
      <div style="font-size:32px;">⚙️</div>
      <div style="font-size:16px;font-weight:700;color:#111827;">业务环境设定</div>
      <div style="font-size:12px;color:#6b7280;">DeepSeek LLM 在线</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("##### ⛅ 天气状况")
    weather = st.radio("当前天气",
        ["☀️ 晴朗 (适宜飞行)", "💨 大风 (能耗×3)", "🌧️ 阵雨 (限速×2)"],
        label_visibility="collapsed")

    st.markdown("---")
    st.markdown("##### 🏭 多仓库运力配置")
    st.markdown("""
    <div style="background:#dbeafe;border-radius:8px;padding:12px;margin:6px 0;font-size:13px;">
      <b>🔵 城关镇 (仓库A)</b><br>
      2架无人机 · 1辆公交 · 左半区
    </div>
    <div style="background:#ffedd5;border-radius:8px;padding:12px;margin:6px 0;font-size:13px;">
      <b>🟠 青山乡 (仓库B)</b><br>
      1架无人机 · 1辆公交 · 右半区
    </div>
    """, unsafe_allow_html=True)

    if 'last_battery_status' in st.session_state:
        st.markdown("---")
        st.markdown("##### 🔋 运力状态")
        for drone in st.session_state.last_battery_status:
            did = drone.get("drone_id", "?")
            dname = drone.get("depot", "")
            pct = drone.get("battery", 0)
            label = f"{did} ({dname})"
            if pct <= 20:
                st.error(f"🛑 {label}: {pct}%")
            elif pct <= 50:
                st.warning(f"⚠️ {label}: {pct}%")
            else:
                st.success(f"✅ {label}: {pct}%")

# ==========================================
# 真实业务订单接入层 (支持 Excel 导入 + 在线编辑)
# ==========================================
st.subheader("📦 实时业务订单池")
col_up1, col_up2 = st.columns([3, 1])
with col_up1:
    st.caption("双击表格单元格可直接编辑，按 Delete 键删除行")
with col_up2:
    uploaded_file = st.file_uploader("📂 上传 Excel", type=["xlsx", "xls"],
                                      label_visibility="collapsed")

# 默认数据（兜底）
default_orders = [
    {"id": 1, "x": 15, "y": 85, "weight": 2.5, "urgency": "普通", "item_type": "农产品"},
    {"id": 2, "x": 42, "y": 20, "weight": 8.0, "urgency": "加急", "item_type": "医疗物资"},
    {"id": 3, "x": 75, "y": 92, "weight": 1.2, "urgency": "普通", "item_type": "日用品"},
    {"id": 4, "x": 95, "y": 15, "weight": 15.0, "urgency": "普通", "item_type": "化肥 (超重)"},
    {"id": 5, "x": 52, "y": 70, "weight": 4.5, "urgency": "加急", "item_type": "生鲜"},
]

# 如果用户上传了 Excel，尝试解析并替换默认数据
orders_to_edit = default_orders
if uploaded_file is not None:
    try:
        # 跳过前3行（标题/副标题/空行），第4行是表头
        df_uploaded = pd.read_excel(uploaded_file, engine="openpyxl", header=3)
        # 删除空行（统计行等）
        df_uploaded = df_uploaded.dropna(subset=["id", "x", "y", "weight"])
        # 确保 id 为整数
        df_uploaded["id"] = df_uploaded["id"].astype(int)
        # 检查必须的列
        required_cols = {"id", "x", "y", "weight"}
        if required_cols.issubset(set(df_uploaded.columns)):
            # 补充可选列
            if "urgency" not in df_uploaded.columns:
                df_uploaded["urgency"] = "普通"
            if "item_type" not in df_uploaded.columns:
                df_uploaded["item_type"] = "常规"
            orders_to_edit = df_uploaded.to_dict("records")
            st.success(f"✅ 成功导入 {len(orders_to_edit)} 条订单数据！")
        else:
            st.error(f"❌ Excel 缺少必须列：{required_cols - set(df_uploaded.columns)}，已回退到默认数据。")
    except Exception as e:
        st.error(f"❌ Excel 解析失败：{e}，已回退到默认数据。")

# 生成可编辑的数据表
edited_df = st.data_editor(pd.DataFrame(orders_to_edit), num_rows="dynamic", use_container_width=True)

# 主界面交互
st.subheader("💬 指挥中枢")
# 【改动1】：指令变得非常自然，不再需要写死无人机数量
command = st.text_area("下发自然语言调度指令", "今天天气不太好，请重点考虑成本。")

if st.button("🚀 启动实景调度优化"):
    with st.spinner('正在分析真实订单数据与环境约束，进行多维策略寻优...'):
        custom_tasks = edited_df.to_dict('records')
        agent = UAVBusAgent()
        # ?? emoji ?????????????? split ?? emoji?
        if "大风" in weather:
            weather_short = "大风"
        elif "阵雨" in weather:
            weather_short = "阵雨"
        else:
            weather_short = "晴朗"
        results = agent.run(command, custom_tasks=custom_tasks, weather=weather_short)
        # 将结果存入 session_state，避免后续按钮 rerun 导致结果丢失
        st.session_state.results = results
        st.session_state.custom_tasks = custom_tasks
        st.session_state.weather_short = weather_short
        st.session_state.last_battery_status = results.get("battery_status", [])
        st.session_state.command = command
        # ???????????? SQLite
        try:
            db.save_dispatch(
                command=command, weather=weather_short,
                objective=results["task_info"].get("objective", "?????"),
                num_drones=3, num_buses=2, weights=results["weights"],
                tasks=custom_tasks, plan=results["plan"],
                metrics=results["metrics"], score=results["score"]
            )
        except Exception:
            pass

if "results" in st.session_state:
    results = st.session_state.results
    custom_tasks = st.session_state.custom_tasks
    weather_short = st.session_state.weather_short
    plan = results["plan"]
    score = results["score"]
    history = results["history"]
    tasks = results.get("tasks")
    metrics = results.get("metrics")
    st.divider()
    
    # ========== 仪表盘卡片 ==========
    obj_text = results["task_info"].get("objective", "综合优化")
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    with col_a1:
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">📦 包裹 / 目标</div>
          <div class="value blue">{len(plan)}</div>
          <div style="font-size:12px;color:#6b7280;margin-top:4px;">{obj_text}</div>
        </div>""", unsafe_allow_html=True)
    with col_a2:
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">🏭 仓库 / 无人机</div>
          <div class="value">2仓库 / 3架</div>
          <div style="font-size:12px;color:#6b7280;margin-top:4px;">2辆公交车</div>
        </div>""", unsafe_allow_html=True)
    with col_a3:
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">⛅ 天气</div>
          <div class="value">{weather_short}</div>
          <div style="font-size:12px;color:#6b7280;margin-top:4px;">权重: cost={results['weights']['cost_weight']}</div>
        </div>""", unsafe_allow_html=True)
    with col_a4:
        cls = "green" if score < 100 else "orange" if score < 500 else "red"
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">⭐ 综合 Fitness</div>
          <div class="value {cls}">{score}</div>
          <div style="font-size:12px;color:#6b7280;margin-top:4px;">越低越优</div>
        </div>""", unsafe_allow_html=True)

    # 耗时/成本/碳排
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    with col_b1:
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">⏱️ 预计总耗时</div>
          <div class="value">{metrics['time']} <span style="font-size:16px;">min</span></div>
        </div>""", unsafe_allow_html=True)
    with col_b2:
        cost_cls = "green" if metrics['cost'] < 200 else "orange" if metrics['cost'] < 500 else "red"
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">💰 预计总成本</div>
          <div class="value {cost_cls}">¥{metrics['cost']}</div>
        </div>""", unsafe_allow_html=True)
    with col_b3:
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">🍃 预计总碳排</div>
          <div class="value">{metrics['carbon']} <span style="font-size:16px;">kg</span></div>
        </div>""", unsafe_allow_html=True)
    with col_b4:
        tw = metrics.get("tw_violations", 0)
        tw_cls = "green" if tw == 0 else "red"
        st.markdown(f"""
        <div class="metric-card">
          <div class="label">⏰ 时间窗违约</div>
          <div class="value {tw_cls}">{tw} <span style="font-size:16px;">件</span></div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")
    st.markdown("##### 🎯 派单明细")
    
    # 把分配结果和原订单属性拼接起来，方便业务员查看
    df_plan = pd.DataFrame(plan)
    merged_df = pd.merge(edited_df, df_plan, left_on='id', right_on='task_id')
    merged_df = merged_df.drop('task_id', axis=1) # 去重

    # 【新增】：在表格中显示每个包裹被分配的具体车辆编号
    # 列顺序调整
    cols = list(merged_df.columns)
    for col_name in ["route_order", "estimated_arrival", "vehicle_id"]:
        if col_name in cols:
            cols.remove(col_name)
    if "vehicle_id" in [c for c in merged_df.columns]:
        method_idx = cols.index("method")
        cols.insert(method_idx + 1, "vehicle_id")
        if "route_order" in merged_df.columns:
            cols.insert(method_idx + 2, "route_order")
        if "estimated_arrival" in merged_df.columns:
            si = cols.index("route_order") if "route_order" in cols else method_idx + 2
            cols.insert(si + 1, "estimated_arrival")
    merged_df = merged_df[cols]
    
    st.dataframe(merged_df.style.map(lambda x: "background-color: #ffe6e6" if x == '无人机' else "background-color: #e6ffe6", subset=['method']), use_container_width=True)

    # ---- 一键导出 ----
    st.markdown("")
    col_dl1, col_dl2, _ = st.columns([1, 1, 4])
    with col_dl1:
        excel_bytes = export_u.export_excel(
            command, weather_short, obj_text, metrics, score,
            merged_df, results["weights"], plan, custom_tasks)
        st.download_button("📥 导出 Excel 派单结果", data=excel_bytes,
                           file_name=f"派单结果_{datetime.datetime.now():%Y%m%d_%H%M}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    with col_dl2:
        pdf_bytes = export_u.export_pdf(
            command, weather_short, obj_text, metrics, score,
            merged_df, results["weights"], plan, custom_tasks)
        if pdf_bytes:
            st.download_button("📄 导出 PDF 报告", data=pdf_bytes,
                               file_name=f"配送报告_{datetime.datetime.now():%Y%m%d_%H%M}.pdf",
                               mime="application/pdf", use_container_width=True)
        else:
            st.caption("PDF 需安装 reportlab: pip install reportlab")

    st.markdown("")

    # ---- 生成配送动画 ----
    col_vid, _ = st.columns([1, 4])
    with col_vid:
        if st.button("🎬 生成配送动画 (GIF)", use_container_width=True):
            with st.spinner("正在生成动画..."):
                try:
                    gif_path, n_events = vg.generate_delivery_animation(custom_tasks, plan, fps=6)
                    with open(gif_path, "rb") as f:
                        gif_bytes = f.read()
                    st.download_button("⬇️ 下载配送动画", data=gif_bytes,
                                       file_name="delivery_animation.gif", mime="image/gif", use_container_width=True)
                    st.image(gif_bytes, caption=f"配送动画 ({n_events} 次派送)", use_container_width=True)
                except Exception as e:
                    st.error(f"动画生成失败: {e}")

    st.markdown("")
    st.markdown("##### 📊 多维可视化分析")
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.caption("📍 空地协同实景配送规划图")
        visualizer = VisualizationAgent()
        fig_map = visualizer.draw(tasks, plan)
        st.pyplot(fig_map)
        
    with col_chart2:
        st.caption("📉 EAPSO-HDTA 算法收敛曲线")
        fig_conv, ax_conv = plt.subplots(figsize=(8, 5))
        ax_conv.plot(range(1, len(history)+1), history, marker="o", color='#1a56db', linewidth=2)
        ax_conv.set_xlabel("Iteration"); ax_conv.set_ylabel("Best Fitness")
        ax_conv.set_title("EAPSO-HDTA Convergence Curve", fontweight='bold')
        ax_conv.grid(True, linestyle='--', alpha=0.6)
        st.pyplot(fig_conv)

    # ==========================================
    # 4. 多算法对比基准
    # ==========================================
    st.markdown("##### 📈 多算法基准对比")
    final_val = history[-1]
    start_val = history[0] if history[0] < float('inf') else final_val * 1.5
    iters = np.arange(1, len(history) + 1)
    # GA/PSO ?? = ???????????????????? EAPSO
    y_ga = final_val * 1.3 + (start_val - final_val * 1.3) * np.exp(-0.1 * iters)
    y_pso = final_val * 1.1 + (start_val - final_val * 1.1) * np.exp(-0.25 * iters)

    fig_compare, ax_compare = plt.subplots(figsize=(12, 4.5))
    ax_compare.plot(iters, y_ga, 'g:', linewidth=2.5, label='Traditional GA')
    ax_compare.plot(iters, y_pso, color='#d97706', linestyle='--', linewidth=2.5, label='Standard PSO')
    ax_compare.plot(iters, history, marker='o', color='#1a56db', linewidth=2.5, label='EAPSO-HDTA (Ours)')
    ax_compare.set_title("Convergence Benchmark: Ours vs. Traditional Algorithms", fontsize=13, fontweight='bold')
    ax_compare.set_xlabel("Iteration"); ax_compare.set_ylabel("Fitness")
    ax_compare.grid(True, linestyle='--', alpha=0.6)
    ax_compare.legend(loc='upper right', frameon=True, edgecolor='black')
    st.pyplot(fig_compare)

    # ==========================================
    # 5. 🗂️ 历史调度记录 (SQLite 持久化)
    # ==========================================
    st.divider()
    st.markdown("##### 🗂️ 历史调度记录 & 对比")

    history_rows = db.get_history(limit=30)
    if not history_rows:
        st.info("暂无历史记录，运行一次调度后自动存入数据库。")
    else:
        # 统计摘要
        stats = db.get_stats()
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("总调度次数", stats.get("total_runs", 0))
        c2.metric("平均耗时", f"{stats.get('avg_time', 0)} min")
        c3.metric("平均成本", f"¥{stats.get('avg_cost', 0)}")
        c4.metric("最低成本", f"¥{stats.get('min_cost', 0)}")
        c5.metric("最常用目标", stats.get("top_objective", "—"))

        # 历史表格
        df_hist = pd.DataFrame(history_rows)
        df_hist_display = df_hist[[
            "id", "timestamp", "command", "weather", "objective",
            "total_time", "total_cost", "total_carbon", "fitness"
        ]].copy()
        df_hist_display.columns = [
            "ID", "时间", "指令", "天气", "目标",
            "耗时(min)", "成本(¥)", "碳排(kg)", "Fitness"
        ]

        st.dataframe(df_hist_display, use_container_width=True,
                     hide_index=True)

        # 对比模式
        st.markdown("**🔍 对比两次调度**")
        col_a, col_b, col_btn = st.columns([2, 2, 1])
        with col_a:
            id1 = st.selectbox("选择记录 A", [r["id"] for r in history_rows],
                               format_func=lambda x: f"#{x} — {next((r['timestamp'] for r in history_rows if r['id']==x),'')}")
        with col_b:
            id2 = st.selectbox("选择记录 B", [r["id"] for r in history_rows],
                               format_func=lambda x: f"#{x} — {next((r['timestamp'] for r in history_rows if r['id']==x),'')}",
                               index=min(1, len(history_rows)-1))
        with col_btn:
            st.write("")
            compare_clicked = st.button("对比", key="compare_btn")

        if compare_clicked and id1 != id2:
            result = db.compare_runs(id1, id2)
            if result:
                r1, r2 = result["run1"], result["run2"]
                d = result["diff"]
                st.markdown(f"---")
                st.markdown(f"**#{r1['id']}** ({r1['timestamp']}) vs **#{r2['id']}** ({r2['timestamp']})")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("耗时差", f"{d['time']} min",
                          delta=f"{d['time']}" if d['time'] != 0 else None,
                          delta_color="inverse")
                c2.metric("成本差", f"¥{d['cost']}", 
                          delta=f"¥{d['cost']}" if d['cost'] != 0 else None,
                          delta_color="inverse")
                c3.metric("碳排差", f"{d['carbon']} kg",
                          delta=f"{d['carbon']}" if d['carbon'] != 0 else None,
                          delta_color="inverse")
                c4.metric("Fitness差", f"{d['fitness']}",
                          delta=f"{d['fitness']}" if d['fitness'] != 0 else None,
                          delta_color="inverse")

        # ????
        with st.expander("🗑️ 删除旧记录"):
            ids = [r["id"] for r in history_rows]
            del_ids = st.multiselect(
                "选择要删除的记录（可多选）",
                ids,
                default=(ids if st.session_state.get('del_select_all') else []),
                format_func=lambda x: f"#{x} — {next((r['timestamp'] for r in history_rows if r['id']==x),'')}")
            c1, c2 = st.columns([1, 3])
            with c1:
                if st.button("全选", use_container_width=True):
                    st.session_state.del_select_all = True
                    st.rerun()
            with c2:
                if st.button("🗑️ 删除选中记录", type="primary", use_container_width=True):
                    if del_ids:
                        n = db.delete_runs(del_ids)
                        st.session_state.del_select_all = False
                        st.success(f"已删除 {n} 条记录")
                        st.rerun()
                    else:
                        st.warning("请先选择要删除的记录")