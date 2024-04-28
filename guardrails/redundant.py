# Import Guard and Validator
from guardrails.hub import RedundantSentences
from guardrails import Guard

# Use the Guard with the validator
guard = Guard().use(RedundantSentences, on_fail="fix")

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
#         OpenAI just released their latest language model, GPT-3. It is the most powerful language model to date. 
#         Also, it's the most powerful language model to date.
#         """
#     )
# except Exception as e:
#     print(e)

text = """
OpenAI just released their latest language model, GPT-3. It is the most powerful language model to date. 
        Also, it's the most powerful language model to date.
"""
output = guard.parse(
    llm_output=text,
    metadata={},
)

print(output)
