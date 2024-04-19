from llm_guard.input_scanners import Secrets

scanner = Secrets()

prompt = """
user_id = "1234"
user_pwd = "password1234"
user_api_key = "sk-xhdfgtest"
"""
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

print("Sanitized prompt: ", sanitized_prompt)
print("Is valid: ", is_valid)
print("Risk_score: ", risk_score)