# Import Guard and Validator
from guardrails.hub import CorrectLanguage
from guardrails import Guard

# Setup Guard
guard = Guard().use(
    CorrectLanguage(expected_language_iso="en", threshold=0.75,on_fail="fix")
)

guard.validate("Thank you")  # Validator passes
guard.validate("Danke")  # Validator fails


# Parse the text
text = "我的邮箱地址"
output = guard.parse(
    llm_output=text,
)

# Print the output
print(output)