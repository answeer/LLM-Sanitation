# Import Guard and Validator
from guardrails.hub import ValidChoices
from guardrails import Guard

# Use the Guard with the validator
guard = Guard().use(
    ValidChoices, choices=["OpenAI", "Anthropic", "Cohere"], on_fail="exception"
)

# Test passing response
guard.validate("OpenAI")

try:
    # Test failing response
    guard.validate("Google")
except Exception as e:
    print(e)
