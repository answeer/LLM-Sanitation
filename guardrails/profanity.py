# Import Guard and Validator
from guardrails.hub import ProfanityFree
from guardrails import Guard

# Use the Guard with the validator
guard = Guard().use(ProfanityFree, on_fail="fix")

# # Test passing response
# guard.validate(
#     """
#     Director Denis Villeneuve's Dune is a visually stunning and epic adaptation of the classic science fiction novel.
#     It is reminiscent of the original Star Wars trilogy, with its grand scale and epic storytelling.
#     """
# )

# try:
#     # Test failing response
#     guard.validate(
#         """
#         He is such a dickhead and a fucking idiot.
#         """
#     )
# except Exception as e:
#     print(e)

text = "He is such a dickhead and a fucking idiot."
# Test with a given text
raw_llm_output,validated_output, _, validation_passed, *rest= guard.parse(
    llm_output=text,
    metadata={},
)

print("raw_llm_output: ",raw_llm_output)
print("validated_output: ",validated_output)
print("validation_passed: ",validation_passed)