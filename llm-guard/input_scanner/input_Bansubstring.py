from llm_guard.input_scanners import BanSubstrings
from llm_guard.input_scanners.ban_substrings import MatchType

competitors_names = [
    "Acorns",
    "Citigroup",
    "Citi",
    "Fidelity Investments",
    "Fidelity",
    "JP Morgan Chase and company",
    "JP Morgan",
    "JP Morgan Chase",
    "JPMorgan Chase",
    "Chase" "M1 Finance",
    "Stash Financial Incorporated",
    "Stash",
    "Tastytrade Incorporated",
    "Tastytrade",
    "ZacksTrade",
    "Zacks Trade",
]

scanner = BanSubstrings(
  substrings=competitors_names,
  match_type=MatchType.STR,
  case_sensitive=False,
  redact=True,
  contains_all=False,
)

prompt = """
We are considering different investment options. Some popular choices include Acorns, fidelity, and JP Morgan Chase.
"""
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

# Print the results
print("Sanitized Prompt:", sanitized_prompt)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)