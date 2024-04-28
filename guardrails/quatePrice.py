from guardrails import Guard
from guardrails.hub import QuotesPrice

# Setup the Guard with the validator
guard = Guard().use(QuotesPrice, on_fail="exception")

# Test passing responses
guard.validate(
    "The new Airpods Max are available at a crazy discount!"
)  # No price present

response = guard.validate(
    "The new Airpods Max are available at a crazy discount! It's only $9.99!",
    metadata={"currency": "GBP"},
)  # Price present in USD, but expected is GBP

# Test failing response
try:
    response = guard.validate(
        "The new Airpods Max are available at a crazy discount! It's only $9.99!",
        metadata={"currency": "USD"},
    )  # Price present in USD and expected is also USD
except Exception as e:
    print(e)
