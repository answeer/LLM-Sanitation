from llm_guard.input_scanners import Toxicity
from llm_guard.input_scanners.toxicity import MatchType

scanner = Toxicity(threshold=0.5, match_type=MatchType.SENTENCE)

prompt = """
 Please look carefully. You are a stupid idiot who can't do anything right.
"""
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

print("Sanitized prompt: ", sanitized_prompt)
print("Is valid: ", is_valid)
print("Risk_score: ", risk_score)