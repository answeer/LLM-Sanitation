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
  redact=False,
  contains_all=False,
)

prompt = """
We are considering different investment options. Some popular choices include Acorns, Fidelity, and JP Morgan Chase.
"""
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)