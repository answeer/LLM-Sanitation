from llm_guard.output_scanners import Toxicity
from llm_guard.output_scanners.toxicity import MatchType

scanner = Toxicity(threshold=0.5, match_type=MatchType.SENTENCE)

model_output = " Please look carefully. You are a stupid idiot who can't do anything right."
sanitized_output, is_valid, risk_score = scanner.scan("", model_output)

print("Sanitized output:", sanitized_output)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)