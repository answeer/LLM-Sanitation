# Import Guard and Validator
from guardrails import Guard
from guardrails.hub import SecretsPresent

# Setup Guard
guard = Guard().use(SecretsPresent, on_fail="fix")

# response = guard.validate(
#     """
#     def hello():
#         name = "James"
#         age = 25
#         return {"name": name, "age": age}
#     """
# )  # Validator passes

# try:
#     response = guard.validate(
#         """
#         def hello():
#             user_id = "1234"
#             user_pwd = "password1234"
#             user_api_key = "sk-xhdfgtest"
#         """
#     )  # Validator fails
# except Exception as e:
#     print(e)

text = """
def hello():
    user_id = "1234"
    user_pwd = "password1234"
    user_api_key = "sk-xhdfgtest"
"""
# Test with a given text
output = guard.parse(
    llm_output=text,
    metadata={},
)

print(output)