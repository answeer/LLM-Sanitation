# Import Guard and Validator
from guardrails import Guard
from guardrails.hub import CompetitorCheck


# Generate competitors list
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

# Define some text to test the validator
text = """\
In the dynamic realm of finance, several prominent entities have emerged as key players,\
leaving an indelible mark on the industry. Acorns, a fintech innovator, has revolutionized saving \
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

# Create the Guard with the CompetitorCheck Validator
guard = Guard.from_string(
    validators=[CompetitorCheck(competitors=competitors_list, on_fail="fix")],
    description="testmeout",
)

# Test with a given text
output = guard.parse(
    llm_output=text,
    metadata={},
)

print(output)
