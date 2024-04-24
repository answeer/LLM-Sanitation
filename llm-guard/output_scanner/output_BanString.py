from llm_guard.output_scanners import BanSubstrings
from llm_guard.input_scanners.ban_substrings import MatchType

scanner = BanSubstrings(
  substrings=["forbidden", "unwanted"],
  match_type=MatchType.WORD,
  case_sensitive=False,
  redact=False,
  contains_all=False,
)
prompt = "You are tasked with writing a report on the recent sales performance of our company."
model_output = "The recent sales performance of our company has been forbidden. We have exceeded our targets in multiple regions."
sanitized_output, is_valid, risk_score = scanner.scan(prompt, model_output)

print("Sanitized output:", sanitized_output)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)