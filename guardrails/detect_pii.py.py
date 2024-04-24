# Import the guardrails package
import guardrails as gd
from guardrails.validators import PIIFilter
from rich import print

# Create Guard object with this validator
# One can specify either pre-defined set of PII or SPI (Sensitive Personal Information) entities by passing in the `pii` or `spi` argument respectively.
# It can be passed either durring intialization or later through the metadata argument in parse method.

# One can also pass in a list of entities supported by Presidio to the `pii_entities` argument.
guard = gd.Guard.from_string(
    validators=[PIIFilter(pii_entities="pii", on_fail="fix")],
    description="testmeout",
)

# Parse the text
text = "My email address is demo@lol.com, and my phone number is 1234567890"
output = guard.parse(
    llm_output=text,
)

# Print the output
print(output)