# Import Guard and Validator
from guardrails.hub import FinancialTone
from guardrails import Guard

# Use the Guard with the validator
guard = Guard().use(FinancialTone, on_fail="exception")

# Test passing response
guard.validate(
    "Growth is strong and we have plenty of liquidity.",
    metadata={"financial_tone": "positive"}
)

try:
    # Test failing response
    guard.validate(
        "There are doubts about our finances, and we are struggling to stay afloat.",
        metadata={"financial_tone": "positive"}
    )
except Exception as e:
    print(e)