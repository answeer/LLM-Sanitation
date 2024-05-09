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
text = """
Hello, my name is David Johnson and I live in Maine.
My credit card number is 4095-2609-9393-4932 and my crypto wallet id is 16Yeky6GMjeNkAiNcBY7ZhrLoMSgg1BoyZ.

On September 18 I visited microsoft.com and sent an email to test@presidio.site,  from the IP 192.168.0.1.

My passport: 191280342 and my phone number: (212) 555-1234.

This is a valid International Bank Account Number: IL150120690000003111111 . Can you please check the status on bank account 954567876544?

Kate's social security number is 078-05-1126.  Her driver license? it is 1234567A.
"""
output = guard.parse(
    llm_output=text,
)

# Print the output
print(output)   