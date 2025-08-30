from llm_chat import test_llm # 导入 LLM 查询模块
from dotenv import load_dotenv
import os

class ComplianceBulletinAgent:
    def __init__(self, updated_sections, model_name, endpoint, key):
        """
        初始化代理，接受提取好的更新内容
        updated_sections: dict, 包含 "new"、"advanced"、"removed" 三个类别的变化
        model_name: LLM 模型名称
        endpoint: LLM 端点
        key: LLM API 密钥
        """
        # 将所有变化合并为一个列表
        self.all_changes = []
        for category, changes in updated_sections.items():
            for change in changes:
                self.all_changes.append(f"{category.capitalize()}: {change}")

        self.model_name = model_name
        self.endpoint = endpoint
        self.key = key

    def identify_responsible_team_with_llm(self, changes):
        """
        使用LLM来识别负责团队
        """
        # 将所有变化描述拼接成一个字符串传给 LLM
        prompt = f"Given the following changes:\n{changes}\nIdentify the responsible team from the following teams:\n"
        prompt += "1. Fraud & Risk Management Team\n"
        prompt += "2. Dispute & Chargeback Operations Team\n"
        prompt += "3. Compliance & Regulatory Affairs\n"
        prompt += "4. IT & Technology / Core Banking Systems\n"
        prompt += "5. Payments Operations / Transaction Processing\n"
        prompt += "6. Interchange & Fees / Finance Team\n"
        prompt += "7. Merchant Acquiring / Partnerships\n"
        prompt += "8. Card Product & Business Team\n"
        prompt += "9. Information Security / Cybersecurity\n"
        prompt += "10. Legal Department\n"
        prompt += "11. Customer Service / Contact Center\n"
        prompt += "12. Audit & Risk Oversight\n"
        prompt += "Please return only the name of the responsible team."

        # 调用 LLM 查询
        team = test_llm(self.model_name, prompt, self.endpoint, self.key)
        return team.strip() if team else "Unknown Team"

    def create_task_with_llm(self, changes, responsible_team):
        """
        使用LLM生成任务，并包含高层任务描述、Definition of Ready 和 Definition of Done
        """
        prompt = f"Create a task for the following changes: '{changes}'. The task should include: \n"
        prompt += "- High-level task description\n"
        prompt += "- Definition of Ready\n"
        prompt += "- Definition of Done\n"
        prompt += f"Assign this task to the '{responsible_team}' team."

        # 调用 LLM 查询生成任务
        task = test_llm(self.model_name, prompt, self.endpoint, self.key)
        return task.strip() if task else "Failed to generate task"

    def process_bulletin(self):
        """
        处理更新内容，生成任务并识别团队
        """
        tasks = []
        
        # 合并所有变化为一个字符串
        changes_str = "\n".join(self.all_changes)
        
        # 识别负责团队
        team = self.identify_responsible_team_with_llm(changes_str)

        # 生成任务
        task = self.create_task_with_llm(changes_str, team)
        tasks.append({
            'changes': changes_str,
            'task': task,
            'responsible_team': team # 记录责任团队
        })

        # 输出结果
        print("Responsible Team:", team)
        print("\nGenerated Task:")
        for task in tasks:
            print(f"Changes: {task['changes']}")
            print(f"Task: {task['task']}")

        return tasks


# 假设更新部分已经由同事提取好了
updated_sections = {
    "new": [
        "Contactless biometric rule, reduced dispute response time."
    ],
    "advanced": [
        "Subscription cancellation requirement from advisory → mandatory."
    ],
    "removed": [
        "Reason code 4530 is no longer valid."
    ]
}

# LLM 配置信息
model_name = "claude-3-7-sonnet"
endpoint = os.getenv("ai_gateway")
key = os.getenv("hackathon_key")

# 初始化代理并处理
agent = ComplianceBulletinAgent(updated_sections, model_name, endpoint, key)
tasks = agent.process_bulletin()

