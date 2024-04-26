from llm_guard.input_scanners import BanCompetitors

# Define a list of competitors
competitors_list = [
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
# Initialize the scanner
scanner = BanCompetitors(competitors=competitors_list, redact=True, threshold=0.3)

# Prepare a test prompt
prompt = """
In the dynamic realm of finance, several prominent entities have emerged as key players,\
leaving an indelible mark on the industry. acorns, a fintech innovator, has revolutionized saving \
and investing with its user-friendly app. citigroup, a multinational investment bank, stands as a \
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

# Scan the prompt using the scanner
sanitized_prompt, is_valid, risk_score = scanner.scan(prompt)

# Print the results
print("Sanitized Prompt:", sanitized_prompt)
print("Is Valid:", is_valid)
print("Risk Score:", risk_score)
