# Import Guard and Validator
from guardrails import Guard
from guardrails.hub import ValidURL

# Setup Guard
guard = Guard().use(ValidURL, on_fail="exception")
response = guard.validate("http://www.google.com")  # Validator passes

try:
    response = guard.validate("http://www.googlea.com")  # Validator fails
except Exception as e:
    print(e)
