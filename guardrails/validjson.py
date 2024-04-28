# Import Guard and Validator
from guardrails.hub import ValidJson
from guardrails import Guard

# Setup Guard
guard = Guard().use(ValidJson, on_fail="exception")

guard.validate('{ "value": "a test value" }')  # Validator passes

try:
    guard.validate(
        '{ "value": "a test value", }'
    )  # Validator fails; note the trailing comma
except Exception as e:
    print(e)
