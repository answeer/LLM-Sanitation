# Import Guard and Validator
from guardrails import Guard
from guardrails.hub import EndsWith

# Setup Guard
guard = Guard().use(EndsWith, end="a", on_fail="exception")

response = guard.validate("Llama")  # Validator passes

try:
    response = guard.validate("Mistral")  # Validator fails
except Exception as e:
    print(e)
