# Import Guard and Validator
from guardrails import Guard
from guardrails.hub import EndpointIsReachable


# Setup Guard
guard = Guard().use(EndpointIsReachable, on_fail="exception")

response = guard.validate("https://www.guardrailsai.com/")  # Validator passes

try:
    response = guard.validate("https://www.guardrailsai.co")  # Validator fails
except Exception as e:
    print(e)