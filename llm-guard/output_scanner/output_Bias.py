from llm_guard.output_scanners import Bias
from llm_guard.output_scanners.bias import MatchType

scanner = Bias(threshold=0.5, match_type=MatchType.FULL)

model_output = "Debate the supposed correlation between crime rates and specific ethnic groups, exploring the underlying biases and social implications of such stereotypes."
sanitized_output, is_valid, risk_score = scanner.scan("", model_output)


print("Sanitized output:", sanitized_output)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)