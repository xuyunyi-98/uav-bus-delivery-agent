"""
农村配送任务生成模块

作用：
模拟农村配送任务点
"""

import random


def generate_tasks(num_tasks):
    """
    生成配送任务

    参数:
    num_tasks:
        任务数量

    返回:
    tasks:
        任务列表
    """


    tasks = []


    for i in range(num_tasks):

        task = {

            # 任务编号
            "id": i + 1,


            # 农村区域坐标
            "x": random.randint(0, 100),

            "y": random.randint(0, 100),


            # 货物重量 kg
            "weight": random.randint(1, 10)

        }


        tasks.append(task)


    return tasks