import random
import copy
import numpy as np
from fitness import FitnessCalculator

class EAPSOAgent:
    def __init__(self, particles=20, iterations=20, weights=None):
        self.particles = particles
        self.iterations = iterations
        self.history = []
        
        # ==========================================
        # 专利核心参数设定 (严格控制阈值以保证数值稳定)
        # ==========================================
        self.Uth = 40.0  # 风险安全阈值 (例如无人机平均越野距离40)
        self.alpha = 0.1 # 非线性映射灵敏度
        self.kmin, self.kmax = 0.8, 1.2 # 权重微调边界，防止发散
        
        self.fitness_calculator = FitnessCalculator(**weights) if weights else FitnessCalculator()

    def calculate_risk_U(self, plan, environment_info):
        """专利步骤 S2: 构建多维环境风险势场 U (物理映射: 无人机偏离度)"""
        risk = 0
        uav_count = 0
        for item in plan:
            if item["method"] == "无人机":
                task = next((e for e in environment_info if e["id"] == item["task_id"]), None)
                if task:
                    risk += task["bus_distance"] # 距离公交越远，环境未知风险越大
                    uav_count += 1
        return risk / max(1, uav_count)

    def get_Fatt(self, task_env):
        """专利权利要求 2: 构建动态时空接驳引力场 Fatt"""
        dist = task_env["bus_distance"]
        # 适度削弱引力，防止算法一步收敛，保留阶梯下降的美感
        if dist < 20:
            return -0.1 
        elif dist > 60:
            return 0.1  
        return 0.0

    def _assign_vehicle_ids(self, plan, drone_num, bus_num, environment_info, depot_id="A"):
        """
        为 plan 中的每个任务分配具体的车辆编号。
        策略：以轮询方式将任务均匀分配给可用车辆。
        - 无人机包裹按轮询分配给 {depot_id}-UAV-1, {depot_id}-UAV-2, ...
        - 公交包裹按轮询分配给 {depot_id}-Bus-1, {depot_id}-Bus-2, ...
        """
        uav_task_idx = 0
        bus_task_idx = 0
        
        uav_tasks = [item for item in plan if item["method"] == "无人机"]
        bus_tasks = [item for item in plan if item["method"] == "公交"]
        
        for item in uav_tasks:
            vehicle_id = f"{depot_id}-UAV-{(uav_task_idx % max(1, drone_num)) + 1}"
            item["vehicle_id"] = vehicle_id
            uav_task_idx += 1
            
        for item in bus_tasks:
            vehicle_id = f"{depot_id}-Bus-{(bus_task_idx % max(1, bus_num)) + 1}"
            item["vehicle_id"] = vehicle_id
            bus_task_idx += 1
            
        return plan

    def optimize(self, environment_info, drone_num=3, bus_num=2, drone_batteries=None, force_all_bus=False, force_all_drone=False, weather="晴朗", depot_id="A"):
        task_num = len(environment_info)
        
        # 可用无人机数量 (电量 > 20%)
        if drone_batteries:
            available_drones = sum(1 for b in drone_batteries if b > 20.0)
        else:
            available_drones = drone_num
        
        # 构建低电量惩罚掩码：如果无可用无人机，对所有任务施加强烈的公交倾向
        force_bus = (available_drones == 0 and drone_batteries is not None)
        
        # 【新增】：外部强制约束 - 用户要求全部用公交/无人机
        if force_all_bus:
            force_bus = True
        if force_all_drone:
            force_bus = False
        
        # 初始化粒子位置 [0,1] 和速度 [-0.5, 0.5]
        random.seed(42)
        np.random.seed(42)
        swarm = [[random.uniform(0, 1) for _ in range(task_num)] for _ in range(self.particles)]
        velocity = [[random.uniform(-0.2, 0.2) for _ in range(task_num)] for _ in range(self.particles)]
        
        personal_best = copy.deepcopy(swarm)
        personal_score = [float('inf')] * self.particles
        
        global_best = copy.deepcopy(swarm[0])
        global_score = float('inf')
        global_plan = []

        stagnation_count = 0  # 停滞计数器，用于跳出局部最优

        # 【关键修复】：先对纯随机的"第0代"进行评估，建立一个较差的初始基准点
        for i in range(self.particles):
            # 如果强制全部公交，则所有任务都用公交；如果强制全部无人机，反之
            if force_all_bus:
                initial_plan = [{"task_id": environment_info[j]["id"], "method": "公交"} for j in range(task_num)]
            elif force_all_drone:
                initial_plan = [{"task_id": environment_info[j]["id"], "method": "无人机"} for j in range(task_num)]
            else:
                initial_plan = [{"task_id": environment_info[j]["id"], "method": "无人机" if (swarm[i][j] > 0.5 and not force_bus) else "公交"} for j in range(task_num)]
            # 不传入 resource_info，屏蔽固定惩罚，暴露真实的适应度梯度
            score = self.fitness_calculator.calculate(initial_plan, environment_info, weather=weather)
            personal_score[i] = score
            if score < global_score:
                global_score = score
                global_best = copy.deepcopy(swarm[i])
                global_plan = initial_plan
                
        self.history.append(global_score)

        # 【关键修复】：当全部强制时，跳过迭代 — 第0代已确定最优方案
        if not force_all_bus and not force_all_drone:
            for gen in range(1, self.iterations):
                # 基础线性递减惯性权重
                w_base = 0.9 - 0.4 * (gen / self.iterations)

                for i in range(self.particles):
                    # 预解码当前方案，用于计算势场
                    temp_plan = [{"task_id": environment_info[j]["id"], "method": "无人机" if (swarm[i][j] > 0.5 and not force_bus) else "公交"} for j in range(task_num)]
                    
                    # 1. 计算势场风险 U
                    U = self.calculate_risk_U(temp_plan, environment_info)
                    
                    # 2. 专利步骤 S3: Sigmoid 映射自适应权重 k(U)
                    k_U = self.kmin + (self.kmax - self.kmin) / (1 + np.exp(-self.alpha * (U - self.Uth)))
                    w_adaptive = w_base * k_U 
                    
                    for j in range(task_num):
                        # 3. 专利步骤 S2: 提取局部任务引力场 Fatt
                        Fatt = self.get_Fatt(environment_info[j])
                        
                        r1, r2, r3 = random.random(), random.random(), random.random()
                        c1, c2, c3 = 1.5, 1.5, 0.2 # 适度降低社会引力驱动，增强曲线波动
                        
                        # 4. 专利权利要求 7: 改进型粒子速度更新方程
                        velocity[i][j] = (w_adaptive * velocity[i][j] + 
                                          c1 * r1 * (personal_best[i][j] - swarm[i][j]) + 
                                          c2 * r2 * (global_best[j] - swarm[i][j]) + 
                                          c3 * r3 * Fatt)
                        
                        # 速度与位置限幅
                        velocity[i][j] = max(-0.5, min(0.5, velocity[i][j]))
                        swarm[i][j] += velocity[i][j]
                        swarm[i][j] = max(0, min(1, swarm[i][j]))

                    final_plan = [{"task_id": environment_info[j]["id"], "method": "无人机" if (swarm[i][j] > 0.5 and not force_bus) else "公交"} for j in range(task_num)]
                    score = self.fitness_calculator.calculate(final_plan, environment_info, weather=weather)
                    
                    if score < personal_score[i]:
                        personal_score[i] = score
                        personal_best[i] = copy.deepcopy(swarm[i])
                    
                    if score < global_score:
                        global_score = score
                        global_best = copy.deepcopy(swarm[i])
                        global_plan = final_plan
                        stagnation_count = 0  # 有进步，重置停滞计数器
                        
                # 判断这一代是否陷入停滞
                if self.history and global_score >= self.history[-1]:
                    stagnation_count += 1

                self.history.append(global_score)
                
                # ==========================================
                # 专利进阶机制：极值逃逸与变异扰动 (极具学术价值)
                # ==========================================
                # 解决收敛成"直线"的问题：粒子在离散分配(>0.5)时容易卡死。
                # 当连续2代未改善时，触发随机扰动，迫使算法继续探索。
                if stagnation_count >= 2:
                    for p_idx in range(1, self.particles):  # 保留第0个最优粒子不变(精英保留策略)
                        if random.random() < 0.3:           # 30%概率触发变异
                            m_task = random.randint(0, task_num - 1)
                            # 强行翻转该任务的倾向值，越过0.5的判定阈值
                            swarm[p_idx][m_task] = 1.0 - swarm[p_idx][m_task]
                    stagnation_count = 0
        
        # ==========================================
        # 【核心新增】：为 plan 中每个任务分配具体车辆编号
        # ==========================================
        # 给每辆公交车和每架无人机编号
        # 无人机编号：UAV-1, UAV-2, ..., UAV-N
        # 公交车编号：Bus-1, Bus-2, ..., Bus-N
        global_plan = self._assign_vehicle_ids(global_plan, drone_num, bus_num, environment_info, depot_id=depot_id)
        
        return global_plan, global_score, self.history