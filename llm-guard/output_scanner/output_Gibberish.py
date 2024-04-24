from llm_guard.output_scanners import Gibberish
from llm_guard.output_scanners.gibberish import MatchType

scanner = Gibberish(match_type=MatchType.FULL)

model_output = "This is a test prompt containing some gibberish text asfdkjahf askldfhlaskdf."
sanitized_output, is_valid, risk_score = scanner.scan("", model_output)

print("Sanitized output:", sanitized_output)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)