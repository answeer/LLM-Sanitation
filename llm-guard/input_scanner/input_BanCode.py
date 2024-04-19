from llm_guard.input_scanners import BanCode

scanner = BanCode()

prompt = """
def add(x, y):
    return x + y

result = add(3, 4)
print(result)
"""
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)