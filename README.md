# 🚁 农村公交-无人机协同配送智能体

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Web%20App-red)](https://streamlit.io/)
[![LLM Agent](https://img.shields.io/badge/LLM-DeepSeek-green)](https://www.deepseek.com/)
[![SQLite](https://img.shields.io/badge/DB-SQLite-lightgrey)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

让运筹优化算法通过自然语言交互落地，解决农村“最后一公里”配送难题。

> 🎬 **演示视频**：<https://pan.quark.cn/s/b0a8a1e35473>
> （点击链接即可在线观看演示，若无法预览请登录夸克网盘账号）


---

## ✨ 核心亮点

### 🏓 学术与算法背书 (Academic Foundation)

本项目并非一个普通的业务系统。其底层的 **EAPSO-HDTA** 调度算法与多智能体协同机制，均基于开发者的个人学术专利与发表论文。系统成功将理论层面的运筹优化算法，通过大模型（LLM）转化为可自然语言交互的落地应用。

四个核心创新点：

1. **改进型粒子群优化（EAPSO）**：在标准 PSO 基础上引入多维风险势场 U、时空引力场 Fatt、Sigmoid 非线性自适应权重与极值逃逸变异机制，有效避免局部最优。
2. **多仓库多智能体协同**：支持多个配送中心独立调度，贪心分仓 + 车辆编号 + TSP 路径规划 + 时间窗约束。
3. **LLM 自然语言落地**：通过 DeepSeek 大模型将人类指令解析为可量化的权重映射，实现“说人话就能调度”。
4. **多维度适应度评价**：时间 + 成本 + 碳排 + 天气 + 加急 + 超重 + 时间窗，七维综合寻优。

---

## 🚀 核心功能特性

### 🧠 智能意图解析
- 中文自然语言指令理解（DeepSeek LLM）
- 优化目标自动识别：成本最低 / 时间最短 / 碳排最低 / 多目标平衡
- 强制约束识别：“全部用公交”“所有用无人机”等
- 空指令保护：无输入时自动回退平衡模式

### 📦 订单数据管理
- Excel 文件一键导入（支持 .xlsx/.xls）
- 在线可视化编辑（双击修改、增删行）
- 超重（>10kg）自动拦截，分配公交
- 加急件 / 时间窗（deadline）属性支持

### 📈 EAPSO-HDTA 核心算法
- 改进粒子群优化（自适应惯性权重）
- 多维风险势场 U + 时空引力场 Fatt
- Sigmoid 非线性权重映射
- 极值逃逸变异 + 精英保留策略
- 固定随机种子，结果可复现

### 🎯 多目标适应度评价
- 时间 + 成本 + 碳排三维加权
- 加急件、超重、时间窗三种惩罚机制
- 天气影响因子（大风、阵雨）

### 🌍 配送环境建模
- 多仓库支持（城关镇 + 青山乡）
- 多公交线路 + 换乘站
- 无人机电量管理

### 🚚 车辆调度与编号
- 车辆编号分配（A-UAV-1, B-Bus-1）
- TSP 路径规划（贪心最近邻）
- 轮询负载均衡

### 📊 可视化分析
- 配送规划图（多仓库、换乘站标注）
- 收敛曲线 + 多算法基准对比
- 配送过程 GIF 动画

### 💾 数据持久化
- SQLite 存储历史调度记录
- 历史对比 + 多选删除

### 📤 导出与报告
- 一键导出 Excel 派单结果
- 一键导出 PDF 调度报告
- 配送动画 GIF 生成与下载

---
## 🏗️ 系统架构图


![系统架构图](architecture2.png)

```
用户自然语言指令
        ↓
DeepSeek LLM 意图解析
        ↓
权重自适应映射
        ↓
EAPSO-HDTA 多仓库寻优
        ↓
TSP 路径 + 时间窗检查
        ↓
可视化 + 导出 + 持久化
```

---

## 📁 项目目录结构

```
UAV_Bus_Agent/
├─ app.py                  # Streamlit Web 界面（主入口）
├─ agent_core.py            # 智能体调度中枢（多仓库编排）
├─ eapso_agent.py           # EAPSO-HDTA 核心算法
├─ fitness.py               # 多目标适应度评价
├─ environment.py           # 配送环境建模（多仓库、多公交线）
├─ routing.py               # TSP 路径规划 + 时间窗检查
├─ llm_agent.py             # DeepSeek LLM 意图解析
├─ visualization.py         # 配送规划图可视化
├─ video_generator.py       # 配送动画 GIF 生成
├─ database.py              # SQLite 持久化
├─ export_utils.py          # Excel / PDF 导出
├─ task_generator.py        # 任务自动生成
├─ generate_orders_excel.py # 生成 50 条测试订单 Excel
├─ config.py                # API 配置（需填入自己的 Key）
└─ results/                 # 输出图片 / GIF / 报告
```

---
## 🛠️ 技术栈

| 依赖 | 用途 |
|------|------|
| Python 3.8+ | 核心语言 |
| Streamlit | Web 交互界面 |
| DeepSeek API (openai SDK) | LLM 意图解析 |
| NumPy | 数值计算 |
| pandas | 数据处理 |
| Matplotlib | 可视化 + 动画 |
| Pillow | GIF 动画输出 |
| openpyxl | Excel 读写 |
| reportlab | PDF 报告导出 |
| SQLite3 | 历史记录持久化 |

---

## 📦 快速启动

### 1. 安装依赖

```bash
pip install streamlit pandas numpy matplotlib openpyxl reportlab pillow openai
```

### 2. 配置 DeepSeek API Key

编辑 `config.py`，填入你自己的 API Key：

```python
API_KEY = "sk-你的密钥"
BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"
```

⚠️ **安全提醒**：请勿将真实 API Key 提交到公开仓库。建议使用环境变量管理敏感信息。

### 3. 启动应用

```bash
streamlit run app.py
```

---
## 🎬 使用示例

1. **导入订单**：上传 `配送包裹数据_50条.xlsx`，或直接在线编辑
2. **选择天气**：无人机受天气影响（大风成本×3、阵雨时间×2）
3. **输入指令**：例如 “介天天气不好，请重点考虑成本” 或 “所有包裹都用公交车配送”
4. **一键调度**：查看仪表盘、派单明细、规划图、收敛曲线
5. **导出与动画**：下载 Excel / PDF 报告，生成配送动画 GIF

---

## 🗺️ Roadmap

- [x] LLM 意图解析与自然语言调度
- [x] EAPSO-HDTA 核心算法
- [x] 多仓库、多公交线路、换乘站
- [x] TSP 路径规划 + 时间窗约束
- [x] 天气影响因子
- [x] SQLite 持久化 + 历史对比
- [x] Excel/PDF 导出 + GIF 动画
- [ ] 真实地图 API 集成（高德/百度）
- [ ] 仓库可配置化（从 Excel 导入）
- [ ] 多智能体博弈与协商

---

## 📄 License

[MIT License](LICENSE)

## 🙏 致谢

感谢 DeepSeek 提供的大模型 API 支持，以及 Streamlit 社区的优秀工具。
