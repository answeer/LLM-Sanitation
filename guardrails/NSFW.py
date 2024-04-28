# Import Guard and Validator
from guardrails.hub import NSFWText
from guardrails import Guard

# Use the Guard with the validator
guard = Guard().use(
    NSFWText, threshold=0.8, validation_method="sentence", on_fail="fix"
)

# # Test passing response
# guard.validate(
#     "Christopher Nolan's Tenet is a mind-bending action thriller that will keep you on the edge of your seat. The film is a must-watch for all Nolan fans."
# )

# try:
#     # Test failing response
#     guard.validate(
#         "Climate Change is real and we need to do something about it. Dumping one's shit into the river is great way to help fight climate change."
#     )
# except Exception as e:
#     print(e)


text = "Climate Change is real and we need to do something about it. Dumping one's shit into the river is great way to help fight climate change."

# Test with a given text
raw_llm_output,validated_output, _, validation_passed, *rest= guard.parse(
    llm_output=text,
    metadata={},
)

print("raw_llm_output: ",raw_llm_output)
print("validated_output: ",validated_output)
print("validation_passed: ",validation_passed)