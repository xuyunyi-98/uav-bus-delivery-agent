from agent_core import UAVBusAgent

if __name__ == "__main__":
    print("====================================")
    print("农村公交-无人机协同配送智能体 (EAPSO-HDTA)")
    print("====================================")

    command = input("\n请输入配送需求 (例如：帮我调度5个包裹，分配3架无人机和2辆公交)：\n> ")

    agent = UAVBusAgent()
    results = agent.run(command)
    
    print(f"\n调度方案得分: {results['score']}")
    print(f"方案详情: {results['plan']}")
    print(f"电池状态: {results.get('battery_status', 'N/A')}")

    print("\n====================================")
    print("所有流程执行完毕，请前往 results 文件夹查看报告和图表！")
    print("====================================")
