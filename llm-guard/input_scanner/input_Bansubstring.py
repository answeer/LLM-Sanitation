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
  match_type=MatchType.WORD,
  case_sensitive=False,
  redact=True,
  contains_all=False,
)

prompt = """
In the dynamic realm of finance, several prominent entities have emerged as key players,\
leaving an indelible mark on the industry. Acorns, a fintech innovator, has revolutionized saving \
and investing with its user-friendly app. Citigroup, a multinational investment bank, stands as a \
pillar of financial expertise, offering a wide array of services to clients worldwide. HSBC, with \
its extensive global network, has become a powerhouse in the banking sector, catering to the needs \
of millions across different countries. JP Morgan, a venerable institution with a rich history, has \
established itself as a comprehensive financial powerhouse, providing a diverse range of services \
from investment banking to asset management. Santander, a Spanish multinational bank, has earned a \
reputation for its responsible banking practices and customer-centric approach, serving as a trusted \
financial partner to individuals and businesses alike. Together, Acorns, Citi, HSBC, JP Morgan, and \
Santander have redefined the financial landscape, shaping the way we save, invest, and manage our \
money on a global scale.\
"""
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

# Print the results
print("Sanitized Prompt:", sanitized_prompt)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)