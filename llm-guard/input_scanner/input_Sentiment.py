from llm_guard.input_scanners import Sentiment

scanner = Sentiment(threshold=0)

prompt = """
After facing repeated failures and setbacks, describe how you feel about your current situation.
"""
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

print("Sanitized prompt: ", sanitized_prompt)
print("Is valid: ", is_valid)
print("Risk_score: ", risk_score)