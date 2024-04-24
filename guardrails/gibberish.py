# Import Guard and Validator
from guardrails.hub import GibberishText
from guardrails import Guard

# Use the Guard with the validator
guard = Guard().use(
    GibberishText, threshold=0.5, validation_method="sentence", on_fail="fix"
)

# Test passing response
guard.validate(
    "Azure is a cloud computing service created by Microsoft. It's a significant competitor to AWS."
)

try:
    # Test failing response
    guard.validate(
        "Floppyland love great coffee okay. Fox fox fox. Move to New York City."
    )
except Exception as e:
    print(e)


text = """
Floppyland love great coffee okay. Fox fox fox. Move to New York City.\
"""
output = guard.parse(
    llm_output=text,
    metadata={},
)

print(output)