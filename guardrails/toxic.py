# Import Guard and Validator
from guardrails.hub import ToxicLanguage
from guardrails import Guard

# Use the Guard with the validator
guard = Guard().use(
    ToxicLanguage, threshold=0.5, validation_method="sentence", on_fail="fix"
)

# # Test passing response
# guard.validate("Love how you think and attack the problem. Great job!")

# try:
#     # Test failing response
#     guard.validate(
#         "Please look carefully. You are a stupid idiot who can't do anything right."
#     )
# except Exception as e:
#     print(e)

text = "Please look carefully. You are a stupid idiot who can't do anything right."

raw_llm_output,validated_output, _, validation_passed, *rest= guard.parse(
    llm_output=text,
    metadata={},
)

print("raw_llm_output: ",raw_llm_output)
print("validated_output: ",validated_output)
print("validation_passed: ",validation_passed)

