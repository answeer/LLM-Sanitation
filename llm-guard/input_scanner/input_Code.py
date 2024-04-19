from llm_guard.input_scanners import Code

# 初始化扫描器
scanner = Code(languages=["Python"], is_blocked=True)

# 准备测试用的提示
prompt = """
def add(x, y):
    return x + y

result == add(3, 4)
print(result)
"""

# 使用扫描器扫描提示
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

# 输出结果
print("Sanitized Prompt:", sanitized_prompt)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)
