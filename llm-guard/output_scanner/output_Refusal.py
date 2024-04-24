from llm_guard.output_scanners import NoRefusal
from llm_guard.output_scanners.no_refusal import MatchType

scanner = NoRefusal(threshold=0.5, match_type=MatchType.FULL)

model_output = """
I can't assist with any illegal activities, including fraud or any form of deception to obtain money. 
If you have any legal financial needs or other difficulties, I'm here to offer constructive advice and support.
"""

sanitized_output, is_valid, risk_score = scanner.scan("", model_output)

print("Sanitized output:", sanitized_output)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)