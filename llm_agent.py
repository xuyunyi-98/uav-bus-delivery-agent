"""
DeepSeek任务理解智能体
"""
from openai import OpenAI
import json
import config

class LLMTaskAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=config.API_KEY,
            base_url=config.BASE_URL
        )

    def parse(self, command):
        prompt = f"""
        你是农村公交-无人机协同配送智能体。
        请理解用户配送需求，并提取以下信息：
        1. 配送任务数量 task_num
        2. 无人机数量 uav_num
        3. 公交车辆数量 bus_num
        4. 优化目标 objective

        用户需求：
        {command}

        请严格返回JSON格式：
        {{
        "task_num":5,
        "uav_num":3,
        "bus_num":2,
        "objective":"成本最低"
        }}
        不要输出其他文字。
        """

        try:
            response = self.client.chat.completions.create(
                model=config.MODEL,
                messages=[{"role":"user", "content":prompt}],
                temperature=0.1
            )
            result_text = response.choices[0].message.content
            
            # 清理Markdown代码块标记
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            result = json.loads(result_text)
        except Exception as e:
            print(f"DeepSeek解析失败 ({e})，使用默认参数")
            result = {
                "task_num": 5,
                "uav_num": 3,
                "bus_num": 2,
                "objective": "综合优化"
            }
        return result